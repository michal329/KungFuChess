import asyncio

from protocol.messages import GameEndedMessage, RatingMessage, TimerMessage
from protocol.serialization import decode_message
from server.auth import DEFAULT_RATING, UserStore
from server.bus import Bus, WILDCARD_TOPIC
from server.connection_manager import ConnectionManager
from server.rating_subscriber import RatingUpdateSubscriber
from server.room_manager import RoomManager


class FakeConnection:
    def __init__(self):
        self.sent = []

    async def send(self, message: str) -> None:
        self.sent.append(decode_message(message))


def _run(coro):
    return asyncio.run(coro)


def _build():
    connection_manager = ConnectionManager()
    room_manager = RoomManager()
    user_store = UserStore()
    bus = Bus()
    subscriber = RatingUpdateSubscriber(connection_manager, room_manager, user_store)
    bus.subscribe(WILDCARD_TOPIC, subscriber)
    return connection_manager, room_manager, user_store, bus


def _seat_players(connection_manager, room_manager, user_store):
    white_conn, black_conn = FakeConnection(), FakeConnection()
    white_id = connection_manager.register(white_conn)
    black_id = connection_manager.register(black_conn)
    connection_manager.authenticate(white_id, "alice")
    connection_manager.authenticate(black_id, "bob")
    user_store.create("alice")
    user_store.create("bob")
    room = room_manager.create_room()
    room_manager.join_room(room.room_id, white_id)
    room_manager.join_room(room.room_id, black_id)
    return room, white_id, white_conn, black_id, black_conn


def test_white_win_updates_both_ratings_and_notifies_both_players():
    async def scenario():
        connection_manager, room_manager, user_store, bus = _build()
        room, white_id, white_conn, black_id, black_conn = _seat_players(connection_manager, room_manager, user_store)

        bus.publish(f"game.{room.room_id}", GameEndedMessage(winner="W"))
        await asyncio.sleep(0)  # let the scheduled task run

        assert user_store.rating_for("alice") == DEFAULT_RATING + 16
        assert user_store.rating_for("bob") == DEFAULT_RATING - 16
        assert white_conn.sent == [RatingMessage(username="alice", rating=DEFAULT_RATING + 16)]
        assert black_conn.sent == [RatingMessage(username="bob", rating=DEFAULT_RATING - 16)]

        user_white = user_store.get("alice")
        user_black = user_store.get("bob")
        assert user_white.wins == 1
        assert user_black.losses == 1

    _run(scenario())


def test_draw_updates_draw_counters_and_leaves_equal_ratings_unchanged():
    async def scenario():
        connection_manager, room_manager, user_store, bus = _build()
        room, white_id, white_conn, black_id, black_conn = _seat_players(connection_manager, room_manager, user_store)

        bus.publish(f"game.{room.room_id}", GameEndedMessage(winner=None))
        await asyncio.sleep(0)

        assert user_store.rating_for("alice") == DEFAULT_RATING
        assert user_store.rating_for("bob") == DEFAULT_RATING
        assert user_store.get("alice").draws == 1
        assert user_store.get("bob").draws == 1

    _run(scenario())


def test_non_game_ended_messages_are_ignored():
    async def scenario():
        connection_manager, room_manager, user_store, bus = _build()
        room, white_id, white_conn, black_id, black_conn = _seat_players(connection_manager, room_manager, user_store)

        bus.publish(f"game.{room.room_id}", TimerMessage(current_time=500))
        await asyncio.sleep(0)

        assert white_conn.sent == []
        assert user_store.rating_for("alice") == DEFAULT_RATING

    _run(scenario())


def test_unknown_room_is_a_no_op():
    async def scenario():
        connection_manager, room_manager, user_store, bus = _build()

        bus.publish("game.nope", GameEndedMessage(winner="W"))
        await asyncio.sleep(0)  # must not raise

    _run(scenario())
