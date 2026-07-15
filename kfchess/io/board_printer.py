"""Formats a Board back into its canonical <color><kind> text form.

Unlike a list-of-lists board, an empty cell is simply absent from the
dict, so the printer iterates the full rectangle (via
board.dimensions()) rather than enumerating occupied cells, filling in
"." for absent ones.
"""
from kfchess.io.pieces_config import EMPTY_TOKEN
from kfchess.model.board import Board
from kfchess.model.position import Position


def _token(piece) -> str:
    if piece is None:
        return EMPTY_TOKEN
    return piece.color + piece.kind


def render(board: Board) -> str:
    height, width = board.dimensions()
    rows = []
    for row in range(height):
        rows.append(" ".join(_token(board.get(Position(row, col))) for col in range(width)))
    return "\n".join(rows)
