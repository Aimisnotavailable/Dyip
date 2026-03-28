# controller/driving_controller.py
import threading
import time
import cv2
import math
from settings import WIN_RES
from controller.ar import AR
from controller.gesture_detector import (
    GestureManager,
    PinchDetector,
    TwoFingerUpDetector,
    FistDetector,
    GestureEvent
)
from controller.input_controller import InputController
from scripts.logger import get_logger_info


class DrivingController:
    """
    Hand tracking controller for driving games.
    Maps hand gestures to steering, throttle, brake, and gear shifts.
    """

    def __init__(self, screen_dim=WIN_RES):
        self.W, self.H = screen_dim
        self.ar = AR(screen_dim)
        self.cap = cv2.VideoCapture(0)
        # Set lower resolution for better performance
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.running = True

        # Gesture manager
        self.gesture_manager = GestureManager()
        self.gesture_manager.add_detector(FistDetector('LEFT', hold_frames=3))
        self.gesture_manager.add_detector(FistDetector('RIGHT', hold_frames=3))
        # self.gesture_manager.add_detector(PinchDetector('LEFT', hold_frames=5))
        # self.gesture_manager.add_detector(PinchDetector('RIGHT', hold_frames=5))
        # self.gesture_manager.add_detector(TwoFingerUpDetector('LEFT', hold_frames=5))
        # self.gesture_manager.add_detector(TwoFingerUpDetector('RIGHT', hold_frames=5))

        # Shared data (protected by a lock)
        self.lock = threading.Lock()
        self._raw_left_landmarks = []
        self._raw_right_landmarks = []
        self._left_hand_type = "REAL"
        self._right_hand_type = "REAL"
        self._annotated_frame = None
        self.frame_lock = threading.Lock()

        # Smoothed positions
        self.smooth_left_pos = None
        self.smooth_right_pos = None
        self.ema_alpha = 0.3

        # Control states (updated by update() from main thread)
        self.steering_mode = False
        self.steering_angle = 0.0
        self.throttle = 0.0
        self.brake = 0.0
        self.gear_up = False
        self.gear_down = False

        # Internal flags
        self._left_fist = False
        self._right_fist = False
        self._gear_up_triggered = False
        self._gear_down_triggered = False

        # Debugging
        self.frame_counter = 0
        self.force_fist = False

        # ---- Separate input thread ----
        self.input = InputController()
        self.controls_lock = threading.Lock()
        self._latest_controls = {
            "steering": 0.0,
            "is_steering" : self.steering_mode,
            "throttle": 0.0,
            "brake": 0.0,
            "gear_up": False,
            "gear_down": False
        }
        self.input_running = True
        self.input_thread = threading.Thread(target=self._input_loop, daemon=True)
        self.input_thread.start()
        # ---------------------------------

        get_logger_info('Driving', 'Controller thread starting')
        self.thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self.thread.start()

    # ------------------------------------------------------------------
    # Input thread – sends key presses in the background
    # ------------------------------------------------------------------
    def _input_loop(self):
        while self.input_running:
            with self.controls_lock:
                controls = self._latest_controls.copy()
            self.input.update(controls)
            time.sleep(0.01)

    # ------------------------------------------------------------------
    # Tracking loop (runs in separate thread)
    # ------------------------------------------------------------------
    def _tracking_loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                continue
            frame = cv2.flip(frame, 1)
            ar_data = self.ar.update(frame)

            if ar_data is None:
                continue

            with self.lock:
                self._raw_left_landmarks = ar_data["POSITION_DATA"].get("LEFT", [])
                self._raw_right_landmarks = ar_data["POSITION_DATA"].get("RIGHT", [])
                self._left_hand_type = ar_data["FRAME_TYPE"].get("LEFT", "REAL")
                self._right_hand_type = ar_data["FRAME_TYPE"].get("RIGHT", "REAL")

            annotated = self.ar.get_annotated_frame()
            if annotated is not None:
                with self.frame_lock:
                    self._annotated_frame = annotated

    # ------------------------------------------------------------------
    # Helper: apply EMA smoothing
    # ------------------------------------------------------------------
    def _apply_ema(self, current_smooth, raw_new):
        if not raw_new or len(raw_new) < 21:
            return None
        tip_raw = raw_new[8]
        if current_smooth is None:
            return tip_raw
        new_x = tip_raw[0] * self.ema_alpha + current_smooth[0] * (1 - self.ema_alpha)
        new_y = tip_raw[1] * self.ema_alpha + current_smooth[1] * (1 - self.ema_alpha)
        new_z = tip_raw[2] * self.ema_alpha + current_smooth[2] * (1 - self.ema_alpha)
        return (new_x, new_y, new_z)

    # ------------------------------------------------------------------
    # Steering computation
    # ------------------------------------------------------------------
    def _compute_steering(self, left_pos, right_pos):
        if left_pos is None or right_pos is None:
            return 0.0
        dx = right_pos[0] - left_pos[0]
        dy = right_pos[1] - left_pos[1]
        if abs(dx) < 1e-6:
            return 0.0
        angle = math.atan2(dy, dx)
        steering = angle / (math.pi / 2)
        return max(-1.0, min(1.0, steering))

    # ------------------------------------------------------------------
    # Reset gesture detectors for a given hand (when hand disappears)
    # ------------------------------------------------------------------
    def _reset_hand_gestures(self, hand):
        """Clear internal state of all gesture detectors for one hand."""
        for det in self.gesture_manager.detectors.get(hand, []):
            det.active = False
            det._count = 0
            det._active_frames = 0
            det._hold_emitted = False
            det._value = None

    # ------------------------------------------------------------------
    # Main update (call this every frame from your game loop)
    # ------------------------------------------------------------------
    def update(self, current_time=None):
        if current_time is None:
            current_time = time.time()

        # Copy raw data with lock
        with self.lock:
            left_raw = list(self._raw_left_landmarks)
            right_raw = list(self._raw_right_landmarks)
            left_type = self._left_hand_type
            right_type = self._right_hand_type

        # Build landmark tuples for gesture detection (real + ghost)
        left_tuples = [(p[0], p[1], p[2]) for p in left_raw] if left_raw else []
        right_tuples = [(p[0], p[1], p[2]) for p in right_raw] if right_raw else []

        # Process gestures
        events = self.gesture_manager.process_both(left_tuples, right_tuples, current_time)

        # Force fist events for testing
        if self.force_fist:
            events.append(GestureEvent('LEFT', 'fist', 'START', None))
            events.append(GestureEvent('RIGHT', 'fist', 'START', None))
            self.force_fist = False

        # Reset per‑frame flags
        self.gear_up = False
        self.gear_down = False

        # Process gesture events
        for ev in events:
            if ev is None:
                continue

            if ev.gesture_name == 'fist':
                if ev.hand == 'LEFT':
                    if ev.event_type == 'START':
                        self._left_fist = True
                elif ev.hand == 'RIGHT':
                    if ev.event_type == 'START':
                        self._right_fist = True
            elif ev.gesture_name == 'pinch':
                if ev.hand == 'LEFT' and ev.event_type == 'UPDATE':
                    self.throttle = min(1.0, max(0.0, ev.value or 0.0))
                elif ev.hand == 'RIGHT' and ev.event_type == 'UPDATE':
                    self.brake = min(1.0, max(0.0, ev.value or 0.0))

            elif ev.gesture_name == 'two_finger_up':
                if ev.hand == 'LEFT' and ev.event_type == 'START':
                    self.gear_up = True
                elif ev.hand == 'RIGHT' and ev.event_type == 'START':
                    self.gear_down = True

        # ---- Reset controls if a hand is completely absent ----
        if not left_tuples:
            self.throttle = 0.0
            self._left_fist = False
            self._reset_hand_gestures('LEFT')
        if not right_tuples:
            self.brake = 0.0
            self._right_fist = False
            self._reset_hand_gestures('RIGHT')
        # --------------------------------------------------------

        # Update steering mode
        self.steering_mode = self._left_fist and self._right_fist

        # Smooth hand positions
        if left_tuples:
            self.smooth_left_pos = self._apply_ema(self.smooth_left_pos, left_tuples)
        else:
            self.smooth_left_pos = None
        if right_tuples:
            self.smooth_right_pos = self._apply_ema(self.smooth_right_pos, right_tuples)
        else:
            self.smooth_right_pos = None

        # Compute steering if in steering mode
        if self.steering_mode:
            self.steering_angle = self._compute_steering(self.smooth_left_pos, self.smooth_right_pos)
        else:
            self.steering_angle = 0.0

        # Build control dict
        controls = {
            "steering": self.steering_angle,
            "is_steering" : self.steering_mode,
            "throttle": self.throttle,
            "brake": self.brake,
            "gear_up": self.gear_up,
            "gear_down": self.gear_down
        }

        # Publish latest controls for the input thread
        with self.controls_lock:
            self._latest_controls.update(controls)

        # Debug logging
        self.frame_counter += 1
        if self.frame_counter % 30 == 0:
            get_logger_info('DEBUG', f"Events: {len(events)}")

        return controls

    # ------------------------------------------------------------------
    # Get annotated frame for visualization
    # ------------------------------------------------------------------
    def get_annotated_frame(self):
        with self.frame_lock:
            if self._annotated_frame is None:
                return None
            return self._annotated_frame.copy()

    # ------------------------------------------------------------------
    # Stop the controller
    # ------------------------------------------------------------------
    def stop(self):
        self.running = False
        self.input_running = False
        self.thread.join(timeout=1.0)
        self.input_thread.join(timeout=1.0)
        self.cap.release()
        get_logger_info('Driving', 'Controller stopped')