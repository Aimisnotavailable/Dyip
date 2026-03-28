# scripts/logger.py
from colorama import Fore, Style

# --- LOGGER CONFIG ---
LOG_DIR = 'logs.txt'
CORE_COLOR = Fore.BLUE
APP_COLOR = Fore.YELLOW
ERROR_COLOR = Fore.RED
DEBUG_COLOR = Fore.MAGENTA
GAME_COLOR = Fore.GREEN
AR_COLOR = Fore.CYAN
ENGINE_COLOR = Fore.GREEN
GAMESTATE_COLOR = Fore.LIGHTWHITE_EX   # new color for game state logs

COLORS = {
    'CORE': CORE_COLOR,
    'APP': APP_COLOR,
    'ERROR': ERROR_COLOR,
    'DEBUG': DEBUG_COLOR,
    'GAME': GAME_COLOR,
    'AR': AR_COLOR,
    'ENGINE': ENGINE_COLOR,
    'GAMESTATE': GAMESTATE_COLOR
}

def dumps(text):
    with open(LOG_DIR, 'a') as fp:
        fp.write(text)

def get_logger_info(type, text, dump=False):
    """Log a message with a specific type."""
    color = COLORS.get(type, Fore.WHITE)
    print(f"{color}[{type:^5}] {text}{Style.RESET_ALL}")
    if dump:
        dumps(f'\n[{type:^5}] {text}')

def log_gamestate(controls):
    """
    Log the current driving controls in a structured way.
    `controls` should be a dict with keys: steering, throttle, brake, gear_up, gear_down.
    """
    steering = controls.get('steering', 0.0)
    throttle = controls.get('throttle', 0.0)
    brake = controls.get('brake', 0.0)
    gear_up = controls.get('gear_up', False)
    gear_down = controls.get('gear_down', False)

    gear_str = ""
    if gear_up:
        gear_str = " ⬆️ SHIFT UP"
    elif gear_down:
        gear_str = " ⬇️ SHIFT DOWN"

    # Format steering as a directional arrow
    if steering < -0.2:
        steer_str = "◀◀ LEFT"
    elif steering > 0.2:
        steer_str = "RIGHT ▶▶"
    else:
        steer_str = "CENTER"

    # Throttle and brake bars
    throttle_bar = "█" * int(throttle * 20) + "░" * (20 - int(throttle * 20))
    brake_bar = "█" * int(brake * 20) + "░" * (20 - int(brake * 20))

    msg = f"Steer: {steer_str:10} | Throttle: {throttle_bar} | Brake: {brake_bar}{gear_str}"
    get_logger_info('GAMESTATE', msg, dump=False)  # optionally dump to file