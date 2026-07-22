"""RemoteGameView: the client's local mirror of a networked game's
``GameState`` -- the only thing that ever mutates it, and only ever
from incoming server ``Message``s, never from a local click or
legality decision. This is the network analogue of ``GameEngine``'s
board-mutation authority (CLAUDE.md rule 1): a client isn't the game's
owner, just a display mirror of a game running on the server (see
``kfchess/io/snapshot.py``'s ``game_state_from_snapshot`` docstring for
the same point made about reconstructing the board itself).

For every message with a local one-shot rendering concern, the
equivalent ``kfchess.events.events.GameEvent`` is reconstructed and
re-dispatched to registered ``Observer``s -- so ``BoardRenderer``
(``kfchess/gui/board_renderer.py``) works completely unmodified,
called exactly the way ``GameEngine`` already calls it locally.
``MoveQueuedMessage``/``JumpQueuedMessage``/``TimerMessage`` only ever
mutate ``state`` and dispatch nothing: ``BoardRenderer`` already reads
``state.pending``/``state.airborne``/``state.current_time`` fresh every
frame for the travel/jump animations and cooldown overlay (see that
module's own docstring on continuous vs. event-driven concerns), so
there is nothing further for an observer to react to.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Type

from kfchess.engine.game_state import GameState
from kfchess.events.events import (
    AirborneCaptureEvent,
    GameEvent,
    GameOverEvent,
    JumpLandedEvent,
    MoveCompletedEvent,
    Observer,
)
from kfchess.io.snapshot import dict_to_piece, dict_to_position, game_state_from_snapshot
from kfchess.realtime.motion import PendingJump, PendingMove
from protocol.messages import (
    AirborneCaptureMessage,
    GameEndedMessage,
    JumpLandedMessage,
    JumpQueuedMessage,
    Message,
    MoveEventMessage,
    MoveQueuedMessage,
    SnapshotMessage,
    TimerMessage,
)


class RemoteGameView:
    def __init__(self, state: GameState) -> None:
        self.state = state
        self._observers: List[Observer] = []

    @classmethod
    def from_snapshot(cls, payload: Dict) -> "RemoteGameView":
        return cls(game_state_from_snapshot(payload))

    def add_observer(self, observer: Observer) -> None:
        self._observers.append(observer)

    def _notify(self, event: GameEvent) -> None:
        for observer in self._observers:
            observer.on_event(event)

    def apply(self, message: Message) -> None:
        handler = _HANDLERS.get(type(message))
        if handler is not None:
            handler(self, message)

    def _apply_snapshot(self, message: SnapshotMessage) -> None:
        fresh = game_state_from_snapshot(message.payload)
        self.state.board = fresh.board
        self.state.current_time = fresh.current_time
        self.state.pending = fresh.pending
        self.state.airborne = fresh.airborne
        self.state.cooldowns = fresh.cooldowns
        self.state.game_over = fresh.game_over
        self.state.winner = fresh.winner

    def _apply_move_queued(self, message: MoveQueuedMessage) -> None:
        self.state.pending.append(PendingMove(
            piece=dict_to_piece(message.piece),
            from_pos=dict_to_position(message.from_),
            to_pos=dict_to_position(message.to),
            arrival_time=message.arrival_time,
            start_time=message.start_time,
        ))

    def _apply_jump_queued(self, message: JumpQueuedMessage) -> None:
        self.state.airborne.append(PendingJump(
            piece=dict_to_piece(message.piece),
            pos=dict_to_position(message.pos),
            land_time=message.land_time,
            start_time=message.start_time,
        ))

    def _apply_move_event(self, message: MoveEventMessage) -> None:
        from_pos = dict_to_position(message.from_)
        to_pos = dict_to_position(message.to)
        piece = dict_to_piece(message.piece)
        self.state.pending = [pm for pm in self.state.pending if pm.from_pos != from_pos]
        self.state.board.move(from_pos, to_pos)
        self._notify(MoveCompletedEvent(piece=piece, from_pos=from_pos, to_pos=to_pos, arrival_time=message.arrival_time))

    def _apply_jump_landed(self, message: JumpLandedMessage) -> None:
        pos = dict_to_position(message.pos)
        piece = dict_to_piece(message.piece)
        self.state.airborne = [pj for pj in self.state.airborne if pj.pos != pos]
        self._notify(JumpLandedEvent(piece=piece, pos=pos, land_time=message.land_time))

    def _apply_airborne_capture(self, message: AirborneCaptureMessage) -> None:
        """The attacker never had a resolution message of its own --
        it's simply gone. Its origin isn't in this message at all, but
        it's exactly what the matching ``PendingMove`` (queued back
        when the attack started, see ``_apply_move_queued``) already
        recorded, so we recover it from there before dropping that
        entry, then clear the attacker off the board at that origin."""
        pos = dict_to_position(message.pos)
        attacker = dict_to_piece(message.attacker)
        defender = dict_to_piece(message.defender)
        matched = next((pm for pm in self.state.pending if pm.to_pos == pos and pm.piece == attacker), None)
        if matched is not None:
            self.state.pending = [pm for pm in self.state.pending if pm is not matched]
            self.state.board.set(matched.from_pos, None)
        self._notify(AirborneCaptureEvent(defender=defender, pos=pos, attacker=attacker))

    def _apply_game_ended(self, message: GameEndedMessage) -> None:
        self.state.game_over = True
        self.state.winner = message.winner
        self._notify(GameOverEvent(winner=message.winner))

    def _apply_timer(self, message: TimerMessage) -> None:
        self.state.current_time = message.current_time


_HANDLERS: Dict[Type[Message], Callable[["RemoteGameView", Message], None]] = {
    SnapshotMessage: RemoteGameView._apply_snapshot,
    MoveQueuedMessage: RemoteGameView._apply_move_queued,
    JumpQueuedMessage: RemoteGameView._apply_jump_queued,
    MoveEventMessage: RemoteGameView._apply_move_event,
    JumpLandedMessage: RemoteGameView._apply_jump_landed,
    AirborneCaptureMessage: RemoteGameView._apply_airborne_capture,
    GameEndedMessage: RemoteGameView._apply_game_ended,
    TimerMessage: RemoteGameView._apply_timer,
}
