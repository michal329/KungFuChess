import asyncio

from client.network_game_engine import NetworkGameEngine
from kfchess.engine.game_state import GameState
from kfchess.input.board_mapper import BoardMapper
from kfchess.model.board import Board
from kfchess.model.piece import ROOK, WHITE, Piece
from kfchess.model.position import Position
from protocol.commands import MoveCommand


class FakeClient:
    def __init__(self):
        self.sent = []

    async def send_command(self, command) -> None:
        self.sent.append(command)


def _run(coro):
    return asyncio.run(coro)


def _engine_and_state():
    board = Board(8, 8)
    board.set(Position(0, 0), Piece(ROOK, WHITE))
    client = FakeClient()
    engine = NetworkGameEngine(client, BoardMapper(100))
    state = GameState(board=board)
    return client, engine, state


def test_is_selectable_true_for_an_idle_piece():
    client, engine, state = _engine_and_state()
    assert engine.is_selectable(state, Position(0, 0))


def test_is_selectable_false_for_an_empty_square():
    client, engine, state = _engine_and_state()
    assert not engine.is_selectable(state, Position(3, 3))


def test_is_selectable_false_while_in_transit():
    client, engine, state = _engine_and_state()
    from kfchess.realtime.motion import PendingMove
    state.pending.append(PendingMove(
        piece=state.board.get(Position(0, 0)), from_pos=Position(0, 0), to_pos=Position(0, 3),
        arrival_time=1000, start_time=0,
    ))
    assert engine.is_in_transit(state, Position(0, 0))
    assert not engine.is_selectable(state, Position(0, 0))


def test_is_selectable_false_while_airborne():
    client, engine, state = _engine_and_state()
    from kfchess.realtime.motion import PendingJump
    state.airborne.append(PendingJump(piece=state.board.get(Position(0, 0)), pos=Position(0, 0), land_time=500, start_time=0))
    assert engine.is_airborne(state, Position(0, 0))
    assert not engine.is_selectable(state, Position(0, 0))


def test_is_selectable_false_while_in_cooldown():
    client, engine, state = _engine_and_state()
    state.current_time = 100
    state.cooldowns[Position(0, 0)] = 500
    assert engine.is_in_cooldown(state, Position(0, 0))
    assert not engine.is_selectable(state, Position(0, 0))


def test_is_selectable_true_once_cooldown_expires():
    client, engine, state = _engine_and_state()
    state.current_time = 600
    state.cooldowns[Position(0, 0)] = 500
    assert not engine.is_in_cooldown(state, Position(0, 0))
    assert engine.is_selectable(state, Position(0, 0))


def test_attempt_move_sends_a_move_command_and_returns_true_optimistically():
    async def scenario():
        client, engine, state = _engine_and_state()
        result = engine.attempt_move(state, Position(0, 0), Position(0, 3))
        assert result is True
        await asyncio.sleep(0)  # let the scheduled send task run
        assert client.sent == [MoveCommand(from_={"row": 0, "col": 0}, to={"row": 0, "col": 3})]

    _run(scenario())


def test_attempt_move_never_mutates_local_state():
    async def scenario():
        client, engine, state = _engine_and_state()
        engine.attempt_move(state, Position(0, 0), Position(0, 3))
        await asyncio.sleep(0)
        assert state.pending == []  # only remote_game_view mutates state, driven by server events
        assert state.board.get(Position(0, 0)) is not None

    _run(scenario())


def test_attempt_jump_sends_a_move_command_with_equal_from_and_to():
    async def scenario():
        client, engine, state = _engine_and_state()
        result = engine.attempt_jump(state, Position(0, 0))
        assert result is True
        await asyncio.sleep(0)
        assert client.sent == [MoveCommand(from_={"row": 0, "col": 0}, to={"row": 0, "col": 0})]

    _run(scenario())


def test_handle_click_selection_then_move_sends_exactly_one_command():
    async def scenario():
        client, engine, state = _engine_and_state()
        engine.handle_click(state, 50, 50)  # select (0,0)
        assert engine.selection == Position(0, 0)
        engine.handle_click(state, 350, 50)  # move to (0,3)
        assert engine.selection is None  # cleared regardless of outcome, same as ClickController always does
        await asyncio.sleep(0)
        assert client.sent == [MoveCommand(from_={"row": 0, "col": 0}, to={"row": 0, "col": 3})]

    _run(scenario())


def test_attempt_move_after_game_over_sends_nothing():
    async def scenario():
        client, engine, state = _engine_and_state()
        state.game_over = True
        assert engine.attempt_move(state, Position(0, 0), Position(0, 3)) is False
        await asyncio.sleep(0)
        assert client.sent == []

    _run(scenario())


def test_handle_click_same_square_twice_sends_a_jump():
    async def scenario():
        client, engine, state = _engine_and_state()
        engine.handle_click(state, 50, 50)
        engine.handle_click(state, 50, 50)  # same square again -> jump, not move
        await asyncio.sleep(0)
        assert client.sent == [MoveCommand(from_={"row": 0, "col": 0}, to={"row": 0, "col": 0})]

    _run(scenario())
