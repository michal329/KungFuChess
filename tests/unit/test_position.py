from kfchess.model.position import Position


def test_delta_to():
    assert Position(2, 3).delta_to(Position(5, 1)) == (3, -2)


def test_translated():
    assert Position(2, 3).translated(1, -1) == Position(3, 2)


def test_equality_and_hash():
    assert Position(1, 1) == Position(1, 1)
    assert hash(Position(1, 1)) == hash(Position(1, 1))
    assert Position(1, 1) != Position(1, 2)
