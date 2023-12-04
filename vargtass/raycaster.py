from math import floor, sqrt
from vargtass.game_state import GameState
from vargtass.game_assets import Level
from vargtass.utils import rotate


class Raycaster:
    # Camera position
    x: float
    y: float

    # Camera direction (radians)
    dir: float

    # Max distance before raycasting stops
    max_distance = 64

    # State for testing horizontal walls
    hray_step_length: float
    hray_step_x: float
    hray_step_y: int
    hray_x: float
    hray_y: float

    # State for testing vertical walls
    vray_step_length: float
    vray_step_x: int
    vray_step_y: float
    vray_x: float
    vray_y: float

    def _prepare(self):
        """Prepare for casting next ray"""
        x, y = self.x, self.y

        # Normalized direction vector
        dx, dy = rotate(1, 0, self.dir)

        self.hray_step_x = dx * (1 / dy) if dy != 0 else 0
        self.vray_step_y = dy * (1 / dx) if dx != 0 else 0

        # How much longer the ray gets for each unit step along the X axis
        self.vray_step_length = sqrt(1 + (dy / dx) ** 2) if dx != 0 else 0

        # How much longer the ray gets for each unit step along the Y axis
        self.hray_step_length = sqrt(1 + (dx / dy) ** 2) if dy != 0 else 0

        if dx < 0:
            self.vray_step_x = -1
            self.vray_length = (x % 1) * self.vray_step_length
            self.vray_x = floor(x)
            self.vray_y = y - (x % 1) * self.vray_step_y
        else:
            self.vray_step_x = 1
            self.vray_length = (1.0 - x % 1) * self.vray_step_length
            self.vray_x = floor(x + 1)
            self.vray_y = y + (1.0 - x % 1) * self.vray_step_y

        if dy < 0:
            self.hray_step_y = -1
            self.hray_length = (y % 1) * self.hray_step_length
            self.hray_x = x - (y % 1) * self.hray_step_x
            self.hray_y = floor(y)
        else:
            self.hray_step_y = 1
            self.hray_length = (1.0 - y % 1) * self.hray_step_length
            self.hray_x = x + (1.0 - y % 1) * self.hray_step_x
            self.hray_y = floor(y + 1)

    def raycast(
        self,
        state: GameState,
        level: Level,
        x: float,
        y: float,
        dir: float,
        max_distance: float = 64,
        door_is_solid: bool = False,  # Quick hack to allow raycasting for doors
    ):
        # Shoot two rays in the same direction. One (vray) is examined at every vertical
        # intersection with the grid, and the other one (hray) is examined at every horizontal
        # intersection. The one that hits a wall first is the one we use.
        self.x, self.y, self.dir = x, y, dir

        self._prepare()

        distance = 0
        tx = 0
        while distance < max_distance:
            if self.vray_length < self.hray_length:
                distance = self.vray_length
                hit_x, hit_y = self.vray_x, self.vray_y
                cell_x = floor(hit_x) if self.vray_step_x > 0 else floor(hit_x - 1)
                cell_y = floor(hit_y)
                wall_index_add = -1

                tile = level.tiles[cell_y][cell_x]

                if tile.is_solid or (tile.is_door and door_is_solid):
                    if self.vray_step_x > 0:
                        texture = tile.get_texture_west()
                    else:
                        texture = tile.get_texture_east()

                    tx = hit_y % 1
                    return (distance, tx, texture, (hit_x, hit_y), tile)

                if tile.is_door:
                    door_hit_x = hit_x + self.vray_step_x / 2
                    door_hit = (
                        hit_y + (self.vray_step_y * self.vray_step_x) / 2
                    ) - cell_y

                    if door_hit >= 0 and door_hit < 1:
                        door_position = state.get_door_position(tile.door_id)
                        door_hit_y = hit_y + (self.vray_step_x * self.vray_step_y) / 2
                        tx = (door_position - door_hit) % 1
                        if (door_hit) < door_position:
                            return (
                                self.vray_length + self.vray_step_length / 2,
                                tx,
                                100 + wall_index_add,
                                (door_hit_x, door_hit_y),
                                tile,
                            )

                self.vray_length += self.vray_step_length
                self.vray_x += self.vray_step_x
                self.vray_y += self.vray_step_y * self.vray_step_x
            else:
                distance = self.hray_length
                hit_x, hit_y = self.hray_x, self.hray_y
                cell_x = floor(hit_x)
                cell_y = floor(hit_y) if self.hray_step_y > 0 else floor(hit_y - 1)
                wall_index_add = -2

                tile = level.tiles[cell_y][cell_x]

                if tile.is_solid or (tile.is_door and door_is_solid):
                    if self.hray_step_y > 0:
                        texture = tile.get_texture_north()
                    else:
                        texture = tile.get_texture_south()

                    tx = hit_x % 1
                    return (distance, tx, texture, (hit_x, hit_y), tile)

                if tile.is_door:
                    door_hit_y = hit_y + self.hray_step_y / 2
                    door_hit = (
                        hit_x + (self.hray_step_y * self.hray_step_x) / 2
                    ) - cell_x

                    if door_hit >= 0 and door_hit < 1:
                        door_position = state.get_door_position(tile.door_id)
                        door_hit_x = hit_x + (self.hray_step_y * self.hray_step_x) / 2
                        tx = (door_position - door_hit) % 1
                        if (door_hit) < door_position:
                            return (
                                self.hray_length + self.hray_step_length / 2,
                                tx,
                                100 + wall_index_add,
                                (door_hit_x, door_hit_y),
                                tile,
                            )

                self.hray_length += self.hray_step_length
                self.hray_x += self.hray_step_x * self.hray_step_y
                self.hray_y += self.hray_step_y

        return None
