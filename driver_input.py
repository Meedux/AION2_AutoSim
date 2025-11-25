"""Driver-based input controller (clean implementation)

This is the canonical driver-backed input controller. `input_controller.py`
is a thin wrapper that delegates to this module so changes are atomic.
"""

import ctypes
import time
from ctypes import wintypes
import win32gui
import win32con
from loguru import logger
import stealth_config

# IOCTL codes (must match kmdf_driver/device.h)
IOCTL_HID_KEYDOWN   = 0x80002004
IOCTL_HID_KEYUP     = 0x80002008
IOCTL_HID_MOUSEMOVE = 0x8000200C
IOCTL_HID_LEFTCLICK = 0x80002010
IOCTL_HID_RIGHTCLICK= 0x80002014

DEFAULT_DEVICE_PATH = r"\\.\AIONVirtualHID"

KEY_SCANCODE = {
    'tab': 0x0F,
    'r': 0x15,
    't': 0x14,
    'f': 0x09,
}

_driver_handle = None
ACTIVE_HWND = None


def open_driver(path: str = DEFAULT_DEVICE_PATH):
    global _driver_handle
    if _driver_handle:
        return _driver_handle

    CreateFileW = ctypes.windll.kernel32.CreateFileW
    CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    CreateFileW.restype = wintypes.HANDLE

    GENERIC_READ = 0x80000000
    GENERIC_WRITE = 0x40000000
    FILE_SHARE_READ = 0x1
    FILE_SHARE_WRITE = 0x2
    OPEN_EXISTING = 3

    try:
        h = CreateFileW(path, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None)
        if h == wintypes.HANDLE(-1).value:
            logger.debug("Driver not present: %s" % path)
            _driver_handle = None
            return None
        _driver_handle = h
        return _driver_handle
    except Exception as e:
        logger.debug("open_driver error: %s" % e)
        _driver_handle = None
        return None


def close_driver():
    global _driver_handle
    try:
        if _driver_handle:
            ctypes.windll.kernel32.CloseHandle(_driver_handle)
            _driver_handle = None
    except Exception:
        pass


def _device_io_control(code: int, in_bytes: bytes = None):
    h = open_driver()
    if not h:
        return False
    DeviceIoControl = ctypes.windll.kernel32.DeviceIoControl
    DeviceIoControl.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
    DeviceIoControl.restype = wintypes.BOOL
    in_ptr = None
    if in_bytes is not None:
        in_ptr = ctypes.create_string_buffer(in_bytes)
        in_size = len(in_bytes)
    else:
        in_size = 0
    bytes_returned = wintypes.DWORD(0)
    ok = DeviceIoControl(h, code, in_ptr, in_size, None, 0, ctypes.byref(bytes_returned), None)
    if not ok:
        logger.debug(f"DeviceIoControl failed code=0x{code:08X}")
        return False
    return True


def set_active_hwnd(hwnd: int):
    global ACTIVE_HWND
    ACTIVE_HWND = hwnd


def is_window_foreground(hwnd: int) -> bool:
    try:
        return win32gui.GetForegroundWindow() == hwnd
    except Exception:
        return True


def focus_window(hwnd: int):
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.02)
        if user32.SetForegroundWindow(hwnd):
            time.sleep(0.15)
            return
        target_tid = user32.GetWindowThreadProcessId(hwnd, 0)
        curr_tid = kernel32.GetCurrentThreadId()
        if target_tid and curr_tid and target_tid != curr_tid:
            attached = user32.AttachThreadInput(curr_tid, target_tid, True)
            try:
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)
                user32.SetFocus(hwnd)
                time.sleep(0.15)
            finally:
                if attached:
                    user32.AttachThreadInput(curr_tid, target_tid, False)
        else:
            user32.SetForegroundWindow(hwnd)
            time.sleep(0.15)
    except Exception:
        pass


def _pack_key_event(scancode: int) -> bytes:
    return bytes([scancode & 0xFF, 0x00])


def _pack_mouse_move(dx: int, dy: int) -> bytes:
    return (ctypes.c_int32(dx).value).to_bytes(4, 'little', signed=True) + (ctypes.c_int32(dy).value).to_bytes(4, 'little', signed=True)


def tap_key(key: str, presses: int = 1, interval: float = 0.05):
    if stealth_config.FOREGROUND_ONLY and ACTIVE_HWND is not None:
        if not is_window_foreground(ACTIVE_HWND):
            logger.debug("tap_key skipped (window not foreground)")
            return
    key_lower = key.lower()
    if key_lower not in KEY_SCANCODE:
        logger.warning(f"Unsupported key for driver: {key}")
        return
    sc = KEY_SCANCODE[key_lower]
    for _ in range(presses):
        _device_io_control(IOCTL_HID_KEYDOWN, _pack_key_event(sc))
        time.sleep(stealth_config.get_key_tap_down_time())
        _device_io_control(IOCTL_HID_KEYUP, _pack_key_event(sc))
        if presses > 1:
            time.sleep(max(interval, 0.05))


def hold_key(key: str, duration: float):
    if stealth_config.FOREGROUND_ONLY and ACTIVE_HWND is not None:
        if not is_window_foreground(ACTIVE_HWND):
            logger.debug("hold_key skipped (window not foreground)")
            return
    key_lower = key.lower()
    if key_lower not in KEY_SCANCODE:
        logger.warning(f"Unsupported key for driver: {key}")
        return
    sc = KEY_SCANCODE[key_lower]
    _device_io_control(IOCTL_HID_KEYDOWN, _pack_key_event(sc))
    time.sleep(duration)
    _device_io_control(IOCTL_HID_KEYUP, _pack_key_event(sc))


def press_key_combination(modifier: str, key: str):
    tap_key(key)


def move_mouse_to(x: int, y: int, duration: float = None):
    point = wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
    start_x, start_y = point.x, point.y
    dx = int(x - start_x)
    dy = int(y - start_y)
    if duration and duration > 0:
        steps = max(int(duration * 30), 1)
        step_dx = dx // steps
        step_dy = dy // steps
        rem_x = dx - step_dx*steps
        rem_y = dy - step_dy*steps
        for i in range(steps):
            _device_io_control(IOCTL_HID_MOUSEMOVE, _pack_mouse_move(step_dx, step_dy))
            time.sleep(duration/steps)
        if rem_x or rem_y:
            _device_io_control(IOCTL_HID_MOUSEMOVE, _pack_mouse_move(rem_x, rem_y))
    else:
        _device_io_control(IOCTL_HID_MOUSEMOVE, _pack_mouse_move(dx, dy))


def click_at(x: int, y: int, button: str = 'left', clicks: int = 1, interval: float = 0.1):
    if stealth_config.FOREGROUND_ONLY and ACTIVE_HWND is not None:
        if not is_window_foreground(ACTIVE_HWND):
            logger.debug("click_at skipped (window not foreground)")
            return
    move_mouse_to(x, y, duration=stealth_config.get_mouse_drag_duration())
    for i in range(clicks):
        if button.lower() == 'right':
            _device_io_control(IOCTL_HID_RIGHTCLICK, b'')
        else:
            _device_io_control(IOCTL_HID_LEFTCLICK, b'')
        time.sleep(stealth_config.get_mouse_button_down_time())
        if clicks > 1 and i < clicks-1:
            time.sleep(max(interval, 0.06))


def double_click_at(x: int, y: int):
    if stealth_config.FOREGROUND_ONLY and ACTIVE_HWND is not None:
        if not is_window_foreground(ACTIVE_HWND):
            logger.debug("double_click_at skipped (window not foreground)")
            return
    click_at(x, y, button='left', clicks=1)
    time.sleep(stealth_config.get_double_click_interval())
    click_at(x, y, button='left', clicks=1)


def perform_human_attack_click(x: int, y: int):
    try:
        strat = stealth_config.choose_attack_click_strategy()
    except Exception:
        strat = 'two_single'
    if strat == 'two_single':
        click_at(x, y, button='left', clicks=2)
        return
    if strat == 'key_then_click':
        key = getattr(stealth_config, 'PRIMARY_ATTACK_KEY', None)
        if key:
            tap_key(key)
            time.sleep(stealth_config.get_click_then_key_delay())
        click_at(x, y, button='left', clicks=1)
        return
    if strat == 'right_click':
        click_at(x, y, button='right', clicks=1)
        return
    click_at(x, y, button='left', clicks=1)
    key = getattr(stealth_config, 'PRIMARY_ATTACK_KEY', None)
    if key:
        time.sleep(stealth_config.get_click_then_key_delay())
        tap_key(key)


def close():
    close_driver()


# auto-open driver on import (silently)
try:
    open_driver()
except Exception:
    pass
