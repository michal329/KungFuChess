"""Text-token configuration for board fixtures: <color><kind>, e.g.
"WK" (white king), "BP" (black pawn), or "." for an empty cell.

Kept as data (not scattered literals) so parsing, validation, and
rendering never hard-code the legal token set.
"""
from kfchess.model.piece import COLORS, PIECE_TYPES

EMPTY_TOKEN = "."


def build_legal_tokens(colors=COLORS, piece_types=PIECE_TYPES, empty_token=EMPTY_TOKEN):
    tokens = {empty_token}
    tokens.update(color + kind for color in colors for kind in piece_types)
    return frozenset(tokens)


LEGAL_TOKENS = build_legal_tokens()


def is_piece(token: str) -> bool:
    return token != EMPTY_TOKEN


def color_of(token: str):
    return token[0] if is_piece(token) else None


def kind_of(token: str):
    return token[1:] if is_piece(token) else None
