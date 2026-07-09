"""
Movement rules for each piece type.

Design note: each rule function receives only (src, dst) as (row, col) tuples.
No board reference needed -- legality is purely geometric for these pieces.
To add a new piece type, add a function and register it in RULES.
"""


def _delta(src, dst):
    return dst[0] - src[0], dst[1] - src[1]


def _is_straight(dr, dc):
    return dr == 0 or dc == 0


def _is_diagonal(dr, dc):
    return abs(dr) == abs(dc)


def king_legal(src, dst):
    dr, dc = _delta(src, dst)
    return max(abs(dr), abs(dc)) == 1


def rook_legal(src, dst):
    dr, dc = _delta(src, dst)
    return (dr, dc) != (0, 0) and _is_straight(dr, dc)


def bishop_legal(src, dst):
    dr, dc = _delta(src, dst)
    return (dr, dc) != (0, 0) and _is_diagonal(dr, dc)


def queen_legal(src, dst):
    dr, dc = _delta(src, dst)
    return (dr, dc) != (0, 0) and (_is_straight(dr, dc) or _is_diagonal(dr, dc))


def knight_legal(src, dst):
    dr, dc = _delta(src, dst)
    return sorted([abs(dr), abs(dc)]) == [1, 2]


RULES = {
    "K": king_legal,
    "R": rook_legal,
    "B": bishop_legal,
    "Q": queen_legal,
    "N": knight_legal,
}


def is_legal_move(piece, src, dst):
    rule = RULES.get(piece.type)
    if rule is None:
        return False
    return rule(src, dst)
