from kfchess.engine.game_engine import GameEngine
from kfchess.engine.game_state import GameState
from kfchess.events.events import GameEvent, RenderEvent
from kfchess.model.piece import BLACK, KING, ROOK, WHITE, Piece
from kfchess.model.position import Position
from protocol.messages import GameEndedMessage, JumpQueuedMessage, MoveEventMessage, MoveQueuedMessage, TimerMessage
from server.bus import Bus
from server.event_bridge import GameEventBridge, translate_event


def test_move_queued_is_published_immediately_before_it_resolves(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    engine = GameEngine(empty_board, move_duration=1000)
    state = GameState(board=empty_board)
    bus = Bus()
    received = []
    bus.subscribe("game.42", lambda topic, message: received.append(message))
    engine.add_observer(GameEventBridge(bus, game_id="42"))

    engine.attempt_move(state, Position(0, 0), Position(0, 3))

    assert received == [MoveQueuedMessage(
        piece="WR", from_={"row": 0, "col": 0}, to={"row": 0, "col": 3}, start_time=0, arrival_time=3000,
    )]


def test_jump_queued_is_published_immediately(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    engine = GameEngine(empty_board, jump_duration=500)
    state = GameState(board=empty_board)
    bus = Bus()
    received = []
    bus.subscribe("game.1", lambda topic, message: received.append(message))
    engine.add_observer(GameEventBridge(bus, game_id="1"))

    engine.attempt_jump(state, Position(0, 0))

    assert received == [JumpQueuedMessage(piece="WR", pos={"row": 0, "col": 0}, start_time=0, land_time=500)]


def test_move_completed_is_published_as_move_event_on_the_game_topic(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    engine = GameEngine(empty_board, move_duration=1000)
    state = GameState(board=empty_board)
    bus = Bus()
    received = []
    bus.subscribe("game.42", lambda topic, message: received.append(message))
    engine.add_observer(GameEventBridge(bus, game_id="42"))

    engine.attempt_move(state, Position(0, 0), Position(0, 3))
    engine.tick(state, 3000)

    move_events = [m for m in received if isinstance(m, MoveEventMessage)]
    assert move_events == [MoveEventMessage(
        piece="WR", from_={"row": 0, "col": 0}, to={"row": 0, "col": 3}, arrival_time=3000,
    )]


def test_tick_publishes_timer_message(empty_board):
    engine = GameEngine(empty_board)
    state = GameState(board=empty_board)
    bus = Bus()
    received = []
    bus.subscribe("game.1", lambda topic, message: received.append(message))
    engine.add_observer(GameEventBridge(bus, game_id="1"))

    engine.tick(state, 500)

    assert TimerMessage(current_time=500) in received


def test_king_capture_publishes_game_ended_message(empty_board):
    empty_board.set(Position(0, 0), Piece(ROOK, WHITE))
    empty_board.set(Position(0, 3), Piece(KING, BLACK))
    engine = GameEngine(empty_board)
    state = GameState(board=empty_board)
    bus = Bus()
    received = []
    bus.subscribe("game.7", lambda topic, message: received.append(message))
    engine.add_observer(GameEventBridge(bus, game_id="7"))

    engine.attempt_move(state, Position(0, 0), Position(0, 3))
    engine.tick(state, 3000)

    assert GameEndedMessage(winner=WHITE) in received


def test_bridge_publishes_to_its_own_game_id_topic_only(empty_board):
    engine = GameEngine(empty_board)
    state = GameState(board=empty_board)
    bus = Bus()
    other_topic_received = []
    bus.subscribe("game.other", lambda topic, message: other_topic_received.append(message))
    engine.add_observer(GameEventBridge(bus, game_id="mine"))

    engine.tick(state, 100)

    assert other_topic_received == []


def test_render_event_has_no_wire_translation():
    assert translate_event(RenderEvent(board_text="...")) is None


def test_unknown_event_subclass_has_no_wire_translation():
    class SomeFutureEvent(GameEvent):
        pass

    assert translate_event(SomeFutureEvent()) is None
