from kungfu_chess.io.board_parser import BoardParser
from kungfu_chess.model.position import Position
from kungfu_chess.realtime.real_time_arbiter import RealTimeArbiter


def make_arbiter(lines):
    board = BoardParser().parse(lines)
    arbiter = RealTimeArbiter(board)
    return board, arbiter


def test_no_active_motion_initially():
    _, arbiter = make_arbiter(["wR ."])
    assert arbiter.has_active_motion() is False


def test_has_active_motion_after_start():
    board, arbiter = make_arbiter(["wR ."])
    piece = board.get(Position(0, 0))
    arbiter.start_motion(piece, Position(0, 0), Position(0, 1))
    assert arbiter.has_active_motion() is True


def test_piece_marked_moving_after_start():
    board, arbiter = make_arbiter(["wR ."])
    piece = board.get(Position(0, 0))
    arbiter.start_motion(piece, Position(0, 0), Position(0, 1))
    assert piece.state == "moving"


def test_advance_time_before_arrival_does_not_resolve():
    board, arbiter = make_arbiter(["wR . ."])
    piece = board.get(Position(0, 0))
    arbiter.start_motion(piece, Position(0, 0), Position(0, 2))
    # 2 cells = 2000ms; advance only 500ms
    arbiter.advance_time(500)
    assert arbiter.has_active_motion() is True


def test_advance_time_at_arrival_moves_piece():
    board, arbiter = make_arbiter(["wR ."])
    piece = board.get(Position(0, 0))
    arbiter.start_motion(piece, Position(0, 0), Position(0, 1))
    # 1 cell = 1000ms
    arbiter.advance_time(1000)
    assert board.get(Position(0, 1)) is piece
    assert board.get(Position(0, 0)) is None
    assert arbiter.has_active_motion() is False


def test_diagonal_move_takes_one_cell_step_not_euclidean():
    board, arbiter = make_arbiter([". . .", ". wR .", ". . ."])
    piece = board.get(Position(1, 1))
    arbiter.start_motion(piece, Position(1, 1), Position(0, 0))
    # diagonal = 1 cell-step = 1000ms (not sqrt(2)*1000)
    arbiter.advance_time(999)
    assert arbiter.has_active_motion() is True
    arbiter.advance_time(1)
    assert arbiter.has_active_motion() is False


def test_arrival_captures_enemy_and_reports_king_captured():
    board, arbiter = make_arbiter(["wR bK"])
    piece = board.get(Position(0, 0))
    arbiter.start_motion(piece, Position(0, 0), Position(0, 1))
    events = arbiter.advance_time(1000)
    assert events.king_captured is True
    assert board.get(Position(0, 1)).type == "R"


def test_arrival_without_king_capture_returns_false():
    board, arbiter = make_arbiter(["wR ."])
    piece = board.get(Position(0, 0))
    arbiter.start_motion(piece, Position(0, 0), Position(0, 1))
    events = arbiter.advance_time(1000)
    assert events.king_captured is False


def test_piece_state_idle_after_arrival():
    board, arbiter = make_arbiter(["wR ."])
    piece = board.get(Position(0, 0))
    arbiter.start_motion(piece, Position(0, 0), Position(0, 1))
    arbiter.advance_time(1000)
    assert piece.state == "idle"


def test_arrived_motion_listed_in_events():
    board, arbiter = make_arbiter(["wR ."])
    piece = board.get(Position(0, 0))
    arbiter.start_motion(piece, Position(0, 0), Position(0, 1))
    events = arbiter.advance_time(1000)
    assert len(events.arrived) == 1
    assert events.arrived[0].piece is piece
