from math import pi
from typing import Dict, List, Optional, Set

from vargtass.game_assets import GameAssets, Level, Tile
from vargtass.utils import rotate


class Actor:
    x: float
    y: float
    visible: bool
    blocking: bool
    sprite: int

    def __init__(self, x: float, y: float, sprite: int, visible=True, blocking=False):
        self.x, self.y = x, y
        self.sprite = sprite
        self.visible = visible
        self.blocking = blocking


class GameState:
    player_x: float = 32
    player_y: float = 32

    # Player viewing angle in degrees. 0 = north, 90 = east.
    player_dir: float = 0.0

    level_no: int = 0
    level: Optional[Level] = None
    actors: List[Actor]

    # Door position identified by door ID. 0 = fully opened, 1 = fully closed
    door_positions: Dict[int, float]

    opening_doors: Set[int]
    closing_doors: Set[int]

    @property
    def player_dir_deg(self):
        return self.player_dir * (180 / pi)

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

    def _create_actors(self):
        blocking_props = [
            24,
            25,
            26,
            28,
        ]

        self.actors = []

        if not self.level:
            return

        for y in range(self.level.height):
            for x in range(self.level.width):
                t = self.level.plane1.get_cell(x, y)
                if t >= 23 and t <= 70:
                    # Props. Typically static decorations, but some block the player
                    self.actors.append(
                        Actor(
                            x + 0.5,
                            y + 0.5,
                            t - 21,
                            blocking=t in blocking_props,
                        )
                    )

    def enter_level(self, level_no: int):
        self.reset()
        self.level_no = level_no
        self.level = self.assets.load_level(level_no)
        self._create_actors()
        print(self.actors)

        spawn = self.level.get_player_spawn()
        self.player_x = spawn[0][0] + 0.5
        self.player_y = spawn[0][1] + 0.5

        print("FIXME: SPAWN POINT VIEW DIRECTION NOT USED!")
        self.player_dir = 0  # (spawn[1] + 180) * (pi / 180)

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

    def handle_open_button_press(self, tile: Tile):
        if tile.is_door:
            self.toggle_door(tile.door_id)

    def update(
        self,
        left_input: bool,
        right_input: bool,
        forward_input: bool,
        backward_input: bool,
        rotation_speed: float,
        move_speed: float,
        elapsed: float,
    ):
        if left_input:
            self.player_dir -= rotation_speed * elapsed
        if right_input:
            self.player_dir += rotation_speed * elapsed
        if forward_input:
            dx, dy = rotate(move_speed * elapsed, 0, self.player_dir)
            if self.is_walkable(int(self.player_x + dx), int(self.player_y)):
                self.player_x += dx
            if self.is_walkable(int(self.player_x), int(self.player_y + dy)):
                self.player_y += dy
        if backward_input:
            dx, dy = rotate(-move_speed * elapsed, 0, self.player_dir)
            if self.is_walkable(int(self.player_x + dx), int(self.player_y)):
                self.player_x += dx
            if self.is_walkable(int(self.player_x), int(self.player_y + dy)):
                self.player_y += dy

        self._update_doors(elapsed)

    def _update_doors(self, elapsed: float):
        # Time to open/close door fully in seconds
        spd = 0.6

        if self.level:
            for door_id in list(self.closing_doors):
                pos = self.get_door_position(door_id) + (1 / spd) * elapsed
                if pos >= 1:
                    pos = 1
                    self.closing_doors.remove(door_id)
                self.door_positions[door_id] = pos

            for door_id in list(self.opening_doors):
                pos = self.get_door_position(door_id) - (1 / spd) * elapsed
                if pos <= 0:
                    pos = 0
                    self.opening_doors.remove(door_id)
                self.door_positions[door_id] = pos
