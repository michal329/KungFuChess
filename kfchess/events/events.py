"""Observer / Subject contracts and immutable event value objects.

Keeping events in their own top-level package:
  * Breaks the potential engine <-> gui circular-import chain.
  * Provides a single catalogue to grow without touching emitters or
    consumers -- the gui, a text renderer, and tests all just subscribe.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from kfchess.model.piece import Piece
from kfchess.model.position import Position


@dataclass(frozen=True)
class GameEvent:
    """Immutable marker base class for all game events."""


@dataclass(frozen=True)
class RenderEvent(GameEvent):
    """Fired when the current board state should be rendered/displayed."""
    board_text: str


@dataclass(frozen=True)
class TimeAdvancedEvent(GameEvent):
    """Fired after the game clock advances (after every ``tick`` call)."""
    current_time: int


@dataclass(frozen=True)
class MoveQueuedEvent(GameEvent):
    """Fired the instant ``attempt_move`` accepts and queues a move --
    before it travels, before it resolves. Nothing about local
    rendering needs this (``BoardRenderer`` already reads
    ``state.pending`` fresh every frame for the travel animation), but
    a networked client has no ``state.pending`` of its own to read
    unless something tells it a move just got queued -- this event
    exists so a server can pass that moment along immediately, rather
    than the client only finding out once the move lands, seconds
    later (see ``server/event_bridge.py`` and
    ``client/remote_game_view.py``)."""
    piece: Piece
    from_pos: Position
    to_pos: Position
    start_time: int
    arrival_time: int


@dataclass(frozen=True)
class JumpQueuedEvent(GameEvent):
    """The jump equivalent of ``MoveQueuedEvent`` -- fired the instant
    ``attempt_jump`` sends a piece airborne, before it lands."""
    piece: Piece
    pos: Position
    start_time: int
    land_time: int


@dataclass(frozen=True)
class MoveCompletedEvent(GameEvent):
    """Fired once for each pending move that executes during a ``tick``."""
    piece: Piece
    from_pos: Position
    to_pos: Position
    arrival_time: int


@dataclass(frozen=True)
class GameOverEvent(GameEvent):
    """Fired exactly once, the moment the game ends."""
    winner: Optional[str]


@dataclass(frozen=True)
class JumpLandedEvent(GameEvent):
    """Fired when a jump's window elapses with no enemy arrival -- the
    piece grounds again, unchanged, on the same cell it jumped from."""
    piece: Piece
    pos: Position
    land_time: int


@dataclass(frozen=True)
class AirborneCaptureEvent(GameEvent):
    """Fired when an airborne piece captures an enemy that arrived at its
    cell during the jump window. The defender never moves; the attacker
    is removed outright -- it never reaches ``pos``."""
    defender: Piece
    pos: Position
    attacker: Piece


class Observer(ABC):
    """Implement this and register with ``GameEngine.add_observer`` to
    receive ``GameEvent`` notifications."""

    @abstractmethod
    def on_event(self, event: GameEvent) -> None:
        ...
