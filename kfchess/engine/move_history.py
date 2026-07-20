"""MoveHistory: a per-color log of every move that's actually completed,
built entirely as an Observer -- GameEngine already fires
MoveCompletedEvent for every completed move (including a friendly/enemy
stop-short landing), so this class adds zero work to GameEngine's own
methods. It doesn't sit in attempt_move's or tick's call path at all;
it's registered once via add_observer and only ever reacts afterward,
"on the side."

This intentionally does NOT check move legality -- that's not something
an Observer can do. GameEngine has already decided a move is legal and
already mutated the board by the time any observer's on_event() runs
(see kfchess.events.events.Observer); an observer has no way to veto or
influence that decision, only react to it. Legality stays exactly where
it was: RuleEngine, consulted synchronously inside attempt_move/
_resolve_due_move, before anything happens. What genuinely can move off
to the side, and does here, is bookkeeping about what already happened.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from kfchess.events.events import GameEvent, MoveCompletedEvent, Observer
from kfchess.model.piece import BLACK, WHITE, Piece
from kfchess.model.position import Position


@dataclass(frozen=True)
class MoveRecord:
    piece: Piece
    from_pos: Position
    to_pos: Position
    arrival_time: int


class MoveHistory(Observer):
    """Register with ``GameEngine.add_observer`` to start recording.
    Keeps one list per color, each in the order moves actually
    completed (arrival order, not queue order -- the same order
    ``MoveCompletedEvent`` itself fires in)."""

    def __init__(self) -> None:
        self._by_color: Dict[str, List[MoveRecord]] = {WHITE: [], BLACK: []}

    def on_event(self, event: GameEvent) -> None:
        if isinstance(event, MoveCompletedEvent):
            record = MoveRecord(
                piece=event.piece, from_pos=event.from_pos,
                to_pos=event.to_pos, arrival_time=event.arrival_time,
            )
            self._by_color[event.piece.color].append(record)

    def moves_for(self, color: str) -> List[MoveRecord]:
        """A defensive copy -- callers can't corrupt the log by mutating
        what they get back."""
        return list(self._by_color[color])

    def move_count(self, color: str) -> int:
        return len(self._by_color[color])
