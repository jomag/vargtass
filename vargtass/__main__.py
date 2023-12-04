import logging
import os

from vargtass.ui import run_ui

from .game_assets import GameAssets
from .game import run_sprite_display, run_wall_display

if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)

    assets_path = os.path.join(os.path.dirname(__file__), "..", "assets")
    assets = GameAssets()
    assets.load(assets_path)

    # run_wall_display(assets)
    # run_sprite_display(assets)
    run_ui(assets)
