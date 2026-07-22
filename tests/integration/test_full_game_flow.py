"""End-to-end proof that epics 4-7 fit together on top of epics 0-3:
two real websocket clients log in, one creates a room and both join
it, and a move one player makes comes back out to both as a real
``MoveEventMessage`` -- all through the actual ``ServerApp``
composition root, no test-local stand-in handlers this time (contrast
with ``tests/integration/test_websocket_roundtrip.py``, written before
the Game Manager existed).

``receive_until`` keeps draining every message that arrives (a real
client -- the GUI's eventual Application Layer -- runs a continuous
receive loop for the whole life of the connection, same as it already
runs a continuous frame loop today; see ``kfchess/gui/game_loop.py``)
rather than assuming a fixed position for the one this test actually
cares about; the per-room tick loop publishes a ``TimerMessage`` on
every tick, and those are expected, ignorable noise here. A client
that stops draining entirely (as an earlier, since-fixed version of
this test did) can stall its own connection's close -- see
``server/connection_manager.py``'s per-connection send lock and
``server/broadcaster.py`` for the server-side half of this; a real
client never leaves messages unread for the reason spelled out above.
"""
import asyncio

from client.websocket_client import WebSocketClient
from protocol.commands import CreateRoomCommand, JoinRoomCommand, LoginCommand, MoveCommand
from protocol.messages import ErrorMessage, GameStartedMessage, MoveEventMessage, RatingMessage, RoomCreatedMessage, SnapshotMessage
from server.app import ServerApp

RECEIVE_TIMEOUT = 3.0


async def receive_until(client: WebSocketClient, message_type, max_attempts: int = 500):
    """Drain messages until one of *message_type* arrives (discarding
    ``TimerMessage`` noise along the way), or fail after *max_attempts*."""
    for _ in range(max_attempts):
        message = await asyncio.wait_for(client.receive_message(), timeout=RECEIVE_TIMEOUT)
        if isinstance(message, message_type):
            return message
    raise AssertionError(f"never received a {message_type.__name__} after {max_attempts} messages")


def test_login_create_join_and_move_flow_over_real_websockets():
    async def scenario():
        app = ServerApp(host="localhost", port=0, db_path=":memory:", tick_interval_seconds=0.05, move_duration=0)
        server = await app.start()
        port = server.sockets[0].getsockname()[1]
        uri = f"ws://localhost:{port}"

        try:
            async with WebSocketClient(uri) as white, WebSocketClient(uri) as black:
                await white.send_command(LoginCommand(username="alice"))
                assert await receive_until(white, RatingMessage) == RatingMessage(username="alice", rating=1200)

                await black.send_command(LoginCommand(username="bob"))
                assert await receive_until(black, RatingMessage) == RatingMessage(username="bob", rating=1200)

                await white.send_command(CreateRoomCommand())
                room_created = await receive_until(white, RoomCreatedMessage)
                room_id = room_created.room_id

                await white.send_command(JoinRoomCommand(room_id=room_id))  # becomes White, room not full yet
                await black.send_command(JoinRoomCommand(room_id=room_id))  # becomes Black, room now full -> game starts

                expected_started_kwargs = dict(move_duration=0, jump_duration=1000, cooldown_duration=1000)
                assert await receive_until(white, GameStartedMessage) == GameStartedMessage(
                    room_id=room_id, color="W", **expected_started_kwargs)
                assert isinstance(await receive_until(white, SnapshotMessage), SnapshotMessage)
                assert await receive_until(black, GameStartedMessage) == GameStartedMessage(
                    room_id=room_id, color="B", **expected_started_kwargs)
                assert isinstance(await receive_until(black, SnapshotMessage), SnapshotMessage)

                await white.send_command(MoveCommand(from_={"row": 6, "col": 0}, to={"row": 5, "col": 0}))

                expected = MoveEventMessage(
                    piece="WP", from_={"row": 6, "col": 0}, to={"row": 5, "col": 0}, arrival_time=0,
                )
                assert await receive_until(white, MoveEventMessage) == expected
                assert await receive_until(black, MoveEventMessage) == expected  # broadcast: both players see every event

                # Keep draining a little longer so neither socket is left
                # holding an unread backlog when the `async with` blocks exit.
                for _ in range(3):
                    await asyncio.wait_for(white.receive_message(), timeout=RECEIVE_TIMEOUT)
                    await asyncio.wait_for(black.receive_message(), timeout=RECEIVE_TIMEOUT)
        finally:
            await app.stop()

    asyncio.run(scenario())


def test_black_cannot_move_whites_pieces_over_the_wire():
    async def scenario():
        app = ServerApp(host="localhost", port=0, db_path=":memory:", tick_interval_seconds=0.05, move_duration=0)
        server = await app.start()
        port = server.sockets[0].getsockname()[1]
        uri = f"ws://localhost:{port}"

        try:
            async with WebSocketClient(uri) as white, WebSocketClient(uri) as black:
                await white.send_command(LoginCommand(username="alice"))
                await receive_until(white, RatingMessage)
                await black.send_command(LoginCommand(username="bob"))
                await receive_until(black, RatingMessage)

                await white.send_command(CreateRoomCommand())
                room_id = (await receive_until(white, RoomCreatedMessage)).room_id
                await white.send_command(JoinRoomCommand(room_id=room_id))
                await black.send_command(JoinRoomCommand(room_id=room_id))
                await receive_until(white, SnapshotMessage)
                await receive_until(black, SnapshotMessage)

                await black.send_command(MoveCommand(from_={"row": 6, "col": 0}, to={"row": 5, "col": 0}))
                error = await receive_until(black, ErrorMessage)
                assert "own pieces" in error.reason

                for _ in range(3):
                    await asyncio.wait_for(white.receive_message(), timeout=RECEIVE_TIMEOUT)
                    await asyncio.wait_for(black.receive_message(), timeout=RECEIVE_TIMEOUT)
        finally:
            await app.stop()

    asyncio.run(scenario())
