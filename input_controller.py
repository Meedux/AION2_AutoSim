
"""Compatibility shim that delegates to the driver-backed implementation.

All previous input functions were migrated to driver_input.py. This file keeps
backwards compatibility for imports that reference input_controller.
"""

from .driver_input import *

__all__ = [
    'open_driver', 'close_driver', 'tap_key', 'hold_key', 'move_mouse_to', 'click_at', 'double_click_at',
    'perform_human_attack_click', 'focus_window', 'set_active_hwnd', 'is_window_foreground', 'close'
]
"""AION Input Controller — KMDF virtual HID driver backend

This module replaces AutoHotkey and SendInput with a kernel-mode driver channel.
It opens a handle to the driver (\\.\AIONVirtualHID) and sends IOCTLs to request
hardware-level keyboard and mouse actions.

Supported keys: Tab, R, T, F (scancodes defined in the driver). Mouse: relative movement, left and right click.

All functions keep the same public signatures used in the rest of the project so integration is straightforward.
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

# Driver path — driver creates a DOS symbolic link named AIONVirtualHID
DEFAULT_DEVICE_PATH = r"\\.\AIONVirtualHID"

# Key scancodes (driver must implement these exact values)
KEY_SCANCODE = {
    'tab': 0x0F,
    'r': 0x15,
    't': 0x14,
    'f': 0x09,
}

# Global driver handle (ctypes.wintypes.HANDLE)
_driver_handle = None

# Track active target window for optional foreground-only enforcement
ACTIVE_HWND = None


def open_driver(path: str = DEFAULT_DEVICE_PATH):
    """Open and cache a handle to the kernel-mode driver.

    Returns: handle or None (if device not present)
    """
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
            logger.warning("AION KMDF driver not available at %s" % path)
            _driver_handle = None
            return None
        _driver_handle = h
        logger.info("Opened KMDF driver handle %s" % path)
        return _driver_handle
    except Exception as e:
        logger.exception("open_driver failed: %s" % e)
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
    """Send DeviceIoControl to the driver. Returns True/False."""
    h = open_driver()
    if not h:
        return False

    DeviceIoControl = ctypes.windll.kernel32.DeviceIoControl
    DeviceIoControl.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
    DeviceIoControl.restype = wintypes.BOOL

    in_ptr = None
    in_size = 0
    if in_bytes is not None:
        in_size = len(in_bytes)
        in_ptr = ctypes.create_string_buffer(in_bytes)

    bytes_returned = wintypes.DWORD(0)
    ok = DeviceIoControl(h, code, in_ptr, in_size, None, 0, ctypes.byref(bytes_returned), None)
    if not ok:
        # Non-fatal: driver may be uninstalled; log and return False
        err = ctypes.windll.kernel32.GetLastError()
        logger.debug(f"DeviceIoControl failed code=0x{code:08X} err={err}")
        return False
    return True


# Track active target window for optional foreground-only enforcement
ACTIVE_HWND = None


def set_active_hwnd(hwnd: int):
    """Record the active game window hwnd for foreground checks."""
    global ACTIVE_HWND
    ACTIVE_HWND = hwnd


def is_window_foreground(hwnd: int) -> bool:
    """Return True if given hwnd is the foreground window."""
    try:
        return win32gui.GetForegroundWindow() == hwnd
    except Exception:
        return True  # fail open


def _bezier_curve(t, p0, p1, p2, p3):
    """Calculate point on cubic Bezier curve at time t (0-1)."""
    return (1-t)**3 * p0 + 3*(1-t)**2*t * p1 + 3*(1-t)*t**2 * p2 + t**3 * p3


def _smooth_mouse_drag(start_x, start_y, end_x, end_y, duration=0.3, curve_intensity=0.15):
    """
    Drag mouse smoothly using Bezier curve (human-like movement).
    NO INSTANT TELEPORT - moves smoothly from start to end.
    
    Args:
        start_x, start_y: Starting position
        end_x, end_y: Ending position
        duration: Total movement time (seconds)
        curve_intensity: How curved the path is (0-1, higher = more curve)
    """
    if duration <= 0:
        # Instant move (fallback)
        if USE_HARDWARE_AHK:
            try:
                ahk.mouse_move(end_x, end_y, speed=0, blocking=True)
                return
            except:
                pass
        # SendInput fallback for instant move
        screen_width = user32.GetSystemMetrics(0)
        screen_height = user32.GetSystemMetrics(1)
        abs_x = int(end_x * 65535 / screen_width)
        abs_y = int(end_y * 65535 / screen_height)
        mi = MOUSEINPUT(abs_x, abs_y, 0, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, 0, None)
        input_move = INPUT(INPUT_MOUSE, INPUT_UNION(mi=mi))
        user32.SendInput(1, ctypes.byref(input_move), ctypes.sizeof(INPUT))
        return
    
    # Calculate Bezier control points for smooth curved movement
    dx = end_x - start_x
    dy = end_y - start_y
    
    # Control points create the curve
    # Add perpendicular offset for natural curve
    perp_x = -dy * curve_intensity
    perp_y = dx * curve_intensity
    
    p0_x, p0_y = start_x, start_y
    p1_x = start_x + dx * 0.25 + perp_x * random.uniform(0.8, 1.2)
    p1_y = start_y + dy * 0.25 + perp_y * random.uniform(0.8, 1.2)
    p2_x = start_x + dx * 0.75 - perp_x * random.uniform(0.8, 1.2)
    p2_y = start_y + dy * 0.75 - perp_y * random.uniform(0.8, 1.2)
    p3_x, p3_y = end_x, end_y
    
    # Number of steps for smooth movement
    steps = max(10, int(duration * 60))  # 60 FPS
    step_delay = duration / steps
    
    screen_width = user32.GetSystemMetrics(0)
    screen_height = user32.GetSystemMetrics(1)
    
    for i in range(steps + 1):
        t = i / steps
        # Cubic Bezier curve
        x = _bezier_curve(t, p0_x, p1_x, p2_x, p3_x)
        y = _bezier_curve(t, p0_y, p1_y, p2_y, p3_y)
        
        if USE_HARDWARE_AHK:
            try:
                ahk.mouse_move(int(x), int(y), speed=0, blocking=True)
            except:
                # Fallback to SendInput
                abs_x = int(x * 65535 / screen_width)
                abs_y = int(y * 65535 / screen_height)
                mi = MOUSEINPUT(abs_x, abs_y, 0, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, 0, None)
                input_move = INPUT(INPUT_MOUSE, INPUT_UNION(mi=mi))
                user32.SendInput(1, ctypes.byref(input_move), ctypes.sizeof(INPUT))
        else:
            # SendInput fallback
            abs_x = int(x * 65535 / screen_width)
            abs_y = int(y * 65535 / screen_height)
            mi = MOUSEINPUT(abs_x, abs_y, 0, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, 0, None)
            input_move = INPUT(INPUT_MOUSE, INPUT_UNION(mi=mi))
            user32.SendInput(1, ctypes.byref(input_move), ctypes.sizeof(INPUT))
        
        if i < steps:
            time.sleep(step_delay)


def focus_window(hwnd: int):
    """Bring the target game window to foreground."""
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


def tap_key(key: str, presses: int = 1, interval: float = 0.05):
    """Send key press(es) using HARDWARE-LEVEL AHK or fallback to SendInput API."""
    # Foreground-only guard
    if stealth_config.FOREGROUND_ONLY and ACTIVE_HWND is not None:
        if not is_window_foreground(ACTIVE_HWND):
            logger.debug("tap_key skipped (window not foreground)")
            return

    # Randomized timings
    down_time = stealth_config.get_key_tap_down_time()
    inter_tap = stealth_config.get_key_tap_interval() if presses > 1 else interval
    if USE_HARDWARE_AHK:
        try:
            # Use AHK for HARDWARE-LEVEL input (most reliable for protected games)
            for _ in range(presses):
                # Press down and up with a slight delay
                ahk.send(f"{{{key} down}}", blocking=True)
                time.sleep(down_time)
                ahk.send(f"{{{key} up}}", blocking=True)
                if presses > 1:
                    time.sleep(max(inter_tap, 0.05))
            return
        except Exception as e:
            logger.warning(f"AHK hardware input failed, using SendInput fallback: {e}")
    
    # Fallback to SendInput API
    try:
        key_lower = key.lower()
        vk_code = VK_CODES.get(key_lower)
        
        if vk_code is None:
            logger.warning(f"Unknown key: {key}")
            return
        
        for _ in range(presses):
            # Key down
            ki_down = KEYBDINPUT(vk_code, 0, 0, 0, None)
            input_down = INPUT(INPUT_KEYBOARD, INPUT_UNION(ki=ki_down))
            
            # Key up
            ki_up = KEYBDINPUT(vk_code, 0, KEYEVENTF_KEYUP, 0, None)
            input_up = INPUT(INPUT_KEYBOARD, INPUT_UNION(ki=ki_up))
            
            # Send both events
            user32.SendInput(1, ctypes.byref(input_down), ctypes.sizeof(INPUT))
            time.sleep(down_time)
            user32.SendInput(1, ctypes.byref(input_up), ctypes.sizeof(INPUT))
            
            if presses > 1:
                time.sleep(max(inter_tap, 0.05))
    except Exception as e:
        logger.error(f"SendInput key press error: {e}")
        pass


def hold_key(key: str, duration: float):
    """Hold a key down for specified duration (for 70-degree turns, etc.)
    
    Args:
        key: Key to hold (e.g., 'a', 'd', 'w')
        duration: How long to hold the key in seconds
    """
    # Foreground-only guard
    if stealth_config.FOREGROUND_ONLY and ACTIVE_HWND is not None:
        if not is_window_foreground(ACTIVE_HWND):
            logger.debug("hold_key skipped (window not foreground)")
            return

    if USE_HARDWARE_AHK:
        try:
            # Use AHK Send command with {key down} and {key up}
            ahk.send(f"{{{key} down}}", blocking=True)
            time.sleep(duration)
            ahk.send(f"{{{key} up}}", blocking=True)
            return
        except Exception as e:
            logger.warning(f"AHK hold_key failed, using SendInput fallback: {e}")
    
    # Fallback to SendInput API
    try:
        key_lower = key.lower()
        vk_code = VK_CODES.get(key_lower)
        
        if vk_code is None:
            logger.warning(f"Unknown key: {key}")
            return
        
        # Key down
        ki_down = KEYBDINPUT(vk_code, 0, 0, 0, None)
        input_down = INPUT(INPUT_KEYBOARD, INPUT_UNION(ki=ki_down))
        user32.SendInput(1, ctypes.byref(input_down), ctypes.sizeof(INPUT))
        
        # Hold for duration
        time.sleep(duration)
        
        # Key up
        ki_up = KEYBDINPUT(vk_code, 0, KEYEVENTF_KEYUP, 0, None)
        input_up = INPUT(INPUT_KEYBOARD, INPUT_UNION(ki=ki_up))
        user32.SendInput(1, ctypes.byref(input_up), ctypes.sizeof(INPUT))
        
    except Exception as e:
        logger.error(f"SendInput hold_key error: {e}")
        pass


def press_key_combination(modifier: str, key: str):
    """Press a key combination (e.g., Alt+1, Ctrl+5) using hardware-level input.
    
    Args:
        modifier: Modifier key ('alt' or 'ctrl')
        key: The key to press with the modifier
    """
    # Foreground-only guard
    if stealth_config.FOREGROUND_ONLY and ACTIVE_HWND is not None:
        if not is_window_foreground(ACTIVE_HWND):
            logger.debug("press_key_combination skipped (window not foreground)")
            return

    mod_delay = stealth_config.get_key_tap_down_time()
    inter_delay = stealth_config.get_key_tap_interval()
    if USE_HARDWARE_AHK:
        try:
            # Use AHK Send command with modifiers
            # AHK syntax: ! = Alt, ^ = Ctrl
            if modifier.lower() == 'alt':
                ahk.send(f"{{Alt down}}", blocking=True)
                time.sleep(mod_delay)
                ahk.send(f"{key}", blocking=True)
                time.sleep(mod_delay)
                ahk.send(f"{{Alt up}}", blocking=True)
                logger.debug(f"AHK: Alt+{key}")
            elif modifier.lower() == 'ctrl':
                ahk.send(f"{{Ctrl down}}", blocking=True)
                time.sleep(mod_delay)
                ahk.send(f"{key}", blocking=True)
                time.sleep(mod_delay)
                ahk.send(f"{{Ctrl up}}", blocking=True)
                logger.debug(f"AHK: Ctrl+{key}")
            else:
                logger.warning(f"Unknown modifier: {modifier}")
            return
        except Exception as e:
            logger.warning(f"AHK press_key_combination failed, using SendInput fallback: {e}")
    
    # Fallback to SendInput API
    try:
        modifier_lower = modifier.lower()
        key_lower = key.lower()
        
        # Get virtual key codes
        key_vk = VK_CODES.get(key_lower)
        if key_vk is None:
            logger.warning(f"Unknown key: {key}")
            return
        
        if modifier_lower == 'alt':
            modifier_vk = VK_CODES['alt']
        elif modifier_lower == 'ctrl':
            modifier_vk = VK_CODES['ctrl']
        else:
            logger.warning(f"Unknown modifier: {modifier}")
            return
        
        # Press modifier down
        ki_mod_down = KEYBDINPUT(modifier_vk, 0, 0, 0, None)
        input_mod_down = INPUT(INPUT_KEYBOARD, INPUT_UNION(ki=ki_mod_down))
        user32.SendInput(1, ctypes.byref(input_mod_down), ctypes.sizeof(INPUT))
        time.sleep(mod_delay)
        
        # Press key down
        ki_key_down = KEYBDINPUT(key_vk, 0, 0, 0, None)
        input_key_down = INPUT(INPUT_KEYBOARD, INPUT_UNION(ki=ki_key_down))
        user32.SendInput(1, ctypes.byref(input_key_down), ctypes.sizeof(INPUT))
        time.sleep(mod_delay)
        
        # Release key up
        ki_key_up = KEYBDINPUT(key_vk, 0, KEYEVENTF_KEYUP, 0, None)
        input_key_up = INPUT(INPUT_KEYBOARD, INPUT_UNION(ki=ki_key_up))
        user32.SendInput(1, ctypes.byref(input_key_up), ctypes.sizeof(INPUT))
        time.sleep(mod_delay)
        
        # Release modifier up
        ki_mod_up = KEYBDINPUT(modifier_vk, 0, KEYEVENTF_KEYUP, 0, None)
        input_mod_up = INPUT(INPUT_KEYBOARD, INPUT_UNION(ki=ki_mod_up))
        user32.SendInput(1, ctypes.byref(input_mod_up), ctypes.sizeof(INPUT))
        
        logger.debug(f"SendInput: {modifier}+{key}")
        
    except Exception as e:
        logger.error(f"SendInput press_key_combination error: {e}")
        pass


def move_mouse_to(x: int, y: int, duration: float = None):
    """
    Move mouse to absolute screen coordinates using SMOOTH DRAGGING (no teleport).
    Uses Bezier curves for human-like movement.
    
    Args:
        x, y: Target screen coordinates
        duration: Movement duration (None = use stealth config)
    """
    # Get current mouse position
    point = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(point))
    start_x, start_y = point.x, point.y
    
    # Use stealth config for duration if not specified
    if duration is None:
        duration = stealth_config.get_mouse_drag_duration()
    
    # Use smooth dragging (Bezier curve) instead of instant teleport
    if stealth_config.MOUSE_DRAG_ENABLED:
        _smooth_mouse_drag(
            start_x, start_y, x, y, 
            duration=duration,
            curve_intensity=stealth_config.MOUSE_DRAG_CURVE
        )
        time.sleep(0.05)
        return
    
    # Fallback: old instant movement (only if dragging disabled)
    if USE_HARDWARE_AHK:
        try:
            # Use AHK for HARDWARE-LEVEL mouse movement
            ahk.mouse_move(x, y, speed=0 if duration == 0 else int(100 / (duration + 0.01)), blocking=True)
            time.sleep(0.05)
            return
        except Exception as e:
            logger.warning(f"AHK hardware mouse move failed, using SendInput fallback: {e}")
    
    # Fallback to SendInput API
    try:
        # Get screen dimensions
        screen_width = user32.GetSystemMetrics(0)
        screen_height = user32.GetSystemMetrics(1)
        
        # Convert to absolute coordinates (0-65535 range)
        abs_x = int(x * 65535 / screen_width)
        abs_y = int(y * 65535 / screen_height)
        
        if duration > 0:
            # Smooth movement
            point = wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(point))
            start_x = int(point.x * 65535 / screen_width)
            start_y = int(point.y * 65535 / screen_height)
            
            steps = max(int(duration * 60), 1)
            for i in range(steps + 1):
                t = i / steps
                intermediate_x = int(start_x + (abs_x - start_x) * t)
                intermediate_y = int(start_y + (abs_y - start_y) * t)
                
                mi = MOUSEINPUT(intermediate_x, intermediate_y, 0, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, 0, None)
                input_move = INPUT(INPUT_MOUSE, INPUT_UNION(mi=mi))
                user32.SendInput(1, ctypes.byref(input_move), ctypes.sizeof(INPUT))
                time.sleep(duration / steps)
        else:
            # Instant move
            mi = MOUSEINPUT(abs_x, abs_y, 0, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, 0, None)
            input_move = INPUT(INPUT_MOUSE, INPUT_UNION(mi=mi))
            user32.SendInput(1, ctypes.byref(input_move), ctypes.sizeof(INPUT))
        
        time.sleep(0.05)
    except Exception as e:
        logger.error(f"SendInput mouse move error: {e}")
        pass


def click_at(x: int, y: int, button: str = 'left', clicks: int = 1, interval: float = 0.1):
    """Click at specific screen coordinates using HARDWARE-LEVEL AHK or fallback to SendInput API."""
    # Foreground-only guard
    if stealth_config.FOREGROUND_ONLY and ACTIVE_HWND is not None:
        if not is_window_foreground(ACTIVE_HWND):
            logger.debug("click_at skipped (window not foreground)")
            return

    # Micro jitter before click, then settle
    jx, jy = stealth_config.get_micro_jitter()
    settle_pause = stealth_config.get_pre_click_pause()
    if USE_HARDWARE_AHK:
        try:
            # Use AHK for HARDWARE-LEVEL mouse clicks
            move_mouse_to(x + jx, y + jy)
            time.sleep(settle_pause)
            move_mouse_to(x, y)
            time.sleep(settle_pause)
            
            down_time = stealth_config.get_mouse_button_down_time()
            inter_click = interval if interval is not None else stealth_config.get_double_click_interval()
            for i in range(clicks):
                ahk.click(x, y, button=button, blocking=True)
                time.sleep(down_time)
                if clicks > 1 and i < clicks - 1:
                    time.sleep(max(inter_click, 0.06))
            return
        except Exception as e:
            logger.warning(f"AHK hardware click failed, using SendInput fallback: {e}")
    
    # Fallback to SendInput API
    try:
        move_mouse_to(x + jx, y + jy)
        time.sleep(settle_pause)
        move_mouse_to(x, y)
        time.sleep(settle_pause)
        
        # Button flags
        button_map = {
            'left': (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
            'right': (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
            'middle': (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP),
        }
        
        down_flag, up_flag = button_map.get(button.lower(), button_map['left'])
        down_time = stealth_config.get_mouse_button_down_time()
        inter_click = interval if interval is not None else stealth_config.get_double_click_interval()
        for i in range(clicks):
            # Mouse down
            mi_down = MOUSEINPUT(0, 0, 0, down_flag, 0, None)
            input_down = INPUT(INPUT_MOUSE, INPUT_UNION(mi=mi_down))
            user32.SendInput(1, ctypes.byref(input_down), ctypes.sizeof(INPUT))
            
            time.sleep(down_time)
            
            # Mouse up
            mi_up = MOUSEINPUT(0, 0, 0, up_flag, 0, None)
            input_up = INPUT(INPUT_MOUSE, INPUT_UNION(mi=mi_up))
            user32.SendInput(1, ctypes.byref(input_up), ctypes.sizeof(INPUT))
            
            if clicks > 1 and i < clicks - 1:
                time.sleep(max(inter_click, 0.06))
    except Exception as e:
        logger.error(f"SendInput click error: {e}")
        pass


def double_click_at(x: int, y: int):
    """Double-click at specific screen coordinates using HARDWARE-LEVEL AHK or fallback to SendInput API."""
    # Foreground-only guard
    if stealth_config.FOREGROUND_ONLY and ACTIVE_HWND is not None:
        if not is_window_foreground(ACTIVE_HWND):
            logger.debug("double_click_at skipped (window not foreground)")
            return

    inter = stealth_config.get_double_click_interval()
    down_time = stealth_config.get_mouse_button_down_time()
    settle_pause = stealth_config.get_pre_click_pause()
    jx, jy = stealth_config.get_micro_jitter()
    if USE_HARDWARE_AHK:
        try:
            # Use AHK for HARDWARE-LEVEL double-click
            move_mouse_to(x + jx, y + jy)
            time.sleep(settle_pause)
            move_mouse_to(x, y)
            time.sleep(settle_pause)
            ahk.click(x, y, blocking=True)
            time.sleep(down_time)
            time.sleep(inter)
            ahk.click(x, y, blocking=True)
            return
        except Exception as e:
            logger.warning(f"AHK hardware double-click failed, using SendInput fallback: {e}")
    
    # Fallback to SendInput API
    try:
        move_mouse_to(x + jx, y + jy)
        time.sleep(settle_pause)
        move_mouse_to(x, y)
        time.sleep(settle_pause)
        
        # Two rapid clicks
        for i in range(2):
            # Mouse down
            mi_down = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, None)
            input_down = INPUT(INPUT_MOUSE, INPUT_UNION(mi=mi_down))
            user32.SendInput(1, ctypes.byref(input_down), ctypes.sizeof(INPUT))
            
            time.sleep(down_time)
            
            # Mouse up
            mi_up = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, None)
            input_up = INPUT(INPUT_MOUSE, INPUT_UNION(mi=mi_up))
            user32.SendInput(1, ctypes.byref(input_up), ctypes.sizeof(INPUT))
            
            if i == 0:  # Delay between first and second click
                time.sleep(inter)
        
        time.sleep(0.05)
    except Exception as e:
        logger.error(f"SendInput double-click error: {e}")
        pass


def perform_human_attack_click(x: int, y: int):
    """Execute an attack on a target using a stealth strategy to avoid double-click detection.

        Strategies:
            - 'two_single': two separate left-clicks with humanized interval
            - 'click_then_key': single left-click to target, then press PRIMARY_ATTACK_KEY
            - 'key_then_click': press key first, then a single left-click
            - 'right_click': single right-click
    """
    # Foreground-only guard
    if stealth_config.FOREGROUND_ONLY and ACTIVE_HWND is not None:
        if not is_window_foreground(ACTIVE_HWND):
            logger.debug("perform_human_attack_click skipped (window not foreground)")
            return

    try:
        strat = stealth_config.choose_attack_click_strategy()
    except Exception:
        strat = 'two_single'

    if strat == 'two_single':
        if getattr(stealth_config, 'AVOID_SEQUENTIAL_CLICKS', False):
            strat = 'click_then_key'
        else:
            # Two single left clicks with natural interval
            click_at(x, y, button='left', clicks=2, interval=None)
            return

    if strat == 'key_then_click':
        key = getattr(stealth_config, 'PRIMARY_ATTACK_KEY', None)
        if key:
            tap_key(key)
            try:
                delay = stealth_config.get_click_then_key_delay()
            except Exception:
                delay = 0.15
            time.sleep(delay)
        click_at(x, y, button='left', clicks=1)
        return

    if strat == 'right_click':
        click_at(x, y, button='right', clicks=1)
        return

    # click_then_key (default)
    click_at(x, y, button='left', clicks=1)
    # Pause a bit before pressing primary attack key
    try:
        delay = stealth_config.get_click_then_key_delay()
    except Exception:
        delay = 0.15
    time.sleep(delay)
    key = getattr(stealth_config, 'PRIMARY_ATTACK_KEY', None)
    if key:
        tap_key(key)
    else:
        # If no key configured, fall back to a second click with humanized gap
        click_at(x, y, button='left', clicks=1)