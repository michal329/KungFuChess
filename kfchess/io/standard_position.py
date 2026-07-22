"""The standard chess starting position -- a single grid literal
``server/game_manager.py`` builds every networked game's board from,
so there's exactly one place that spells out the starting position
instead of one copy per caller that could drift.
"""
from kfchess.io.board_parser import build_board
from kfchess.model.board import Board

STANDARD_START = [
    ["BR", "BN", "BB", "BQ", "BK", "BB", "BN", "BR"],
    ["BP", "BP", "BP", "BP", "BP", "BP", "BP", "BP"],
    [".", ".", ".", ".", ".", ".", ".", "."],
    [".", ".", ".", ".", ".", ".", ".", "."],
    [".", ".", ".", ".", ".", ".", ".", "."],
    [".", ".", ".", ".", ".", ".", ".", "."],
    ["WP", "WP", "WP", "WP", "WP", "WP", "WP", "WP"],
    ["WR", "WN", "WB", "WQ", "WK", "WB", "WN", "WR"],
]


def build_standard_board() -> Board:
    return build_board(STANDARD_START)
