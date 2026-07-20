from kfchess.engine.game_engine import GameEngine
from kfchess.engine.game_state import GameState
from kfchess.model.piece import BLACK, ROOK, WHITE, Piece
from kfchess.model.position import Position


def _engine_and_state(board, cell_size=100):
    engine = GameEngine(board, cell_size=cell_size)
    return engine, GameState(board=board)


def test_click_selects_piece(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    engine, state = _engine_and_state(empty_board)
    engine.handle_click(state, x=50, y=50)
    assert engine.selection == Position(0, 0)


def test_click_empty_cell_selects_nothing(empty_board):
    engine, state = _engine_and_state(empty_board)
    engine.handle_click(state, x=50, y=50)
    assert engine.selection is None


def test_click_switches_selection_between_friendly_pieces(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    empty_board.set(Position(0, 1), Piece(ROOK, WHITE))
    engine, state = _engine_and_state(empty_board)
    engine.handle_click(state, x=50, y=50)
    engine.handle_click(state, x=150, y=50)
    assert engine.selection == Position(0, 1)
    assert state.pending == []  # switching selection is not a move attempt


def test_second_click_attempts_move_and_clears_selection(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    engine, state = _engine_and_state(empty_board)
    engine.handle_click(state, x=50, y=50)
    engine.handle_click(state, x=350, y=50)  # empty cell, same row
    assert engine.selection is None
    assert len(state.pending) == 1


def test_click_on_enemy_after_selection_attempts_capture(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    empty_board.set(Position(0, 3), Piece(ROOK, BLACK))
    engine, state = _engine_and_state(empty_board)
    engine.handle_click(state, x=50, y=50)
    engine.handle_click(state, x=350, y=50)
    assert len(state.pending) == 1
    assert engine.selection is None


def test_clicks_ignored_after_game_over(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    engine, state = _engine_and_state(empty_board)
    state.game_over = True
    engine.handle_click(state, x=50, y=50)
    assert engine.selection is None


def test_second_click_on_same_square_triggers_jump_not_move(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    engine, state = _engine_and_state(empty_board)
    engine.handle_click(state, x=50, y=50)
    engine.handle_click(state, x=50, y=50)  # same square again
    assert engine.selection is None
    assert state.pending == []  # not a move attempt
    assert len(state.airborne) == 1
    assert state.airborne[0].pos == Position(0, 0)
