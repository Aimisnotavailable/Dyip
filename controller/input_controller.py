# controller/input_controller.py
import pyautogui
import sys

class InputController:
    def __init__(self):
        pyautogui.PAUSE = 0.02
        # Optionally disable fail‑safe (not recommended, but you can uncomment if you understand the risk)
        # pyautogui.FAILSAFE = False

    def update(self, controls):
        try:
            # Steering: left/right arrow keys
            steering = controls['steering']
            if steering < -0.2:
                pyautogui.keyDown('a')
                pyautogui.keyUp('d')
            elif steering > 0.2:
                pyautogui.keyDown('d')
                pyautogui.keyUp('a')
            # else:
            #     pyautogui.keyUp('left')
            #     pyautogui.keyUp('right')

            # Throttle: up arrow
            if controls['is_steering']:
                pyautogui.keyDown('up')
            else:
                pyautogui.keyUp('up')
            # if controls['throttle'] > 0.1:
            #     pyautogui.keyDown('up')
            # else:
            #     pyautogui.keyUp('up')

            # # Brake: down arrow
            # if controls['brake'] > 0.1:
            #     pyautogui.keyDown('down')
            # else:
            #     pyautogui.keyUp('down')

            # Gear shifts: quick press
            if controls['gear_up']:
                pyautogui.press('e')
            if controls['gear_down']:
                pyautogui.press('q')

        except pyautogui.FailSafeException:
            print("\n[ERROR] PyAutoGUI fail‑safe triggered – mouse moved to a corner.")
            print("Exiting gracefully. To disable this, set pyautogui.FAILSAFE = False (not recommended).")
            sys.exit(1)