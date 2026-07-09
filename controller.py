"""
Input controller: converts pixel clicks into board actions.

Design note (per course email re: user-defined games):
This class only knows "select" / "replace selection" / "send move request".
Chess legality is delegated to a RuleSet injected at construction time --
swap in a different RuleSet (e.g. reversed pawn) without touching this file.
"""

from rules import DEFAULT_RULE_SET

CELL_SIZE = 100


class Controller:
    def __init__(self, board, rule_set=DEFAULT_RULE_SET, cell_size=CELL_SIZE):
        self._board = board
        self._rule_set = rule_set
        self._cell_size = cell_size
        self._selected = None
        self._clock_ms = 0

    def handle_click(self, x, y):
        row, col = self._pixel_to_cell(x, y)
        if not self._board.in_bounds(row, col):
            return

        piece = self._board.get(row, col)

        if self._selected is None:
            if piece is not None:
                self._selected = (row, col)
            return

        selected_piece = self._board.get(*self._selected)
        if piece is not None and piece.color == selected_piece.color:
            self._selected = (row, col)
            return

        if not self._rule_set.is_legal_move(selected_piece, self._selected, (row, col), self._board):
            self._selected = None
            return

        self._board.move(self._selected, (row, col))
        self._selected = None

    def advance_clock(self, ms):
        self._clock_ms += ms

    def _pixel_to_cell(self, x, y):
        return y // self._cell_size, x // self._cell_size
