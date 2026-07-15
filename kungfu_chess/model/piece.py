class Piece:
    __slots__ = ("id", "color", "type", "cell", "state")

    def __init__(self, id, color, type, cell, state="idle"):
        self.id = id
        self.color = color
        self.type = type
        self.cell = cell
        self.state = state

    def __repr__(self):
        return f"Piece(id={self.id}, {self.color}{self.type}, cell={self.cell}, state={self.state})"