from __future__ import annotations

from typing import Iterator, Optional

from kfchess.model.piece import Piece
from kfchess.model.position import Position


class Board:
    """Board occupancy keyed by Position -> Piece.

    A dict of sparse cells instead of a list-of-lists of raw string
    tokens: an absent key means the cell is empty, and dimensions are
    stored explicitly since a sparse dict can't infer a rectangular
    extent from its occupied cells alone.
    """

    def __init__(self, height: int, width: int, cells: Optional[dict] = None):
        self._height = height
        self._width = width
        self._cells: dict[Position, Piece] = dict(cells) if cells else {}

    def dimensions(self) -> tuple[int, int]:
        return self._height, self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def width(self) -> int:
        return self._width

    def get(self, position: Position) -> Optional[Piece]:
        return self._cells.get(position)

    def set(self, position: Position, piece: Optional[Piece]) -> None:
        if piece is None:
            self._cells.pop(position, None)
        else:
            self._cells[position] = piece

    def move(self, from_position: Position, to_position: Position) -> None:
        piece = self.get(from_position)
        self.set(from_position, None)
        self.set(to_position, piece)

    def is_inside(self, position: Position) -> bool:
        return 0 <= position.row < self._height and 0 <= position.col < self._width

    def all_positions(self) -> Iterator[Position]:
        for row in range(self._height):
            for col in range(self._width):
                yield Position(row, col)

    def occupied_positions(self) -> Iterator[Position]:
        return iter(self._cells.keys())

    def copy(self) -> "Board":
        return Board(self._height, self._width, dict(self._cells))
