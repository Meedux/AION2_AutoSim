"""player.py
Player stats, HP, MP, skills (boilerplate)

This module defines a Player dataclass and basic methods used by the autoplay
and combat systems. Implementation is intentionally minimal and documented so
features can be filled in later.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Callable
import time


@dataclass
class Skill:
    id: str
    name: str
    cooldown: float
    last_used: float = field(default=0.0)
    power: int = field(default=0)

    def ready(self) -> bool:
        return (time.time() - self.last_used) >= self.cooldown

    def use(self) -> None:
        self.last_used = time.time()


@dataclass
class Player:
    id: str
    name: str
    max_hp: int
    hp: int
    max_mp: int
    mp: int
    attack: int
    defense: int
    skills: Dict[str, Skill] = field(default_factory=dict)
    inventory: Dict[str, int] = field(default_factory=dict)
    stamina: float = 100.0

    def is_alive(self) -> bool:
        return self.hp > 0

    def take_damage(self, amount: int) -> None:
        self.hp = max(0, self.hp - amount)

    def heal(self, amount: int) -> None:
        self.hp = min(self.max_hp, self.hp + amount)

    def use_mana(self, amount: int) -> bool:
        if self.mp >= amount:
            self.mp -= amount
            return True
        return False

    def add_item(self, item_id: str, qty: int = 1) -> None:
        self.inventory[item_id] = self.inventory.get(item_id, 0) + qty

    def use_skill(self, skill_id: str) -> bool:
        skill = self.skills.get(skill_id)
        if not skill:
            return False
        if skill.ready():
            skill.use()
            return True
        return False


def sample_player() -> Player:
    p = Player(
        id="p1",
        name="TestPlayer",
        max_hp=100,
        hp=100,
        max_mp=50,
        mp=50,
        attack=10,
        defense=5,
    )
    p.skills["basic"] = Skill(id="basic", name="Strike", cooldown=1.0, power=10)
    p.skills["heavy"] = Skill(id="heavy", name="Heavy Blow", cooldown=5.0, power=30)
    return p
