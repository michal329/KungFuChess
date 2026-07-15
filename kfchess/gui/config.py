"""GUI-wide constants: cell size, window size, FPS, asset paths."""
import pathlib

CELL_SIZE_PX = 100
BOARD_SIZE_CELLS = 8
BOARD_SIZE_PX = BOARD_SIZE_CELLS * CELL_SIZE_PX

HUD_HEIGHT_PX = 60
WINDOW_WIDTH_PX = BOARD_SIZE_PX
WINDOW_HEIGHT_PX = BOARD_SIZE_PX + HUD_HEIGHT_PX

FPS = 60
PIECE_STATES = ("idle", "move", "jump", "short_rest", "long_rest")

ASSETS_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent / "assets"
BOARD_IMAGE_PATH = ASSETS_ROOT / "board.png"
PIECES_ROOT = ASSETS_ROOT / "pieces"
