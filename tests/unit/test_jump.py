from kfchess.engine.game_engine import GameEngine
from kfchess.engine.game_state import GameState
from kfchess.events.events import JumpQueuedEvent, Observer
from kfchess.model.piece import BLACK, ROOK, WHITE, Piece
from kfchess.model.position import Position


class _Recorder(Observer):
    def __init__(self):
        self.events = []

    def on_event(self, event):
        self.events.append(event)


def test_jump_sends_piece_airborne(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    engine = GameEngine(empty_board, jump_duration=500)
    state = GameState(board=empty_board)

    assert engine.attempt_jump(state, Position(0, 0))
    assert engine.is_airborne(state, Position(0, 0))
    assert state.board.get(Position(0, 0)) is not None  # never relocates


def test_attempt_jump_fires_jump_queued_event_immediately(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    engine = GameEngine(empty_board, jump_duration=500)
    state = GameState(board=empty_board)
    recorder = _Recorder()
    engine.add_observer(recorder)

    engine.attempt_jump(state, Position(0, 0))

    assert recorder.events == [JumpQueuedEvent(
        piece=Piece(ROOK, WHITE), pos=Position(0, 0), start_time=0, land_time=500,
    )]


def test_jump_expires_with_no_interception_lands_unchanged(empty_board):
    piece = Piece(ROOK, WHITE)
    empty_board.set(Position(0, 0), piece)
    engine = GameEngine(empty_board, jump_duration=500, cooldown_duration=200)
    state = GameState(board=empty_board)

    engine.attempt_jump(state, Position(0, 0))
    engine.tick(state, 500)
    assert not engine.is_airborne(state, Position(0, 0))
    assert state.board.get(Position(0, 0)) == piece
    assert engine.is_in_cooldown(state, Position(0, 0))


def test_airborne_piece_intercepts_arriving_enemy(empty_board):
    defender = Piece(ROOK, BLACK)
    attacker = Piece(ROOK, WHITE)
    empty_board.set(Position(0, 3), defender)
    empty_board.set(Position(0, 0), attacker)
    engine = GameEngine(empty_board, move_duration=1000, jump_duration=5000)
    state = GameState(board=empty_board)

    engine.attempt_jump(state, Position(0, 3))  # defender jumps
    engine.attempt_move(state, Position(0, 0), Position(0, 3))  # attacker moves in
    engine.tick(state, 3000)  # attacker arrives while defender still airborne

    assert state.board.get(Position(0, 3)) == defender  # defender never moved
    assert state.board.get(Position(0, 0)) is None  # attacker removed outright


def test_friendly_arrival_at_airborne_cell_is_ordinary_friendly_fire_rejection(empty_board):
    piece = Piece(ROOK, WHITE)
    empty_board.set(Position(0, 3), piece)
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    engine = GameEngine(empty_board, jump_duration=5000)
    state = GameState(board=empty_board)

    engine.attempt_jump(state, Position(0, 3))
    assert not engine.attempt_move(state, Position(0, 0), Position(0, 3))


def test_busy_piece_cannot_jump_twice(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    engine = GameEngine(empty_board, jump_duration=5000)
    state = GameState(board=empty_board)

    assert engine.attempt_jump(state, Position(0, 0))
    assert not engine.attempt_jump(state, Position(0, 0))  # already airborne
    assert len(state.airborne) == 1


def test_moving_piece_cannot_jump(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    engine = GameEngine(empty_board, move_duration=1000)
    state = GameState(board=empty_board)

    engine.attempt_move(state, Position(0, 0), Position(0, 3))
    assert not engine.attempt_jump(state, Position(0, 0))
    assert state.airborne == []


def test_jump_via_selecting_and_clicking_same_square_again(empty_board):
    """The actual UI trigger: select a piece, then click its own square
    a second time -- see kfchess.input.click_controller.ClickController."""
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    engine = GameEngine(empty_board, jump_duration=500)
    state = GameState(board=empty_board)

    engine.handle_click(state, x=50, y=50)
    engine.handle_click(state, x=50, y=50)
    assert engine.is_airborne(state, Position(0, 0))
