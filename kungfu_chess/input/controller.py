from dataclasses import dataclass


@dataclass(frozen=True)
class ControllerResult:
    reason: str  # "selected" | "deselected" | "cancelled" | "empty_source" | "ok" | MoveResult reason


class Controller:
    """Translates pixel clicks into GameEngine.request_move calls.

    Click protocol (two-click selection):
    1. First click on a piece → selects it (returns "selected").
    2. First click on empty → returns "empty_source", no selection.
    3. Second click on same cell → deselects (returns "deselected").
    4. Out-of-bounds click → cancels selection (returns "cancelled").
    5. Second click on different cell → submits move, returns MoveResult reason.
    """

    def __init__(self, board, game_engine, board_mapper):
        self._board = board
        self._engine = game_engine
        self._mapper = board_mapper
        self._selected = None

    @property
    def selected(self):
        return self._selected

    def click(self, x: int, y: int) -> ControllerResult:
        cell = self._mapper.pixel_to_cell(x, y)

        if cell is None or not self._board.in_bounds(cell):
            self._selected = None
            return ControllerResult("cancelled")

        if self._selected is None:
            if self._board.get(cell) is None:
                return ControllerResult("empty_source")
            self._selected = cell
            return ControllerResult("selected")

        if cell == self._selected:
            self._selected = None
            return ControllerResult("deselected")

        src, dst = self._selected, cell
        self._selected = None
        result = self._engine.request_move(src, dst)
        return ControllerResult(result.reason)
