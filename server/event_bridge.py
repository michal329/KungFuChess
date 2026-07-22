"""GameEventBridge: an ``Observer`` (kfchess.events.events) that
translates every ``GameEvent`` a ``GameEngine`` fires into its
``protocol.messages`` wire equivalent and publishes it on the
``Bus``, topic ``"game.<game_id>"``.

Registered exactly like ``MoveHistory`` (see
``kfchess/engine/move_history.py``) via ``GameEngine.add_observer`` --
it reacts strictly after the engine has already decided and mutated
the board, same as any other Observer, so it has no legality say (see
CLAUDE.md rule 8). ``game_id`` is an opaque string correlator; this
module has no notion of a "room" -- a future Room/Game Manager just
constructs one bridge per active game and hands it whatever id it
likes.

``RenderEvent`` (text-mode only) has no wire equivalent and is
silently dropped, same as any future GameEvent subclass this bridge
doesn't yet know how to translate.
"""
from __future__ import annotations

from typing import Callable, Dict, Optional, Type

from kfchess.events.events import (
    AirborneCaptureEvent,
    GameEvent,
    GameOverEvent,
    JumpLandedEvent,
    JumpQueuedEvent,
    MoveCompletedEvent,
    MoveQueuedEvent,
    Observer,
    TimeAdvancedEvent,
)
from kfchess.io.board_printer import piece_token
from kfchess.io.snapshot import position_to_dict
from protocol.messages import (
    AirborneCaptureMessage,
    GameEndedMessage,
    JumpLandedMessage,
    JumpQueuedMessage,
    Message,
    MoveEventMessage,
    MoveQueuedMessage,
    TimerMessage,
)
from server.bus import Bus


def _translate_move_queued(event: MoveQueuedEvent) -> MoveQueuedMessage:
    return MoveQueuedMessage(
        piece=piece_token(event.piece),
        from_=position_to_dict(event.from_pos),
        to=position_to_dict(event.to_pos),
        start_time=event.start_time,
        arrival_time=event.arrival_time,
    )


def _translate_jump_queued(event: JumpQueuedEvent) -> JumpQueuedMessage:
    return JumpQueuedMessage(
        piece=piece_token(event.piece),
        pos=position_to_dict(event.pos),
        start_time=event.start_time,
        land_time=event.land_time,
    )


def _translate_move_completed(event: MoveCompletedEvent) -> MoveEventMessage:
    return MoveEventMessage(
        piece=piece_token(event.piece),
        from_=position_to_dict(event.from_pos),
        to=position_to_dict(event.to_pos),
        arrival_time=event.arrival_time,
    )


def _translate_jump_landed(event: JumpLandedEvent) -> JumpLandedMessage:
    return JumpLandedMessage(
        piece=piece_token(event.piece),
        pos=position_to_dict(event.pos),
        land_time=event.land_time,
    )


def _translate_airborne_capture(event: AirborneCaptureEvent) -> AirborneCaptureMessage:
    return AirborneCaptureMessage(
        defender=piece_token(event.defender),
        pos=position_to_dict(event.pos),
        attacker=piece_token(event.attacker),
    )


def _translate_game_over(event: GameOverEvent) -> GameEndedMessage:
    return GameEndedMessage(winner=event.winner)


def _translate_time_advanced(event: TimeAdvancedEvent) -> TimerMessage:
    return TimerMessage(current_time=event.current_time)


_TRANSLATORS: Dict[Type[GameEvent], Callable[[GameEvent], Message]] = {
    MoveQueuedEvent: _translate_move_queued,
    JumpQueuedEvent: _translate_jump_queued,
    MoveCompletedEvent: _translate_move_completed,
    JumpLandedEvent: _translate_jump_landed,
    AirborneCaptureEvent: _translate_airborne_capture,
    GameOverEvent: _translate_game_over,
    TimeAdvancedEvent: _translate_time_advanced,
}


def translate_event(event: GameEvent) -> Optional[Message]:
    translator = _TRANSLATORS.get(type(event))
    return translator(event) if translator is not None else None


class GameEventBridge(Observer):
    def __init__(self, bus: Bus, game_id: str) -> None:
        self._bus = bus
        self._game_id = game_id

    @property
    def topic(self) -> str:
        return f"game.{self._game_id}"

    def on_event(self, event: GameEvent) -> None:
        message = translate_event(event)
        if message is not None:
            self._bus.publish(self.topic, message)
