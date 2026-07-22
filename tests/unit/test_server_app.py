"""Tests ServerApp's own wiring directly (registering fake connections
and dispatching real encoded commands through command_router.dispatch)
rather than through a real socket -- the same lower-level style
test_game_manager.py already uses for GameManager. Real end-to-end
socket coverage lives in tests/integration/test_full_game_flow.py.
"""
import asyncio

from protocol.commands import CreateRoomCommand, JoinRoomCommand, LeaveRoomCommand, LoginCommand
from protocol.messages import ErrorMessage, GameEndedMessage
from protocol.serialization import decode_message, encode_command
from server.app import ServerApp


class FakeConnection:
    def __init__(self):
        self.sent = []

    async def send(self, message: str) -> None:
        self.sent.append(decode_message(message))


def _run(coro):
    return asyncio.run(coro)


async def _login(app, connection_id, username):
    await app.command_router.dispatch(connection_id, encode_command(LoginCommand(username=username)))


def test_leave_room_before_a_game_starts_just_frees_the_seat():
    async def scenario():
        app = ServerApp(db_path=":memory:")
        conn = FakeConnection()
        connection_id = app.connection_manager.register(conn)
        await _login(app, connection_id, "alice")

        await app.command_router.dispatch(connection_id, encode_command(CreateRoomCommand()))
        room_id = next(m for m in conn.sent if hasattr(m, "room_id")).room_id
        await app.command_router.dispatch(connection_id, encode_command(JoinRoomCommand(room_id=room_id)))

        room = app.room_manager.get(room_id)
        assert room.white == connection_id

        await app.command_router.dispatch(connection_id, encode_command(LeaveRoomCommand()))

        assert room.white is None
        assert not app.game_manager.has_game(room_id)

    _run(scenario())


def test_leave_room_mid_game_forfeits_for_the_opponent():
    async def scenario():
        app = ServerApp(db_path=":memory:", tick_interval_seconds=0.01, move_duration=0)
        white_conn, black_conn = FakeConnection(), FakeConnection()
        white_id = app.connection_manager.register(white_conn)
        black_id = app.connection_manager.register(black_conn)
        await _login(app, white_id, "alice")
        await _login(app, black_id, "bob")

        await app.command_router.dispatch(white_id, encode_command(CreateRoomCommand()))
        room_id = next(m for m in white_conn.sent if hasattr(m, "room_id")).room_id
        await app.command_router.dispatch(white_id, encode_command(JoinRoomCommand(room_id=room_id)))
        await app.command_router.dispatch(black_id, encode_command(JoinRoomCommand(room_id=room_id)))

        assert app.game_manager.has_game(room_id)
        white_conn.sent.clear()

        await app.command_router.dispatch(white_id, encode_command(LeaveRoomCommand()))
        await asyncio.sleep(0)  # let the scheduled broadcast task actually run

        assert GameEndedMessage(winner="B") in [m for m in black_conn.sent]
        # The seat itself is left alone (same policy as a disconnect).
        room = app.room_manager.get(room_id)
        assert room.white == white_id

        app.game_manager.stop_all()
        await asyncio.sleep(0)

    _run(scenario())


def test_leave_room_for_a_spectator_removes_only_the_spectator():
    async def scenario():
        app = ServerApp(db_path=":memory:")
        white_conn, black_conn, spectator_conn = FakeConnection(), FakeConnection(), FakeConnection()
        white_id = app.connection_manager.register(white_conn)
        black_id = app.connection_manager.register(black_conn)
        spectator_id = app.connection_manager.register(spectator_conn)
        await _login(app, white_id, "alice")
        await _login(app, black_id, "bob")
        await _login(app, spectator_id, "carl")

        await app.command_router.dispatch(white_id, encode_command(CreateRoomCommand()))
        room_id = next(m for m in white_conn.sent if hasattr(m, "room_id")).room_id
        await app.command_router.dispatch(white_id, encode_command(JoinRoomCommand(room_id=room_id)))
        await app.command_router.dispatch(black_id, encode_command(JoinRoomCommand(room_id=room_id)))
        await app.command_router.dispatch(spectator_id, encode_command(JoinRoomCommand(room_id=room_id)))

        room = app.room_manager.get(room_id)
        assert spectator_id in room.spectators

        await app.command_router.dispatch(spectator_id, encode_command(LeaveRoomCommand()))

        assert spectator_id not in room.spectators
        assert room.white == white_id and room.black == black_id  # untouched
        assert not any(isinstance(m, ErrorMessage) for m in spectator_conn.sent)

        app.game_manager.stop_all()
        await asyncio.sleep(0)

    _run(scenario())
