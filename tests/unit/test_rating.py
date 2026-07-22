from kfchess.model.piece import BLACK, WHITE
from server.rating import compute_new_ratings


def test_equal_ratings_winner_gains_half_k_loser_loses_half_k():
    new_white, new_black = compute_new_ratings(1200, 1200, WHITE)
    assert new_white == 1200 + 16
    assert new_black == 1200 - 16


def test_black_win_is_symmetric():
    new_white, new_black = compute_new_ratings(1200, 1200, BLACK)
    assert new_white == 1200 - 16
    assert new_black == 1200 + 16


def test_draw_between_equal_ratings_changes_nothing():
    new_white, new_black = compute_new_ratings(1200, 1200, None)
    assert new_white == 1200
    assert new_black == 1200


def test_upset_win_gains_more_than_expected_win():
    # Black is much lower-rated; white winning is "expected" (small gain).
    expected_win_white, _ = compute_new_ratings(1600, 1000, WHITE)
    # Black is much lower-rated but wins anyway -- a bigger upset.
    _, upset_win_black = compute_new_ratings(1600, 1000, BLACK)
    assert (expected_win_white - 1600) < (upset_win_black - 1000)


def test_ratings_are_integers():
    new_white, new_black = compute_new_ratings(1250, 1180, WHITE)
    assert isinstance(new_white, int)
    assert isinstance(new_black, int)
