from math import pi
from typing import Optional, Tuple
from vargtass.game import render_3d, render_top_view
from vargtass.game_assets import GameAssets
import pygame
import pygame.freetype

from vargtass.game_state import GameState
from vargtass.raycaster import Raycaster


def render_stats_panel(
    surf: pygame.Surface,
    font: pygame.freetype.Font,
    state: GameState,
    tile: Optional[Tuple[float, float]] = None,
):
    bg = 0x111111
    fg = 0xCCCCCC
    padding = 5
    x, y = padding, padding

    if tile is None:
        tile = (state.player_x, state.player_y)

    content = f"Player XY: {state.player_x:.2f}, {state.player_y:.2f}\n"
    content += f"Direction: {state.player_dir_deg:.1f}\n"

    lines = content.splitlines()

    surf.fill(bg)
    for line in lines:
        font.render_to(surf, (x, y), line, fg, bg)
        y += font.get_sized_height(0)


def run_ui(assets: GameAssets):
    # Move speed in units per second
    move_speed = 4.8

    # Rotation speed of viewing angle in radians per second
    rotation_speed = pi

    spacing = 10

    ui_background_color = 0x333333

    top_view_size = (512, 512)
    top_view_width, top_view_height = top_view_size

    game_view_size = (320, 240)
    game_view_width, game_view_height = game_view_size

    stats_panel_view_size = (
        game_view_width,
        top_view_height - game_view_height - spacing,
    )
    stats_panel_view_height = stats_panel_view_size[1]

    window_size = (
        spacing + game_view_width + spacing + top_view_width + spacing,
        spacing
        + max(game_view_height + stats_panel_view_height, top_view_height)
        + spacing,
    )

    # Temporary test. Game state and logic should be handled outside of run_ui
    state = GameState(assets)
    state.enter_level(0)

    # Initialize pygame core and modules
    pygame.init()
    pygame.font.init()
    clock = pygame.time.Clock()

    # Setup fonts
    font = pygame.freetype.SysFont(pygame.font.get_default_font(), 14)

    screen_surface = pygame.display.set_mode(window_size)
    screen_surface.fill(
        ui_background_color,
        (0, 0, window_size[0], window_size[1]),
    )

    game_view_surface = screen_surface.subsurface(
        (spacing, spacing),
        game_view_size,
    )

    top_view_surface = screen_surface.subsurface(
        (spacing + game_view_width + spacing, spacing),
        top_view_size,
    )

    stats_panel_surface = screen_surface.subsurface(
        (spacing, spacing + game_view_height + spacing),
        stats_panel_view_size,
    )

    running = True

    while running:
        for evt in pygame.event.get():
            if evt.type == pygame.KEYDOWN:
                if evt.key == pygame.K_SPACE and state.level:
                    rc = Raycaster()
                    hit = rc.raycast(
                        state,
                        state.level,
                        state.player_x,
                        state.player_y,
                        state.player_dir,
                        door_is_solid=True,
                    )
                    if hit:
                        tile = hit[4]
                        state.handle_open_button_press(tile)
            if evt.type == pygame.QUIT:
                running = False
                continue

        pressed = pygame.key.get_pressed()

        # Assume we're running at full speed (60Hz)
        elapsed = 1 / 60

        state.update(
            pressed[pygame.K_a],
            pressed[pygame.K_d],
            pressed[pygame.K_w],
            pressed[pygame.K_s],
            rotation_speed,
            move_speed,
            elapsed,
        )

        render_3d(game_view_surface, state)
        render_top_view(top_view_surface, state, (state.player_x, state.player_y))
        render_stats_panel(
            stats_panel_surface,
            font,
            state,
            tile=(state.player_x, state.player_y),
        )

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
