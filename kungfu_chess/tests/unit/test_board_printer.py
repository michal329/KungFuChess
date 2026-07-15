# test_board_printer.py
from kungfu_chess.io.board_parser import BoardParser
from kungfu_chess.io.board_printer import BoardPrinter
from kungfu_chess.model.board import Board

def test_round_trips_a_simple_board():
    board = BoardParser().parse(["wK . .", ". wR .", ". . bK"])
    assert BoardPrinter().print(board) == "wK . .\n. wR .\n. . bK"

def test_prints_dots_for_an_all_empty_board():
    assert BoardPrinter().print(Board(2, 2)) == ". .\n. ."