"""combat.py
Combat engine and cooldown management (boilerplate).
"""
from __future__ import annotations
from typing import Optional
from player import Player, Skill
import logging

logger = logging.getLogger(__name__)


class CombatEngine:
    def __init__(self):
        # placeholder for state like active fights, aggro tables, etc.
        pass

    def calculate_damage(self, attacker: Player, defender_hp: int, skill: Optional[Skill] = None) -> int:
        base = attacker.attack
        if skill:
            base += skill.power
        # simple formula placeholder
        dmg = max(1, base - int(defender_hp * 0.01))
        logger.debug("Calculated damage: %s", dmg)
        return dmg

    def attack(self, attacker: Player, enemy) -> None:
        # enemy is a map.Enemy instance
        skill = attacker.skills.get("basic")
        if skill and attacker.use_skill(skill.id):
            dmg = self.calculate_damage(attacker, enemy.hp, skill)
        else:
            dmg = self.calculate_damage(attacker, enemy.hp)
        enemy.hp = max(0, enemy.hp - dmg)
        logger.info("%s attacked %s for %d damage (enemy hp %d)", attacker.name, enemy.name, dmg, enemy.hp)
