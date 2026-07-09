"""
Movement rules for each piece type.

Design note: RuleSet is injected into Controller so the controller never
imports this module directly. A custom ruleset (e.g. reversed pawn) is
swapped in at construction time without touching Controller or Board.
Each rule function is purely geometric -- (src, dst) tuples only.
To add a new piece type, add a function and register it in _RULES.
"""


def _delta(src, dst):
    return dst[0] - src[0], dst[1] - src[1]


def _is_straight(dr, dc):
    return dr == 0 or dc == 0


def _is_diagonal(dr, dc):
    return abs(dr) == abs(dc)


def _king_legal(src, dst):
    dr, dc = _delta(src, dst)
    return max(abs(dr), abs(dc)) == 1


def _rook_legal(src, dst):
    dr, dc = _delta(src, dst)
    return (dr, dc) != (0, 0) and _is_straight(dr, dc)


def _bishop_legal(src, dst):
    dr, dc = _delta(src, dst)
    return (dr, dc) != (0, 0) and _is_diagonal(dr, dc)


def _queen_legal(src, dst):
    dr, dc = _delta(src, dst)
    return (dr, dc) != (0, 0) and (_is_straight(dr, dc) or _is_diagonal(dr, dc))


def _knight_legal(src, dst):
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
    """Validates move geometry. Inject into Controller at construction time."""

    def is_legal_move(self, piece, src, dst):
        rule = _RULES.get(piece.type)
        if rule is None:
            return False
        return rule(src, dst)


DEFAULT_RULE_SET = RuleSet()
