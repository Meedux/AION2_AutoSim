import ctypes
from typing import Tuple

try:
    import importlib
    win32gui = importlib.import_module('win32gui')
    win32con = importlib.import_module('win32con')
    win32api = importlib.import_module('win32api')
    win32process = importlib.import_module('win32process')
except Exception:
    # Allow imports to fail in static analysis environments; runtime will require these packages on Windows
    win32gui = None
    win32con = None
    win32api = None
    win32process = None

def enum_windows():
    """Return list of (hwnd, title) for visible windows with non-empty titles."""
    results = []

    def callback(hwnd, extra):
        try:
            if win32gui and win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    results.append((hwnd, title))
        except Exception:
            pass

    win32gui.EnumWindows(callback, None)
    return results


def get_window_rect(hwnd) -> Tuple[int,int,int,int]:
    """Return (left, top, right, bottom) in screen coordinates of the window client area."""
    # Use GetClientRect and ClientToScreen to get client area coordinates
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    # left/top are relative; convert to screen
    left_top = win32gui.ClientToScreen(hwnd, (left, top))
    right_bottom = win32gui.ClientToScreen(hwnd, (right, bottom))
    return (left_top[0], left_top[1], right_bottom[0], right_bottom[1])


def hwnd_to_pid(hwnd):
    try:
        if win32process:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            return pid
    except Exception:
        return None




def bring_window_to_front(hwnd):
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        # Fall back to attaching threads if needed
        pass
