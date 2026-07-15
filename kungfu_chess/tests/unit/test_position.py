from kungfu_chess.model.position import Position


def test_equality_by_value():
    assert Position(1, 2) == Position(1, 2)


def test_inequality_when_different():
    assert Position(1, 2) != Position(2, 1)


def test_hashable_and_usable_in_set():
    s = {Position(0, 0), Position(0, 0), Position(1, 1)}
    assert len(s) == 2


def test_repr_contains_row_and_col():
    r = repr(Position(3, 4))
    assert "3" in r and "4" in r
