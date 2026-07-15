# test_board.py
import pytest
from kungfu_chess.model.board import Board, DuplicateOccupancyError
from kungfu_chess.model.piece import Piece
from kungfu_chess.model.position import Position

def make_piece(id=0, color="w", type="K"):
    return Piece(id=id, color=color, type=type, cell=None)

def test_board_dimensions_are_correct():
    board = Board(3, 4)
    assert board.rows == 3
    assert board.cols == 4

def test_empty_cells_return_no_piece():
    assert Board(2, 2).get(Position(0, 0)) is None

def test_occupied_cells_return_the_correct_piece():
    board = Board(2, 2)
    piece = make_piece()
    board.add_piece(Position(0, 0), piece)
    assert board.get(Position(0, 0)) is piece

def test_adding_two_pieces_to_the_same_cell_fails():
    board = Board(2, 2)
    board.add_piece(Position(0, 0), make_piece(id=0))
    with pytest.raises(DuplicateOccupancyError):
        board.add_piece(Position(0, 0), make_piece(id=1))

def test_moving_a_piece_updates_source_and_destination():
    board = Board(2, 2)
    piece = make_piece()
    board.add_piece(Position(0, 0), piece)
    board.move_piece(Position(0, 0), Position(1, 1))
    assert board.get(Position(0, 0)) is None
    assert board.get(Position(1, 1)) is piece
    assert piece.cell == Position(1, 1)

def test_removing_a_captured_piece_clears_its_cell():
    board = Board(2, 2)
    piece = make_piece()
    board.add_piece(Position(0, 0), piece)
    board.remove_piece(Position(0, 0))
    assert board.get(Position(0, 0)) is None

def test_in_bounds_accepts_cells_inside_the_board():
    board = Board(2, 2)
    assert board.in_bounds(Position(0, 0)) is True
    assert board.in_bounds(Position(1, 1)) is True

def test_in_bounds_rejects_cells_outside_the_board():
    board = Board(2, 2)
    assert board.in_bounds(Position(2, 0)) is False
    assert board.in_bounds(Position(-1, 0)) is False

def test_has_king_reflects_current_occupancy():
    board = Board(2, 2)
    board.add_piece(Position(0, 0), make_piece(color="w", type="K"))
    assert board.has_king("w") is True
    assert board.has_king("b") is False