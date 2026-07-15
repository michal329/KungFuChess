import pytest

from kfchess.io.board_parser import build_board, parse_board_section
from kfchess.io.errors import RowWidthMismatchError, UnknownTokenError
from kfchess.model.piece import KING, ROOK, WHITE, Piece
from kfchess.model.position import Position


def test_parse_board_section_splits_rows_into_tokens():
    lines = ["Board:", "WR . .", ". . BK", "Commands:", "click 0 0"]
    grid = parse_board_section(lines)
    assert grid == [["WR", ".", "."], [".", ".", "BK"]]


def test_build_board_places_pieces():
    board = build_board([["WR", "."], [".", "BK"]])
    assert board.get(Position(0, 0)) == Piece(ROOK, WHITE)
    assert board.get(Position(1, 1)) == Piece(KING, "B")
    assert board.get(Position(0, 1)) is None


def test_build_board_empty_grid():
    board = build_board([])
    assert board.dimensions() == (0, 0)


def test_build_board_rejects_mismatched_row_width():
    with pytest.raises(RowWidthMismatchError):
        build_board([["WR", "."], ["."]])


def test_build_board_rejects_unknown_token():
    with pytest.raises(UnknownTokenError):
        build_board([["ZZ", "."]])
