import pygame
from array import array

from vargtass.utils import chunks

from .game_assets import GameAssets


def run_game():
    pygame.init()
    screen = pygame.display.set_mode((320, 200))
    clock = pygame.time.Clock()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.fill("purple")

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

    walls = assets.media.walls.values()

    for i, wall in enumerate(walls):
        surf = pygame.Surface((64, 64))
        pxarray = pygame.PixelArray(surf)
        for x in range(64):
            for y in range(64):
                pxarray[x, y] = wall[y + x * 64]  # type: ignore
        pxarray.close()

        x = i % per_row
        y = i // per_row
        screen.blit(surf, (x * 74 + 10, y * 74 + 10))

    pygame.display.flip()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        clock.tick(60)
    pygame.quit()
