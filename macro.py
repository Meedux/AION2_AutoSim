"""macro.py
Platform input automation adapter (boilerplate).

This module provides a safe wrapper around OS input libraries like
`pyautogui` and `pynput`. By default it runs in `safe_mode=True` which will
only log simulated actions instead of sending real keypresses/mouse events.

IMPORTANT: Using automation to control third-party games can violate Terms of
Service; only use these tools for local testing, simulation, or with explicit
permission. The code below intentionally defaults to non-invasive behavior.
"""
from __future__ import annotations
import logging
from typing import Iterable, Tuple

logger = logging.getLogger(__name__)

# Attempt optional imports
try:
    import pyautogui
except Exception:
    pyautogui = None

try:
    from pynput.keyboard import Controller as KeyboardController, Key
    from pynput.mouse import Controller as MouseController
except Exception:
    KeyboardController = None
    MouseController = None


class MacroController:
    def __init__(self, safe_mode: bool = True):
        """safe_mode=True logs actions instead of sending them to the OS.

        Set safe_mode=False only when you're absolutely sure you want to send
        real input events to the OS. Keep in mind this can affect other
        applications if window focus changes.
        """
        self.safe_mode = safe_mode
        self.kb = KeyboardController() if KeyboardController and not safe_mode else None
        self.mouse = MouseController() if MouseController and not safe_mode else None

    def press(self, key: str) -> None:
        logger.info("Macro press: %s (safe_mode=%s)", key, self.safe_mode)
        if not self.safe_mode:
            if pyautogui:
                pyautogui.press(key)
            elif self.kb:
                # basic support for single-character keys
                self.kb.press(key)
                self.kb.release(key)

    def key_down(self, key: str) -> None:
        logger.info("Macro key_down: %s (safe_mode=%s)", key, self.safe_mode)
        if not self.safe_mode and self.kb:
            self.kb.press(key)

    def key_up(self, key: str) -> None:
        logger.info("Macro key_up: %s (safe_mode=%s)", key, self.safe_mode)
        if not self.safe_mode and self.kb:
            self.kb.release(key)

    def type_text(self, text: str, interval: float = 0.0) -> None:
        logger.info("Macro type_text: %s (safe_mode=%s)", text, self.safe_mode)
        if not self.safe_mode and pyautogui:
            pyautogui.typewrite(text, interval=interval)

    def click(self, x: int = None, y: int = None, button: str = "left") -> None:
        logger.info("Macro click: (%s,%s) button=%s (safe_mode=%s)", x, y, button, self.safe_mode)
        if not self.safe_mode and pyautogui:
            if x is None or y is None:
                pyautogui.click(button=button)
            else:
                pyautogui.click(x, y, button=button)

    def sequence(self, actions: Iterable[Tuple[str, dict]]) -> None:
        """Execute a sequence of (method_name, kwargs) actions.

        Example: [('press', {'key': 'space'}), ('click', {'x':100,'y':200})]
        """
        for method, kwargs in actions:
            fn = getattr(self, method, None)
            if fn:
                fn(**kwargs)


def sample_macro_controller() -> MacroController:
    return MacroController(safe_mode=True)
