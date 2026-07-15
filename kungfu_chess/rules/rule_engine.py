from dataclasses import dataclass
from kungfu_chess.rules.piece_rules import PieceRules


@dataclass(frozen=True)
class MoveValidation:
    is_valid: bool
    reason: str  # "ok" | "outside_board" | "empty_source" | "friendly_destination" | "illegal_piece_move"


_PIECE_RULES = PieceRules()


class RuleEngine:
    """Pure legality check — no side effects, no game-state awareness."""

    def validate_move(self, board, src, dst) -> MoveValidation:
        if not board.in_bounds(src) or not board.in_bounds(dst):
            return MoveValidation(False, "outside_board")
        piece = board.get(src)
        if piece is None:
            return MoveValidation(False, "empty_source")
        target = board.get(dst)
        if target is not None and target.color == piece.color:
            return MoveValidation(False, "friendly_destination")
        if dst not in _PIECE_RULES.legal_destinations(board, piece):
            return MoveValidation(False, "illegal_piece_move")
        return MoveValidation(True, "ok")
