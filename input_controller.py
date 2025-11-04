"""Input controller using AutoHotkey HARDWARE-LEVEL inputs for maximum game compatibility.

This uses AutoHotkey's hardware-level input methods which directly simulate
physical keyboard and mouse hardware. This is the most reliable method for
protected games like AION that block software-level inputs.

The AHK script runs in the background and provides true hardware-level simulation.
"""
import time
import os
import sys
import ctypes
from ctypes import wintypes
import win32con
import win32gui
from pathlib import Path
from loguru import logger

# Try to import AHK library for hardware-level inputs
try:
    from ahk import AHK
    
    # Find AutoHotkey executable
    ahk_paths = [
        os.path.join(os.path.dirname(__file__), 'ahk', 'AutoHotkeyU64.exe'),
        os.path.join(os.path.dirname(__file__), 'ahk', 'AutoHotkeyU32.exe'),
        os.path.join(os.path.dirname(__file__), 'ahk', 'AutoHotkeyA32.exe'),
    ]
    
    ahk_exe = None
    for path in ahk_paths:
        if os.path.exists(path):
            ahk_exe = path
            logger.info(f"Found AutoHotkey at: {path}")
            break
    
    if ahk_exe:
        ahk = AHK(executable_path=ahk_exe)
        logger.info("✓ AutoHotkey HARDWARE-LEVEL input controller loaded")
        USE_HARDWARE_AHK = True
    else:
        logger.warning("AutoHotkey.exe not found - falling back to SendInput")
        USE_HARDWARE_AHK = False
        
except Exception as e:
    logger.warning(f"Could not load AHK hardware controller: {e}")
    logger.warning("Falling back to SendInput API")
    USE_HARDWARE_AHK = False

# Windows API constants and structures for SendInput
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_ABSOLUTE = 0x8000

# Virtual key codes for common keys
VK_CODES = {
    'w': 0x57, 'a': 0x41, 's': 0x53, 'd': 0x44,
    'q': 0x51, 'e': 0x45, 'r': 0x52, 'f': 0x46,
    't': 0x54, 'y': 0x59, 'u': 0x55, 'i': 0x49,
    'o': 0x4F, 'p': 0x50, 'g': 0x47, 'h': 0x48,
    'j': 0x4A, 'k': 0x4B, 'l': 0x4C, 'z': 0x5A,
    'x': 0x58, 'c': 0x43, 'v': 0x56, 'b': 0x42,
    'n': 0x4E, 'm': 0x4D,
    '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34,
    '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38,
    '9': 0x39, '0': 0x30,
    'space': 0x20, 'tab': 0x09, 'esc': 0x1B, 'escape': 0x1B,
    'enter': 0x0D, 'return': 0x0D, 'shift': 0x10,
    'ctrl': 0x11, 'control': 0x11, 'alt': 0x12,
    'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73,
    'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77,
    'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
}

# Define input structures for SendInput
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]

class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]

# Load user32.dll for SendInput
user32 = ctypes.windll.user32

logger.info("✓ Windows SendInput API ready for input control")


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
    if USE_HARDWARE_AHK:
        try:
            # Use AHK for HARDWARE-LEVEL input (most reliable for protected games)
            for _ in range(presses):
                ahk.send(key, blocking=True)
                if presses > 1 and interval > 0:
                    time.sleep(max(interval, 0.05))
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
            time.sleep(0.01)  # Small delay between down and up
            user32.SendInput(1, ctypes.byref(input_up), ctypes.sizeof(INPUT))
            
            if presses > 1 and interval > 0:
                time.sleep(max(interval, 0.05))
    except Exception as e:
        logger.error(f"SendInput key press error: {e}")
        pass


def move_mouse_to(x: int, y: int, duration: float = 0.0):
    """Move mouse to absolute screen coordinates using HARDWARE-LEVEL AHK or fallback to SendInput API."""
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
    if USE_HARDWARE_AHK:
        try:
            # Use AHK for HARDWARE-LEVEL mouse clicks
            move_mouse_to(x, y)
            time.sleep(0.1)
            
            for _ in range(clicks):
                ahk.click(x, y, button=button, blocking=True)
                if clicks > 1 and interval > 0:
                    time.sleep(max(interval, 0.1))
            return
        except Exception as e:
            logger.warning(f"AHK hardware click failed, using SendInput fallback: {e}")
    
    # Fallback to SendInput API
    try:
        move_mouse_to(x, y)
        time.sleep(0.1)
        
        # Button flags
        button_map = {
            'left': (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
            'right': (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
            'middle': (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP),
        }
        
        down_flag, up_flag = button_map.get(button.lower(), button_map['left'])
        
        for _ in range(clicks):
            # Mouse down
            mi_down = MOUSEINPUT(0, 0, 0, down_flag, 0, None)
            input_down = INPUT(INPUT_MOUSE, INPUT_UNION(mi=mi_down))
            user32.SendInput(1, ctypes.byref(input_down), ctypes.sizeof(INPUT))
            
            time.sleep(0.05)
            
            # Mouse up
            mi_up = MOUSEINPUT(0, 0, 0, up_flag, 0, None)
            input_up = INPUT(INPUT_MOUSE, INPUT_UNION(mi=mi_up))
            user32.SendInput(1, ctypes.byref(input_up), ctypes.sizeof(INPUT))
            
            if clicks > 1 and interval > 0:
                time.sleep(max(interval, 0.1))
    except Exception as e:
        logger.error(f"SendInput click error: {e}")
        pass


def double_click_at(x: int, y: int):
    """Double-click at specific screen coordinates using HARDWARE-LEVEL AHK or fallback to SendInput API."""
    if USE_HARDWARE_AHK:
        try:
            # Use AHK for HARDWARE-LEVEL double-click
            move_mouse_to(x, y)
            time.sleep(0.1)
            ahk.click(x, y, click_count=2, blocking=True)
            return
        except Exception as e:
            logger.warning(f"AHK hardware double-click failed, using SendInput fallback: {e}")
    
    # Fallback to SendInput API
    try:
        move_mouse_to(x, y)
        time.sleep(0.1)
        
        # Two rapid clicks
        for _ in range(2):
            # Mouse down
            mi_down = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, None)
            input_down = INPUT(INPUT_MOUSE, INPUT_UNION(mi=mi_down))
            user32.SendInput(1, ctypes.byref(input_down), ctypes.sizeof(INPUT))
            
            time.sleep(0.01)
            
            # Mouse up
            mi_up = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, None)
            input_up = INPUT(INPUT_MOUSE, INPUT_UNION(mi=mi_up))
            user32.SendInput(1, ctypes.byref(input_up), ctypes.sizeof(INPUT))
            
            if _ == 0:  # Delay between first and second click
                time.sleep(0.08)
        
        time.sleep(0.05)
    except Exception as e:
        logger.error(f"SendInput double-click error: {e}")
        pass