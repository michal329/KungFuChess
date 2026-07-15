from kungfu_chess.model.position import Position


class BoardMapper:
    """Converts pixel (x, y) to board Position(row, col).

    origin_x, origin_y: pixel coordinates of the top-left corner of cell (0,0).
    cell_size: width and height of each square cell in pixels.
    """

    def __init__(self, origin_x: int, origin_y: int, cell_size: int):
        self._ox = origin_x
        self._oy = origin_y
        self._cell = cell_size

    def pixel_to_cell(self, x: int, y: int) -> Position | None:
        """Returns Position or None if the click is outside the board."""
        col = (x - self._ox) // self._cell
        row = (y - self._oy) // self._cell
        if col < 0 or row < 0:
            return None
        return Position(row, col)
