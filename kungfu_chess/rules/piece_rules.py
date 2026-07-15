"""Movement rules for each piece type -- Strategy pattern, one class per
piece type, dispatched through the PieceRules facade.

Stateless: these rules do not store selected pieces, active motions,
elapsed time, or game-over state. They only calculate legal destinations
from the given board and piece.

Enemy-occupied destinations may be legal destinations. These functions
never capture, remove, move, or mutate pieces -- that happens later, in
RealTimeArbiter, only after a move has been validated.

Implementation order (fixed by the design doc): Rook, Bishop, Queen,
Knight, King, Pawn.
"""

from kungfu_chess.model.position import Position

_ROOK_DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
_BISHOP_DIRECTIONS = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
_KNIGHT_OFFSETS = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]
_KING_OFFSETS = _ROOK_DIRECTIONS + _BISHOP_DIRECTIONS


def _sliding_destinations(board, piece, directions):
    """Shared geometry for Rook/Bishop/Queen: walk each direction until
    blocked. A friendly blocker stops before it; an enemy blocker is
    included as a legal destination but stops the slide there."""
    destinations = set()
    for dr, dc in directions:
        pos = Position(piece.cell.row + dr, piece.cell.col + dc)
        while board.in_bounds(pos):
            occupant = board.get(pos)
            if occupant is None:
                destinations.add(pos)
            else:
                if occupant.color != piece.color:
                    destinations.add(pos)
                break
            pos = Position(pos.row + dr, pos.col + dc)
    return destinations


def _stepping_destinations(board, piece, offsets):
    """Shared geometry for Knight/King: fixed offsets, no path blocking."""
    destinations = set()
    for dr, dc in offsets:
        pos = Position(piece.cell.row + dr, piece.cell.col + dc)
        if not board.in_bounds(pos):
            continue
        occupant = board.get(pos)
        if occupant is None or occupant.color != piece.color:
            destinations.add(pos)
    return destinations


class RookRule:
    def legal_destinations(self, board, piece):
        return _sliding_destinations(board, piece, _ROOK_DIRECTIONS)


class BishopRule:
    def legal_destinations(self, board, piece):
        return _sliding_destinations(board, piece, _BISHOP_DIRECTIONS)


class QueenRule:
    def legal_destinations(self, board, piece):
        return _sliding_destinations(board, piece, _ROOK_DIRECTIONS + _BISHOP_DIRECTIONS)


class KnightRule:
    def legal_destinations(self, board, piece):
        return _stepping_destinations(board, piece, _KNIGHT_OFFSETS)


class KingRule:
    def legal_destinations(self, board, piece):
        return _stepping_destinations(board, piece, _KING_OFFSETS)


class PawnRule:
    """Simplified pawn: one step forward only (no double-step, no en
    passant). Captures one diagonal step forward. White advances toward
    row 0; black advances toward increasing row. Promotion is not a
    movement-rule concern -- the common route has none at all."""

    def legal_destinations(self, board, piece):
        forward = -1 if piece.color == "w" else 1
        destinations = set()

        forward_pos = Position(piece.cell.row + forward, piece.cell.col)
        if board.in_bounds(forward_pos) and board.get(forward_pos) is None:
            destinations.add(forward_pos)

        for dc in (-1, 1):
            capture_pos = Position(piece.cell.row + forward, piece.cell.col + dc)
            if not board.in_bounds(capture_pos):
                continue
            occupant = board.get(capture_pos)
            if occupant is not None and occupant.color != piece.color:
                destinations.add(capture_pos)

        return destinations


_RULES = {
    "R": RookRule(),
    "B": BishopRule(),
    "Q": QueenRule(),
    "N": KnightRule(),
    "K": KingRule(),
    "P": PawnRule(),
}


class PieceRules:
    """Facade: dispatches to the per-type Strategy rule."""

    def legal_destinations(self, board, piece):
        rule = _RULES.get(piece.type)
        if rule is None:
            return set()
        return rule.legal_destinations(board, piece)