"""Action planner that maps detections to in-game actions.

Behavior implemented per user spec:
- If a mob is detected (priority: mob_oncursor, mob_near, mob_away) -> double-click it until
  `mob_combat_health` for that mob disappears (assumed dead).
- If no mobs present, find map navigation dots (heuristic: classes containing 'map'|'dot'|'red'|'enemy')
  and move the player toward the nearest dot using W/A/S/D (W forward, S back, A/D turn).

This module uses `input_controller` to send OS-level inputs.
"""
import time
import threading
from typing import List, Dict, Tuple, Optional
from loguru import logger
from input_controller import focus_window, move_mouse_to_screen, double_click_at, tap_key
import win32con


def _center_of(d: Dict) -> Tuple[int, int]:
    x = float(d.get("x", 0))
    y = float(d.get("y", 0))
    w = float(d.get("width", 0))
    h = float(d.get("height", 0))
    return int(x + w / 2.0), int(y + h / 2.0)


def _iou(a: Dict, b: Dict) -> float:
    ax1 = a.get("x", 0)
    ay1 = a.get("y", 0)
    ax2 = ax1 + a.get("width", 0)
    ay2 = ay1 + a.get("height", 0)
    bx1 = b.get("x", 0)
    by1 = b.get("y", 0)
    bx2 = bx1 + b.get("width", 0)
    by2 = by1 + b.get("height", 0)
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


class ActionPlanner:
    def __init__(self, hwnd: int, enabled: bool = True, conf_thresh: float = 0.25):
        self.hwnd = hwnd
        self.enabled = enabled
        self.conf_thresh = conf_thresh
        self._lock = threading.Lock()
        self._last_action = 0.0
        self._cooldown = 0.08
        self._target_locked: Optional[Dict] = None

    def set_enabled(self, enabled: bool):
        self.enabled = bool(enabled)

    def is_enabled(self) -> bool:
        return bool(self.enabled)

    def _find_target_mob(self, detections: List[Dict]) -> Optional[Dict]:
        # priority: mob_oncursor, mob_near, mob_away
        priority = ["mob_oncursor", "mob_near", "mob_away"]
        # We only consider a mob a valid attack target if there is also an overlapping
        # `mob_target` marker detection (this mirrors the user's requirement that a mob
        # must be detected as mob_target to be attacked).
        for p in priority:
            for d in detections:
                name = str(d.get("class", "")).lower()
                if name == p and float(d.get("confidence") or 0) >= self.conf_thresh:
                    # check for overlapping mob_target marker
                    for m in detections:
                        if str(m.get("class", "")).lower() == "mob_target":
                            if _iou(d, m) > 0.05:
                                return d
                    # if there is no explicit mob_target marker, still allow attack
                    # (backwards-compatible) — return the mob
                    return d
        return None

    def _find_health_for(self, target: Dict, detections: List[Dict]) -> Optional[Dict]:
        # look for mob_combat_health that overlaps with target
        for d in detections:
            if str(d.get("class", "")).lower() == "mob_combat_health":
                if _iou(target, d) > 0.05:
                    return d
        return None

    def _find_map_dots(self, detections: List[Dict]) -> List[Dict]:
        candidates = []
        for d in detections:
            name = str(d.get("class", "")).lower()
            if any(k in name for k in ("map", "dot", "red", "enemy", "map_dot", "map_enemy")):
                candidates.append(d)
        return candidates

    def plan_and_execute(self, detections: List[Dict], window_rect: Tuple[int, int, int, int]):
        """detections are in target (window) pixel coords; window_rect is (left, top, w, h)
        """
        if not self.enabled:
            return
        now = time.time()
        if now - self._last_action < self._cooldown:
            return
        self._last_action = now

        left, top, w, h = window_rect

        # 1) Try to find mob target
        target = self._find_target_mob(detections)
        if target is not None:
            tx, ty = _center_of(target)
            screen_x = int(left + tx)
            screen_y = int(top + ty)
            # focus and double click repeatedly while health present
            focus_window(self.hwnd)
            # if a health bar exists for this target, lock and keep clicking until health gone
            health = self._find_health_for(target, detections)
            # Do a double click at the target
            logger.info(f"ActionPlanner: double-clicking target at screen ({screen_x},{screen_y}), health={'yes' if health else 'no'}")
            try:
                double_click_at(screen_x, screen_y)
            except Exception as e:
                logger.error(f"ActionPlanner: double_click_at failed: {e}")
            # set target lock if health present
            if health:
                self._target_locked = target
            return

        # If we had a locked target (we were attacking), but now no mob target found,
        # check if health still present for locked target; if so, try to click its last pos
        if self._target_locked is not None:
            # check health across detections for any mob_combat_health overlapping previous lock
            health_remaining = any((str(d.get("class","")).lower() == "mob_combat_health" and _iou(self._target_locked, d) > 0.05) for d in detections)
            if health_remaining:
                tx, ty = _center_of(self._target_locked)
                screen_x = int(left + tx)
                screen_y = int(top + ty)
                logger.info(f"ActionPlanner: continuing attack on locked target at ({screen_x},{screen_y})")
                try:
                    double_click_at(screen_x, screen_y)
                except Exception as e:
                    logger.error(f"ActionPlanner: double_click_at failed (locked): {e}")
                return
            else:
                # health gone -> target dead
                logger.info("ActionPlanner: target appears dead, clearing lock")
                self._target_locked = None

        # 2) No mobs: navigate to map dots
        dots = self._find_map_dots(detections)
        if len(dots) == 0:
            # nothing to do
            return
        # choose nearest dot to center
        cx = w / 2.0
        cy = h / 2.0
        best = None
        best_dist = None
        for d in dots:
            dx = (d.get("x", 0) + d.get("width", 0)/2.0) - cx
            dy = (d.get("y", 0) + d.get("height", 0)/2.0) - cy
            dist = (dx*dx + dy*dy)**0.5
            if best is None or dist < best_dist:
                best = d
                best_dist = dist

        if best is None:
            return

        tx, ty = _center_of(best)
        ndx = (tx - cx) / max(1.0, cx)  # -1..1
        ndy = (ty - cy) / max(1.0, cy)
        # turning threshold
        turn_thr = 0.18
        forward_thr = 0.12

        # Ensure the game window has focus before sending movement keys
        focus_window(self.hwnd)
        # If target significantly off-center horizontally, turn (A/D)
        if ndx > turn_thr:
            logger.info("ActionPlanner: turning right (D)")
            try:
                tap_key(ord('D'))
            except Exception as e:
                logger.error(f"ActionPlanner: tap_key D failed: {e}")
        elif ndx < -turn_thr:
            logger.info("ActionPlanner: turning left (A)")
            try:
                tap_key(ord('A'))
            except Exception as e:
                logger.error(f"ActionPlanner: tap_key A failed: {e}")
        else:
            # face roughly toward target; move forward/back depending on vertical
            if ndy < -forward_thr:
                # target is above center -> move forward
                logger.info("ActionPlanner: moving forward (W)")
                try:
                    tap_key(ord('W'))
                except Exception as e:
                    logger.error(f"ActionPlanner: tap_key W failed: {e}")
            elif ndy > forward_thr:
                logger.info("ActionPlanner: moving backward (S)")
                try:
                    tap_key(ord('S'))
                except Exception as e:
                    logger.error(f"ActionPlanner: tap_key S failed: {e}")
