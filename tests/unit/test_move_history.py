from kfchess.engine.game_engine import GameEngine
from kfchess.engine.game_state import GameState
from kfchess.engine.move_history import MoveHistory
from kfchess.events.events import AirborneCaptureEvent, MoveCompletedEvent
from kfchess.model.piece import BLACK, KING, ROOK, WHITE, Piece
from kfchess.model.position import Position


def test_records_a_completed_move_under_its_color():
    history = MoveHistory()
    piece = Piece(ROOK, WHITE)
    history.on_event(MoveCompletedEvent(piece=piece, from_pos=Position(0, 0), to_pos=Position(0, 3), arrival_time=3000))

    assert history.move_count(WHITE) == 1
    assert history.move_count(BLACK) == 0
    record = history.moves_for(WHITE)[0]
    assert record.piece == piece
    assert record.from_pos == Position(0, 0)
    assert record.to_pos == Position(0, 3)
    assert record.arrival_time == 3000


def test_separates_moves_by_color():
    history = MoveHistory()
    history.on_event(MoveCompletedEvent(Piece(ROOK, WHITE), Position(0, 0), Position(0, 1), 1000))
    history.on_event(MoveCompletedEvent(Piece(ROOK, BLACK), Position(7, 0), Position(6, 0), 1000))
    history.on_event(MoveCompletedEvent(Piece(KING, WHITE), Position(0, 4), Position(0, 5), 2000))

    assert history.move_count(WHITE) == 2
    assert history.move_count(BLACK) == 1


def test_ignores_events_that_are_not_move_completed():
    history = MoveHistory()
    history.on_event(AirborneCaptureEvent(defender=Piece(ROOK, WHITE), pos=Position(0, 0), attacker=Piece(ROOK, BLACK)))
    assert history.move_count(WHITE) == 0
    assert history.move_count(BLACK) == 0


def test_moves_for_returns_a_defensive_copy():
    history = MoveHistory()
    history.on_event(MoveCompletedEvent(Piece(ROOK, WHITE), Position(0, 0), Position(0, 1), 1000))

    got = history.moves_for(WHITE)
    got.append("not a real record")
    assert history.move_count(WHITE) == 1  # untouched by mutating the returned list


def test_wired_into_a_real_game_engine_records_without_affecting_execution(empty_board):
    """MoveHistory sits entirely outside attempt_move/tick's own logic --
    registering it must not change what GameEngine actually does, only
    add a parallel record of what happened."""
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    empty_board.set(Position(7, 0), Piece(ROOK, BLACK))
    engine = GameEngine(empty_board, move_duration=1000)
    state = GameState(board=empty_board)
    history = MoveHistory()
    engine.add_observer(history)

    engine.attempt_move(state, Position(0, 0), Position(0, 3))
    engine.attempt_move(state, Position(7, 0), Position(6, 0))
    engine.tick(state, 3000)

    # GameEngine's own outcome is exactly as it would be with no observer.
    assert state.board.get(Position(0, 3)) == Piece(ROOK, WHITE)
    assert state.board.get(Position(6, 0)) == Piece(ROOK, BLACK)

    # And the history recorded both, correctly separated by color.
    assert history.move_count(WHITE) == 1
    assert history.move_count(BLACK) == 1
    assert history.moves_for(WHITE)[0].to_pos == Position(0, 3)
    assert history.moves_for(BLACK)[0].to_pos == Position(6, 0)
