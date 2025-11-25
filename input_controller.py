"""
High-level input controller using pydirectinput (cross-validated with PyAutoGUI naming).

This module replaces the old SendInput-based controller and exposes the same
public API used across the codebase so other modules (ActionPlanner,
SkillComboManager, main.py) can remain unchanged.

Behavior
- When pydirectinput is available we use it for all keyboard/mouse actions.
- If pydirectinput is not installed the module falls back to a DRY_RUN mode
  where calls are logged and return success (useful for CI / headless tests).

Important: pydirectinput follows the same key naming conventions as PyAutoGUI
for common keys. We translate a handful of repo-specific symbols (-, =) to
their pydirectinput names ('minus','equals').
"""
from typing import Optional
import time
import logging
import win32gui
import win32con

logger = logging.getLogger(__name__)

try:
    import pydirectinput
    PDI_AVAILABLE = True
except Exception:
    pydirectinput = None  # type: ignore
    PDI_AVAILABLE = False
    logger.warning("pydirectinput not available — input_controller in DRY_RUN mode")

# Compatibility / state
ACTIVE_HWND: Optional[int] = None


def open_driver(path: str = None):
    # compatibility shim — always ready
    return True


def close():
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
    """Restore and set the target window to foreground (best-effort)."""
    try:
        if not hwnd:
            return
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.02)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.1)
    except Exception:
        # best-effort only
        logger.debug("focus_window: unable to focus hwnd=%s" % (str(hwnd)))


# Local helper for key name translation
_KEY_TRANSLATION = {
    '-': 'minus',
    '=': 'equals',
}


def _translate_key(key: str) -> str:
    if not isinstance(key, str):
        return str(key).lower()
    k = key.lower().strip()
    return _KEY_TRANSLATION.get(k, k)


def tap_key(key: str, presses: int = 1, interval: float = 0.05):
    """Press a key (or numeric keys) using pydirectinput.press.

    Returns True on success. In DRY_RUN mode logs the call and returns True.
    """
    key_name = _translate_key(key)
    if not PDI_AVAILABLE:
        logger.info(f"DRY_RUN: tap_key({key_name}, presses={presses}, interval={interval})")
        return True

    try:
        for i in range(presses):
            pydirectinput.press(key_name)
            if presses > 1 and i < presses - 1:
                time.sleep(max(interval, 0.01))
        return True
    except Exception as e:
        logger.error(f"tap_key failed: {e}")
        return False


def hold_key(key: str, duration: float):
    key_name = _translate_key(key)
    if not PDI_AVAILABLE:
        logger.info(f"DRY_RUN: hold_key({key_name}, duration={duration})")
        return True

    try:
        pydirectinput.keyDown(key_name)
        time.sleep(max(0.0, duration))
        pydirectinput.keyUp(key_name)
        return True
    except Exception as e:
        logger.error(f"hold_key failed: {e}")
        return False


def move_mouse_to(x: int, y: int, duration: float = 0.0):
    """Move mouse to (x,y). Duration is forwarded to pydirectinput.moveTo.

    In DRY_RUN mode logs the call and returns True.
    """
    if not PDI_AVAILABLE:
        logger.info(f"DRY_RUN: move_mouse_to({x},{y}, duration={duration})")
        return True
    try:
        # pydirectinput uses screen coordinates
        pydirectinput.moveTo(x, y, duration=duration)
        return True
    except Exception as e:
        logger.error(f"move_mouse_to failed: {e}")
        return False


def click_at(x: int, y: int, button: str = 'left', clicks: int = 1, interval: float = 0.1):
    if not PDI_AVAILABLE:
        logger.info(f"DRY_RUN: click_at({x},{y}, button={button}, clicks={clicks}, interval={interval})")
        return True
    try:
        # pydirectinput functions accept x,y coordinates
        for i in range(clicks):
            pydirectinput.click(x=x, y=y, button=button)
            if i < clicks - 1:
                time.sleep(max(interval, 0.01))
        return True
    except Exception as e:
        logger.error(f"click_at failed: {e}")
        return False


def double_click_at(x: int, y: int):
    return click_at(x, y, button='left', clicks=2, interval=0.08)


def perform_human_attack_click(x: int, y: int):
    # Compatibility helper: historically this performed a double-click attack.
    # ActionPlanner now uses keyboard-based targeting (Tab + R/T) so callers
    # should prefer the new behavior, but keep this function for backward-compat.
    return double_click_at(x, y)


def press_key_combination(modifier: str, key: str):
    """Hold modifier, press key, release modifier.

    Supported modifiers: 'alt', 'ctrl' (case-insensitive).
    """
    mod = modifier.lower() if modifier else ''
    key_name = _translate_key(key)
    if not PDI_AVAILABLE:
        logger.info(f"DRY_RUN: press_key_combination({mod}, {key_name})")
        return True

    try:
        mod_key = 'alt' if mod == 'alt' else 'ctrl' if mod in ('ctrl', 'control') else None
        if mod_key is None:
            logger.warning(f"Unsupported modifier: {modifier}")
            return False
        pydirectinput.keyDown(mod_key)
        pydirectinput.press(key_name)
        pydirectinput.keyUp(mod_key)
        return True
    except Exception as e:
        logger.error(f"press_key_combination failed: {e}")
        return False


# module init
try:
    open_driver()
except Exception:
    pass
