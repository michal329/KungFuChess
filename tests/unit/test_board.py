from kfchess.model.board import Board
from kfchess.model.piece import KING, WHITE, Piece
from kfchess.model.position import Position


def test_get_set_empty_cell_is_none(empty_board):
    assert empty_board.get(Position(0, 0)) is None


def test_set_and_get(empty_board):
    piece = Piece(KING, WHITE)
    empty_board.set(Position(1, 1), piece)
    assert empty_board.get(Position(1, 1)) == piece


def test_set_none_clears_cell(empty_board):
    empty_board.set(Position(1, 1), Piece(KING, WHITE))
    empty_board.set(Position(1, 1), None)
    assert empty_board.get(Position(1, 1)) is None


def test_move_relocates_and_clears_origin(empty_board):
    piece = Piece(KING, WHITE)
    empty_board.set(Position(0, 0), piece)
    empty_board.move(Position(0, 0), Position(0, 1))
    assert empty_board.get(Position(0, 0)) is None
    assert empty_board.get(Position(0, 1)) == piece


def test_is_inside(empty_board):
    assert empty_board.is_inside(Position(0, 0))
    assert empty_board.is_inside(Position(7, 7))
    assert not empty_board.is_inside(Position(8, 0))
    assert not empty_board.is_inside(Position(-1, 0))


def test_all_positions_count(empty_board):
    assert len(list(empty_board.all_positions())) == 64


def test_copy_is_independent(empty_board):
    empty_board.set(Position(0, 0), Piece(KING, WHITE))
    copy = empty_board.copy()
    copy.set(Position(0, 0), None)
    assert empty_board.get(Position(0, 0)) is not None
    assert copy.get(Position(0, 0)) is None
