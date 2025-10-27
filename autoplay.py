"""autoplay.py
AutoPlayController: handles auto-hunt, movement, loot, AI state.
Boilerplate with clear extension points.
"""
from __future__ import annotations
from typing import Tuple, Optional, List
import logging
from player import Player
from map import GridMap, Enemy, ResourceNode
from combat import CombatEngine
from macro import MacroController
from window_manager import WindowManager
from pathfinding import astar

logger = logging.getLogger(__name__)


class AIState:
    AGGRESSIVE = "aggressive"
    DEFENSIVE = "defensive"
    PASSIVE = "passive"


class AutoPlayController:
    def __init__(
        self,
        player: Player,
        grid: GridMap,
        macro: Optional[MacroController] = None,
        window_manager: Optional[WindowManager] = None,
        inventory_capacity: int = 30,
        hp_potion_name: str = "hp_potion",
        potion_refill_amount: int = 10,
    ):
        self.player = player
        self.grid = grid
        self.combat = CombatEngine()
        self.state = AIState.AGGRESSIVE
        self.target = None
        self.macro = macro or MacroController(safe_mode=True)
        self.window_manager = window_manager or WindowManager(safe_mode=True)
        self.inventory_capacity = inventory_capacity
        self.hp_potion_name = hp_potion_name
        self.potion_refill_amount = potion_refill_amount

    def find_target(self) -> Optional[Enemy]:
        # find nearest enemy based on simple radius search around player
        nearby = self.grid.get_enemies_near(self.player.pos, radius=6)
        return nearby[0] if nearby else None

    def auto_hunt(self) -> None:
        # stub: pick target, move, attack
        target = self.find_target()
        if not target:
            logger.debug("No targets found")
            return
        logger.info("Auto-hunt target found: %s at %s", target.name, target.pos)
        # move to target (pathfinding) - placeholder
        self.go_to(target.pos)
        self.combat.attack(self.player, target)
        if not target.is_alive():
            logger.info("Target %s defeated. Looting...", target.name)
            self.collect_loot(target)

    def collect_loot(self, enemy: Enemy) -> None:
        for item, qty in enemy.loot_table.items():
            self.player.add_item(item, qty)
            logger.info("Picked up %s x%d", item, qty)

    def auto_heal(self) -> None:
        # use a potion automatically when HP low
        hp_pct = self.player.hp / max(1, self.player.max_hp)
        if hp_pct < 0.3:
            potions = self.player.inventory.get(self.hp_potion_name, 0)
            if potions > 0:
                logger.info("HP low (%.2f) - consuming potion", hp_pct)
                self.player.inventory[self.hp_potion_name] = potions - 1
                self.player.heal(int(self.player.max_hp * 0.4))
            else:
                logger.info("No potions left; need to return to village")

    def inventory_full(self) -> bool:
        # simple slot-based capacity: total item count
        total_items = sum(self.player.inventory.values())
        return total_items >= self.inventory_capacity

    def potions_empty(self) -> bool:
        return self.player.inventory.get(self.hp_potion_name, 0) <= 0

    def go_to(self, pos: Tuple[int, int]) -> None:
        # use A* to compute path on the grid and simulate movement
        path = astar(self.grid.width, self.grid.height, self.player.pos, pos)
        if not path:
            logger.warning("No path found from %s to %s", self.player.pos, pos)
            return
        # step along path (we'll just update player.pos and optionally send macro actions)
        for step in path[1:]:
            logger.debug("Moving from %s to %s", self.player.pos, step)
            # simulate movement action via macro (safe_mode will only log)
            # real implementation should map steps to keystrokes or clicks
            try:
                self.macro.sequence([])
            except Exception:
                # if macro not fully available just continue
                pass
            self.player.pos = step

    def return_to_village(self, village_pos: Tuple[int, int]) -> None:
        logger.info("Initiating return to village from %s", self.player.pos)
        origin = self.player.pos
        # move to village
        self.go_to(village_pos)
        # perform village actions: sell/dispose and register exchange
        self.village_actions()
        # refill potions
        self.refill_potions()
        # return to origin hunting ground
        logger.info("Returning to hunting ground at %s", origin)
        self.go_to(origin)

    def village_actions(self) -> None:
        # stub: sell unwanted items
        keep_items = {self.hp_potion_name}
        sold = {}
        for item in list(self.player.inventory.keys()):
            if item in keep_items:
                continue
            qty = self.player.inventory.pop(item, 0)
            if qty:
                sold[item] = qty
                # fake gold reward per item
                self.player.gold += qty * 1
                logger.info("Sold %s x%d for %d gold", item, qty, qty * 1)
        # stub: register some items on exchange (log only)
        logger.info("Registered %d item types on exchange (stub)", len(sold))

    def refill_potions(self) -> None:
        cur = self.player.inventory.get(self.hp_potion_name, 0)
        need = max(0, self.potion_refill_amount - cur)
        if need > 0:
            # pretend buying potions costs gold
            cost = need * 1
            if self.player.gold >= cost:
                self.player.gold -= cost
                self.player.inventory[self.hp_potion_name] = cur + need
                logger.info("Refilled %d potions (cost %d gold)", need, cost)
            else:
                # not enough gold — just set to zero/leave as is
                logger.info("Not enough gold to refill potions (have %d, need %d)", self.player.gold, cost)

    def tick(self) -> None:
        # called every simulation tick
        self.auto_heal()

        # check inventory / potion conditions
        if self.inventory_full() or self.potions_empty():
            # for demo, village is at (0,0)
            self.return_to_village((0, 0))
            return

        if self.state == AIState.AGGRESSIVE:
            self.auto_hunt()
