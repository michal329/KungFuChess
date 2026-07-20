from __future__ import annotations

from dataclasses import dataclass

from kfchess.model.piece import Piece
from kfchess.model.position import Position


@dataclass(frozen=True)
class PendingMove:
    """A validated move that is queued and waiting to arrive.

    ``piece``        -- the piece at the origin cell at the moment the
                         move was queued. Stored so the engine can
                         double-check it's still there when the move
                         resolves (it may have been captured mid-flight).
    ``start_time``   -- game-clock value (ms) at which the move was
                         queued. Together with ``arrival_time`` this is
                         enough for a renderer to interpolate the
                         piece's on-screen position during the flight,
                         without needing to know engine-internal
                         configuration like move_duration.
    ``arrival_time``  -- game-clock value (ms) at which the move executes.
    """
    piece: Piece
    from_pos: Position
    to_pos: Position
    arrival_time: int
    start_time: int = 0


@dataclass(frozen=True)
class PendingJump:
    """A piece committed to an in-place jump, defending its own cell.

    Unlike PendingMove, a jump never relocates its piece -- ``pos`` is
    both origin and destination for the jump's whole duration.

    ``start_time`` -- game-clock value (ms) at which the jump began;
    see ``PendingMove.start_time`` for why it's carried alongside
    ``land_time``.
    """
    piece: Piece
    pos: Position
    land_time: int
    start_time: int = 0
