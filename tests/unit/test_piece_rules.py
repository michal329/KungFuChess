import pytest

from kfchess.model.piece import BISHOP, BLACK, KING, KNIGHT, PAWN, QUEEN, ROOK, WHITE
from kfchess.model.position import Position
from kfchess.rules.piece_rules import is_legal_shape, is_path_clear, line_path_cells


@pytest.mark.parametrize("delta_row,delta_col,expected", [
    (0, 5, True), (5, 0, True), (3, 3, False), (1, 2, False),
])
def test_rook_shape(delta_row, delta_col, expected):
    assert is_legal_shape(ROOK, delta_row, delta_col) is expected


@pytest.mark.parametrize("delta_row,delta_col,expected", [
    (3, 3, True), (-2, 2, True), (0, 5, False), (2, 3, False),
])
def test_bishop_shape(delta_row, delta_col, expected):
    assert is_legal_shape(BISHOP, delta_row, delta_col) is expected


@pytest.mark.parametrize("delta_row,delta_col,expected", [
    (0, 5, True), (3, 3, True), (2, 3, False),
])
def test_queen_shape(delta_row, delta_col, expected):
    assert is_legal_shape(QUEEN, delta_row, delta_col) is expected


@pytest.mark.parametrize("delta_row,delta_col,expected", [
    (1, 2, True), (-2, -1, True), (2, 2, False), (1, 1, False),
])
def test_knight_shape(delta_row, delta_col, expected):
    assert is_legal_shape(KNIGHT, delta_row, delta_col) is expected


@pytest.mark.parametrize("delta_row,delta_col,expected", [
    (1, 1, True), (1, 0, True), (0, 1, True), (0, 2, False), (2, 0, False),
])
def test_king_shape(delta_row, delta_col, expected):
    assert is_legal_shape(KING, delta_row, delta_col) is expected


def test_pawn_single_step_forward():
    assert is_legal_shape(PAWN, -1, 0, color=WHITE, from_row=6, board_height=8)
    assert is_legal_shape(PAWN, 1, 0, color=BLACK, from_row=1, board_height=8)


def test_pawn_double_step_only_from_start_row():
    assert is_legal_shape(PAWN, -2, 0, color=WHITE, from_row=6, board_height=8)
    assert not is_legal_shape(PAWN, -2, 0, color=WHITE, from_row=5, board_height=8)


def test_pawn_diagonal_requires_capture():
    assert is_legal_shape(PAWN, -1, 1, color=WHITE, is_capture=True, from_row=6, board_height=8)
    assert not is_legal_shape(PAWN, -1, 1, color=WHITE, is_capture=False, from_row=6, board_height=8)


def test_pawn_forward_cannot_capture():
    assert not is_legal_shape(PAWN, -1, 0, color=WHITE, is_capture=True, from_row=6, board_height=8)


def test_line_path_cells_straight():
    cells = line_path_cells(Position(0, 0), Position(0, 3))
    assert cells == [Position(0, 1), Position(0, 2)]


def test_line_path_cells_knight_returns_none():
    assert line_path_cells(Position(0, 0), Position(2, 1)) is None


def test_is_path_clear_blocked(empty_board):
    from kfchess.model.piece import Piece
    empty_board.set(Position(0, 1), Piece(PAWN, WHITE))
    assert not is_path_clear(empty_board, ROOK, Position(0, 0), 0, 3)


def test_is_path_clear_open(empty_board):
    assert is_path_clear(empty_board, ROOK, Position(0, 0), 0, 3)


def test_knight_ignores_path_clear(empty_board):
    from kfchess.model.piece import Piece
    empty_board.set(Position(1, 1), Piece(PAWN, WHITE))
    assert is_path_clear(empty_board, KNIGHT, Position(0, 0), 2, 1)
