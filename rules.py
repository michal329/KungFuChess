"""
Movement rules for each piece type.

Design note: RuleSet is injected into Controller so the controller never
imports this module directly. A custom ruleset (e.g. reversed pawn) is
swapped in at construction time without touching Controller or Board.
Geometric checks live in the private rule functions.
Path-blocking (sliding pieces) is handled in _is_path_clear via board.get().
Knight is exempt from path checks -- it jumps over blockers.
To add a new piece type, add a function and register it in _RULES.
"""

import math


def _delta(src, dst):
    return dst[0] - src[0], dst[1] - src[1]


def _is_straight(dr, dc):
    return dr == 0 or dc == 0


def _is_diagonal(dr, dc):
    return abs(dr) == abs(dc)


def _is_path_clear(src, dst, board):
    """Returns True if every cell strictly between src and dst is empty."""
    dr, dc = _delta(src, dst)
    step_r = int(math.copysign(1, dr)) if dr != 0 else 0
    step_c = int(math.copysign(1, dc)) if dc != 0 else 0
    r, c = src[0] + step_r, src[1] + step_c
    while (r, c) != dst:
        if board.get(r, c) is not None:
            return False
        r += step_r
        c += step_c
    return True


def _king_legal(src, dst, board):
    dr, dc = _delta(src, dst)
    return max(abs(dr), abs(dc)) == 1


def _rook_legal(src, dst, board):
    dr, dc = _delta(src, dst)
    return (dr, dc) != (0, 0) and _is_straight(dr, dc) and _is_path_clear(src, dst, board)


def _bishop_legal(src, dst, board):
    dr, dc = _delta(src, dst)
    return (dr, dc) != (0, 0) and _is_diagonal(dr, dc) and _is_path_clear(src, dst, board)


def _queen_legal(src, dst, board):
    dr, dc = _delta(src, dst)
    return (dr, dc) != (0, 0) and (_is_straight(dr, dc) or _is_diagonal(dr, dc)) and _is_path_clear(src, dst, board)


def _knight_legal(src, dst, board):
    dr, dc = _delta(src, dst)
    return sorted([abs(dr), abs(dc)]) == [1, 2]


_RULES = {
    "K": _king_legal,
    "R": _rook_legal,
    "B": _bishop_legal,
    "Q": _queen_legal,
    "N": _knight_legal,
}


class RuleSet:
    """Validates move geometry and path blocking. Inject into Controller at construction time."""

    def is_legal_move(self, piece, src, dst, board):
        rule = _RULES.get(piece.type)
        if rule is None:
            return False
        return rule(src, dst, board)


DEFAULT_RULE_SET = RuleSet()
