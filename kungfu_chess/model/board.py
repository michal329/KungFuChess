class BoardError(Exception):
    code = "BOARD_ERROR"

class RowWidthMismatchError(BoardError):
    code = "ROW_WIDTH_MISMATCH"

class UnknownTokenError(BoardError):
    code = "UNKNOWN_TOKEN"

class DuplicateOccupancyError(BoardError):
    code = "DUPLICATE_OCCUPANCY"


class Board:
    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self._grid = [[None] * cols for _ in range(rows)]

    def in_bounds(self, position):
        return 0 <= position.row < self.rows and 0 <= position.col < self.cols

    def get(self, position):
        return self._grid[position.row][position.col]

    def add_piece(self, position, piece):
        if self._grid[position.row][position.col] is not None:
            raise DuplicateOccupancyError()
        self._grid[position.row][position.col] = piece
        piece.cell = position

    def remove_piece(self, position):
        self._grid[position.row][position.col] = None

    def move_piece(self, src, dst):
        piece = self._grid[src.row][src.col]
        self._grid[dst.row][dst.col] = piece
        self._grid[src.row][src.col] = None
        if piece is not None:
            piece.cell = dst

    def has_king(self, color):
        return any(
            cell is not None and cell.color == color and cell.type == "K"
            for row in self._grid for cell in row
        )