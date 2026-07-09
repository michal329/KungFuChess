"""
Input controller: converts pixel clicks into board actions.

Design note (per course email re: user-defined games):
This class only knows "select" / "replace selection" / "send move request".
Chess legality is delegated to a RuleSet injected at construction time --
swap in a different RuleSet (e.g. reversed pawn) without touching this file.

Movement is time-based: a click schedules a move that arrives after
MOVE_DURATION_MS. Board.move() is called only when advance_clock() reaches
the arrival time -- the board never sees an in-flight piece.
"""

from rules import DEFAULT_RULE_SET

CELL_SIZE = 100
MOVE_DURATION_MS = 1000


class Controller:
    def __init__(self, board, rule_set=DEFAULT_RULE_SET, cell_size=CELL_SIZE):
        self._board = board
        self._rule_set = rule_set
        self._cell_size = cell_size
        self._selected = None
        self._clock_ms = 0
        self._pending = []  # list of (arrive_at_ms, src, dst, color)
        self._game_over = False

    @property
    def is_game_over(self):
        return self._game_over

    def handle_click(self, x, y):
        if self._game_over:
            return
        row, col = self._pixel_to_cell(x, y)
        if not self._board.in_bounds(row, col):
            return

        piece = self._board.get(row, col)

        if self._selected is None:
            if piece is not None and not self._is_in_flight(row, col):
                self._selected = (row, col)
            return

        selected_piece = self._board.get(*self._selected)
        if piece is not None and piece.color == selected_piece.color:
            if not self._is_in_flight(row, col):
                self._selected = (row, col)
            return

        if not self._rule_set.is_legal_move(selected_piece, self._selected, (row, col), self._board):
            self._selected = None
            return

        if self._is_route_blocked(self._selected, (row, col)):
            self._selected = None
            return

        arrive_at = self._clock_ms + MOVE_DURATION_MS
        self._pending.append((arrive_at, self._selected, (row, col), selected_piece.color))
        self._selected = None

    def _is_in_flight(self, row, col):
        return any(src == (row, col) for _, src, _, __ in self._pending)

    def _is_route_blocked(self, src, dst):
        """Returns True if any in-flight piece's dst shares the same column or row as this dst."""
        return any(
            existing_dst[0] == dst[0] or existing_dst[1] == dst[1]
            for _, _, existing_dst, __ in self._pending
        )

    def advance_clock(self, ms):
        self._clock_ms += ms
        due = [p for p in self._pending if p[0] <= self._clock_ms]
        self._pending = [p for p in self._pending if p[0] > self._clock_ms]
        for arrive_at, src, dst, color in due:
            self._resolve_arrival(src, dst, color)

    def _resolve_arrival(self, src, dst, scheduled_color):
        """Apply a pending move at arrival time, respecting the current board state."""
        src_piece = self._board.get(*src)
        if src_piece is None or src_piece.color != scheduled_color:
            return
        dst_piece = self._board.get(*dst)
        if dst_piece is not None and dst_piece.color == scheduled_color:
            return
        self._board.move(src, dst)
        if dst_piece is not None and dst_piece.type == "K":
            self._game_over = True

    def _pixel_to_cell(self, x, y):
        return y // self._cell_size, x // self._cell_size
