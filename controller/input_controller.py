# controller/input_controller.py
import pydirectinput
import threading
import time
import sys

class InputController:
    def __init__(self, update_freq=60):
        """
        update_freq: Hz – how often we send key pulses.
        """
        self.update_freq = update_freq
        self.update_interval = 1.0 / update_freq

        # Shared control values (protected by lock)
        self.lock = threading.Lock()
        self.target_steering = 0.0      # -1.0 .. 1.0
        self.throttle = False
        self.brake = False
        self.gear_up = False
        self.gear_down = False

        # Thread control
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

        # Initial throttle press (if needed)
        pydirectinput.keyDown('up')

    def update(self, controls):
        """
        Called from the main thread to set target controls.
        """
        with self.lock:
            self.target_steering = controls.get('steering', 0.0)
            self.throttle = controls.get('is_steering', False)   # throttle only in steering mode
            self.brake = controls.get('brake', 0.0) > 0.1
            self.gear_up = controls.get('gear_up', False)
            self.gear_down = controls.get('gear_down', False)

    def _loop(self):
        """
        Runs at a fixed rate and translates target steering into key pulses.
        """
        # For gear shifts: debounce to avoid repeated triggers
        last_gear_up = False
        last_gear_down = False

        while self.running:
            start = time.time()

            # --- 1. Gear shifts (momentary events) ---
            # disabled for now, no gestures linked to it
            # with self.lock:
            #     gear_up = self.gear_up
            #     gear_down = self.gear_down

            # if gear_up and not last_gear_up:
            #     pydirectinput.press('e')   # or whatever key your game uses
            # if gear_down and not last_gear_down:
            #     pydirectinput.press('q')
            # last_gear_up = gear_up
            # last_gear_down = gear_down

            # --- 2. Throttle & Brake (simple on/off) ---
            with self.lock:
                throttle = self.throttle
                # brake = self.brake

            if throttle:
                pydirectinput.keyDown('up')
            else:
                pydirectinput.keyUp('up')

            # if brake:
            #     pydirectinput.keyDown('down')
            # else:
            #     pydirectinput.keyUp('down')

            # --- 3. Steering: duty‑cycle pulsing ---
            with self.lock:
                steering = self.target_steering

            # Deadzone
            if abs(steering) < 0.1:
                # No steering – release both keys
                pydirectinput.keyUp('a')
                pydirectinput.keyUp('d')
            else:
                # Determine direction
                direction = 'a' if steering < 0 else 'd'
                intensity = min(1.0, (abs(steering) - 0.1) / 0.9)   # 0..1

                # Duty cycle: hold key for (intensity * cycle_time) seconds,
                # then release for the remaining time.
                hold_duration = intensity * self.update_interval
                release_duration = self.update_interval - hold_duration

                # Press the key for the hold duration
                pydirectinput.keyDown(direction)
                time.sleep(hold_duration)
                pydirectinput.keyUp(direction)
                # Sleep for the remainder of the cycle
                time.sleep(max(0, release_duration))

            # Adjust for any drift in the loop
            elapsed = time.time() - start
            if elapsed < self.update_interval:
                time.sleep(self.update_interval - elapsed)

    def stop(self):
        """Stop the background thread and release all keys."""
        self.running = False
        self.thread.join(timeout=1.0)
        pydirectinput.keyUp('up')
        pydirectinput.keyUp('down')
        pydirectinput.keyUp('a')
        pydirectinput.keyUp('d')