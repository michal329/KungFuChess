from kfchess.model.piece import BLACK, PAWN, ROOK, WHITE, Piece
from kfchess.model.position import Position
from kfchess.rules.rule_engine import (
    REASON_FRIENDLY_DESTINATION,
    REASON_NO_PIECE,
    REASON_OUTSIDE_BOARD,
    REASON_PATH_BLOCKED,
    REASON_WRONG_SHAPE,
    RuleEngine,
)


def test_legal_rook_move(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    result = RuleEngine().evaluate(empty_board, Position(0, 0), Position(0, 5), Piece(ROOK, WHITE))
    assert result.is_legal


def test_illegal_shape_reason(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    result = RuleEngine().evaluate(empty_board, Position(0, 0), Position(3, 3), Piece(ROOK, WHITE))
    assert not result.is_legal
    assert result.reason == REASON_WRONG_SHAPE


def test_no_piece_at_source(empty_board):
    result = RuleEngine().evaluate(empty_board, Position(0, 0), Position(0, 1), Piece(ROOK, WHITE))
    assert not result.is_legal
    assert result.reason == REASON_NO_PIECE


def test_outside_board(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    result = RuleEngine().evaluate(empty_board, Position(0, 0), Position(0, 20), Piece(ROOK, WHITE))
    assert not result.is_legal
    assert result.reason == REASON_OUTSIDE_BOARD


def test_friendly_destination_rejected(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    empty_board.set(Position(0, 3), Piece(PAWN, WHITE))
    result = RuleEngine().evaluate(empty_board, Position(0, 0), Position(0, 3), Piece(ROOK, WHITE))
    assert not result.is_legal
    assert result.reason == REASON_FRIENDLY_DESTINATION


def test_capture_of_enemy_is_legal(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    empty_board.set(Position(0, 3), Piece(PAWN, BLACK))
    result = RuleEngine().evaluate(empty_board, Position(0, 0), Position(0, 3), Piece(ROOK, WHITE))
    assert result.is_legal


def test_path_blocked(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    empty_board.set(Position(0, 1), Piece(PAWN, BLACK))
    result = RuleEngine().evaluate(empty_board, Position(0, 0), Position(0, 3), Piece(ROOK, WHITE))
    assert not result.is_legal
    assert result.reason == REASON_PATH_BLOCKED
