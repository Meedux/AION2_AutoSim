"""Action planner that maps detections to in-game actions.

Behavior implemented per user spec:
 - The planner ONLY reacts to detections with class `monster`.
 - On detection the planner uses keyboard targeting: press `Tab` to lock the target and use `R`/`T` for light/heavy single-press attacks (no mouse double-clicks, no movement macros).
 - After target acquisition the planner enters a COMBAT period (duration depends on target size & distance, minimum 5s) then a 5s cooldown where `F` is pressed randomly.

This module uses `input_controller` to send OS-level inputs.

(Stealth mode removed) Uses deterministic timings and immediate actions.
"""
import time
import threading
from typing import List, Dict, Tuple, Optional
from loguru import logger
import input_controller as ic
import skill_combo_config
import random


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
        # Use non-stealth deterministic timing
        self._cooldown = 0.2
        # previous target lock removed; use self._current_target state instead
        
        # Warmup/idle tracking removed (no stealth behavior)
        self._action_count = 0
        
        # Skill Combo Manager - handles skill macros with cooldown tracking
        try:
            from skill_combo_manager import SkillComboManager
            self.skill_combo_manager = SkillComboManager(hwnd)
            logger.info("✓ Skill Combo Manager integrated into Action Planner")
        except Exception as e:
            logger.warning(f"Skill Combo Manager not available: {e}")
            self.skill_combo_manager = None
        # New state machine: scanning -> combat -> cooldown
        self._mode = 'scanning'  # scanning | combat | cooldown
        self._current_target: Optional[Dict] = None
        self._combat_until = 0.0
        self._cooldown_until = 0.0
        self._last_attack = 0.0
        self._attack_interval = (0.45, 1.25)  # seconds between R/T presses during combat
        self._last_cooldown_action = 0.0
        self._cooldown_f_interval = (0.6, 1.8)  # random press F intervals during 5s cooldown

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

    def _find_all_monsters(self, detections: List[Dict]) -> List[Dict]:
        """Return all detections that match the 'monster' class using the new model.

        The updated model only outputs detections with class 'monster' for enemies.
        """
        out = []
        for d in detections:
            name = str(d.get('class', '')).lower()
            # New model uses exact class 'monster'
            if name == 'monster':
                try:
                    if float(d.get('confidence', 0.0)) >= self.conf_thresh:
                        out.append(d)
                except Exception:
                    out.append(d)
        return out

    def _compute_combat_duration(self, target: Dict, window_w: int, window_h: int) -> float:
        """Heuristic: base 5s + scaled by target size and distance to lower-center of screen.

        Larger targets and targets further from the player's lower-center require longer combat windows.
        """
        try:
            tw = float(target.get('width', 0))
            th = float(target.get('height', 0))
            tx, ty = _center_of(target)
        except Exception:
            return 5.0

        area = max(1.0, tw * th)
        window_area = max(1.0, window_w * window_h)
        area_ratio = area / window_area  # small value e.g. 0.01

        # Lower-center reference point (player is slightly lower than center)
        px = window_w / 2.0
        py = window_h * 0.70
        dist = ((tx - px) ** 2 + (ty - py) ** 2) ** 0.5
        max_diag = (window_w ** 2 + window_h ** 2) ** 0.5
        dist_ratio = dist / max(1.0, max_diag)

        # scale more with size than distance. Keep within reasonable bounds
        extra = (area_ratio * 30.0) + (dist_ratio * 8.0)
        duration = max(5.0, 5.0 + extra)
        # clamp to a sane max (e.g., 20s)
        return min(duration, 20.0)
    
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
    
    # Movement macros removed — this planner focuses on scanning -> combat -> cooldown.

    def plan_and_execute(self, detections: List[Dict], window_rect: Tuple[int, int, int, int]):
        """detections are in target (window) pixel coords; window_rect is (left, top, w, h)
        """
        if not self.enabled:
            return
        
        now = time.time()
        
        # Idle simulation removed (deterministic, continuous execution)
        
        # SYNC FIX: Detection loop controls timing at 1 FPS
        # Action planner executes on EVERY detection update (no extra cooldown)
        # This keeps detection overlay and combat actions perfectly synchronized
        
        # Warmup removed — no extra delays
        
        self._last_action = now
        self._action_count += 1

        left, top, w, h = window_rect

        # Global cooldown behavior: if in cooldown mode, randomly press F during the cooldown window
        if self._mode == 'cooldown':
            if time.time() < self._cooldown_until:
                # schedule random F presses during cooldown
                if time.time() - self._last_cooldown_action >= random.uniform(*self._cooldown_f_interval):
                    try:
                        ic.focus_window(self.hwnd)
                        ic.tap_key('f')
                        self._last_cooldown_action = time.time()
                        logger.info("ActionPlanner(COOLDOWN): pressed 'F' during cooldown")
                    except Exception as e:
                        logger.error(f"ActionPlanner(COOLDOWN): failed to press F: {e}")
                return
            else:
                # cooldown finished — go back to scanning
                self._mode = 'scanning'
                self._current_target = None
                logger.info("ActionPlanner: cooldown finished, back to scanning")

        # 1) New MONSTER targeting + combat state-machine
        mobs = self._find_all_monsters(detections)

        # SCANNING: detect mobs and acquire a target
        if self._mode == 'scanning':
            if mobs:
                # Choose a reasonable candidate: prefer nearest to lower-center (player area)
                px = w / 2.0
                py = h * 0.70
                def score_m(d):
                    cx, cy = _center_of(d)
                    # smaller score = better (closer and larger)
                    dist = ((cx - px) ** 2 + (cy - py) ** 2) ** 0.5
                    area = (d.get('width', 0) or 0) * (d.get('height', 0) or 0)
                    return dist - (area * 0.05)

                mobs.sort(key=score_m)
                candidate = mobs[0]

                # Acquire target: press tab to lock-on and then trigger an attack (R or T)
                try:
                    ic.focus_window(self.hwnd)
                    # Press Tab to target (one press)
                    ic.tap_key('tab')
                    ic.tap_key('tab')
                    # small human-like delay
                    time.sleep(random.uniform(0.08, 0.20))
                    # press either 'r' or 't' once
                    atk = random.choice(['r', 't'])
                    ic.tap_key(atk)
                    ic.tap_key(atk)
                    logger.info(f"ActionPlanner: target acquired via TAB and initial attack '{atk.upper()}'")
                except Exception as e:
                    logger.error(f"ActionPlanner: initial target/attack failed: {e}")

                # start combat mode with duration based on target size/distance
                dur = self._compute_combat_duration(candidate, w, h)
                self._current_target = candidate
                self._combat_until = time.time() + dur
                self._mode = 'combat'
                self._last_attack = 0.0
                logger.info(f"ActionPlanner: entering COMBAT mode for {dur:.1f}s")
                return

        # During COMBAT, perform R/T attacks at humanlike intervals
        if self._mode == 'combat':
            if time.time() < self._combat_until:
                # Attack cadence - do R or T single presses
                if time.time() - self._last_attack >= random.uniform(*self._attack_interval):
                    ic.focus_window(self.hwnd)
                    try:
                        atk = random.choice(['r', 't'])
                        ic.tap_key(atk)
                        self._last_attack = time.time()
                        logger.info(f"ActionPlanner(COMBAT): pressed '{atk.upper()}' (single) against target")
                    except Exception as e:
                        logger.error(f"ActionPlanner(COMBAT): attack press failed: {e}")
                return
            else:
                # combat period ended -> go to cooldown
                self._mode = 'cooldown'
                self._cooldown_until = time.time() + 5.0
                self._last_cooldown_action = 0.0
                logger.info("ActionPlanner: combat finished, entering 5s cooldown (F spam)")
                return

        # If we had a locked target (we were attacking), but now no monster target found,
        # check if health still present for locked target; if so, try to click its last pos
        if self._current_target is not None:
            # check health across detections for any mob_combat_health overlapping previous lock
            health_remaining = any((str(d.get("class","")) .lower() == "mob_combat_health" and _iou(self._current_target, d) > 0.05) for d in detections)
            if health_remaining:
                tx, ty = _center_of(self._current_target)
                screen_x = int(left + tx)
                screen_y = int(top + ty)
                # If health remains, stay engaged — press a small attack (R/T) occasionally
                if time.time() - self._last_attack >= random.uniform(*self._attack_interval):
                    ic.focus_window(self.hwnd)
                    try:
                        atk = random.choice(['r', 't'])
                        ic.tap_key(atk)
                        self._last_attack = time.time()
                        logger.info(f"ActionPlanner: locked target attack '{atk.upper()}'")
                    except Exception as e:
                        logger.error(f"ActionPlanner: locked attack failed: {e}")
                return
            else:
                # health gone -> target dead
                logger.info("ActionPlanner: target appears dead, clearing lock")
                self._current_target = None

        # 2) No monsters detected: do nothing (movement macros removed)
        # The planner will wait in scanning mode until a monster appears.
        if not mobs:
            return
        # No movement macros — when no monsters are detected, remain idle in scanning mode.
