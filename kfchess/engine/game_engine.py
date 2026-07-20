"""GameEngine: stateless game-rules service, operating on an
externally-owned GameState passed into every action method.

Responsibilities
-----------------
* Hold zero per-game state. Every attribute on ``self`` is either a
  collaborator (RuleEngine, CollisionResolver, BoardMapper, ...) or
  static per-game configuration (move/cooldown duration) -- fixed at
  construction, never mutated afterward. Board, clock, pending moves,
  cooldowns, game-over/winner all live on the caller's GameState
  instead, threaded through every call as an explicit ``state``
  argument. This lets one GameEngine instance (and all its
  collaborators) drive many independent GameStates concurrently, and
  makes every method trivially unit-testable without setup/teardown
  races.
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
from kfchess.model.piece import KING, PAWN, QUEEN, Piece
from kfchess.model.position import Position
from kfchess.realtime.collision_resolver import CollisionResolver
from kfchess.realtime.motion import PendingJump, PendingMove
from kfchess.rules.rule_engine import RuleEngine

MOVE_DURATION_MS = 1000
JUMP_DURATION_MS = 1000
COOLDOWN_DURATION_MS = 1000
DEFAULT_CELL_SIZE = 100


class _VacatedOriginsView:
    """A read-only board view used only for legality/collision checks
    against OTHER pieces' moves: it reports every position in
    *vacated* as empty, regardless of what the real Board still has
    recorded there.

    The real Board is deliberately never mutated until a move actually
    resolves -- rendering and the text-mode printer both read it
    directly and are expected to keep showing a piece at its origin
    for the whole flight (that's what makes the travel animation and
    "print board" mid-flight snapshots meaningful). This view exists
    so that *legality* can disagree with that raw snapshot: a piece
    that's currently in flight (has a PendingMove) is real-world gone
    from its origin already, so nothing should be able to capture it,
    or be blocked by it, there -- even though the Board dict hasn't
    "caught up" yet.

    Only the three methods RuleEngine/CollisionResolver actually call
    are implemented; this is not a general-purpose Board substitute.
    """

    def __init__(self, board: Board, vacated) -> None:
        self._board = board
        self._vacated = vacated

    def get(self, position: Position):
        if position in self._vacated:
            return None
        return self._board.get(position)

    def is_inside(self, position: Position) -> bool:
        return self._board.is_inside(position)

    def dimensions(self) -> tuple:
        return self._board.dimensions()


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
        only legality, via attempt_move/attempt_jump/is_selectable.
        Clicking a selected piece's own square again (rather than a
        different destination) is what ClickController interprets as a
        jump -- see its class docstring."""
        self._click_controller.handle_click(state, x, y)

    def attempt_jump(self, state: GameState, pos: Position) -> bool:
        """Sends the piece at *pos* airborne for jump_duration ms, iff
        it isn't busy. Unlike a move, a jump never relocates its piece
        -- it stays on its own square the whole time, tracked separately
        in state.airborne rather than state.pending. While airborne, it
        can't be selected or jumped again (see _is_busy), and if an
        enemy's queued move arrives at its square before the window
        closes, the jump wins: see _resolve_due_move."""
        if state.game_over:
            return False

        piece = state.board.get(pos)
        if piece is None or self._is_busy(state, pos):
            return False

        state.airborne.append(PendingJump(
            piece=piece, pos=pos,
            land_time=state.current_time + self._jump_duration,
            start_time=state.current_time,
        ))
        return True

    def is_selectable(self, state: GameState, pos: Position) -> bool:
        piece = state.board.get(pos)
        return piece is not None and not self._is_busy(state, pos)

    def attempt_move(self, state: GameState, from_pos: Position, to_pos: Position) -> bool:
        """Queues a PendingMove iff every check passes; returns True iff
        queued. The piece itself only relocates later, when ``tick``
        reaches its ``arrival_time``. Checks, in order: game not over; a
        piece sits at *from_pos* and isn't busy; RuleEngine approves
        shape/destination/path *as the board looks right now* -- except
        that any square another piece is currently mid-flight away from
        counts as empty, not as "that piece is still there": a piece
        that's already in motion can't be blocked against or captured
        at the origin it's already left (see ``_VacatedOriginsView``).

        No route is "reserved" by queuing this move -- there is no
        advance notion of a lane being locked. Whatever happens to be
        blocking the path (or not) at resolution time, possibly minutes
        of simulated time from now and possibly not even queued yet, is
        what decides the outcome -- see ``_resolve_due_move`` /
        ``CollisionResolver.stop_before_block``.
        """
        if state.game_over:
            return False

        piece = state.board.get(from_pos)
        if piece is None or self._is_busy(state, from_pos):
            return False

        vacated = {pm.from_pos for pm in state.pending}
        effective_board = _VacatedOriginsView(state.board, vacated)
        legality = self._rule_engine.evaluate(effective_board, from_pos, to_pos, piece)
        if not legality.is_legal:
            return False

        cells_moved = max(abs(from_pos.row - to_pos.row), abs(from_pos.col - to_pos.col))
        arrival = state.current_time + cells_moved * self._move_duration
        state.pending.append(PendingMove(
            piece=piece, from_pos=from_pos, to_pos=to_pos,
            arrival_time=arrival, start_time=state.current_time,
        ))
        return True

    def tick(self, state: GameState, ms: int) -> None:
        """Advance *state*'s clock by *ms*. Due moves execute in
        chronological order (earliest arrival first; ties keep queue
        order), then jump landings resolve, then a GameOver check runs.

        Because earlier-arriving moves in the same tick apply first, a
        later move's re-validation sees their results -- e.g. two
        pieces racing for the same square: whichever arrives first
        occupies it, and a later enemy can still capture it there, while
        a later friendly is rejected as blocked. A piece whose path gets
        blocked (by anyone actually at rest there) between being queued
        and actually resolving stops short instead of completing -- see
        ``CollisionResolver.stop_before_block``. An airborne defender
        can defeat multiple arrivals in the same tick this way -- it
        never leaves its cell.

        Due moves are removed from ``state.pending`` one at a time,
        immediately before each is resolved -- not all at once up
        front -- so that at every step, ``state.pending`` accurately
        answers "which pieces (including other due moves not yet their
        turn this same tick) are still genuinely in flight." That list
        is exactly what ``_resolve_due_move`` needs to know which
        squares to treat as vacated for this move's own checks.
        """
        state.current_time += ms

        due = sorted(
            (pm for pm in state.pending if pm.arrival_time <= state.current_time),
            key=lambda pm: pm.arrival_time,
        )
        for pending_move in due:
            state.pending.remove(pending_move)
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
        """* Anything actually at rest -- friend or enemy -- partway
          along the route stops the mover short there instead of
          dropping the move outright (a no-op if that's the mover's own
          origin). The mover never reaches, or captures, whatever's
          blocking it. A piece that's itself still mid-flight (has its
          own not-yet-resolved PendingMove) never counts as "at rest"
          here -- see ``_VacatedOriginsView`` -- so it can neither block
          nor be captured at the square it's already left.
        * If the path is clear all the way, the move must still be legal
          at the destination (re-checks it isn't now a friendly piece;
          an enemy actually at rest there is an ordinary capture; a
          square that only *looks* occupied because another in-flight
          piece hasn't formally left it yet counts as empty).
        * If the destination is an airborne enemy's cell, the jump wins:
          the defender never moves and the arriving piece is removed
          outright instead of relocating there.

        Note there's no "was I captured mid-flight" check here anymore:
        a piece in flight has nothing left at its origin that anything
        else could legally interact with (see attempt_move), so nothing
        can invalidate this move out from under it before it resolves.
        """
        vacated = {pm.from_pos for pm in state.pending}
        effective_board = _VacatedOriginsView(state.board, vacated)

        stop_pos = self._collision_resolver.stop_before_block(pending_move, effective_board)
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

        legality = self._rule_engine.evaluate(effective_board, pending_move.from_pos, pending_move.to_pos, pending_move.piece)
        if not legality.is_legal:
            return

        defender = self._collision_resolver.airborne_defender(pending_move.to_pos, pending_move.piece.color, state.airborne)
        if defender is not None:
            state.board.set(pending_move.from_pos, None)
            self._notify(AirborneCaptureEvent(defender=defender.piece, pos=defender.pos, attacker=pending_move.piece))
            return

        captured_piece = effective_board.get(pending_move.to_pos)  # read before move() overwrites the real board
        state.board.move(pending_move.from_pos, pending_move.to_pos)
        self._maybe_promote(state, pending_move.piece, pending_move.to_pos, captured_piece=captured_piece)
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

    @property
    def cooldown_duration(self) -> int:
        """Read-only: how long, in ms, a cooldown lasts -- exposed so a
        renderer can compute what fraction of a cooldown remains at a
        given cell without duplicating this configuration value."""
        return self._cooldown_duration

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

    def _maybe_promote(self, state: GameState, piece, pos: Position, captured_piece=None) -> None:
        """Promote a Pawn to a Queen the instant it reaches the back
        rank. White promotes on row 0 (the row it advances toward);
        Black on ``num_rows - 1`` -- the mirror image.

        Skipped entirely if this same move just captured the enemy
        King: the game is already over the instant ``_check_game_over``
        runs later this tick, so there's no game left for a queen to
        play in -- promoting first would just leave a Queen sitting on
        a finished board for no reason.
        """
        if piece.kind != PAWN:
            return
        if captured_piece is not None and captured_piece.kind == KING:
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
