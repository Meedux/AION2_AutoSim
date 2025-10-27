"""window_manager.py
Lightweight window manager for selecting/focusing game clients.

This module prefers `pygetwindow` if available; otherwise it logs actions
and provides a safe fallback so the rest of the project can operate in
environments without the dependency.
"""
from __future__ import annotations
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

try:
    import pygetwindow as gw
except Exception:
    gw = None


class WindowManager:
    def __init__(self, safe_mode: bool = True):
        self.safe_mode = safe_mode

    def list_windows(self, title_contains: Optional[str] = None) -> List[str]:
        """Return list of window titles (or empty list if unavailable)."""
        if not gw:
            logger.debug("pygetwindow not available; returning empty window list")
            return []
        titles = gw.getAllTitles()
        if title_contains:
            return [t for t in titles if title_contains.lower() in (t or "").lower()]
        return [t for t in titles if t]

    def focus_window(self, title: str) -> bool:
        """Attempt to focus a window with the exact title. Returns True on success."""
        logger.info("Request to focus window '%s' (safe_mode=%s)", title, self.safe_mode)
        if self.safe_mode:
            logger.debug("Window focus skipped because safe_mode=True")
            return False
        if not gw:
            logger.warning("pygetwindow not available; cannot focus window")
            return False
        wins = gw.getWindowsWithTitle(title)
        if not wins:
            logger.warning("No window found with title: %s", title)
            return False
        try:
            wins[0].activate()
            return True
        except Exception as e:
            logger.exception("Failed to activate window '%s': %s", title, e)
            return False
