import asyncio

from protocol.messages import MoveEventMessage
from protocol.serialization import decode_message
from server.broadcaster import Broadcaster
from server.connection_manager import ConnectionManager
from server.room_manager import RoomManager


class FakeConnection:
    def __init__(self):
        self.sent = []

    async def send(self, message: str) -> None:
        self.sent.append(decode_message(message))


def _run(coro):
    return asyncio.run(coro)


_MESSAGE = MoveEventMessage(piece="WP", from_={"row": 6, "col": 0}, to={"row": 5, "col": 0}, arrival_time=0)


def test_game_topic_reaches_only_that_rooms_members():
    async def scenario():
        connection_manager = ConnectionManager()
        room_manager = RoomManager()
        white, black, spectator, outsider = (FakeConnection() for _ in range(4))
        white_id = connection_manager.register(white)
        black_id = connection_manager.register(black)
        spectator_id = connection_manager.register(spectator)
        connection_manager.register(outsider)  # never joins any room

        room = room_manager.create_room()
        room_manager.join_room(room.room_id, white_id)
        room_manager.join_room(room.room_id, black_id)
        room_manager.join_room(room.room_id, spectator_id)

        broadcaster = Broadcaster(connection_manager, room_manager)
        broadcaster(f"game.{room.room_id}", _MESSAGE)
        await asyncio.sleep(0)

        assert white.sent == [_MESSAGE]
        assert black.sent == [_MESSAGE]
        assert spectator.sent == [_MESSAGE]
        assert outsider.sent == []

    _run(scenario())


def test_two_rooms_never_see_each_others_messages():
    async def scenario():
        connection_manager = ConnectionManager()
        room_manager = RoomManager()
        conn_a, conn_b = FakeConnection(), FakeConnection()
        id_a = connection_manager.register(conn_a)
        id_b = connection_manager.register(conn_b)
        room_a = room_manager.create_room()
        room_b = room_manager.create_room()
        room_manager.join_room(room_a.room_id, id_a)
        room_manager.join_room(room_b.room_id, id_b)

        broadcaster = Broadcaster(connection_manager, room_manager)
        broadcaster(f"game.{room_a.room_id}", _MESSAGE)
        await asyncio.sleep(0)

        assert conn_a.sent == [_MESSAGE]
        assert conn_b.sent == []  # the bug this class exists to fix

    _run(scenario())


def test_unknown_room_id_sends_to_nobody_without_raising():
    async def scenario():
        connection_manager = ConnectionManager()
        room_manager = RoomManager()
        conn = FakeConnection()
        connection_manager.register(conn)

        broadcaster = Broadcaster(connection_manager, room_manager)
        broadcaster("game.does-not-exist", _MESSAGE)
        await asyncio.sleep(0)

        assert conn.sent == []

    _run(scenario())


def test_without_a_room_manager_falls_back_to_broadcasting_to_everyone():
    async def scenario():
        connection_manager = ConnectionManager()
        conn_a, conn_b = FakeConnection(), FakeConnection()
        connection_manager.register(conn_a)
        connection_manager.register(conn_b)

        broadcaster = Broadcaster(connection_manager)  # no room_manager
        broadcaster("game.whatever", _MESSAGE)
        await asyncio.sleep(0)

        assert conn_a.sent == [_MESSAGE]
        assert conn_b.sent == [_MESSAGE]

    _run(scenario())


def test_non_game_topic_falls_back_to_broadcasting_to_everyone():
    async def scenario():
        connection_manager = ConnectionManager()
        room_manager = RoomManager()
        conn_a, conn_b = FakeConnection(), FakeConnection()
        connection_manager.register(conn_a)
        connection_manager.register(conn_b)

        broadcaster = Broadcaster(connection_manager, room_manager)
        broadcaster("lobby", _MESSAGE)
        await asyncio.sleep(0)

        assert conn_a.sent == [_MESSAGE]
        assert conn_b.sent == [_MESSAGE]

    _run(scenario())
