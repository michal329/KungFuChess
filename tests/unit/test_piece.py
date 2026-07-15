from kfchess.model.piece import BLACK, KING, KNIGHT, WHITE, Piece, same_color


def test_code_is_kind_plus_color():
    assert Piece(KNIGHT, BLACK).code == "NB"
    assert Piece(KING, WHITE).code == "KW"


def test_same_color():
    assert same_color(Piece(KING, WHITE), Piece(KNIGHT, WHITE))
    assert not same_color(Piece(KING, WHITE), Piece(KNIGHT, BLACK))


def test_same_color_none_is_false():
    assert not same_color(None, Piece(KING, WHITE))
    assert not same_color(Piece(KING, WHITE), None)
    assert not same_color(None, None)
