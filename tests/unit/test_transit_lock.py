from kfchess.engine.game_engine import GameEngine
from kfchess.engine.game_state import GameState
from kfchess.model.piece import ROOK, WHITE, Piece
from kfchess.model.position import Position


def test_in_transit_piece_is_not_selectable(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    engine = GameEngine(empty_board, move_duration=1000)
    state = GameState(board=empty_board)

    engine.attempt_move(state, Position(0, 0), Position(0, 4))
    assert engine.is_in_transit(state, Position(0, 0))
    assert not engine.is_selectable(state, Position(0, 0))


def test_click_on_in_transit_piece_is_a_no_op(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    engine = GameEngine(empty_board, move_duration=1000)
    state = GameState(board=empty_board)

    engine.attempt_move(state, Position(0, 0), Position(0, 4))
    engine.handle_click(state, x=50, y=50)  # click on origin, still in transit
    assert engine.selection is None


def test_transit_flag_clears_once_move_resolves(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    engine = GameEngine(empty_board, move_duration=1000)
    state = GameState(board=empty_board)

    engine.attempt_move(state, Position(0, 0), Position(0, 1))
    engine.tick(state, 1000)
    assert not engine.is_in_transit(state, Position(0, 0))
