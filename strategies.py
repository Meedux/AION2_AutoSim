"""strategies.py
Automation strategies and macro/action planners (boilerplate).

Contains placeholders for skill rotation, heal/buff management, and resource
gathering strategies. These classes will be used by `autoplay.py` to decide
what actions to execute and when.
"""
from __future__ import annotations
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class SkillRotation:
    def __init__(self, priority: List[str]):
        self.priority = priority

    def next_skill(self, player_state: Dict) -> str:
        # Return the next skill id to use based on player_state and priority
        for s in self.priority:
            # placeholder: in future check cooldowns and resource costs
            return s
        return ""


class HealManager:
    def __init__(self, hp_threshold: float = 0.3):
        self.hp_threshold = hp_threshold

    def should_heal(self, player_state: Dict) -> bool:
        hp_pct = player_state.get("hp", 1.0) / player_state.get("max_hp", 1)
        return hp_pct <= self.hp_threshold


class LootManager:
    def __init__(self):
        pass

    def should_pickup(self, item_id: str, importance: int = 0) -> bool:
        # placeholder logic
        return True
