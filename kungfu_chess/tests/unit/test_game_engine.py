from kungfu_chess.io.board_parser import BoardParser
from kungfu_chess.engine.game_engine import GameEngine
from kungfu_chess.model.position import Position
from kungfu_chess.model.game_state import GameSnapshot


def make_engine(lines):
    board = BoardParser().parse(lines)
    engine = GameEngine(board)
    return board, engine


def test_valid_move_accepted():
    _, engine = make_engine(["wR . ."])
    result = engine.request_move(Position(0, 0), Position(0, 2))
    assert result.is_accepted is True
    assert result.reason == "ok"


def test_motion_in_progress_blocks_second_move():
    _, engine = make_engine(["wR . .", "wK . ."])
    engine.request_move(Position(0, 0), Position(0, 2))
    result = engine.request_move(Position(1, 0), Position(1, 2))
    assert result.reason == "motion_in_progress"
    assert result.is_accepted is False


def test_game_over_blocks_all_moves():
    _, engine = make_engine(["wR bK"])
    engine.request_move(Position(0, 0), Position(0, 1))
    engine.wait(1000)
    assert engine.game_over is True
    result = engine.request_move(Position(0, 1), Position(0, 0))
    assert result.reason == "game_over"


def test_rule_violation_reason_propagated():
    _, engine = make_engine(["wK . ."])
    result = engine.request_move(Position(0, 0), Position(0, 2))
    assert result.reason == "illegal_piece_move"
    assert result.is_accepted is False


def test_empty_source_reason():
    _, engine = make_engine([". wK"])
    result = engine.request_move(Position(0, 0), Position(0, 1))
    assert result.reason == "empty_source"


def test_wait_advances_time_and_resolves_motion():
    board, engine = make_engine(["wR . ."])
    engine.request_move(Position(0, 0), Position(0, 2))
    engine.wait(2000)  # 2 cells = 2000ms
    assert board.get(Position(0, 2)) is not None
    assert board.get(Position(0, 0)) is None


def test_wait_partial_does_not_resolve():
    board, engine = make_engine(["wR . ."])
    engine.request_move(Position(0, 0), Position(0, 2))
    engine.wait(500)
    assert board.get(Position(0, 0)) is not None


def test_snapshot_returns_game_snapshot():
    _, engine = make_engine(["wK ."])
    snap = engine.snapshot()
    assert isinstance(snap, GameSnapshot)
    assert snap.game_over is False


def test_snapshot_game_over_true_after_king_capture():
    _, engine = make_engine(["wR bK"])
    engine.request_move(Position(0, 0), Position(0, 1))
    engine.wait(1000)
    snap = engine.snapshot()
    assert snap.game_over is True
