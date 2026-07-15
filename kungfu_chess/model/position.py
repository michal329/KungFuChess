class Position:
    __slots__ = ("row", "col")

    def __init__(self, row, col):
        self.row = row
        self.col = col

    def __eq__(self, other):
        return isinstance(other, Position) and self.row == other.row and self.col == other.col

    def __hash__(self):
        return hash((self.row, self.col))

    def __repr__(self):
        return f"Position(row={self.row}, col={self.col})"