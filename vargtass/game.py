from math import acos, atan, atan2, cos, floor, fmod, pi, sin, sqrt
from typing import Dict, Optional, Set, Tuple
import pygame
from array import array
from vargtass.game_state import GameState
from vargtass.raycaster import Raycaster

from vargtass.utils import Vec2, chunks, d2r, r2d, rotate

from .game_assets import GameAssets, Level


def render_player(screen: pygame.Surface, x: float, y: float, dir: float):
    poly = [(-3, -5), (10, 0), (-3, 5), (0, 0)]
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


def raycast(level: Level, x: float, y: float, dir: float):
    # ) -> Optional[tuple[float, int, int]]:
    # Shoot two rays in the same direction. One (vray) is examined at every vertical
    # intersection with the grid, and the other one (hray) is examined at every horizontal
    # intersection. The one that hits a wall first is the one we use.
    # Direction angle 0 will raycast to the east. Angle 90 to the south.

    max_distance = 64

    # Normalized direction vector
    dx, dy = rotate(1, 0, dir)

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
    return dx * cos(angle) + dy * sin(angle)


def render_top_view(
    screen: pygame.Surface, state: GameState, center: Tuple[float, float] = (0, 0)
):
    grid_size = 64
    w, h = screen.get_size()
    cx, cy = center[0] * grid_size, center[1] * grid_size
    offs_x, offs_y = w / 2 - cx, h / 2 - cy

    level = state.level
    if not level:
        return

    media = state.assets.media

    screen.fill(0x555555)

    for x in range(level.width):
        for y in range(level.height):
            wall_index = level.plane0.get_cell(x, y) * 2 - 2
            if wall_index <= 256:
                surf = media.get_wall_surface(wall_index)
                if surf:
                    if grid_size != 64:
                        surf = pygame.transform.scale(surf, (grid_size, grid_size))
                    screen.blit(
                        surf,
                        (x * grid_size + offs_x, y * grid_size + offs_y),
                    )

    all_objects = [obj for obj in state.static_objects]
    all_objects.extend([c for c in state.collectibles if not c.collected])

    for a in all_objects:
        try:
            sprite = state.assets.media.sprites[a.sprite]
        except KeyError:
            print("Sprite not found!")
            continue
        if sprite:
            sprite.render(
                screen,
                int(a.x * grid_size + offs_x) - grid_size // 2,
                int(a.y * grid_size + offs_y) - grid_size // 2,
                grid_size,
                grid_size,
            )

    raycaster = Raycaster()

    fov = pi * 0.125
    dir = state.player_dir - fov
    while dir <= state.player_dir + fov:
        hit = raycaster.raycast(state, level, state.player_x, state.player_y, dir)
        if hit:
            distance, tx, _, xy, tile = hit
            x, y = state.player_x * grid_size, state.player_y * grid_size
            dx, dy = rotate(grid_size, 0, dir)
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
    fov = pi * 0.125

    level = state.level
    if not level:
        return

    floor_color = 0x707070
    ceil_color = 0x383838

    sw, sh = screen.get_width(), screen.get_height()
    screen.fill(ceil_color, (0, 0, sw, sh // 2))
    screen.fill(floor_color, (0, sh // 2, sw, sh // 2))

    zbuf = [0.0] * screen.get_width()

    # Raycast walls
    raycaster = Raycaster()
    w, h = screen.get_width(), screen.get_height()
    step = (fov * 2) / w
    for x in range(w):
        dir = state.player_dir - fov + step * x
        hit = (
            raycaster.raycast(state, level, state.player_x, state.player_y, dir) or None
        )

        if hit is not None:
            dist, tx, wall_index, xy, tile = hit
            pdist = projected_distance(
                xy[0] - state.player_x,
                xy[1] - state.player_y,
                state.player_dir,
            )

            # Note that we use distance instead of wall height
            # for the Z-buffer, which is used to determine if
            # each column of the sprites should be rendered or
            # not. Wolfenstein use wall height, and the reason
            # could be that the projected distance is not same
            # as the real distance.
            zbuf[x] = max(pdist, 0)

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

    # Render actors

    # TODO: better algo to find visible actors/sprites (4.7.8.1)
    all_objects = [actor for actor in state.static_objects]
    all_objects.extend([obj for obj in state.collectibles if not obj.collected])
    visible_objects = []

    for a in all_objects:
        rel = Vec2(a.x - state.player_x, a.y - state.player_y)
        rel = rel.rotate(-state.player_dir)
        if rel.length == 0:
            continue

        x_axis = Vec2(1, 0)
        axis_angle = acos(rel.dot(x_axis) / (rel.length))
        angle = axis_angle
        if rel.y < 0:
            angle = -angle

        # TODO: Try this instead!!
        angle = atan2(rel.y, rel.x)

        # if angle < fov:
        center_x = w / 2 + (w / (fov * 2)) * angle
        # else:
        # continue

        pdist = projected_distance(
            a.x - state.player_x, a.y - state.player_y, state.player_dir
        )

        # FIXME: Without this, there's a lot of flickering
        # from sprites not in front of the player, but directly
        # to the left/right side of the player. And 0.1 does not
        # seem to be enough to get rid of *all* the flickering.
        if pdist < 0.1:
            continue

        visible_objects.append((a, center_x, pdist))

    visible_objects = reversed(sorted(visible_objects, key=lambda a: a[2]))

    for a, center_x, pdist in visible_objects:
        sz = h / (pdist or 1)
        top = h / 2 - sz / 2
        left = center_x - sz / 2

        try:
            sprite = state.assets.media.sprites[a.sprite]
            sprite.render_with_zbuf(
                screen, int(left), int(top), int(sz), int(sz), pdist, zbuf
            )
        except KeyError:
            print(f"Sprite not found: {a.sprite}")


def run_wall_display(assets: GameAssets):
    tot = len(assets.media.walls)
    per_row = 8
    rows = tot // per_row

    pygame.init()
    screen = pygame.display.set_mode((per_row * (64 + 10) + 10, rows * (64 + 10) + 10))
    clock = pygame.time.Clock()
    running = True

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


def run_sprite_display(assets: GameAssets):
    pygame.init()

    margin = 16
    w, h = 512, 512

    screen = pygame.display.set_mode((w + margin * 2, h + margin * 2))
    clock = pygame.time.Clock()
    running = True

    # for i, idx in enumerate(assets.media.walls):
    #     wall = assets.media.get_wall_surface(idx)
    #     if wall:
    #         x = i % per_row
    #         y = i // per_row
    #         screen.blit(wall, (x * 74 + 10, y * 74 + 10))

    sprite_index = 0

    def render_sprite(index):
        screen.fill("black")

        sprite = assets.media.get_sprite_surface(index)
        if sprite:
            scaled = pygame.transform.scale(sprite, (512, 512))
            screen.blit(scaled, (margin, margin, w, h))

        pygame.display.flip()

    render_sprite(sprite_index)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RIGHT:
                    sprite_index += 1
                    print(f"Sprite {sprite_index}")
                    render_sprite(sprite_index)
                if event.key == pygame.K_LEFT:
                    sprite_index -= 1
                    print(f"Sprite {sprite_index}")
                    render_sprite(sprite_index)
            if event.type == pygame.QUIT:
                running = False
        clock.tick(60)
    pygame.quit()
