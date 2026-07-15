from kfchess.engine.game_over import KingCaptureRule
from kfchess.model.piece import BLACK, KING, WHITE, Piece
from kfchess.model.position import Position


def test_no_result_while_both_kings_present(empty_board):
    empty_board.set(Position(0, 0), Piece(KING, WHITE))
    empty_board.set(Position(7, 7), Piece(KING, BLACK))
    rule = KingCaptureRule()
    assert not rule.check(empty_board).is_over


def test_white_wins_when_black_king_captured(empty_board):
    empty_board.set(Position(0, 0), Piece(KING, WHITE))
    empty_board.set(Position(7, 7), Piece(KING, BLACK))
    rule = KingCaptureRule()
    rule.check(empty_board)  # prime as armed

    empty_board.set(Position(7, 7), None)
    result = rule.check(empty_board)
    assert result.is_over
    assert result.winner == WHITE


def test_unarmed_color_never_ends_game(empty_board):
    # Board only ever had a white King -- black was never armed, so the
    # ever-true "black has no king" fact must never end the game.
    empty_board.set(Position(0, 0), Piece(KING, WHITE))
    rule = KingCaptureRule()
    assert not rule.check(empty_board).is_over
    assert not rule.check(empty_board).is_over  # still true on repeated checks


def test_armed_side_losing_ends_game_even_if_opponent_unarmed(empty_board):
    empty_board.set(Position(0, 0), Piece(KING, WHITE))
    rule = KingCaptureRule()
    rule.check(empty_board)  # prime: white armed, black unarmed

    empty_board.set(Position(0, 0), None)
    result = rule.check(empty_board)
    assert result.is_over
    assert result.winner == BLACK


def test_simultaneous_double_capture_is_draw(empty_board):
    empty_board.set(Position(0, 0), Piece(KING, WHITE))
    empty_board.set(Position(7, 7), Piece(KING, BLACK))
    rule = KingCaptureRule()
    rule.check(empty_board)

    empty_board.set(Position(0, 0), None)
    empty_board.set(Position(7, 7), None)
    result = rule.check(empty_board)
    assert result.is_over
    assert result.winner is None
