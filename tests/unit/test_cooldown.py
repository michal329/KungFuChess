from kfchess.engine.game_engine import GameEngine
from kfchess.engine.game_state import GameState
from kfchess.model.piece import ROOK, WHITE, Piece
from kfchess.model.position import Position


def test_piece_unselectable_immediately_after_landing(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    engine = GameEngine(empty_board, move_duration=1000, cooldown_duration=1000)
    state = GameState(board=empty_board)

    engine.attempt_move(state, Position(0, 0), Position(0, 1))
    engine.tick(state, 1000)  # arrives, cooldown starts

    assert not engine.is_selectable(state, Position(0, 1))
    assert engine.is_in_cooldown(state, Position(0, 1))


def test_cooldown_expires_after_its_full_duration(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    engine = GameEngine(empty_board, move_duration=1000, cooldown_duration=1000)
    state = GameState(board=empty_board)

    engine.attempt_move(state, Position(0, 0), Position(0, 1))
    engine.tick(state, 1000)  # arrives
    engine.tick(state, 999)
    assert engine.is_in_cooldown(state, Position(0, 1))

    engine.tick(state, 1)
    assert not engine.is_in_cooldown(state, Position(0, 1))
    assert engine.is_selectable(state, Position(0, 1))


def test_cooldown_restarts_on_each_landing(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    engine = GameEngine(empty_board, move_duration=1000, cooldown_duration=1000)
    state = GameState(board=empty_board)

    engine.attempt_move(state, Position(0, 0), Position(0, 1))
    engine.tick(state, 1000)
    engine.tick(state, 999)
    assert engine.is_in_cooldown(state, Position(0, 1))

    # Move again right as the first cooldown was about to expire.
    engine.tick(state, 1)  # cooldown now expired
    engine.attempt_move(state, Position(0, 1), Position(0, 2))
    engine.tick(state, 1000)
    assert engine.is_in_cooldown(state, Position(0, 2))
