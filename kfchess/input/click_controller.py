"""ClickController decides what a click MEANS -- select a piece,
switch selection to a different friendly piece, jump the selected
piece in place, or attempt to move it -- and nothing more. It never
decides whether a move or jump is legal: every attempt is forwarded to
GameEngine.attempt_move()/attempt_jump(), and this class only reacts to
the True/False result by clearing selection -- it never inspects why.

GameEngine remains the sole legality authority (RuleEngine, mid-route
blocking, and the busy/in-transit/airborne/cooldown check behind
is_selectable()/attempt_move()/attempt_jump()). This class owns only:
pixel -> cell translation (via BoardMapper) and the selection state
machine that interprets a sequence of clicks.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from kfchess.input.board_mapper import BoardMapper
from kfchess.model.piece import same_color
from kfchess.model.position import Position

if TYPE_CHECKING:
    from kfchess.engine.game_engine import GameEngine
    from kfchess.engine.game_state import GameState


class ClickController:
    """Click semantics:

    * No selection, click on a selectable piece -> select it.
    * No selection, click on an empty cell (or a busy piece) -> no-op.
    * Selection held, click the SAME square again -> a jump attempt,
      forwarded to GameEngine.attempt_jump: the piece rises in place and
      lands back a moment later, capturing anything that arrives on its
      square in the meantime (see GameEngine.attempt_jump).
    * Selection held, click on a different, selectable friendly piece ->
      selection switches to it (not a move attempt).
    * Selection held, click anywhere else -> forwarded to
      GameEngine.attempt_move, which validates the move and, if legal,
      queues it as a PendingMove -- it does not relocate the piece
      immediately. Selection is cleared afterward regardless of result.
    * Game over -> every click is a no-op.
    """

    def __init__(self, engine: "GameEngine", mapper: BoardMapper) -> None:
        self._engine = engine
        self._mapper = mapper
        self.selection: Optional[Position] = None

    def handle_click(self, state: "GameState", x: int, y: int) -> None:
        if state.game_over:
            return

        pos = self._mapper.pixel_to_cell(x, y)
        board = state.board
        if not board.is_inside(pos):
            return

        clicked_piece = board.get(pos)

        if self.selection is None:
            if clicked_piece is not None and self._engine.is_selectable(state, pos):
                self.selection = pos
            return

        # A second click on the very square that's selected is a jump
        # attempt, not a (zero-distance, always-illegal) move attempt.
        if pos == self.selection:
            self._engine.attempt_jump(state, pos)
            self.selection = None
            return

        selected_piece = board.get(self.selection)

        # A click on a different friendly, selectable piece switches the
        # selection -- it is never treated as a move attempt.
        if clicked_piece is not None and same_color(selected_piece, clicked_piece):
            if self._engine.is_selectable(state, pos):
                self.selection = pos
            return

        # Anything else -- empty cell or enemy piece -- is a move
        # attempt. This controller does not decide whether it's legal;
        # it just forwards it and clears the selection either way.
        self._engine.attempt_move(state, self.selection, pos)
        self.selection = None
