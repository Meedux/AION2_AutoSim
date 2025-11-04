"""Input controller using AutoHotkey for game automation.

AutoHotkey provides reliable input simulation that works with most games,
including AION. It's simpler than kernel-level drivers and doesn't require
administrator privileges or system modifications.

The ahk library automatically downloads and manages AutoHotkey if not installed.
"""
import time
import ctypes
import win32con
import win32gui
import os
import sys
from loguru import logger

# Import AutoHotkey - automatically downloads AHK if needed
try:
    from ahk import AHK
    
    # Try to find AutoHotkey.exe automatically
    ahk_paths = [
        # Check project folder first (where we downloaded it)
        os.path.join(os.path.dirname(__file__), 'ahk', 'AutoHotkeyU64.exe'),
        os.path.join(os.path.dirname(__file__), 'ahk', 'AutoHotkeyU32.exe'),
        os.path.join(os.path.dirname(__file__), 'ahk', 'AutoHotkeyA32.exe'),
        # Check if ahk-binary installed it
        os.path.join(sys.prefix, 'lib', 'site-packages', 'ahk_binary', 'AutoHotkey.exe'),
        os.path.join(sys.prefix, 'Lib', 'site-packages', 'ahk_binary', 'AutoHotkey.exe'),
        # Check common installation locations
        r'C:\Program Files\AutoHotkey\AutoHotkey.exe',
        r'C:\Program Files\AutoHotkey\v2\AutoHotkey.exe',
        r'C:\Program Files (x86)\AutoHotkey\AutoHotkey.exe',
    ]
    
    ahk_exe = None
    for path in ahk_paths:
        if os.path.exists(path):
            ahk_exe = path
            logger.info(f"Found AutoHotkey at: {path}")
            break
    
    if ahk_exe:
        ahk = AHK(executable_path=ahk_exe)
    else:
        # Try without specifying path - may work if on PATH
        ahk = AHK()
    
    logger.info("✓ AutoHotkey loaded - ready for input control")
except Exception as e:
    logger.error(f"❌ AutoHotkey not available: {e}")
    logger.error("Please install AutoHotkey from https://www.autohotkey.com/")
    logger.error("Or run: pip install \"ahk[binary]\"")
    raise ImportError(f"AutoHotkey required but not available: {e}")


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
    """Send key press(es) using AutoHotkey."""
    try:
        # AutoHotkey uses key names directly (supports special keys too)
        # Common mappings: space, tab, esc/escape, f1-f12, 1-9, letters
        key_name = key.lower()
        
        # Map common aliases to AHK key names
        key_map = {
            'escape': 'esc',
            'control': 'ctrl',
            'return': 'enter',
        }
        key_name = key_map.get(key_name, key_name)
        
        for _ in range(presses):
            ahk.key_press(key_name)
            if presses > 1 and interval > 0:
                time.sleep(max(interval, 0.05))
    except Exception as e:
        logger.error(f"AutoHotkey key press error: {e}")
        pass


def move_mouse_to(x: int, y: int, duration: float = 0.0):
    """Move mouse to absolute screen coordinates using AutoHotkey."""
    try:
        # AHK mouse_move uses absolute screen coordinates
        if duration > 0:
            # For smooth movement, calculate steps
            current_pos = ahk.mouse_position
            steps = max(int(duration * 60), 1)  # 60 steps per second
            for i in range(steps + 1):
                t = i / steps
                intermediate_x = int(current_pos[0] + (x - current_pos[0]) * t)
                intermediate_y = int(current_pos[1] + (y - current_pos[1]) * t)
                ahk.mouse_move(intermediate_x, intermediate_y, speed=0)
                time.sleep(duration / steps)
        else:
            ahk.mouse_move(x, y, speed=0)
        time.sleep(0.05)
    except Exception as e:
        logger.error(f"AutoHotkey mouse move error: {e}")
        pass


def click_at(x: int, y: int, button: str = 'left', clicks: int = 1, interval: float = 0.1):
    """Click at specific screen coordinates using AutoHotkey."""
    try:
        move_mouse_to(x, y)
        time.sleep(0.1)
        
        # AHK click function: button parameter is 'L', 'R', or 'M'
        button_map = {
            'left': 'L',
            'right': 'R', 
            'middle': 'M'
        }
        ahk_button = button_map.get(button.lower(), 'L')
        
        for _ in range(clicks):
            ahk.click(x, y, button=ahk_button)
            if clicks > 1 and interval > 0:
                time.sleep(max(interval, 0.1))
    except Exception as e:
        logger.error(f"AutoHotkey click error: {e}")
        pass


def double_click_at(x: int, y: int):
    """Double-click at specific screen coordinates using AutoHotkey."""
    try:
        move_mouse_to(x, y)
        time.sleep(0.1)
        
        # AHK supports click count parameter
        ahk.click(x, y, button='L', click_count=2)
        time.sleep(0.05)
    except Exception as e:
        logger.error(f"AutoHotkey double-click error: {e}")
        pass