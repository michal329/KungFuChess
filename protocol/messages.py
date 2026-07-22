"""Server -> client messages.

Same JSON-primitive-only rule as ``protocol.commands``. ``SnapshotMessage.payload``
carries exactly the dict produced by ``kfchess.io.snapshot.game_state_snapshot`` --
this module never imports ``kfchess.model`` itself, it just carries that
already-boundary-crossed data in an envelope.

Schemas below cover every message the architecture doc lists (snapshot,
move event, timer, rating, game started/ended, room created, error).
Only ``SnapshotMessage``/``MoveEventMessage``/``JumpLandedMessage``/
``AirborneCaptureMessage``/``TimerMessage``/``GameEndedMessage`` have a
producer wired up yet (``server.event_bridge``, epic 1/2); ``rating``,
``game_started`` and ``room_created`` are schema-only until rooms/
matchmaking/ratings (later epics) exist to emit them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, Dict, Optional

_FROM_KEY = {"json_key": "from"}


@dataclass(frozen=True)
class Message:
    """Marker base class for all server -> client messages. Every
    subclass sets ``type`` (a plain class attribute, not a dataclass
    field) to its wire discriminator string."""
    type: ClassVar[str] = ""


@dataclass(frozen=True)
class SnapshotMessage(Message):
    type: ClassVar[str] = "snapshot"
    payload: Dict


@dataclass(frozen=True)
class MoveQueuedMessage(Message):
    """The wire form of ``kfchess.events.events.MoveQueuedEvent`` --
    fired the instant a move is accepted, not when it lands, so a
    client can start the travel animation immediately (see that
    event's docstring for why local rendering never needed this)."""
    type: ClassVar[str] = "move_queued"
    piece: str
    from_: Dict[str, int] = field(metadata=_FROM_KEY)
    to: Dict[str, int] = None
    start_time: int = 0
    arrival_time: int = 0


@dataclass(frozen=True)
class JumpQueuedMessage(Message):
    type: ClassVar[str] = "jump_queued"
    piece: str
    pos: Dict[str, int]
    start_time: int
    land_time: int


@dataclass(frozen=True)
class MoveEventMessage(Message):
    type: ClassVar[str] = "move_event"
    piece: str
    from_: Dict[str, int] = field(metadata=_FROM_KEY)
    to: Dict[str, int] = None
    arrival_time: int = 0


@dataclass(frozen=True)
class JumpLandedMessage(Message):
    type: ClassVar[str] = "jump_landed"
    piece: str
    pos: Dict[str, int]
    land_time: int


@dataclass(frozen=True)
class AirborneCaptureMessage(Message):
    type: ClassVar[str] = "airborne_capture"
    defender: str
    pos: Dict[str, int]
    attacker: str


@dataclass(frozen=True)
class TimerMessage(Message):
    type: ClassVar[str] = "timer"
    current_time: int


@dataclass(frozen=True)
class GameEndedMessage(Message):
    type: ClassVar[str] = "game_ended"
    winner: Optional[str]


@dataclass(frozen=True)
class RatingMessage(Message):
    type: ClassVar[str] = "rating"
    username: str
    rating: int


@dataclass(frozen=True)
class GameStartedMessage(Message):
    """``move_duration``/``jump_duration``/``cooldown_duration`` (ms) are
    this game's actual configured values -- carried over the wire so a
    networked client can compute cooldown-overlay timing itself without
    hardcoding a copy of ``kfchess.engine.game_engine``'s defaults that
    could silently drift if the server ever configures a game
    differently."""
    type: ClassVar[str] = "game_started"
    room_id: str
    color: str
    move_duration: int
    jump_duration: int
    cooldown_duration: int


@dataclass(frozen=True)
class RoomCreatedMessage(Message):
    type: ClassVar[str] = "room_created"
    room_id: str


@dataclass(frozen=True)
class ErrorMessage(Message):
    type: ClassVar[str] = "error"
    reason: str


# Registry used by protocol.serialization to reconstruct the right
# dataclass from an incoming {"type": ...} dict.
MESSAGE_TYPES = {
    "snapshot": SnapshotMessage,
    "move_queued": MoveQueuedMessage,
    "jump_queued": JumpQueuedMessage,
    "move_event": MoveEventMessage,
    "jump_landed": JumpLandedMessage,
    "airborne_capture": AirborneCaptureMessage,
    "timer": TimerMessage,
    "game_ended": GameEndedMessage,
    "rating": RatingMessage,
    "game_started": GameStartedMessage,
    "room_created": RoomCreatedMessage,
    "error": ErrorMessage,
}
