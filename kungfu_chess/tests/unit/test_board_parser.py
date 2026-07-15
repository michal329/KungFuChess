# test_board_parser.py
import pytest
from kungfu_chess.io.board_parser import BoardParser
from kungfu_chess.model.board import RowWidthMismatchError, UnknownTokenError
from kungfu_chess.model.position import Position

def test_accepts_a_rectangular_board():
    board = BoardParser().parse(["wK . .", ". wR .", ". . bK"])
    assert board.rows == 3
    assert board.cols == 3

def test_places_pieces_at_the_correct_cells():
    board = BoardParser().parse(["wK . .", ". wR .", ". . bK"])
    king = board.get(Position(0, 0))
    assert king.color == "w"
    assert king.type == "K"
    assert board.get(Position(1, 1)).type == "R"

def test_rejects_inconsistent_row_length():
    with pytest.raises(RowWidthMismatchError):
        BoardParser().parse(["wK . .", ". wR"])

def test_rejects_illegal_piece_token():
    with pytest.raises(UnknownTokenError):
        BoardParser().parse(["wZ . .", ". . ."])

def test_assigns_unique_ids_to_each_piece():
    board = BoardParser().parse(["wK bK"])
    assert board.get(Position(0, 0)).id != board.get(Position(0, 1)).id

def test_ignores_blank_lines_around_the_board():
    board = BoardParser().parse(["", "wK .", "", ". bK", ""])
    assert board.rows == 2
    assert board.cols == 2