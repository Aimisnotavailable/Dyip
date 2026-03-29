# controller/input_controller.py
import pydirectinput
import sys
import time

class InputController:
    def __init__(self):
        # pydirectinput does not have a global PAUSE like pyautogui, 
        # but we can simulate it or keep logic consistent.
        self.last_steer_time = 0          # last time we sent a steering event
        self.steer_cooldown = 0.2         # seconds to wait between steering events
        self.current_steer_key = None     # which key is currently held ('a' or 'd')
        self.steer_hold_start = 0         # time when we started holding
        self.steer_hold_duration = 0.0    # duration to hold the key
        
        # Initializing the 'always on' throttle state
        # We press it once here to ensure it's active from the start
        pydirectinput.keyDown('up')

    def update(self, controls):
        """
        Processes control inputs and translates them to DirectInput key presses.
        """
        try:
            # --- 1. ALWAYS ON THROTTLE if (Testing Mode) ---
            # Else
            # use is_steering to throttle
            if controls.get('is_steering', False):
                pydirectinput.keyDown('up')
            else:
                pydirectinput.keyUp('up')

            # --- 2. PROPORTIONAL STEERING LOGIC ---
            steering = controls.get('steering', 0.0)
            now = time.time()

            # Deadzone check (0.2)
            if abs(steering) > 0.2:
                target_key = 'a' if steering < 0 else 'd'
                
                # Map intensity: 0.2 - 1.0 steering magnitude -> 0.0 - 1.0 strength
                strength = min(1.0, (abs(steering) - 0.2) / 0.8)
                # Map strength to hold duration: 0.05s to 0.25s
                hold_time = 0.05 + strength * 0.20

                # Check if we can initiate a new steering pulse
                if now - self.last_steer_time > self.steer_cooldown:
                    # Release previous key if it's different
                    if self.current_steer_key and self.current_steer_key != target_key:
                        pydirectinput.keyUp(self.current_steer_key)
                    
                    pydirectinput.keyDown(target_key)
                    self.current_steer_key = target_key
                    self.steer_hold_start = now
                    self.steer_hold_duration = hold_time
                    self.last_steer_time = now
                else:
                    # If we are currently holding a key, check if it's time to release it
                    if self.current_steer_key:
                        if now - self.steer_hold_start >= self.steer_hold_duration:
                            pydirectinput.keyUp(self.current_steer_key)
                            self.current_steer_key = None
            else:
                # Neutral steering: release any active steering keys
                if self.current_steer_key:
                    pydirectinput.keyUp(self.current_steer_key)
                    self.current_steer_key = None

            # --- 3. OPTIONAL CONTROLS (Commented out for testing) ---
            # if controls.get('brake', 0.0) > 0.1:
            #     pydirectinput.keyDown('down')
            # else:
            #     pydirectinput.keyUp('down')

        except Exception as e:
            print(f"\n[ERROR] Input Controller encountered an error: {e}")
            # Safety: Release keys on crash
            self.release_all()
            sys.exit(1)

    def release_all(self):
        """Emergency release of all keys used by the controller."""
        pydirectinput.keyUp('up')
        pydirectinput.keyUp('down')
        pydirectinput.keyUp('a')
        pydirectinput.keyUp('d')
        print("[INFO] All keys released.")