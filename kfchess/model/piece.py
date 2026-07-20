from __future__ import annotations

from dataclasses import dataclass

KING, QUEEN, ROOK, BISHOP, KNIGHT, PAWN = "K", "Q", "R", "B", "N", "P"
WHITE, BLACK = "W", "B"

PIECE_TYPES = (KING, QUEEN, ROOK, BISHOP, KNIGHT, PAWN)
COLORS = (WHITE, BLACK)

# Standard chess material values. The king has none since it is never
# actually captured for score -- a king capture ends the game instead
# (see kfchess.engine.game_over.KingCaptureRule).
PIECE_VALUES = {
    KING: 0,
    QUEEN: 9,
    ROOK: 5,
    BISHOP: 3,
    KNIGHT: 3,
    PAWN: 1,
}


@dataclass(frozen=True)
class Piece:
    kind: str   # one of KING/QUEEN/ROOK/BISHOP/KNIGHT/PAWN
    color: str  # WHITE or BLACK

    @property
    def code(self) -> str:
        """Two-letter asset code, e.g. 'NB' for a black knight."""
        return f"{self.kind}{self.color}"

    def __repr__(self) -> str:
        return f"Piece({self.kind!r}, {self.color!r})"


def same_color(piece_a: "Piece | None", piece_b: "Piece | None") -> bool:
    """True iff both pieces are real (not None) and share a color.

    Centralizes a check that would otherwise be duplicated everywhere
    two board cells' occupants are compared (friendly-fire detection,
    selection/reselection).
    """
    if piece_a is None or piece_b is None:
        return False
    return piece_a.color == piece_b.color
