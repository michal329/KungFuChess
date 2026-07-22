"""Covers the testable pieces of NetworkGameLoop: the login/room-choice
prompts and the incoming-message pump, all against a fake client with
no real socket or pygame window involved. ``_play``/``run`` themselves
open a real pygame window and are left untested here -- both are a thin
composition root over already-tested pieces (see EXPLANATION.md §5.5).
"""
import asyncio

import pytest
import websockets.exceptions

from client.network_game_loop import NetworkGameLoop
from protocol.commands import CreateRoomCommand, JoinRoomCommand, LoginCommand, PlayCommand
from protocol.messages import ErrorMessage, GameStartedMessage, RatingMessage, RoomCreatedMessage, SnapshotMessage, TimerMessage


class FakeClient:
    def __init__(self, incoming):
        self.sent = []
        self._incoming = list(incoming)

    async def send_command(self, command) -> None:
        self.sent.append(command)

    async def receive_message(self):
        return self._incoming.pop(0)


def _run(coro):
    return asyncio.run(coro)


def test_login_sends_command_and_authenticates_on_success(monkeypatch):
    inputs = iter(["alice", ""])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))
    client = FakeClient([RatingMessage(username="alice", rating=1200)])
    loop = NetworkGameLoop("ws://irrelevant")

    _run(loop._login(client))

    assert client.sent == [LoginCommand(username="alice", password=None)]


def test_login_with_password_sends_it(monkeypatch):
    inputs = iter(["alice", "hunter2"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))
    client = FakeClient([RatingMessage(username="alice", rating=1200)])
    loop = NetworkGameLoop("ws://irrelevant")

    _run(loop._login(client))

    assert client.sent == [LoginCommand(username="alice", password="hunter2")]


def test_login_failure_raises_system_exit(monkeypatch):
    inputs = iter(["alice", ""])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))
    client = FakeClient([ErrorMessage(reason="invalid username or password")])
    loop = NetworkGameLoop("ws://irrelevant")

    with pytest.raises(SystemExit):
        _run(loop._login(client))


def test_join_or_matchmake_create_room_then_joins_it(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _prompt: "c")
    client = FakeClient([RoomCreatedMessage(room_id="abc123")])
    loop = NetworkGameLoop("ws://irrelevant")

    _run(loop._join_or_matchmake(client))

    assert client.sent == [CreateRoomCommand(), JoinRoomCommand(room_id="abc123")]


def test_join_or_matchmake_join_room(monkeypatch):
    inputs = iter(["j", "myroom"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))
    client = FakeClient([])
    loop = NetworkGameLoop("ws://irrelevant")

    _run(loop._join_or_matchmake(client))

    assert client.sent == [JoinRoomCommand(room_id="myroom")]


def test_join_or_matchmake_anything_else_plays_matchmaking(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _prompt: "p")
    client = FakeClient([])
    loop = NetworkGameLoop("ws://irrelevant")

    _run(loop._join_or_matchmake(client))

    assert client.sent == [PlayCommand()]


def test_await_game_start_skips_noise_and_returns_started_message_and_view():
    payload = {"board": {"height": 1, "width": 1, "grid": [["."]]}, "current_time": 0,
               "cooldowns": [], "pending": [], "airborne": [], "game_over": False, "winner": None}
    started = GameStartedMessage(room_id="r1", color="W", move_duration=1000, jump_duration=1000, cooldown_duration=1000)
    client = FakeClient([TimerMessage(current_time=0), started, SnapshotMessage(payload=payload)])
    loop = NetworkGameLoop("ws://irrelevant")

    game_started, view = _run(loop._await_game_start(client))

    assert game_started == started
    assert view.state.current_time == 0


def test_await_game_start_error_raises_system_exit():
    client = FakeClient([ErrorMessage(reason="no such room")])
    loop = NetworkGameLoop("ws://irrelevant")

    with pytest.raises(SystemExit):
        _run(loop._await_game_start(client))


def test_pump_incoming_drains_every_message_into_the_queue():
    async def scenario():
        messages = [TimerMessage(current_time=1), TimerMessage(current_time=2)]

        class EndlessClient:
            def __init__(self):
                self._messages = list(messages)

            async def receive_message(self):
                if self._messages:
                    return self._messages.pop(0)
                raise websockets.exceptions.ConnectionClosedOK(None, None)

        loop = NetworkGameLoop("ws://irrelevant")
        queue: asyncio.Queue = asyncio.Queue()
        await loop._pump_incoming(EndlessClient(), queue)  # returns once "connection" closes

        drained = []
        while not queue.empty():
            drained.append(queue.get_nowait())
        assert drained == messages

    _run(scenario())


def test_pump_incoming_stops_cleanly_on_cancellation():
    async def scenario():
        class NeverEndingClient:
            async def receive_message(self):
                await asyncio.sleep(10)  # never actually resolves within the test

        loop = NetworkGameLoop("ws://irrelevant")
        queue: asyncio.Queue = asyncio.Queue()
        task = asyncio.create_task(loop._pump_incoming(NeverEndingClient(), queue))
        await asyncio.sleep(0)
        task.cancel()
        await task  # must not raise -- CancelledError is swallowed inside _pump_incoming

    _run(scenario())
