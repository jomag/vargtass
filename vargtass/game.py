from math import atan, cos, floor, pi, sin, sqrt
from typing import Optional, Tuple
import pygame
from array import array
from vargtass.raycaster import Raycaster

from vargtass.utils import chunks, d2r, rotate

from .game_assets import GameAssets, Level


class GameState:
    player_x: float = 32
    player_y: float = 32
    player_dir: float = 0.0
    level_no: int = 0
    level: Optional[Level] = None

    def __init__(self, assets: GameAssets):
        self.assets = assets

    def enter_level(self, level_no: int):
        self.level_no = level_no
        self.level = self.assets.load_level(level_no)


def render_player(screen: pygame.Surface, x: float, y: float, dir: float):
    poly = [(-5, -3), (0, 10), (5, -3), (0, 0)]
    poly = [rotate(c[0], c[1], dir) for c in poly]
    poly = [(c[0] + x, c[1] + y) for c in poly]

    pygame.draw.polygon(screen, "yellow", poly)


def draw_column(
    screen: pygame.Surface, wall: list[int], x: int, top: int, bottom: int, tx: float
):
    assert tx >= 0 and tx < 1.0
    tx = int(tx * 64)

    # pygame.draw.line(screen, "#221100", (x, top), (x, bottom))
    ty = 0
    tstep = 64 / (bottom - top)

    if top < 0:
        ty += tstep * -top
        top = 0

    for y in range(top, min(bottom, screen.get_height())):
        # c = 0xFF444444
        # if tx < 1:
        #     c = 0xFF0000FF
        # if tx >= 63:
        #     c = 0xFF00FF00
        # if ty < 1:
        #     c = 0xFFFF0000
        # if ty >= 63:
        #     c = 0xFFFF00FF

        # screen.set_at((x, y), c)

        screen.set_at((x, y), wall[int(tx) * 64 + int(ty)])
        ty += tstep


def xraycast(level: Level, x: float, y: float, dir: float):
    # ) -> Optional[tuple[float, int, int]]:
    # Shoot two rays in the same direction. One (vray) is examined at every vertical
    # intersection with the grid, and the other one (hray) is examined at every horizontal
    # intersection. The one that hits a wall first is the one we use.

    max_distance = 64

    # Normalized direction vector
    dx, dy = rotate(0, 1, dir)

    x_per_y_unit = dx * (1 / dy) if dy != 0 else 0
    y_per_x_unit = dy * (1 / dx) if dx != 0 else 0

    # How much longer the ray gets for each unit step along the X axis
    vray_step_length = sqrt(1 + (dy / dx) ** 2) if dx != 0 else 0

    # How much longer the ray gets for each unit step along the Y axis
    hray_step_length = sqrt(1 + (dx / dy) ** 2) if dy != 0 else 0

    # The current cell we're investigating
    # cell_x = int(x)
    # cell_y = int(y)

    if dx < 0:
        vray_step_x = -1
        vray_length = (x % 1) * vray_step_length
        vray_x = floor(x)
        vray_y = y - (x % 1) * y_per_x_unit
    else:
        vray_step_x = 1
        vray_length = (1.0 - x % 1) * vray_step_length
        vray_x = floor(x + 1)
        vray_y = y + (1.0 - x % 1) * y_per_x_unit

    if dy < 0:
        hray_step_y = -1
        hray_length = (y % 1) * hray_step_length
        hray_x = x - (y % 1) * x_per_y_unit
        hray_y = floor(y)
    else:
        hray_step_y = 1
        hray_length = (1.0 - y % 1) * hray_step_length
        hray_x = x + (1.0 - y % 1) * x_per_y_unit
        hray_y = floor(y + 1)

    distance = 0
    tx = 0
    while distance < max_distance:
        if vray_length < hray_length:
            distance = vray_length
            hit_x, hit_y = vray_x, vray_y
            ray = "vray"
            cell_x = floor(hit_x) if dx > 0 else floor(hit_x - 1)
            cell_y = floor(hit_y)
            wall_index_add = -1

            vray_length += vray_step_length
            vray_x += vray_step_x
            vray_y += y_per_x_unit * vray_step_x
            tx = hit_y % 1
        else:
            distance = hray_length
            hit_x, hit_y = hray_x, hray_y
            ray = "hray"
            cell_x = floor(hit_x)
            cell_y = floor(hit_y) if dy > 0 else floor(hit_y - 1)
            wall_index_add = -2

            hray_length += hray_step_length
            hray_x += x_per_y_unit * hray_step_y
            hray_y += hray_step_y
            tx = hit_x % 1

        if level.plane0.is_solid(cell_x, cell_y):
            idx = level.plane0.get_cell(cell_x, cell_y) * 2 + wall_index_add
            return (distance, tx, idx, (hit_x, hit_y))

        if level.plane0.is_door(cell_x, cell_y):
            orientation = level.plane0.get_door_orientation(cell_x, cell_y)
            # if (hit_x + x_per_y_unit * hray_step_y / 2) % 1.0 < 0.5:
            return (
                distance + hray_step_length / 2,
                tx,
                100 + wall_index_add,
                (hit_x + 1 / 2, hit_y + hray_step_y / 2),
            )

    return None


def projected_distance(dx: float, dy: float, angle: float):
    angle += pi * 0.5
    return dx * cos(angle) + dy * sin(angle)


def render_top_view(
    screen: pygame.Surface, state: GameState, center: Tuple[float, float] = (0, 0)
):
    grid_size = 16
    w, h = screen.get_size()
    cx, cy = center[0] * grid_size, center[1] * grid_size
    offs_x, offs_y = w / 2 - cx, h / 2 - cy

    level = state.level
    if not level:
        return

    media = state.assets.media

    for x in range(level.width):
        for y in range(level.height):
            wall_index = level.plane0.get_cell(x, y)
            if wall_index <= 256:
                surf = media.get_wall_surface(wall_index)
                if surf:
                    if grid_size != 64:
                        surf = pygame.transform.scale(surf, (grid_size, grid_size))
                    screen.blit(
                        surf,
                        (x * grid_size + offs_x, y * grid_size + offs_y),
                    )

    raycaster = Raycaster()

    fov = pi * 0.125
    dir = state.player_dir - fov
    while dir <= state.player_dir + fov:
        hit = raycaster.raycast(level, state.player_x, state.player_y, dir)
        if hit:
            distance, tx, _, xy = hit
            x, y = state.player_x * grid_size, state.player_y * grid_size
            dx, dy = rotate(0, grid_size, dir)
            pygame.draw.line(
                screen,
                "green",
                (x + offs_x, y + offs_y),
                (x + dx * distance + offs_x, y + dy * distance + offs_y),
            )
            pygame.draw.circle(
                screen,
                "orange",
                (xy[0] * grid_size + offs_x, xy[1] * grid_size + offs_y),
                2,
            )
        dir += fov / 10

    render_player(
        screen,
        floor(state.player_x * grid_size) + offs_x,
        floor(state.player_y * grid_size) + offs_y,
        state.player_dir,
    )


def render_3d(screen: pygame.Surface, state: GameState):
    level = state.level
    if not level:
        return

    raycaster = Raycaster()
    w, h = screen.get_width(), screen.get_height()
    fov = pi * 0.125
    step = (fov * 2) / w
    for x in range(w):
        dir = state.player_dir - fov + step * x
        hit = raycaster.raycast(level, state.player_x, state.player_y, dir) or None

        if hit is not None:
            dist, tx, wall_index, xy = hit
            pdist = projected_distance(
                xy[0] - state.player_x,
                xy[1] - state.player_y,
                state.player_dir,
            )

            if pdist > 0:
                wh = h / (pdist or 1) * 0.5
                y1 = h / 2 - wh
                y2 = h / 2 + wh

                draw_column(
                    screen,
                    state.assets.media.walls[wall_index],
                    x,
                    floor(y1),
                    floor(y2),
                    tx,
                )


def run_game(assets: GameAssets):
    width = 512
    height = 512

    floor_color = 0x707070
    ceil_color = 0x383838

    pygame.init()
    screen = pygame.display.set_mode((width, height))
    clock = pygame.time.Clock()
    running = True

    move_speed = 0.08
    rot_speed = 0.02

    state = GameState(assets)
    state.enter_level(0)
    mode = "top"

    if state.level:
        spawn = state.level.get_player_spawn()
        state.player_x = spawn[0][0] + 0.5
        state.player_y = spawn[0][1] + 0.5
        state.player_dir = (spawn[1] + 180) * pi / 180

    while running:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB:
                    mode = "top" if mode == "3d" else "3d"
            if event.type == pygame.QUIT:
                running = False

        px, py = state.player_x, state.player_y
        level = state.level

        pressed = pygame.key.get_pressed()
        if pressed[pygame.K_a]:
            state.player_dir -= rot_speed
        if pressed[pygame.K_d]:
            state.player_dir += rot_speed
        if pressed[pygame.K_w]:
            dx, dy = rotate(0, move_speed, state.player_dir)
            if level:
                if not level.plane0.is_solid(
                    int(state.player_x + dx), int(state.player_y)
                ):
                    state.player_x += dx
                if not level.plane0.is_solid(
                    int(state.player_x), int(state.player_y + dy)
                ):
                    state.player_y += dy
        if pressed[pygame.K_s]:
            dx, dy = rotate(0, -move_speed, state.player_dir)
            if level:
                if not level.plane0.is_solid(
                    int(state.player_x + dx), int(state.player_y)
                ):
                    state.player_x += dx
                if not level.plane0.is_solid(
                    int(state.player_x), int(state.player_y + dy)
                ):
                    state.player_y += dy

        screen.fill(ceil_color, (0, 0, width, height // 2))
        screen.fill(floor_color, (0, height // 2, width, height // 2))

        if mode == "top":
            render_top_view(screen, state, (state.player_x, state.player_y))
        else:
            render_3d(screen, state)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


def run_wall_display(assets: GameAssets):
    tot = len(assets.media.walls)
    per_row = 8
    rows = tot // per_row

    pygame.init()
    screen = pygame.display.set_mode((per_row * (64 + 10) + 10, rows * (64 + 10) + 10))
    clock = pygame.time.Clock()
    running = True

    screen.fill("purple")

    for i, idx in enumerate(assets.media.walls):
        wall = assets.media.get_wall_surface(idx)
        if wall:
            x = i % per_row
            y = i // per_row
            screen.blit(wall, (x * 74 + 10, y * 74 + 10))

    pygame.display.flip()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        clock.tick(60)
    pygame.quit()
