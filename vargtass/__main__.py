import logging
import os
from .game_assets import GameAssets
from .game import run_game, run_wall_display

if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)

    assets_path = os.path.join(os.path.dirname(__file__), "..", "assets")
    assets = GameAssets()
    assets.load(assets_path)

    # run_game()
    run_wall_display(assets)
