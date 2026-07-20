from kfchess.engine.game_engine import GameEngine
from kfchess.engine.game_state import GameState
from kfchess.model.piece import BLACK, KING, PAWN, QUEEN, ROOK, WHITE, Piece
from kfchess.model.position import Position


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
