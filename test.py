import pygetwindow as gw

def list_all_windows():
    """Print all visible windows with their titles."""
    windows = gw.getAllWindows()
    print(f"Found {len(windows)} windows:")
    for i, win in enumerate(windows):
        print(f"{i+1}. Title: '{win.title}' | Size: {win.width}x{win.height} | Position: ({win.left},{win.top})")
    return windows

if __name__ == "__main__":
    list_all_windows()