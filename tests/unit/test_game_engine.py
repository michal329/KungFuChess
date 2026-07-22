from kfchess.engine.game_engine import GameEngine
from kfchess.engine.game_state import GameState
from kfchess.events.events import MoveQueuedEvent, Observer
from kfchess.model.piece import BLACK, KING, PAWN, QUEEN, ROOK, WHITE, Piece
from kfchess.model.position import Position


class _Recorder(Observer):
    def __init__(self):
        self.events = []

    def on_event(self, event):
        self.events.append(event)


def test_attempt_move_queues_not_applies_immediately(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    engine = GameEngine(empty_board)
    state = GameState(board=empty_board)

    assert engine.attempt_move(state, Position(0, 0), Position(0, 3))
    assert state.board.get(Position(0, 0)) is not None  # not yet moved
    assert state.board.get(Position(0, 3)) is None


def test_move_arrives_after_full_duration(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    engine = GameEngine(empty_board, move_duration=1000)
    state = GameState(board=empty_board)
    engine.attempt_move(state, Position(0, 0), Position(0, 3))  # 3 cells -> 3000ms

    engine.tick(state, 2999)
    assert state.board.get(Position(0, 0)) is not None  # still in transit

    engine.tick(state, 1)
    assert state.board.get(Position(0, 0)) is None
    assert state.board.get(Position(0, 3)) == Piece(ROOK, WHITE)


def test_illegal_move_is_not_queued(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    engine = GameEngine(empty_board)
    state = GameState(board=empty_board)
    assert not engine.attempt_move(state, Position(0, 0), Position(3, 3))
    assert state.pending == []


def test_king_capture_ends_game(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    empty_board.set(Position(0, 3), Piece(KING, BLACK))
    engine = GameEngine(empty_board)
    state = GameState(board=empty_board)

    engine.attempt_move(state, Position(0, 0), Position(0, 3))
    engine.tick(state, 3000)
    assert state.game_over
    assert state.winner == WHITE


def test_pawn_promotes_on_back_rank(empty_board):
    empty_board.set(Position(1, 0), Piece(PAWN, WHITE))
    engine = GameEngine(empty_board)
    state = GameState(board=empty_board)

    engine.attempt_move(state, Position(1, 0), Position(0, 0))
    engine.tick(state, 1000)
    assert state.board.get(Position(0, 0)) == Piece(QUEEN, WHITE)


def test_pawn_capturing_the_enemy_king_on_the_back_rank_does_not_promote(empty_board):
    """The game is already over the instant this move lands -- there's
    no point turning the pawn into a Queen for a game that just ended."""
    empty_board.set(Position(1, 0), Piece(PAWN, WHITE))
    empty_board.set(Position(0, 1), Piece(KING, BLACK))  # diagonal capture, also the back rank
    engine = GameEngine(empty_board)
    state = GameState(board=empty_board)

    engine.attempt_move(state, Position(1, 0), Position(0, 1))
    engine.tick(state, 1000)

    assert state.board.get(Position(0, 1)) == Piece(PAWN, WHITE)  # still a pawn, not a queen
    assert state.game_over
    assert state.winner == WHITE


def test_pawn_capturing_a_non_king_on_the_back_rank_still_promotes(empty_board):
    empty_board.set(Position(1, 0), Piece(PAWN, WHITE))
    empty_board.set(Position(0, 1), Piece(ROOK, BLACK))
    engine = GameEngine(empty_board)
    state = GameState(board=empty_board)

    engine.attempt_move(state, Position(1, 0), Position(0, 1))
    engine.tick(state, 1000)

    assert state.board.get(Position(0, 1)) == Piece(QUEEN, WHITE)
    assert not state.game_over


def test_friendly_block_stops_move_short(empty_board):
    mover = Piece(ROOK, WHITE)
    empty_board.set(Position(0, 0), mover)
    engine = GameEngine(empty_board)
    state = GameState(board=empty_board)
    engine.attempt_move(state, Position(0, 0), Position(0, 4))

    # A friendly piece drops into the route mid-flight.
    empty_board.set(Position(0, 2), Piece(ROOK, WHITE))
    engine.tick(state, 4000)

    assert state.board.get(Position(0, 1)) == mover  # stopped short
    assert state.board.get(Position(0, 4)) is None


def test_busy_piece_cannot_be_reselected_or_redirected(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    engine = GameEngine(empty_board)
    state = GameState(board=empty_board)
    engine.attempt_move(state, Position(0, 0), Position(0, 4))

    assert not engine.is_selectable(state, Position(0, 0))
    assert not engine.attempt_move(state, Position(0, 0), Position(0, 1))


def test_pending_move_records_start_time_for_animation(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    engine = GameEngine(empty_board, move_duration=1000)
    state = GameState(board=empty_board)

    engine.tick(state, 500)  # advance the clock before queuing
    engine.attempt_move(state, Position(0, 0), Position(0, 2))

    assert state.pending[0].start_time == 500
    assert state.pending[0].arrival_time == 500 + 2 * 1000


def test_cooldown_duration_is_publicly_readable(empty_board):
    engine = GameEngine(empty_board, cooldown_duration=1234)
    assert engine.cooldown_duration == 1234


def test_attempt_move_fires_move_queued_event_immediately(empty_board):
    """Unlike MoveCompletedEvent, this fires the instant the move is
    accepted -- before it travels -- so a networked client can start
    showing the travel animation right away instead of only learning
    about the move once it lands (see kfchess/events/events.py's
    MoveQueuedEvent docstring)."""
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    engine = GameEngine(empty_board, move_duration=1000)
    state = GameState(board=empty_board)
    recorder = _Recorder()
    engine.add_observer(recorder)

    engine.attempt_move(state, Position(0, 0), Position(0, 3))

    queued = [e for e in recorder.events if isinstance(e, MoveQueuedEvent)]
    assert queued == [MoveQueuedEvent(
        piece=Piece(ROOK, WHITE), from_pos=Position(0, 0), to_pos=Position(0, 3),
        start_time=0, arrival_time=3000,
    )]


def test_illegal_move_never_fires_move_queued_event(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    engine = GameEngine(empty_board)
    state = GameState(board=empty_board)
    recorder = _Recorder()
    engine.add_observer(recorder)

    assert not engine.attempt_move(state, Position(0, 0), Position(3, 3))  # not a rook shape

    assert not any(isinstance(e, MoveQueuedEvent) for e in recorder.events)


def test_resign_ends_the_game_for_the_opposite_color(empty_board):
    engine = GameEngine(empty_board)
    state = GameState(board=empty_board)
    recorder = _Recorder()
    engine.add_observer(recorder)

    assert engine.resign(state, WHITE)

    assert state.game_over
    assert state.winner == BLACK
    from kfchess.events.events import GameOverEvent
    assert recorder.events == [GameOverEvent(winner=BLACK)]


def test_black_resign_gives_white_the_win(empty_board):
    engine = GameEngine(empty_board)
    state = GameState(board=empty_board)

    engine.resign(state, BLACK)

    assert state.winner == WHITE


def test_resign_works_even_with_a_piece_mid_flight(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    engine = GameEngine(empty_board, move_duration=1000)
    state = GameState(board=empty_board)
    engine.attempt_move(state, Position(0, 0), Position(0, 3))  # now busy/in-transit

    assert engine.resign(state, WHITE)
    assert state.game_over


def test_resign_after_game_over_is_a_no_op(empty_board):
    engine = GameEngine(empty_board)
    state = GameState(board=empty_board)
    engine.resign(state, WHITE)

    assert not engine.resign(state, BLACK)
    assert state.winner == BLACK  # unchanged by the second call
