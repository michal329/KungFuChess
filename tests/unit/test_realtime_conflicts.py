from kfchess.model.piece import BISHOP, ROOK, WHITE, BLACK, Piece
from kfchess.model.position import Position

from kfchess.engine.game_engine import GameEngine
from kfchess.engine.game_state import GameState


def test_opposite_color_moves_sharing_overlapping_lanes_can_both_be_queued(empty_board):
    """There is no advance route lock: a move never reserves a lane. Two
    opposite-color moves can freely be queued along overlapping spans;
    whatever conflict actually develops is resolved reactively, only
    when a move resolves, against the board as it looks right then --
    see test_enemy_blocks_move_mid_flight_stops_it_short below."""
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    empty_board.set(Position(2, 2), Piece(ROOK, BLACK))
    engine = GameEngine(empty_board, move_duration=1000)
    state = GameState(board=empty_board)

    assert engine.attempt_move(state, Position(0, 0), Position(0, 4))  # occupies cols 0-4
    assert engine.attempt_move(state, Position(2, 2), Position(2, 6))  # cols 2-6 overlap -- allowed


def test_enemy_blocks_move_mid_flight_stops_it_short(empty_board):
    """A blocker mid-route stops the mover short regardless of color --
    unlike a friendly block, an enemy blocker used to fail the whole
    move outright; now both are treated the same way."""
    mover = Piece(ROOK, WHITE)
    empty_board.set(Position(0, 0), mover)
    engine = GameEngine(empty_board, move_duration=1000)
    state = GameState(board=empty_board)
    engine.attempt_move(state, Position(0, 0), Position(0, 4))

    # An enemy piece drops into the route mid-flight, after the move was
    # already queued.
    blocker = Piece(ROOK, BLACK)
    empty_board.set(Position(0, 2), blocker)
    engine.tick(state, 4000)

    assert state.board.get(Position(0, 1)) == mover  # stopped short
    assert state.board.get(Position(0, 4)) is None
    assert state.board.get(Position(0, 2)) == blocker  # blocker never captured, never moved


def test_diagonal_move_also_stops_short_on_a_mid_route_block(empty_board):
    mover = Piece(BISHOP, WHITE)
    empty_board.set(Position(0, 0), mover)
    engine = GameEngine(empty_board, move_duration=1000)
    state = GameState(board=empty_board)
    engine.attempt_move(state, Position(0, 0), Position(4, 4))

    empty_board.set(Position(2, 2), Piece(ROOK, BLACK))
    engine.tick(state, 4000)

    assert state.board.get(Position(1, 1)) == mover  # stopped short
    assert state.board.get(Position(4, 4)) is None


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


def test_enemy_arriving_at_a_vacated_origin_does_not_capture_the_in_flight_piece(empty_board):
    """The exact reported bug: a piece already in flight has genuinely
    left its origin -- an opponent's move targeting that square lands
    on empty ground, not a capture, and the in-flight piece completes
    its own journey completely untouched."""
    mover = Piece(ROOK, WHITE)
    empty_board.set(Position(0, 0), mover)          # about to fly away
    empty_board.set(Position(5, 0), Piece(ROOK, BLACK))
    engine = GameEngine(empty_board, move_duration=1000)
    state = GameState(board=empty_board)

    assert engine.attempt_move(state, Position(0, 0), Position(0, 5))  # mover: 5 cells -> arrives 5000
    assert engine.attempt_move(state, Position(5, 0), Position(0, 0))  # enemy targets the now-vacated origin

    engine.tick(state, 5000)

    assert state.board.get(Position(0, 5)) == mover           # completed its own journey, untouched
    assert state.board.get(Position(0, 0)) == Piece(ROOK, BLACK)  # landed on empty ground, not a capture


def test_queuing_a_move_onto_an_in_flight_pieces_origin_is_legal_at_queue_time_too(empty_board):
    """The vacated-origin treatment isn't just applied at resolution --
    attempt_move's own legality check sees it too, immediately."""
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    empty_board.set(Position(5, 0), Piece(ROOK, BLACK))
    engine = GameEngine(empty_board, move_duration=1000)
    state = GameState(board=empty_board)

    assert engine.attempt_move(state, Position(0, 0), Position(0, 5))
    # Without the fix this would be evaluated as a legal *capture* of the
    # rook still nominally recorded at (0,0); it should just be an
    # ordinary move onto what is, in every sense that matters, empty
    # ground.
    assert engine.attempt_move(state, Position(5, 0), Position(0, 0))


def test_path_is_not_blocked_by_another_pieces_still_unresolved_origin(empty_board):
    """A mover's path crossing a square that's some OTHER piece's
    not-yet-resolved origin must pass straight through -- that other
    piece has already vacated it too, even though it hasn't formally
    landed anywhere yet."""
    mover = Piece(ROOK, WHITE)
    other = Piece(ROOK, BLACK)
    empty_board.set(Position(0, 0), mover)
    empty_board.set(Position(0, 3), other)  # directly in mover's path
    engine = GameEngine(empty_board, move_duration=1000)
    state = GameState(board=empty_board)

    assert engine.attempt_move(state, Position(0, 3), Position(6, 3))  # other: 6 cells -> arrives 6000
    assert engine.attempt_move(state, Position(0, 0), Position(0, 5))  # mover: 5 cells -> arrives 5000, crosses (0,3)

    engine.tick(state, 5000)  # mover resolves; other is still mid-flight (due at 6000)
    assert state.board.get(Position(0, 5)) == mover  # passed straight through, unblocked

    engine.tick(state, 1000)  # other resolves too, completely unaffected
    assert state.board.get(Position(6, 3)) == other
