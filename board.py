"""
Board and Piece domain model.

Design note (per course email re: future binary board format):
All knowledge of the *text* board representation lives in Board.parse()
and Board.__str__(). Nothing outside this file depends on "wK", ".", etc.
To support a binary format later, add Board.from_bytes()/to_bytes() here
and leave every other module untouched -- they only talk to Board/Piece
objects and (row, col) coordinates.
"""

EMPTY_TOKEN = "."
VALID_COLORS = {"w", "b"}
# Config, not hardcoded logic: new piece types (e.g. a future "Quadcopter")
# are added here, nowhere else.
VALID_PIECE_TYPES = {"K", "Q", "R", "B", "N", "P"}


class BoardError(Exception):
    """Base class for board-validation failures."""
    code = "BOARD_ERROR"


class RowWidthMismatchError(BoardError):
    code = "ROW_WIDTH_MISMATCH"


class UnknownTokenError(BoardError):
    code = "UNKNOWN_TOKEN"


class Piece:
    __slots__ = ("color", "type")

    def __init__(self, color, piece_type):
        self.color = color
        self.type = piece_type

    @classmethod
    def parse(cls, token):
        if len(token) != 2 or token[0] not in VALID_COLORS or token[1] not in VALID_PIECE_TYPES:
            raise UnknownTokenError(token)
        return cls(token[0], token[1])

    def __str__(self):
        return f"{self.color}{self.type}"

    def __repr__(self):
        return f"Piece({self.color}{self.type})"


class Board:
    def __init__(self, grid):
        # grid: list of rows, each row a list of Optional[Piece]
        self._grid = grid
        self.rows = len(grid)
        self.cols = len(grid[0]) if grid else 0

    @classmethod
    def parse(cls, lines):
        """lines: iterable of raw board-section lines (no header/footer)."""
        rows = [line.split() for line in lines if line.strip() != ""]
        if not rows:
            return cls([])

        width = len(rows[0])
        for row_tokens in rows:
            if len(row_tokens) != width:
                raise RowWidthMismatchError()

        grid = []
        for row_tokens in rows:
            parsed_row = []
            for token in row_tokens:
                if token == EMPTY_TOKEN:
                    parsed_row.append(None)
                else:
                    parsed_row.append(Piece.parse(token))
            grid.append(parsed_row)
        return cls(grid)

    def get(self, row, col):
        return self._grid[row][col]

    def in_bounds(self, row, col):
        return 0 <= row < self.rows and 0 <= col < self.cols

    def has_king(self, color):
        return any(
            cell is not None and cell.color == color and cell.type == "K"
            for row in self._grid for cell in row
        )

    def move(self, src, dst):
        src_row, src_col = src
        dst_row, dst_col = dst
        self._grid[dst_row][dst_col] = self._grid[src_row][src_col]
        self._grid[src_row][src_col] = None

    def __str__(self):
        lines = []
        for row in self._grid:
            tokens = [EMPTY_TOKEN if cell is None else str(cell) for cell in row]
            lines.append(" ".join(tokens))
        return "\n".join(lines)