"""autoplay.py
AutoPlayController: handles auto-hunt, movement, loot, AI state.
Boilerplate with clear extension points.
"""
from __future__ import annotations
from typing import Tuple, Optional
import logging
from player import Player
from map import GridMap, Enemy, ResourceNode
from combat import CombatEngine

logger = logging.getLogger(__name__)


class AIState:
    AGGRESSIVE = "aggressive"
    DEFENSIVE = "defensive"
    PASSIVE = "passive"


class AutoPlayController:
    def __init__(self, player: Player, grid: GridMap):
        self.player = player
        self.grid = grid
        self.combat = CombatEngine()
        self.state = AIState.AGGRESSIVE
        self.target = None

    def find_target(self) -> Optional[Enemy]:
        # find nearest enemy based on simple radius search
        # placeholder uses 5 tile radius
        nearby = self.grid.get_enemies_near((0, 0), radius=100)
        return nearby[0] if nearby else None

    def auto_hunt(self) -> None:
        # stub: pick target, move, attack
        target = self.find_target()
        if not target:
            logger.debug("No targets found")
            return
        logger.info("Auto-hunt target found: %s at %s", target.name, target.pos)
        self.combat.attack(self.player, target)
        if not target.is_alive():
            logger.info("Target %s defeated. Looting...", target.name)
            self.collect_loot(target)

    def collect_loot(self, enemy: Enemy) -> None:
        for item, qty in enemy.loot_table.items():
            self.player.add_item(item, qty)
            logger.info("Picked up %s x%d", item, qty)

    def auto_heal(self) -> None:
        # stub logic
        hp_pct = self.player.hp / self.player.max_hp
        if hp_pct < 0.3:
            logger.info("HP low (%.2f) - using potion", hp_pct)
            self.player.heal(20)

    def tick(self) -> None:
        # called every simulation tick
        self.auto_heal()
        if self.state == AIState.AGGRESSIVE:
            self.auto_hunt()
