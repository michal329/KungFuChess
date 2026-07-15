"""GameEngine: stateless game-rules service, operating on an
externally-owned GameState passed into every action method.

Responsibilities
-----------------
* Hold zero per-game state. Every attribute on ``self`` is either a
  collaborator (RuleEngine, CollisionResolver, BoardMapper, ...) or
  static per-game configuration (move/jump/cooldown duration) -- fixed
  at construction, never mutated afterward. Board, clock, pending
  moves, airborne jumps, cooldowns, game-over/winner all live on the
  caller's GameState instead, threaded through every call as an
  explicit ``state`` argument. This lets one GameEngine instance (and
  all its collaborators) drive many independent GameStates
  concurrently, and makes every method trivially unit-testable without
  setup/teardown races.
* The single service layer with board *mutation* authority: nothing
  else may mutate a board. RuleEngine and CollisionResolver only ever
  read it.
* Translate pixel coordinates to board cells via BoardMapper -- the
  only component that does so; nothing does raw ``x // cell_size``
  arithmetic.
* Advance a GameState's clock (``tick``); execute due moves and
  resolve jump landings.
* Notify registered Observer instances of GameEvents.
"""
from __future__ import annotations

from typing import List, Optional

from kfchess.engine.game_over import GameOverRule, KingCaptureRule
from kfchess.engine.game_state import GameState
from kfchess.events.events import (
    AirborneCaptureEvent,
    GameEvent,
    GameOverEvent,
    JumpLandedEvent,
    MoveCompletedEvent,
    Observer,
    TimeAdvancedEvent,
)
from kfchess.input.board_mapper import BoardMapper
from kfchess.input.click_controller import ClickController
from kfchess.model.board import Board
from kfchess.model.piece import PAWN, QUEEN, Piece, same_color
from kfchess.model.position import Position
from kfchess.realtime.collision_resolver import CollisionResolver
from kfchess.realtime.motion import PendingJump, PendingMove
from kfchess.rules.rule_engine import RuleEngine

MOVE_DURATION_MS = 1000
JUMP_DURATION_MS = 1000
COOLDOWN_DURATION_MS = 1000
DEFAULT_CELL_SIZE = 100


class GameEngine:
    def __init__(
        self,
        board: Board,
        cell_size: int = DEFAULT_CELL_SIZE,
        move_duration: int = MOVE_DURATION_MS,
        jump_duration: int = JUMP_DURATION_MS,
        cooldown_duration: int = COOLDOWN_DURATION_MS,
        rule_engine: Optional[RuleEngine] = None,
        collision_resolver: Optional[CollisionResolver] = None,
        game_over_rule: Optional[GameOverRule] = None,
        mapper: Optional[BoardMapper] = None,
    ) -> None:
        self._move_duration = move_duration
        self._jump_duration = jump_duration
        self._cooldown_duration = cooldown_duration
        self._rule_engine = rule_engine if rule_engine is not None else RuleEngine()
        self._collision_resolver = collision_resolver if collision_resolver is not None else CollisionResolver()
        self._game_over_rule = game_over_rule if game_over_rule is not None else KingCaptureRule()
        self._mapper = mapper if mapper is not None else BoardMapper(cell_size)
        self._observers: List[Observer] = []
        # Prime the rule with the pristine starting board -- before any
        # move can run -- so a stateful rule like KingCaptureRule can
        # tell "this color never had a King" apart from "its King was
        # captured". *board* is used here only for this one-time
        # priming call; it is never stored on self.
        self._game_over_rule.check(board)
        self._click_controller = ClickController(self, self._mapper)

    # ------------------------------------------------------------------
    # Subject interface
    # ------------------------------------------------------------------

    def add_observer(self, observer: Observer) -> None:
        self._observers.append(observer)

    def _notify(self, event: GameEvent) -> None:
        for observer in self._observers:
            observer.on_event(event)

    # ------------------------------------------------------------------
    # Game commands
    # ------------------------------------------------------------------

    def handle_click(self, state: GameState, x: int, y: int) -> None:
        """Entirely delegated to ClickController, which owns click
        semantics and the ``selection`` state. GameEngine's role here is
        only legality, via attempt_move/is_selectable."""
        self._click_controller.handle_click(state, x, y)

    def handle_jump(self, state: GameState, x: int, y: int) -> None:
        """A piece already moving or already airborne cannot jump again.
        Unlike handle_click, a jump needs no selection step: origin and
        destination are always the same cell."""
        if state.game_over:
            return

        pos = self._mapper.pixel_to_cell(x, y)
        if not state.board.is_inside(pos):
            return

        piece = state.board.get(pos)
        if piece is None or self._is_busy(state, pos):
            return

        state.airborne.append(PendingJump(piece=piece, pos=pos, land_time=state.current_time + self._jump_duration))

    def is_selectable(self, state: GameState, pos: Position) -> bool:
        piece = state.board.get(pos)
        return piece is not None and not self._is_busy(state, pos)

    def attempt_move(self, state: GameState, from_pos: Position, to_pos: Position) -> bool:
        """Queues a PendingMove iff every check passes; returns True iff
        queued. The piece itself only relocates later, when ``tick``
        reaches its ``arrival_time``. Checks, in order: game not over; a
        piece sits at *from_pos* and isn't busy; RuleEngine approves
        shape/destination/path; the move doesn't violate the
        opposite-color route lock."""
        if state.game_over:
            return False

        piece = state.board.get(from_pos)
        if piece is None or self._is_busy(state, from_pos):
            return False

        legality = self._rule_engine.evaluate(state.board, from_pos, to_pos, piece)
        if not legality.is_legal:
            return False
        if self._route_conflicts(state, piece, from_pos, to_pos):
            return False

        cells_moved = max(abs(from_pos.row - to_pos.row), abs(from_pos.col - to_pos.col))
        arrival = state.current_time + cells_moved * self._move_duration
        state.pending.append(PendingMove(piece=piece, from_pos=from_pos, to_pos=to_pos, arrival_time=arrival))
        return True

    def tick(self, state: GameState, ms: int) -> None:
        """Advance *state*'s clock by *ms*. Due moves execute in
        chronological order (earliest arrival first; ties keep queue
        order), then jump landings resolve, then a GameOver check runs.

        Because earlier-arriving moves in the same tick apply first, a
        later move's re-validation sees their results -- e.g. two
        pieces racing for the same square: whichever arrives first
        occupies it, and a later enemy can still capture it there, while
        a later friendly is rejected as blocked. An airborne defender
        can defeat multiple arrivals in the same tick this way -- it
        never leaves its cell.
        """
        state.current_time += ms

        due: List[PendingMove] = []
        remaining: List[PendingMove] = []
        for pending_move in state.pending:
            (due if pending_move.arrival_time <= state.current_time else remaining).append(pending_move)
        state.pending = remaining
        due.sort(key=lambda pm: pm.arrival_time)

        for pending_move in due:
            self._resolve_due_move(state, pending_move)

        grounded: List[PendingJump] = []
        still_airborne: List[PendingJump] = []
        for pending_jump in state.airborne:
            (grounded if pending_jump.land_time <= state.current_time else still_airborne).append(pending_jump)
        state.airborne = still_airborne
        for pending_jump in grounded:
            self._set_cooldown(state, pending_jump.pos)
            self._notify(JumpLandedEvent(piece=pending_jump.piece, pos=pending_jump.pos, land_time=pending_jump.land_time))

        self._check_game_over(state)
        self._notify(TimeAdvancedEvent(current_time=state.current_time))

    def _resolve_due_move(self, state: GameState, pending_move: PendingMove) -> None:
        """* The origin must still hold the same piece (not captured, or
          already resolved) -- otherwise dropped.
        * A FRIENDLY piece now blocking the route stops the mover short
          instead of dropping the move outright (a no-op if that's the
          mover's own origin). An ENEMY piece blocking is still handled
          by RuleEngine's ordinary path-clear check below.
        * The move must still be legal (re-checks destination content
          and, for sliding pieces, that the path is still clear).
        * If the destination is an airborne enemy's cell, the jump wins:
          the defender never moves and the arriving piece is removed
          outright instead of relocating there.
        """
        if state.board.get(pending_move.from_pos) != pending_move.piece:
            return

        stop_pos = self._collision_resolver.stop_before_friendly_block(pending_move, state.board)
        if stop_pos is not None:
            if stop_pos != pending_move.from_pos:
                state.board.move(pending_move.from_pos, stop_pos)
                self._maybe_promote(state, pending_move.piece, stop_pos)
                self._set_cooldown(state, stop_pos)
                self._notify(MoveCompletedEvent(
                    piece=pending_move.piece, from_pos=pending_move.from_pos,
                    to_pos=stop_pos, arrival_time=pending_move.arrival_time,
                ))
            return

        legality = self._rule_engine.evaluate(state.board, pending_move.from_pos, pending_move.to_pos, pending_move.piece)
        if not legality.is_legal:
            return

        defender = self._collision_resolver.airborne_defender(pending_move.to_pos, pending_move.piece.color, state.airborne)
        if defender is not None:
            state.board.set(pending_move.from_pos, None)
            self._notify(AirborneCaptureEvent(defender=defender.piece, pos=defender.pos, attacker=pending_move.piece))
            return

        state.board.move(pending_move.from_pos, pending_move.to_pos)
        self._maybe_promote(state, pending_move.piece, pending_move.to_pos)
        self._set_cooldown(state, pending_move.to_pos)
        self._notify(MoveCompletedEvent(
            piece=pending_move.piece, from_pos=pending_move.from_pos,
            to_pos=pending_move.to_pos, arrival_time=pending_move.arrival_time,
        ))

    # ------------------------------------------------------------------
    # Read-only queries
    # ------------------------------------------------------------------

    @property
    def selection(self) -> Optional[Position]:
        return self._click_controller.selection

    def is_in_transit(self, state: GameState, pos: Position) -> bool:
        return any(pm.from_pos == pos for pm in state.pending)

    def is_airborne(self, state: GameState, pos: Position) -> bool:
        return self._airborne_at(state, pos) is not None

    def is_in_cooldown(self, state: GameState, pos: Position) -> bool:
        expiry = state.cooldowns.get(pos)
        return expiry is not None and expiry > state.current_time

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _is_busy(self, state: GameState, pos: Position) -> bool:
        return self.is_in_transit(state, pos) or self.is_airborne(state, pos) or self.is_in_cooldown(state, pos)

    def _set_cooldown(self, state: GameState, pos: Position) -> None:
        state.cooldowns[pos] = state.current_time + self._cooldown_duration

    def _airborne_at(self, state: GameState, pos: Position) -> Optional[PendingJump]:
        for pending_jump in state.airborne:
            if pending_jump.pos == pos:
                return pending_jump
        return None

    def _maybe_promote(self, state: GameState, piece, pos: Position) -> None:
        """Promote a Pawn to a Queen the instant it reaches the back
        rank. White promotes on row 0 (the row it advances toward);
        Black on ``num_rows - 1`` -- the mirror image."""
        if piece.kind != PAWN:
            return
        last_row = 0 if piece.color == "W" else state.board.height - 1
        if pos.row == last_row:
            state.board.set(pos, Piece(QUEEN, piece.color))

    def _check_game_over(self, state: GameState) -> None:
        if state.game_over:
            return
        result = self._game_over_rule.check(state.board)
        if not result.is_over:
            return
        state.game_over = True
        state.winner = result.winner
        self._notify(GameOverEvent(winner=state.winner))

    @staticmethod
    def _lane(from_pos: Position, to_pos: Position) -> Optional[tuple]:
        """The (axis, lo, hi) lane a straight move travels through.
        Diagonal / knight moves don't travel a single-axis lane and
        return None -- they never participate in route locking."""
        if from_pos.row == to_pos.row and from_pos.col != to_pos.col:
            lo, hi = sorted((from_pos.col, to_pos.col))
            return ("col", lo, hi)
        if from_pos.col == to_pos.col and from_pos.row != to_pos.row:
            lo, hi = sorted((from_pos.row, to_pos.row))
            return ("row", lo, hi)
        return None

    def _route_conflicts(self, state: GameState, piece, from_pos: Position, to_pos: Position) -> bool:
        """True if this move's lane overlaps an opposite-color piece
        already in transit along the same lane. Same-color moves and
        non-lane moves (diagonal / knight) never conflict."""
        lane = self._lane(from_pos, to_pos)
        if lane is None:
            return False
        axis, lo, hi = lane
        for pending_move in state.pending:
            if same_color(pending_move.piece, piece):
                continue
            other_lane = self._lane(pending_move.from_pos, pending_move.to_pos)
            if other_lane is None:
                continue
            other_axis, other_lo, other_hi = other_lane
            if other_axis != axis:
                continue
            if lo <= other_hi and other_lo <= hi:
                return True
        return False
