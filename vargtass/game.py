from math import pi, sqrt
from typing import Optional
import pygame
from array import array

from vargtass.utils import chunks, rotate

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


def raycast_naive(level: Level, x: float, y: float, dir: float):
    dist = 0

    while dist < 64:
        dx, dy = rotate(0, dist, dir)
        if level.plane0.is_solid(int(x + dx), int(y + dy)):
            return sqrt(dx * dx + dy * dy)
        dist += 0.5

    return None


def raycast(level: Level, x: float, y: float, dir: float):
    max_distance = 64

    # Normalized direction vector
    dx, dy = rotate(0, 1, dir)

    # How far to move along X when moving one unit along Y, and vice versa
    step_size_x = sqrt(1 + (dy / dx) ** 2)
    step_size_y = sqrt(1 + (dx / dy) ** 2)

    # The current cell we're investigating
    cell_x = int(x)
    cell_y = int(y)

    # Accumulated length of ray in X and Y direction
    ray_length_x = 0
    ray_length_y = 0

    if dx < 0:
        step_x = -1
        ray_length_x = (x - cell_x) * step_size_x
    else:
        step_x = 1
        ray_length_x = (cell_x + 1 - x) * step_size_x

    if dy < 0:
        step_y = -1
        ray_length_y = (y - cell_y) * step_size_y
    else:
        step_y = 1
        ray_length_y = (cell_y + 1 - y) * step_size_y

    distance = 0
    while distance < max_distance:
        if ray_length_x < ray_length_y:
            cell_x += step_x
            distance = ray_length_x
            ray_length_x += step_size_x
        else:
            cell_y += step_y
            distance = ray_length_y
            ray_length_y += step_size_y

        if level.plane0.is_solid(cell_x, cell_y):
            return distance

    return None


def render_top_view(
    screen: pygame.Surface,
    state: GameState,
):
    grid_size = 16

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
                    screen.blit(surf, (x * grid_size, y * grid_size))

    fov = pi * 0.125
    dir = state.player_dir - fov
    while dir <= state.player_dir + fov:
        distance = raycast(level, state.player_x, state.player_y, dir) or 64
        x, y = state.player_x * grid_size, state.player_y * grid_size
        dx, dy = rotate(0, grid_size, dir)
        pygame.draw.line(
            screen,
            "green",
            (x, y),
            (x + dx * distance, y + dy * distance),
        )
        dir += fov / 50

    render_player(
        screen,
        int(state.player_x * grid_size),
        int(state.player_y * grid_size),
        state.player_dir,
    )


def run_game(assets: GameAssets):
    pygame.init()
    screen = pygame.display.set_mode((1024, 1024))
    clock = pygame.time.Clock()
    running = True

    state = GameState(assets)
    state.enter_level(0)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        px, py, pdir = state.player_x, state.player_y, state.player_dir
        level = state.level

        pressed = pygame.key.get_pressed()
        if pressed[pygame.K_a]:
            state.player_dir -= 0.08
        if pressed[pygame.K_d]:
            state.player_dir += 0.08
        if pressed[pygame.K_w]:
            dx, dy = rotate(0, 0.08, state.player_dir)
            state.player_x += dx
            state.player_y += dy
            if level and level.plane0.is_solid(
                int(state.player_x),
                int(state.player_y),
            ):
                state.player_x, state.player_y = px, py
        if pressed[pygame.K_s]:
            dx, dy = rotate(0, -0.08, state.player_dir)
            state.player_x += dx
            state.player_y += dy
            if level and level.plane0.is_solid(
                int(state.player_x),
                int(state.player_y),
            ):
                state.player_x, state.player_y = px, py

        screen.fill("black")
        render_top_view(screen, state)

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
