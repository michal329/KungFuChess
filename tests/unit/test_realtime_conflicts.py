from kfchess.model.piece import BISHOP, BLACK, ROOK, WHITE, Piece
from kfchess.model.position import Position

from kfchess.engine.game_engine import GameEngine
from kfchess.engine.game_state import GameState


def test_opposite_color_move_sharing_a_column_span_on_different_rows_is_rejected(empty_board):
    """Route locking compares only the axis (horizontal/vertical) and the
    span of columns/rows crossed -- not which row/column it's fixed on.
    Two horizontal moves on different rows with overlapping column spans
    still count as sharing a route."""
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    empty_board.set(Position(2, 2), Piece(ROOK, BLACK))
    engine = GameEngine(empty_board, move_duration=1000)
    state = GameState(board=empty_board)

    assert engine.attempt_move(state, Position(0, 0), Position(0, 4))  # occupies cols 0-4
    assert not engine.attempt_move(state, Position(2, 2), Position(2, 6))  # cols 2-6 overlap


def test_non_overlapping_column_spans_do_not_conflict(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    empty_board.set(Position(2, 5), Piece(ROOK, BLACK))
    engine = GameEngine(empty_board, move_duration=1000)
    state = GameState(board=empty_board)

    assert engine.attempt_move(state, Position(0, 0), Position(0, 1))  # cols 0-1
    assert engine.attempt_move(state, Position(2, 5), Position(2, 7))  # cols 5-7, no overlap


def test_same_color_moves_sharing_a_route_do_not_conflict(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    empty_board.set(Position(2, 2), Piece(ROOK, WHITE))
    engine = GameEngine(empty_board, move_duration=1000)
    state = GameState(board=empty_board)

    assert engine.attempt_move(state, Position(0, 0), Position(0, 4))
    assert engine.attempt_move(state, Position(2, 2), Position(2, 6))


def test_diagonal_moves_never_route_lock(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    empty_board.set(Position(4, 4), Piece(BISHOP, BLACK))
    engine = GameEngine(empty_board, move_duration=1000)
    state = GameState(board=empty_board)

    assert engine.attempt_move(state, Position(0, 0), Position(0, 4))
    assert engine.attempt_move(state, Position(4, 4), Position(1, 1))


def test_earliest_arrival_wins_the_square_then_a_later_enemy_can_still_capture_it(empty_board):
    first = Piece(ROOK, WHITE)
    second = Piece(ROOK, BLACK)
    empty_board.set(Position(0, 0), first)   # 1 cell down -> arrives at 1000ms
    empty_board.set(Position(1, 3), second)  # 3 cells left -> arrives at 3000ms, same destination
    engine = GameEngine(empty_board, move_duration=1000)
    state = GameState(board=empty_board)

    assert engine.attempt_move(state, Position(0, 0), Position(1, 0))
    assert engine.attempt_move(state, Position(1, 3), Position(1, 0))

    engine.tick(state, 3000)

    assert state.board.get(Position(1, 0)) == second  # second captured first there
    assert state.board.get(Position(0, 0)) is None
