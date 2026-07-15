from kfchess.io.board_printer import render
from kfchess.model.board import Board
from kfchess.model.piece import KING, ROOK, WHITE, Piece
from kfchess.model.position import Position


def test_render_round_trips_with_build_board():
    from kfchess.io.board_parser import build_board
    grid = [["WR", ".", "."], [".", ".", "BK"]]
    board = build_board(grid)
    assert render(board) == "WR . .\n. . BK"


def test_render_empty_board_is_all_dots():
    board = Board(2, 2)
    assert render(board) == ". .\n. ."
