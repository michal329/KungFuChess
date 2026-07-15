from dataclasses import dataclass, field
from kungfu_chess.model.position import Position
from kungfu_chess.model.piece import Piece

CELL_SIZE_PX = 100       # pixels per cell
PIECE_SPEED_PX_MS = 0.1  # 100 px/sec = 0.1 px/ms  →  1 cell = 1000 ms


def travel_time_ms(src: Position, dst: Position) -> int:
    """Duration in ms using cell-step (Chebyshev) distance, not Euclidean.
    Spec: CELL_SIZE=100px, PIECE_SPEED=100px/sec → 1 cell = 1000ms.
    Diagonal counts as 1 cell-step, same as straight.
    """
    steps = max(abs(dst.row - src.row), abs(dst.col - src.col))
    return steps * 1000


@dataclass
class Motion:
    piece: Piece
    src: Position
    dst: Position
    arrival_ms: int   # absolute simulated time in ms when the piece arrives


@dataclass
class ArrivalEvents:
    """Returned by RealTimeArbiter.advance_time(ms)."""
    king_captured: bool = False
    arrived: list = field(default_factory=list)  # list of Motion objects that resolved
