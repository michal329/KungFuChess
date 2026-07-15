"""Asset root resolution -- the one place that knows where on disk the
board and piece sprite folders live."""
from pathlib import Path

from kfchess.gui.config import BOARD_IMAGE_PATH, PIECES_ROOT


def board_image_path() -> Path:
    return BOARD_IMAGE_PATH


def piece_states_dir(piece_code: str) -> Path:
    """piece_code is <kind><color>, e.g. 'NB' for a black knight --
    Piece.code already produces this exact folder name."""
    return PIECES_ROOT / piece_code / "states"
