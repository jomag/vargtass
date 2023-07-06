from typing import Dict, Optional, Set

from vargtass.game_assets import GameAssets, Level


class GameState:
    player_x: float = 32
    player_y: float = 32
    player_dir: float = 0.0
    level_no: int = 0
    level: Optional[Level] = None

    # Door position identified by door ID. 0 = fully opened, 1 = fully closed
    door_positions: Dict[int, float]

    opening_doors: Set[int]
    closing_doors: Set[int]

    def __init__(self, assets: GameAssets):
        self.assets = assets
        self.reset()

    def reset(self):
        self.door_positions = {}
        self.opening_doors = set()
        self.closing_doors = set()

    def get_door_position(self, door_id):
        try:
            return self.door_positions[door_id]
        except KeyError:
            return 1.0

    def enter_level(self, level_no: int):
        self.reset()
        self.level_no = level_no
        self.level = self.assets.load_level(level_no)

    def toggle_door(self, door_id: int):
        if self.level:
            if door_id in self.opening_doors:
                self.opening_doors.remove(door_id)
                self.closing_doors.add(door_id)
            elif door_id in self.closing_doors:
                self.closing_doors.remove(door_id)
                self.opening_doors.add(door_id)
            else:
                if self.get_door_position(door_id) == 0:
                    self.closing_doors.add(door_id)
                else:
                    self.opening_doors.add(door_id)

    # Returns True if the tile is walkable
    # Walls and closed doors are not walkable
    def is_walkable(self, x: int, y: int):
        if self.level:
            tile = self.level.tiles[y][x]
            if tile.is_solid:
                return False
            if tile.is_door and self.get_door_position(tile.door_id) != 0:
                return False
            return True

    def step(self):
        spd = 0.13

        if self.level:
            for door_id in list(self.closing_doors):
                pos = self.get_door_position(door_id) + spd
                if pos >= 1:
                    pos = 1
                    self.closing_doors.remove(door_id)
                self.door_positions[door_id] = pos

            for door_id in list(self.opening_doors):
                pos = self.get_door_position(door_id) - spd
                if pos <= 0:
                    pos = 0
                    self.opening_doors.remove(door_id)
                self.door_positions[door_id] = pos
