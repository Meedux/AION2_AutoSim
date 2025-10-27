"""map.py
Grid map, enemies, and resource node boilerplate.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Tuple, List, Dict


Position = Tuple[int, int]


@dataclass
class Enemy:
    id: str
    name: str
    hp: int
    pos: Position
    loot_table: Dict[str, int] = field(default_factory=dict)

    def is_alive(self) -> bool:
        return self.hp > 0


@dataclass
class ResourceNode:
    id: str
    resource_type: str
    qty: int
    pos: Position


class GridMap:
    def __init__(self, width: int = 20, height: int = 20):
        self.width = width
        self.height = height
        self.enemies: List[Enemy] = []
        self.resources: List[ResourceNode] = []

    def in_bounds(self, pos: Position) -> bool:
        x, y = pos
        return 0 <= x < self.width and 0 <= y < self.height

    def add_enemy(self, enemy: Enemy) -> None:
        if self.in_bounds(enemy.pos):
            self.enemies.append(enemy)

    def add_resource(self, node: ResourceNode) -> None:
        if self.in_bounds(node.pos):
            self.resources.append(node)

    def get_enemies_near(self, pos: Position, radius: int = 3) -> List[Enemy]:
        x, y = pos
        res = []
        for e in self.enemies:
            ex, ey = e.pos
            if abs(ex - x) <= radius and abs(ey - y) <= radius and e.is_alive():
                res.append(e)
        return res


def sample_map() -> GridMap:
    m = GridMap(30, 30)
    m.add_enemy(Enemy(id="e1", name="Goblin", hp=20, pos=(5, 5), loot_table={"coin": 5}))
    m.add_enemy(Enemy(id="e2", name="Wolf", hp=30, pos=(8, 6), loot_table={"fur": 1}))
    m.add_resource(ResourceNode(id="r1", resource_type="herb", qty=3, pos=(10, 10)))
    return m
