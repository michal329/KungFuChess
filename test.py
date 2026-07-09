import pytest

from board import Board, RowWidthMismatchError, UnknownTokenError, Piece
from controller import Controller
from rules import is_legal_move


# ---------- Board.parse ----------

def test_parse_rectangular_board():
    board = Board.parse(["wK . . bK", ". . . .", "wR . . bR"])
    assert board.rows == 3
    assert board.cols == 4
    assert str(board) == "wK . . bK\n. . . .\nwR . . bR"


def test_parse_piece_tokens_and_colors():
    board = Board.parse(["wK . bQ", ". wN .", "bP . wR"])
    king = board.get(0, 0)
    assert king.color == "w" and king.type == "K"
    assert board.get(0, 1) is None


def test_reject_unknown_token():
    with pytest.raises(UnknownTokenError):
        Board.parse(["wK xZ", ". ."])


def test_reject_row_width_mismatch():
    with pytest.raises(RowWidthMismatchError):
        Board.parse(["wK . .", ". bK"])


# ---------- Piece.parse ----------

def test_piece_parse_valid():
    p = Piece.parse("wK")
    assert p.color == "w"
    assert p.type == "K"


def test_piece_parse_invalid_raises():
    with pytest.raises(UnknownTokenError):
        Piece.parse("xZ")


# ---------- Controller click handling ----------

def make_board():
    return Board.parse(["wK . .", ". . .", ". . ."])


def test_select_piece_by_center_click():
    board = make_board()
    controller = Controller(board)
    controller.handle_click(50, 50)
    controller.handle_click(150, 150)
    controller.advance_clock(1000)
    assert str(board) == ". . .\n. wK .\n. . ."


def test_click_empty_cell_does_not_select():
    board = make_board()
    controller = Controller(board)
    controller.handle_click(150, 150)
    controller.handle_click(250, 250)
    assert str(board) == "wK . .\n. . .\n. . ."


def test_click_outside_board_is_ignored():
    board = make_board()
    controller = Controller(board)
    controller.handle_click(350, 50)
    controller.handle_click(-10, 50)
    assert str(board) == "wK . .\n. . .\n. . ."


def test_clicking_another_friendly_piece_replaces_selection():
    board = Board.parse(["wR . wK", ". . ."])
    controller = Controller(board)
    controller.handle_click(50, 50)    # select wR
    controller.handle_click(250, 50)   # replace selection with wK
    controller.handle_click(250, 150)  # move wK to (1,2)
    assert str(board) == "wR . .\n. . wK"


# ---------- Movement rules ----------

def make_piece(t):
    return Piece("w", t)


# King
def test_king_legal_one_step():
    assert is_legal_move(make_piece("K"), (4, 4), (5, 5))

def test_king_illegal_two_steps():
    assert not is_legal_move(make_piece("K"), (4, 4), (6, 4))


# Rook
def test_rook_legal_straight():
    assert is_legal_move(make_piece("R"), (0, 0), (0, 7))

def test_rook_illegal_diagonal():
    assert not is_legal_move(make_piece("R"), (0, 0), (3, 3))


# Bishop
def test_bishop_legal_diagonal():
    assert is_legal_move(make_piece("B"), (0, 0), (4, 4))

def test_bishop_illegal_straight():
    assert not is_legal_move(make_piece("B"), (0, 0), (0, 4))


# Queen
def test_queen_legal_straight():
    assert is_legal_move(make_piece("Q"), (3, 3), (3, 7))

def test_queen_legal_diagonal():
    assert is_legal_move(make_piece("Q"), (3, 3), (6, 6))

def test_queen_illegal_knight_shape():
    assert not is_legal_move(make_piece("Q"), (3, 3), (5, 4))


# Knight
def test_knight_legal_l_shape():
    assert is_legal_move(make_piece("N"), (4, 4), (2, 5))

def test_knight_illegal_straight():
    assert not is_legal_move(make_piece("N"), (4, 4), (4, 6))


# Integration: illegal move is ignored on the board
def test_illegal_move_not_executed():
    board = Board.parse(["wK . .", ". . .", ". . ."])
    controller = Controller(board)
    controller.handle_click(50, 50)   # select wK at (0,0)
    controller.handle_click(250, 50)  # illegal: king moving 2 cols
    assert str(board) == "wK . .\n. . .\n. . ."


def test_legal_move_is_executed():
    board = Board.parse(["wR . .", ". . .", ". . ."])
    controller = Controller(board)
    controller.handle_click(50, 50)   # select wR at (0,0)
    controller.handle_click(250, 50)  # legal: rook moving straight to (0,2)
    assert str(board) == ". . wR\n. . .\n. . ."
