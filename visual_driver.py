# visual_driver.py
import cv2
import time
import math
import numpy as np
from controller.driving_controller import DrivingController
from scripts.logger import log_gamestate

def draw_steering_wheel(img, center, angle, radius=100):
    """
    Draw a steering wheel rotated by angle (radians) at the given center.
    angle: steering angle in radians, with 0 meaning straight.
    """
    # Draw outer circle
    cv2.circle(img, center, radius, (200,200,200), 2)
    # Draw inner circle
    cv2.circle(img, center, radius-15, (200,200,200), 1)
    # Draw crosshair
    cv2.line(img, (center[0]-radius, center[1]), (center[0]+radius, center[1]), (200,200,200), 1)
    cv2.line(img, (center[0], center[1]-radius), (center[0], center[1]+radius), (200,200,200), 1)

    # Draw a rotating line (spoke) at angle
    end_x = int(center[0] + radius * 0.8 * math.cos(angle))
    end_y = int(center[1] + radius * 0.8 * math.sin(angle))
    cv2.line(img, center, (end_x, end_y), (0,255,255), 3)

    # Draw small circles at rim for grip
    for i in range(4):
        a = math.radians(i * 90)
        x = int(center[0] + radius * math.cos(a))
        y = int(center[1] + radius * math.sin(a))
        cv2.circle(img, (x, y), 8, (0,255,255), -1)

def draw_bar(img, x, y, width, height, value, color, label):
    """Draw a horizontal bar with value (0..1)."""
    cv2.rectangle(img, (x, y), (x+width, y+height), (50,50,50), -1)
    fill_width = int(width * min(1.0, max(0.0, value)))
    cv2.rectangle(img, (x, y), (x+fill_width, y+height), color, -1)
    cv2.putText(img, label, (x+5, y+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)

def main():
    # Initialize controller
    driving = DrivingController()

    # Wait for camera to warm up
    time.sleep(1)

    print("Starting visual driver. Focus browser window.")
    print("Gestures:")
    print("  - Both fists: steering mode")
    print("  - Left pinch: throttle")
    print("  - Right pinch: brake")
    print("  - Two fingers up (left): gear up (press 'e')")
    print("  - Two fingers up (right): gear down (press 'q')")
    print("Press 'q' in the OpenCV window to quit.")

    cv2.namedWindow("AR Driving", cv2.WINDOW_NORMAL)

    frame_counter = 0
    while True:
        # Get current controls and annotated frame
        controls = driving.update()
        frame = driving.get_annotated_frame()

        if frame is None:
            time.sleep(0.01)
            continue

        # Get hand positions (index tips in pixel coordinates)
        left_pos = driving.smooth_left_pos
        right_pos = driving.smooth_right_pos
        h, w = frame.shape[:2]
        left_px = None
        right_px = None
        if left_pos:
            left_px = (int(left_pos[0] * w), int(left_pos[1] * h))
        if right_pos:
            right_px = (int(right_pos[0] * w), int(right_pos[1] * h))

        # Determine steering wheel center
        if driving.steering_mode and left_px and right_px:
            # Both fists held – center between the two hands
            center_x = (left_px[0] + right_px[0]) // 2
            center_y = (left_px[1] + right_px[1]) // 2
            wheel_center = (center_x, center_y)
        elif right_px:
            wheel_center = right_px
            # Not in steering mode, but right hand visible – use its index tip
        else:
            # Fallback to fixed position
            wheel_center = (int(w * 0.15), int(h * 0.2))

        # Draw steering wheel
        steering_rad = controls['steering'] * math.pi / 2
        draw_steering_wheel(frame, wheel_center, steering_rad, radius=60)

        # Draw throttle and brake bars at bottom
        bar_width = w // 3
        bar_height = 30
        throttle_x = w // 10
        brake_x = w // 10 * 6
        y_bar = h - 60
        draw_bar(frame, throttle_x, y_bar, bar_width, bar_height, controls['throttle'], (0,255,0), "THROTTLE")
        draw_bar(frame, brake_x, y_bar, bar_width, bar_height, controls['brake'], (0,0,255), "BRAKE")

        # Gear shift indicators
        if controls['gear_up']:
            cv2.putText(frame, "SHIFT UP", (w//2 - 60, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
        if controls['gear_down']:
            cv2.putText(frame, "SHIFT DOWN", (w//2 - 70, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)

        # Show steering mode status and debug info
        if driving.steering_mode:
            cv2.putText(frame, "STEERING MODE ACTIVE", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 2)
        else:
            cv2.putText(frame, "Make both fists to steer", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 1)

        if left_px:
            cv2.putText(frame, f"Left: {left_px}", (10, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)
        if right_px:
            cv2.putText(frame, f"Right: {right_px}", (10, h-40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1)
        cv2.putText(frame, f"Steering: {controls['steering']:.2f}", (w-200, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)

        # Display the frame
        cv2.imshow("AR Driving", frame)

        # No separate input controller here – the thread inside DrivingController handles key presses.

        # Optional: log gamestate every 30 frames
        if frame_counter % 30 == 0:
            log_gamestate(controls)
        frame_counter += 1

        # Quit on 'q'
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

        if key == ord('f'):
            driving.force_fist = True
            print("Forcing fist events for one frame")

    driving.stop()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()