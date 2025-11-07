"""Action planner that maps detections to in-game actions.

Behavior implemented per user spec:
- If a mob is detected (priority: mob_oncursor, mob_near, mob_away) -> double-click it until
  `mob_combat_health` for that mob disappears (assumed dead).
- If no mobs present, find map navigation dots (heuristic: classes containing 'map'|'dot'|'red'|'enemy')
  and move the player toward the nearest dot using W/A/S/D (W forward, S back, A/D turn).

This module uses `input_controller` to send OS-level inputs.

STEALTH MODE: Uses ultra-slow timing to avoid CryEngine anti-cheat detection.
"""
import time
import threading
from typing import List, Dict, Tuple, Optional
from loguru import logger
from input_controller import focus_window, double_click_at, tap_key
import random
import stealth_config


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
        # Use stealth timing - MUCH slower to avoid CryEngine detection
        self._cooldown = stealth_config.ACTION_COOLDOWN_MIN
        self._target_locked: Optional[Dict] = None
        
        # Warmup tracking - first N actions get extra delays
        self._action_count = 0
        self._last_idle_check = time.time()
        self._in_idle_state = False
        self._idle_until = 0.0
        
        # Movement macro state
        self._current_movement_pattern = stealth_config.get_movement_pattern()
        self._movement_pattern_start = 0.0
        self._movement_pattern_duration = stealth_config.get_movement_pattern_duration()

    def set_enabled(self, enabled: bool):
        self.enabled = bool(enabled)

    def is_enabled(self) -> bool:
        return bool(self.enabled)

    def _find_target_mob(self, detections: List[Dict]) -> Optional[Dict]:
        # priority: mob_oncursor, mob_near, mob_away
        priority = ["mob_oncursor", "mob_near", "mob_away"]
        
        # Get player position (center of screen)
        from utils import get_window_rect
        window_rect = get_window_rect(self.hwnd)
        if window_rect:
            _, _, screen_w, screen_h = window_rect
            player_x = screen_w / 2.0
            player_y = screen_h / 2.0
        else:
            player_x = player_y = 0
        
        # Collect all valid mob targets with their distances to player
        candidates = []
        
        for p in priority:
            for d in detections:
                name = str(d.get("class", "")).lower()
                if name == p and float(d.get("confidence") or 0) >= self.conf_thresh:
                    # check for overlapping mob_target marker
                    has_target_marker = False
                    for m in detections:
                        if str(m.get("class", "")).lower() == "mob_target":
                            if _iou(d, m) > 0.05:
                                has_target_marker = True
                                break
                    
                    # Calculate distance to player (center of screen)
                    mob_cx, mob_cy = _center_of(d)
                    distance = ((mob_cx - player_x) ** 2 + (mob_cy - player_y) ** 2) ** 0.5
                    
                    # Store candidate with priority weight and distance
                    priority_weight = priority.index(p)  # 0=oncursor, 1=near, 2=away
                    candidates.append((d, priority_weight, distance, has_target_marker))
        
        if not candidates:
            return None
        
        # Sort by: priority first (oncursor > near > away), then by distance (nearest first)
        # Prefer mobs with target markers
        candidates.sort(key=lambda x: (x[1], not x[3], x[2]))  # priority, not has_marker, distance
        
        return candidates[0][0]  # Return the closest mob with highest priority

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
    
    def _find_north_map_dots(self, dots: List[Dict], window_w: int, window_h: int) -> List[Dict]:
        """
        Find map dots that are in the 'north' direction relative to player.
        Assumes minimap is typically in top-right corner and player is at center.
        Dots above the player's position on minimap = north direction.
        """
        if not dots:
            return []
        
        # Find the minimap region (usually top-right quadrant)
        # Assume dots with x > window_w/2 and y < window_h/2 are on minimap
        map_dots = []
        for d in dots:
            dx = float(d.get("x", 0))
            dy = float(d.get("y", 0))
            # Minimap is typically in top-right
            if dx > window_w * 0.5 and dy < window_h * 0.5:
                map_dots.append(d)
        
        if not map_dots:
            return dots  # Fallback: return all dots
        
        # Find the center of minimap dots (approximate player position on minimap)
        avg_x = sum(float(d.get("x", 0)) for d in map_dots) / len(map_dots)
        avg_y = sum(float(d.get("y", 0)) for d in map_dots) / len(map_dots)
        
        # Dots with y < avg_y are "north" of player
        north_dots = [d for d in map_dots if float(d.get("y", 0)) < avg_y]
        
        return north_dots if north_dots else map_dots
    
    def _execute_movement_macro(self, pattern: str, duration: float):
        """
        Execute a randomized movement pattern.
        Patterns: forward, forward_zigzag, circle_left, circle_right, backup_turn, strafe_left, strafe_right
        """
        logger.info(f"Movement macro: {pattern} for {duration:.2f}s")
        focus_window(self.hwnd)
        
        if pattern == "forward":
            tap_key('w')
            time.sleep(duration)
        
        elif pattern == "forward_zigzag":
            # Forward with slight left/right adjustments
            end_time = time.time() + duration
            while time.time() < end_time:
                tap_key('w')
                time.sleep(0.3)
                if random.random() < 0.5:
                    tap_key('a')
                else:
                    tap_key('d')
                time.sleep(0.1)
        
        elif pattern == "circle_left":
            # Strafe left while moving forward
            end_time = time.time() + duration
            while time.time() < end_time:
                tap_key('w')
                tap_key('a')
                time.sleep(0.2)
        
        elif pattern == "circle_right":
            # Strafe right while moving forward
            end_time = time.time() + duration
            while time.time() < end_time:
                tap_key('w')
                tap_key('d')
                time.sleep(0.2)
        
        elif pattern == "backup_turn":
            # Backup and turn
            tap_key('s')
            time.sleep(duration * 0.5)
            if random.random() < 0.5:
                tap_key('a')
            else:
                tap_key('d')
            time.sleep(duration * 0.5)
        
        elif pattern == "strafe_left":
            tap_key('a')
            time.sleep(duration)
        
        elif pattern == "strafe_right":
            tap_key('d')
            time.sleep(duration)
        
        time.sleep(stealth_config.get_post_movement_delay())

    def plan_and_execute(self, detections: List[Dict], window_rect: Tuple[int, int, int, int]):
        """detections are in target (window) pixel coords; window_rect is (left, top, w, h)
        """
        if not self.enabled:
            return
        
        now = time.time()
        
        # Check if we're in idle simulation state
        if self._in_idle_state:
            if now < self._idle_until:
                return  # Still idling, do nothing
            else:
                self._in_idle_state = False
                logger.info("✓ Idle period ended, resuming actions")
        
        # Periodic idle simulation (simulates human "thinking")
        if now - self._last_idle_check > stealth_config.IDLE_CHECK_INTERVAL:
            self._last_idle_check = now
            if stealth_config.should_idle():
                idle_duration = stealth_config.get_idle_duration()
                self._in_idle_state = True
                self._idle_until = now + idle_duration
                logger.info(f"⏸ Entering idle state for {idle_duration:.1f}s (human simulation)")
                return
        
        # Apply stealth cooldown with randomization
        cooldown = stealth_config.get_action_delay()
        
        # Add extra delay for warmup actions (anti-cheat: simulate "getting oriented")
        if self._action_count < stealth_config.WARMUP_ACTIONS:
            warmup_delay = stealth_config.get_warmup_delay()
            cooldown += warmup_delay
            logger.debug(f"Warmup action {self._action_count + 1}/{stealth_config.WARMUP_ACTIONS} (+{warmup_delay:.1f}s)")
        
        if now - self._last_action < cooldown:
            return
        
        self._last_action = now
        self._action_count += 1

        left, top, w, h = window_rect

        # 1) Try to find mob target
        target = self._find_target_mob(detections)
        if target is not None:
            # Calculate target position - click in LOWER PART of detection box
            tx = float(target.get("x", 0))
            ty = float(target.get("y", 0))
            tw = float(target.get("width", 0))
            th = float(target.get("height", 0))
            
            # Click in the LOWER PART of the box (70-90% down from top)
            # This is WITHIN the box, not below it
            y_percentage = random.uniform(stealth_config.MOB_CLICK_Y_MIN, stealth_config.MOB_CLICK_Y_MAX)
            
            # Add mouse jitter (randomization)
            jitter_x, jitter_y = stealth_config.get_mouse_jitter()
            
            # Final click position (center X, lower part Y - WITHIN the box)
            click_x = tx + (tw / 2.0) + jitter_x
            click_y = ty + (th * y_percentage) + jitter_y
            
            screen_x = int(left + click_x)
            screen_y = int(top + click_y)
            
            # focus and double click repeatedly while health present
            focus_window(self.hwnd)
            # if a health bar exists for this target, lock and keep clicking until health gone
            health = self._find_health_for(target, detections)
            # Do a double click at the target
            logger.info(f"ActionPlanner: clicking mob at ({screen_x},{screen_y}) with jitter ({jitter_x},{jitter_y}), health={'yes' if health else 'no'}")
            focus_window(self.hwnd)  # Ensure focused before input
            try:
                double_click_at(screen_x, screen_y)
                # Add post-click delay (stealth)
                time.sleep(stealth_config.get_post_click_delay())
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
                focus_window(self.hwnd)  # Ensure focused before input
                try:
                    double_click_at(screen_x, screen_y)
                except Exception as e:
                    logger.error(f"ActionPlanner: double_click_at failed (locked): {e}")
                return
            else:
                # health gone -> target dead
                logger.info("ActionPlanner: target appears dead, clearing lock")
                self._target_locked = None

        # 2) No mobs: navigate using map dots (minimap red dots)
        dots = self._find_map_dots(detections)
        if len(dots) == 0:
            # No map dots - use movement macro to explore
            now = time.time()
            if stealth_config.should_change_movement_pattern() or \
               (now - self._movement_pattern_start > self._movement_pattern_duration):
                self._current_movement_pattern = stealth_config.get_movement_pattern()
                self._movement_pattern_duration = stealth_config.get_movement_pattern_duration()
                self._movement_pattern_start = now
            
            self._execute_movement_macro(
                self._current_movement_pattern,
                min(2.0, self._movement_pattern_duration)  # Max 2s per execution
            )
            return
        
        # Filter dots to find those in "north" direction (where player is facing)
        north_dots = self._find_north_map_dots(dots, w, h)
        if not north_dots:
            north_dots = dots  # Fallback
        
        # Choose nearest dot to center from north dots
        cx = w / 2.0
        cy = h / 2.0
        best = None
        best_dist = None
        for d in north_dots:
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
        
        # Wider turn threshold for 70-degree turns
        turn_thr_70deg = 0.30  # Requires more offset for 70-degree turn
        turn_thr_small = 0.15  # Small adjustments
        forward_thr = 0.12

        # Ensure the game window has focus before sending movement keys
        focus_window(self.hwnd)
        
        # Check if we need a 70-degree turn (large offset)
        if abs(ndx) > turn_thr_70deg:
            # Big turn (70 degrees)
            hold_duration = stealth_config.get_turn_70_degrees_duration()
            if ndx > 0:
                logger.info(f"ActionPlanner: BIG TURN right (D) ~70° for {hold_duration:.2f}s")
                focus_window(self.hwnd)
                try:
                    tap_key('d')
                    time.sleep(hold_duration)
                    time.sleep(stealth_config.get_post_movement_delay())
                except Exception as e:
                    logger.error(f"ActionPlanner: tap_key D failed: {e}")
            else:
                logger.info(f"ActionPlanner: BIG TURN left (A) ~70° for {hold_duration:.2f}s")
                focus_window(self.hwnd)
                try:
                    tap_key('a')
                    time.sleep(hold_duration)
                    time.sleep(stealth_config.get_post_movement_delay())
                except Exception as e:
                    logger.error(f"ActionPlanner: tap_key A failed: {e}")
        elif abs(ndx) > turn_thr_small:
            # Small turn adjustment
            hold_duration = stealth_config.get_key_hold_duration()
            if ndx > 0:
                logger.info(f"ActionPlanner: turning right (D) for {hold_duration:.2f}s")
                focus_window(self.hwnd)
                try:
                    tap_key('d')
                    time.sleep(hold_duration)
                    time.sleep(stealth_config.get_post_movement_delay())
                except Exception as e:
                    logger.error(f"ActionPlanner: tap_key D failed: {e}")
            else:
                logger.info(f"ActionPlanner: turning left (A) for {hold_duration:.2f}s")
                focus_window(self.hwnd)
                try:
                    tap_key('a')
                    time.sleep(hold_duration)
                    time.sleep(stealth_config.get_post_movement_delay())
                except Exception as e:
                    logger.error(f"ActionPlanner: tap_key A failed: {e}")
        else:
            # face roughly toward target; move forward/back depending on vertical
            if ndy < -forward_thr:
                # target is above center -> move forward
                hold_duration = stealth_config.get_key_hold_duration()
                logger.info(f"ActionPlanner: moving forward (W) for {hold_duration:.2f}s")
                focus_window(self.hwnd)  # Ensure focused before input
                try:
                    tap_key('w')
                    time.sleep(hold_duration)  # Hold the key
                    time.sleep(stealth_config.get_post_movement_delay())  # Post-movement delay
                except Exception as e:
                    logger.error(f"ActionPlanner: tap_key W failed: {e}")
            elif ndy > forward_thr:
                hold_duration = stealth_config.get_key_hold_duration()
                logger.info(f"ActionPlanner: moving backward (S) for {hold_duration:.2f}s")
                focus_window(self.hwnd)  # Ensure focused before input
                try:
                    tap_key('s')
                    time.sleep(hold_duration)  # Hold the key
                    time.sleep(stealth_config.get_post_movement_delay())  # Post-movement delay
                except Exception as e:
                    logger.error(f"ActionPlanner: tap_key S failed: {e}")
