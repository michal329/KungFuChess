import asyncio

from protocol.commands import MoveCommand
from protocol.messages import ErrorMessage, GameStartedMessage, MoveEventMessage, SnapshotMessage
from protocol.serialization import decode_message
from server.bus import Bus, WILDCARD_TOPIC
from server.connection_manager import ConnectionManager
from server.game_manager import GameManager
from server.room_manager import RoomManager


class FakeConnection:
    def __init__(self):
        self.sent = []

    async def send(self, message: str) -> None:
        self.sent.append(decode_message(message))


def _run(coro):
    return asyncio.run(coro)


def _build(**game_manager_kwargs):
    bus = Bus()
    connection_manager = ConnectionManager()
    room_manager = RoomManager()
    game_manager = GameManager(bus, connection_manager, room_manager, **game_manager_kwargs)
    # ServerApp always wires this; do the same here so a plain
    # connection_manager.unregister(...) in a test behaves the same
    # way it would against the real composition root.
    connection_manager.add_disconnect_hook(game_manager.handle_disconnect)
    return bus, connection_manager, room_manager, game_manager


def _seated_room(connection_manager, room_manager):
    white_conn, black_conn = FakeConnection(), FakeConnection()
    white_id = connection_manager.register(white_conn)
    black_id = connection_manager.register(black_conn)
    room = room_manager.create_room()
    room_manager.join_room(room.room_id, white_id)
    room_manager.join_room(room.room_id, black_id)
    return room, white_id, white_conn, black_id, black_conn


def test_start_game_sends_game_started_and_snapshot_to_both_players():
    async def scenario():
        bus, connection_manager, room_manager, game_manager = _build()
        room, white_id, white_conn, black_id, black_conn = _seated_room(connection_manager, room_manager)

        await game_manager.start_game(room, [white_id, black_id])

        assert game_manager.has_game(room.room_id)
        white_messages = white_conn.sent
        black_messages = black_conn.sent
        assert white_messages[0] == GameStartedMessage(
            room_id=room.room_id, color="W", move_duration=1000, jump_duration=1000, cooldown_duration=1000,
        )
        assert isinstance(white_messages[1], SnapshotMessage)
        assert black_messages[0] == GameStartedMessage(
            room_id=room.room_id, color="B", move_duration=1000, jump_duration=1000, cooldown_duration=1000,
        )
        assert isinstance(black_messages[1], SnapshotMessage)

        game_manager.stop_all()
        await asyncio.sleep(0)

    _run(scenario())


def test_handle_move_rejects_moving_the_opponents_piece():
    async def scenario():
        bus, connection_manager, room_manager, game_manager = _build()
        room, white_id, white_conn, black_id, black_conn = _seated_room(connection_manager, room_manager)
        await game_manager.start_game(room, [white_id, black_id])
        white_conn.sent.clear()

        # White tries to move a black pawn (row 1).
        await game_manager.handle_move(white_id, MoveCommand(
            from_={"row": 1, "col": 0}, to={"row": 2, "col": 0},
        ))

        assert isinstance(white_conn.sent[-1], ErrorMessage)
        game_manager.stop_all()
        await asyncio.sleep(0)

    _run(scenario())


def test_handle_move_rejects_spectators():
    async def scenario():
        bus, connection_manager, room_manager, game_manager = _build()
        room, white_id, white_conn, black_id, black_conn = _seated_room(connection_manager, room_manager)
        spectator_conn = FakeConnection()
        spectator_id = connection_manager.register(spectator_conn)
        room_manager.join_room(room.room_id, spectator_id)
        await game_manager.start_game(room, [white_id, black_id, spectator_id])
        spectator_conn.sent.clear()

        await game_manager.handle_move(spectator_id, MoveCommand(
            from_={"row": 6, "col": 0}, to={"row": 5, "col": 0},
        ))

        assert isinstance(spectator_conn.sent[-1], ErrorMessage)
        game_manager.stop_all()
        await asyncio.sleep(0)

    _run(scenario())


def test_handle_move_with_no_room_sends_error():
    async def scenario():
        bus, connection_manager, room_manager, game_manager = _build()
        conn = FakeConnection()
        connection_id = connection_manager.register(conn)

        await game_manager.handle_move(connection_id, MoveCommand(
            from_={"row": 6, "col": 0}, to={"row": 5, "col": 0},
        ))

        assert isinstance(conn.sent[-1], ErrorMessage)

    _run(scenario())


def test_legal_move_resolves_and_publishes_move_event_via_tick_loop():
    async def scenario():
        bus, connection_manager, room_manager, game_manager = _build(
            tick_interval_seconds=0.01, move_duration=0,
        )
        room, white_id, white_conn, black_id, black_conn = _seated_room(connection_manager, room_manager)
        received = []
        bus.subscribe(WILDCARD_TOPIC, lambda topic, message: received.append(message))
        await game_manager.start_game(room, [white_id, black_id])

        await game_manager.handle_move(white_id, MoveCommand(
            from_={"row": 6, "col": 0}, to={"row": 5, "col": 0},
        ))
        await asyncio.sleep(0.05)  # let the tick loop run at least once

        move_events = [m for m in received if isinstance(m, MoveEventMessage)]
        assert move_events == [MoveEventMessage(
            piece="WP", from_={"row": 6, "col": 0}, to={"row": 5, "col": 0}, arrival_time=0,
        )]

        game_manager.stop_all()
        await asyncio.sleep(0)

    _run(scenario())


def test_jump_is_a_move_command_with_equal_from_and_to():
    async def scenario():
        bus, connection_manager, room_manager, game_manager = _build(
            tick_interval_seconds=0.01, move_duration=0, jump_duration=0,
        )
        room, white_id, white_conn, black_id, black_conn = _seated_room(connection_manager, room_manager)
        received = []
        bus.subscribe(WILDCARD_TOPIC, lambda topic, message: received.append(message))
        await game_manager.start_game(room, [white_id, black_id])

        await game_manager.handle_move(white_id, MoveCommand(
            from_={"row": 6, "col": 0}, to={"row": 6, "col": 0},
        ))
        await asyncio.sleep(0.05)

        from protocol.messages import JumpLandedMessage
        jump_events = [m for m in received if isinstance(m, JumpLandedMessage)]
        assert jump_events == [JumpLandedMessage(piece="WP", pos={"row": 6, "col": 0}, land_time=0)]

        game_manager.stop_all()
        await asyncio.sleep(0)

    _run(scenario())


def test_send_snapshot_reaches_a_spectator_joining_an_in_progress_game():
    async def scenario():
        bus, connection_manager, room_manager, game_manager = _build()
        room, white_id, white_conn, black_id, black_conn = _seated_room(connection_manager, room_manager)
        await game_manager.start_game(room, [white_id, black_id])

        spectator_conn = FakeConnection()
        spectator_id = connection_manager.register(spectator_conn)
        await game_manager.send_snapshot(room.room_id, spectator_id)

        assert isinstance(spectator_conn.sent[-1], SnapshotMessage)
        game_manager.stop_all()
        await asyncio.sleep(0)

    _run(scenario())


def test_handle_resign_ends_the_game_for_the_opponent():
    async def scenario():
        bus, connection_manager, room_manager, game_manager = _build()
        room, white_id, white_conn, black_id, black_conn = _seated_room(connection_manager, room_manager)
        received = []
        bus.subscribe(WILDCARD_TOPIC, lambda topic, message: received.append(message))
        await game_manager.start_game(room, [white_id, black_id])

        from protocol.commands import ResignCommand
        await game_manager.handle_resign(white_id, ResignCommand())

        from protocol.messages import GameEndedMessage
        assert GameEndedMessage(winner="B") in received
        game_manager.stop_all()
        await asyncio.sleep(0)

    _run(scenario())


def test_handle_resign_rejects_spectators():
    async def scenario():
        bus, connection_manager, room_manager, game_manager = _build()
        room, white_id, white_conn, black_id, black_conn = _seated_room(connection_manager, room_manager)
        spectator_conn = FakeConnection()
        spectator_id = connection_manager.register(spectator_conn)
        room_manager.join_room(room.room_id, spectator_id)
        await game_manager.start_game(room, [white_id, black_id, spectator_id])
        spectator_conn.sent.clear()

        from protocol.commands import ResignCommand
        await game_manager.handle_resign(spectator_id, ResignCommand())

        assert isinstance(spectator_conn.sent[-1], ErrorMessage)
        game_manager.stop_all()
        await asyncio.sleep(0)

    _run(scenario())


def test_handle_resign_with_no_room_sends_error():
    async def scenario():
        bus, connection_manager, room_manager, game_manager = _build()
        conn = FakeConnection()
        connection_id = connection_manager.register(conn)

        from protocol.commands import ResignCommand
        await game_manager.handle_resign(connection_id, ResignCommand())

        assert isinstance(conn.sent[-1], ErrorMessage)

    _run(scenario())


def _seated_and_authenticated_room(connection_manager, room_manager):
    room, white_id, white_conn, black_id, black_conn = _seated_room(connection_manager, room_manager)
    connection_manager.authenticate(white_id, "alice")
    connection_manager.authenticate(black_id, "bob")
    return room, white_id, white_conn, black_id, black_conn


def test_disconnect_without_reconnecting_auto_resigns_after_the_timeout():
    async def scenario():
        bus, connection_manager, room_manager, game_manager = _build(reconnect_timeout_seconds=0.02)
        room, white_id, white_conn, black_id, black_conn = _seated_and_authenticated_room(connection_manager, room_manager)
        received = []
        bus.subscribe(WILDCARD_TOPIC, lambda topic, message: received.append(message))
        await game_manager.start_game(room, [white_id, black_id])

        connection_manager.unregister(white_id)  # fires the disconnect hook
        await asyncio.sleep(0.05)

        from protocol.messages import GameEndedMessage
        assert GameEndedMessage(winner="B") in received  # white disconnected -> black wins
        game_manager.stop_all()
        await asyncio.sleep(0)

    _run(scenario())


def test_reconnect_before_timeout_cancels_the_auto_resign():
    async def scenario():
        bus, connection_manager, room_manager, game_manager = _build(reconnect_timeout_seconds=0.05)
        room, white_id, white_conn, black_id, black_conn = _seated_and_authenticated_room(connection_manager, room_manager)
        received = []
        bus.subscribe(WILDCARD_TOPIC, lambda topic, message: received.append(message))
        await game_manager.start_game(room, [white_id, black_id])

        connection_manager.unregister(white_id)
        await asyncio.sleep(0)  # well before the 0.05s timeout

        new_conn = FakeConnection()
        new_white_id = connection_manager.register(new_conn)
        connection_manager.authenticate(new_white_id, "alice")
        reconnected = await game_manager.attempt_reconnect("alice", new_white_id)

        assert reconnected
        assert room.white == new_white_id
        assert isinstance(new_conn.sent[0], GameStartedMessage)
        assert isinstance(new_conn.sent[1], SnapshotMessage)

        # Long enough that the original (cancelled) timer would have
        # fired by now if it hadn't actually been cancelled.
        await asyncio.sleep(0.15)
        from protocol.messages import GameEndedMessage
        assert not any(isinstance(m, GameEndedMessage) for m in received)

        game_manager.stop_all()
        await asyncio.sleep(0)

    _run(scenario())


def test_attempt_reconnect_with_nothing_pending_returns_false():
    async def scenario():
        bus, connection_manager, room_manager, game_manager = _build()
        assert not await game_manager.attempt_reconnect("nobody", "conn-x")

    _run(scenario())


def test_disconnect_of_a_spectator_is_ignored():
    async def scenario():
        bus, connection_manager, room_manager, game_manager = _build(reconnect_timeout_seconds=0.02)
        room, white_id, white_conn, black_id, black_conn = _seated_and_authenticated_room(connection_manager, room_manager)
        spectator_conn = FakeConnection()
        spectator_id = connection_manager.register(spectator_conn)
        connection_manager.authenticate(spectator_id, "carl")
        room_manager.join_room(room.room_id, spectator_id)
        received = []
        bus.subscribe(WILDCARD_TOPIC, lambda topic, message: received.append(message))
        await game_manager.start_game(room, [white_id, black_id, spectator_id])

        connection_manager.unregister(spectator_id)
        await asyncio.sleep(0.05)

        from protocol.messages import GameEndedMessage
        assert not any(isinstance(m, GameEndedMessage) for m in received)
        game_manager.stop_all()
        await asyncio.sleep(0)

    _run(scenario())


def test_stop_game_cancels_the_tick_task_and_forgets_the_game():
    async def scenario():
        bus, connection_manager, room_manager, game_manager = _build(tick_interval_seconds=0.01)
        room, white_id, white_conn, black_id, black_conn = _seated_room(connection_manager, room_manager)
        await game_manager.start_game(room, [white_id, black_id])

        game_manager.stop_game(room.room_id)
        await asyncio.sleep(0)

        assert not game_manager.has_game(room.room_id)

    _run(scenario())
