"""ELO rating calculation -- the architecture doc's Rating System
section: initial rating 1200 (``server.auth.DEFAULT_RATING``), winner
gains points, loser loses points, scaled by how much of an upset the
result was (a low-rated player beating a high-rated one moves the
needle more than the "expected" outcome would).
"""
from __future__ import annotations

from typing import Optional, Tuple

from kfchess.model.piece import BLACK, WHITE

DEFAULT_K_FACTOR = 32


def _expected_score(rating_a: int, rating_b: int) -> float:
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def compute_new_ratings(
    white_rating: int,
    black_rating: int,
    winner: Optional[str],
    k_factor: int = DEFAULT_K_FACTOR,
) -> Tuple[int, int]:
    """*winner* is ``WHITE``, ``BLACK``, or ``None`` (a draw). Returns
    ``(new_white_rating, new_black_rating)``, each rounded to the
    nearest integer."""
    if winner == WHITE:
        white_score, black_score = 1.0, 0.0
    elif winner == BLACK:
        white_score, black_score = 0.0, 1.0
    else:
        white_score, black_score = 0.5, 0.5

    expected_white = _expected_score(white_rating, black_rating)
    expected_black = 1.0 - expected_white

    new_white = white_rating + k_factor * (white_score - expected_white)
    new_black = black_rating + k_factor * (black_score - expected_black)
    return round(new_white), round(new_black)
