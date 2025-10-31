"""Low-level input controller using Win32 SendInput.

Provides safe wrappers for keyboard and mouse actions used by the ActionPlanner.
"""
import ctypes
import time
from ctypes import wintypes
import win32con
import win32gui

# Create a pointer type that matches platform pointer width for dwExtraInfo
_PTR_SIZE = ctypes.sizeof(ctypes.c_void_p)
if _PTR_SIZE == 8:
    _UINTPTR = ctypes.c_ulonglong
else:
    _UINTPTR = ctypes.c_ulong
PUL = ctypes.POINTER(_UINTPTR)

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", PUL)]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG),
                ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", PUL)]

class INPUT_I(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("ii", INPUT_I)]

SendInput = ctypes.windll.user32.SendInput

# pointer to use for dwExtraInfo (avoids passing None)
_DWEXTRA = ctypes.pointer(_UINTPTR(0))

def focus_window(hwnd: int):
    """Attempt to reliably bring the target window to foreground.

    Uses a sequence of calls and AttachThreadInput as a fallback when
    SetForegroundWindow does not succeed (Windows may restrict focus changes).
    """
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        # Try a simple restore + SetForegroundWindow first
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        if user32.SetForegroundWindow(hwnd):
            return

        # If simple SetForegroundWindow failed, try attaching input threads
        # Get the thread id for the target window and the current thread
        target_tid = user32.GetWindowThreadProcessId(hwnd, 0)
        curr_tid = kernel32.GetCurrentThreadId()
        if target_tid and curr_tid and target_tid != curr_tid:
            # attach threads, force foreground, then detach
            attached = user32.AttachThreadInput(curr_tid, target_tid, True)
            try:
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)
                user32.SetFocus(hwnd)
            finally:
                # detach only if we attached
                if attached:
                    user32.AttachThreadInput(curr_tid, target_tid, False)
        else:
            # last resort
            user32.SetForegroundWindow(hwnd)
    except Exception:
        # best-effort; ignore errors
        pass

def _send_input(inp: INPUT):
    return SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))

def key_down(vk: int):
    ki = KEYBDINPUT(wVk=vk, wScan=0, dwFlags=0, time=0, dwExtraInfo=_DWEXTRA)
    ii = INPUT_I(); ii.ki = ki
    inp = INPUT(type=1, ii=ii)
    return _send_input(inp)

def key_up(vk: int):
    ki = KEYBDINPUT(wVk=vk, wScan=0, dwFlags=0x0002, time=0, dwExtraInfo=_DWEXTRA)  # KEYEVENTF_KEYUP
    ii = INPUT_I(); ii.ki = ki
    inp = INPUT(type=1, ii=ii)
    return _send_input(inp)

def tap_key(vk: int, hold: float = 0.06):
    key_down(vk)
    time.sleep(hold)
    key_up(vk)

def move_mouse_to_screen(x_px: int, y_px: int):
    # Map to absolute coords expected by SendInput (0..65535)
    user32 = ctypes.windll.user32
    sx = user32.GetSystemMetrics(0)
    sy = user32.GetSystemMetrics(1)
    # map to 0..65535 using (width-1)/(height-1) to match MSDN guidance
    ax = int(x_px * 65535 / max(1, sx - 1)) if sx > 1 else 0
    ay = int(y_px * 65535 / max(1, sy - 1)) if sy > 1 else 0
    mi = MOUSEINPUT(dx=ax, dy=ay, mouseData=0, dwFlags=win32con.MOUSEEVENTF_MOVE | win32con.MOUSEEVENTF_ABSOLUTE, time=0, dwExtraInfo=_DWEXTRA)
    ii = INPUT_I(); ii.mi = mi
    inp = INPUT(type=0, ii=ii)
    return _send_input(inp)

def left_click():
    mi_down = MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=win32con.MOUSEEVENTF_LEFTDOWN, time=0, dwExtraInfo=_DWEXTRA)
    ii = INPUT_I(); ii.mi = mi_down
    inp_down = INPUT(type=0, ii=ii)
    _send_input(inp_down)
    time.sleep(0.01)
    mi_up = MOUSEINPUT(dx=0, dy=0, mouseData=0, dwFlags=win32con.MOUSEEVENTF_LEFTUP, time=0, dwExtraInfo=_DWEXTRA)
    ii2 = INPUT_I(); ii2.mi = mi_up
    inp_up = INPUT(type=0, ii=ii2)
    _send_input(inp_up)

def double_click_at(x_px: int, y_px: int, inter: float = 0.06):
    # move then double click
    move_mouse_to_screen(x_px, y_px)
    # small pause to allow the OS to move the cursor
    time.sleep(0.03)
    left_click()
    time.sleep(inter)
    left_click()


def click_at(x_px: int, y_px: int):
    """Move the mouse to screen coords and perform a single left click."""
    move_mouse_to_screen(x_px, y_px)
    time.sleep(0.02)
    left_click()
