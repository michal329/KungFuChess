from kungfu_chess.io.board_parser import BoardParser
from kungfu_chess.model.position import Position
from kungfu_chess.rules.piece_rules import PieceRules


def piece_at(board, row, col):
    return board.get(Position(row, col))


def destinations_of(board, row, col):
    return PieceRules().legal_destinations(board, piece_at(board, row, col))


def test_rook_moves_across_empty_row_and_column():
    board = BoardParser().parse([". . . .", ". wR . .", ". . . .", ". . . ."])
    destinations = destinations_of(board, 1, 1)
    assert Position(1, 0) in destinations
    assert Position(1, 3) in destinations
    assert Position(0, 1) in destinations
    assert Position(3, 1) in destinations
    assert Position(0, 0) not in destinations


def test_rook_stops_before_a_friendly_blocker():
    board = BoardParser().parse([". . . .", ". wR wP .", ". . . .", ". . . ."])
    destinations = destinations_of(board, 1, 1)
    assert Position(1, 2) not in destinations
    assert Position(1, 3) not in destinations


def test_rook_captures_an_enemy_blocker_but_does_not_pass_it():
    board = BoardParser().parse([". . . .", ". wR bP .", ". . . .", ". . . ."])
    destinations = destinations_of(board, 1, 1)
    assert Position(1, 2) in destinations
    assert Position(1, 3) not in destinations


def test_bishop_moves_diagonally_and_not_straight():
    board = BoardParser().parse([". . . .", ". wB . .", ". . . .", ". . . ."])
    destinations = destinations_of(board, 1, 1)
    assert Position(0, 0) in destinations
    assert Position(2, 2) in destinations
    assert Position(1, 0) not in destinations
    assert Position(1, 2) not in destinations


def test_queen_combines_rook_and_bishop_movement():
    board = BoardParser().parse([". . . .", ". wQ . .", ". . . .", ". . . ."])
    destinations = destinations_of(board, 1, 1)
    assert Position(1, 0) in destinations
    assert Position(0, 0) in destinations


def test_knight_jumps_over_blockers():
    board = BoardParser().parse([". wP . .", "wP wN wP .", ". wP . .", ". . . ."])
    destinations = destinations_of(board, 1, 1)
    assert Position(3, 0) in destinations
    assert Position(3, 2) in destinations


def test_king_moves_one_cell_only():
    board = BoardParser().parse([". . .", ". wK .", ". . ."])
    destinations = destinations_of(board, 1, 1)
    assert len(destinations) == 8
    assert Position(0, 0) in destinations
    assert Position(2, 2) in destinations


def test_pawn_moves_forward_one_square():
    board = BoardParser().parse([". . .", ". wP .", ". . ."])
    assert destinations_of(board, 1, 1) == {Position(0, 1)}


def test_pawn_captures_diagonally():
    board = BoardParser().parse(["bP . bP", ". wP .", ". . ."])
    destinations = destinations_of(board, 1, 1)
    assert Position(0, 0) in destinations
    assert Position(0, 2) in destinations


def test_pawn_cannot_advance_straight_into_an_occupied_square():
    board = BoardParser().parse([". bP .", ". wP .", ". . ."])
    assert Position(0, 1) not in destinations_of(board, 1, 1)


def test_pawn_has_no_double_step_move():
    board = BoardParser().parse([". . .", ". . .", ". wP ."])
    assert destinations_of(board, 2, 1) == {Position(1, 1)}


def test_black_pawn_moves_toward_increasing_row():
    board = BoardParser().parse([". . .", ". bP .", ". . ."])
    assert destinations_of(board, 1, 1) == {Position(2, 1)}