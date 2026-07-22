"""Formats a Board back into its canonical <color><kind> text form.

Unlike a list-of-lists board, an empty cell is simply absent from the
dict, so the printer iterates the full rectangle (via
board.dimensions()) rather than enumerating occupied cells, filling in
"." for absent ones.
"""
from typing import List

from kfchess.io.pieces_config import EMPTY_TOKEN
from kfchess.model.board import Board
from kfchess.model.position import Position


def _token(piece) -> str:
    if piece is None:
        return EMPTY_TOKEN
    return piece.color + piece.kind


def piece_token(piece) -> str:
    """Public alias for ``_token`` -- for callers (e.g.
    ``kfchess.io.snapshot``) that need a single piece's token rather
    than a whole board's."""
    return _token(piece)


def token_grid(board: Board) -> List[List[str]]:
    """The same <color><kind>/"." tokens as ``render``, as a rectangular
    list-of-lists instead of a printable string -- the shape a JSON
    snapshot (``kfchess.io.snapshot``) needs. Kept here, not
    duplicated, so both ways of rendering a board agree on one token
    vocabulary."""
    height, width = board.dimensions()
    return [
        [_token(board.get(Position(row, col))) for col in range(width)]
        for row in range(height)
    ]


def render(board: Board) -> str:
    return "\n".join(" ".join(row) for row in token_grid(board))
