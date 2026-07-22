from client.remote_game_view import RemoteGameView
from kfchess.engine.game_state import GameState
from kfchess.events.events import (
    AirborneCaptureEvent,
    GameOverEvent,
    JumpLandedEvent,
    MoveCompletedEvent,
    Observer,
)
from kfchess.io.board_parser import build_board
from kfchess.io.snapshot import game_state_snapshot
from kfchess.model.piece import BLACK, ROOK, WHITE, Piece
from kfchess.model.position import Position
from kfchess.realtime.motion import PendingJump, PendingMove
from protocol.messages import (
    AirborneCaptureMessage,
    ErrorMessage,
    GameEndedMessage,
    JumpLandedMessage,
    JumpQueuedMessage,
    MoveEventMessage,
    MoveQueuedMessage,
    SnapshotMessage,
    TimerMessage,
)


class _Recorder(Observer):
    def __init__(self):
        self.events = []

    def on_event(self, event):
        self.events.append(event)


def _view_with_rook_at_00():
    board = build_board([["WR", ".", ".", "."]])
    return RemoteGameView(GameState(board=board))


def test_from_snapshot_rebuilds_state_and_board():
    board = build_board([["WK", "."], [".", "BK"]])
    payload = game_state_snapshot(GameState(board=board, current_time=42))
    view = RemoteGameView.from_snapshot(payload)
    assert view.state.current_time == 42
    assert view.state.board.get(Position(0, 0)) == Piece("K", WHITE)


def test_move_queued_appends_a_pending_move_without_moving_the_board():
    view = _view_with_rook_at_00()
    view.apply(MoveQueuedMessage(
        piece="WR", from_={"row": 0, "col": 0}, to={"row": 0, "col": 3}, start_time=0, arrival_time=3000,
    ))
    assert view.state.pending == [PendingMove(
        piece=Piece(ROOK, WHITE), from_pos=Position(0, 0), to_pos=Position(0, 3),
        arrival_time=3000, start_time=0,
    )]
    assert view.state.board.get(Position(0, 0)) is not None  # not yet moved


def test_jump_queued_appends_a_pending_jump():
    view = _view_with_rook_at_00()
    view.apply(JumpQueuedMessage(piece="WR", pos={"row": 0, "col": 0}, start_time=0, land_time=500))
    assert view.state.airborne == [PendingJump(
        piece=Piece(ROOK, WHITE), pos=Position(0, 0), land_time=500, start_time=0,
    )]


def test_move_event_relocates_the_board_clears_pending_and_notifies_move_completed():
    view = _view_with_rook_at_00()
    view.apply(MoveQueuedMessage(piece="WR", from_={"row": 0, "col": 0}, to={"row": 0, "col": 3}, start_time=0, arrival_time=3000))
    recorder = _Recorder()
    view.add_observer(recorder)

    view.apply(MoveEventMessage(piece="WR", from_={"row": 0, "col": 0}, to={"row": 0, "col": 3}, arrival_time=3000))

    assert view.state.board.get(Position(0, 0)) is None
    assert view.state.board.get(Position(0, 3)) == Piece(ROOK, WHITE)
    assert view.state.pending == []
    assert recorder.events == [MoveCompletedEvent(
        piece=Piece(ROOK, WHITE), from_pos=Position(0, 0), to_pos=Position(0, 3), arrival_time=3000,
    )]


def test_jump_landed_clears_airborne_and_notifies():
    view = _view_with_rook_at_00()
    view.apply(JumpQueuedMessage(piece="WR", pos={"row": 0, "col": 0}, start_time=0, land_time=500))
    recorder = _Recorder()
    view.add_observer(recorder)

    view.apply(JumpLandedMessage(piece="WR", pos={"row": 0, "col": 0}, land_time=500))

    assert view.state.airborne == []
    assert recorder.events == [JumpLandedEvent(piece=Piece(ROOK, WHITE), pos=Position(0, 0), land_time=500)]


def test_airborne_capture_removes_attacker_from_pending_and_from_its_origin_on_the_board():
    board = build_board([["WR", ".", ".", "BR"]])  # attacker at (0,0), defender at (0,3)
    view = RemoteGameView(GameState(board=board))
    view.apply(MoveQueuedMessage(piece="WR", from_={"row": 0, "col": 0}, to={"row": 0, "col": 3}, start_time=0, arrival_time=3000))
    recorder = _Recorder()
    view.add_observer(recorder)

    view.apply(AirborneCaptureMessage(defender="BR", pos={"row": 0, "col": 3}, attacker="WR"))

    assert view.state.pending == []
    assert view.state.board.get(Position(0, 0)) is None  # attacker removed from its origin
    assert view.state.board.get(Position(0, 3)) == Piece(ROOK, BLACK)  # defender untouched
    assert recorder.events == [AirborneCaptureEvent(
        defender=Piece(ROOK, BLACK), pos=Position(0, 3), attacker=Piece(ROOK, WHITE),
    )]


def test_game_ended_sets_flags_and_notifies():
    view = _view_with_rook_at_00()
    recorder = _Recorder()
    view.add_observer(recorder)

    view.apply(GameEndedMessage(winner=WHITE))

    assert view.state.game_over is True
    assert view.state.winner == WHITE
    assert recorder.events == [GameOverEvent(winner=WHITE)]


def test_timer_updates_current_time_only():
    view = _view_with_rook_at_00()
    recorder = _Recorder()
    view.add_observer(recorder)

    view.apply(TimerMessage(current_time=1234))

    assert view.state.current_time == 1234
    assert recorder.events == []  # nothing to react to -- BoardRenderer reads current_time fresh


def test_resnapshot_replaces_state_in_place_same_object_identity():
    view = _view_with_rook_at_00()
    original_state = view.state

    board = build_board([["BK"]])
    payload = game_state_snapshot(GameState(board=board, current_time=999))
    view.apply(SnapshotMessage(payload=payload))

    assert view.state is original_state  # mutated in place, not replaced
    assert view.state.current_time == 999
    assert view.state.board.get(Position(0, 0)) == Piece("K", BLACK)


def test_message_with_no_handler_is_a_no_op():
    view = _view_with_rook_at_00()
    view.apply(ErrorMessage(reason="whatever"))  # must not raise
