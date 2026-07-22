import asyncio

from protocol.commands import PlayCommand
from protocol.messages import ErrorMessage, GameStartedMessage
from protocol.serialization import decode_message
from server.bus import Bus
from server.connection_manager import ConnectionManager
from server.game_manager import GameManager
from server.matchmaking import Matchmaker
from server.room_manager import RoomManager


class FakeConnection:
    def __init__(self):
        self.sent = []

    async def send(self, message: str) -> None:
        self.sent.append(decode_message(message))


def _run(coro):
    return asyncio.run(coro)


def _build(ratings, **matchmaker_kwargs):
    bus = Bus()
    connection_manager = ConnectionManager()
    room_manager = RoomManager()
    game_manager = GameManager(bus, connection_manager, room_manager)
    matchmaker = Matchmaker(
        connection_manager, room_manager, game_manager,
        rating_lookup=lambda username: ratings[username],
        **matchmaker_kwargs,
    )
    return connection_manager, room_manager, game_manager, matchmaker


def _login(connection_manager, username):
    conn = FakeConnection()
    connection_id = connection_manager.register(conn)
    connection_manager.authenticate(connection_id, username)
    return connection_id, conn


def test_play_without_login_is_rejected():
    async def scenario():
        connection_manager, room_manager, game_manager, matchmaker = _build({})
        conn = FakeConnection()
        connection_id = connection_manager.register(conn)

        await matchmaker.handle_play(connection_id, PlayCommand())

        assert isinstance(conn.sent[-1], ErrorMessage)
        assert matchmaker.queue_size() == 0

    _run(scenario())


def test_two_close_ratings_match_immediately():
    async def scenario():
        connection_manager, room_manager, game_manager, matchmaker = _build(
            {"alice": 1200, "bob": 1250},
        )
        alice_id, alice_conn = _login(connection_manager, "alice")
        bob_id, bob_conn = _login(connection_manager, "bob")

        await matchmaker.handle_play(alice_id, PlayCommand())
        assert matchmaker.queue_size() == 1

        await matchmaker.handle_play(bob_id, PlayCommand())

        assert matchmaker.queue_size() == 0
        assert isinstance(alice_conn.sent[-2], GameStartedMessage)
        assert isinstance(bob_conn.sent[-2], GameStartedMessage)

        game_manager.stop_all()
        await asyncio.sleep(0)

    _run(scenario())


def test_ratings_too_far_apart_both_stay_queued():
    async def scenario():
        connection_manager, room_manager, game_manager, matchmaker = _build(
            {"alice": 1200, "carl": 1500}, timeout_seconds=10,
        )
        alice_id, _ = _login(connection_manager, "alice")
        carl_id, _ = _login(connection_manager, "carl")

        await matchmaker.handle_play(alice_id, PlayCommand())
        await matchmaker.handle_play(carl_id, PlayCommand())

        assert matchmaker.queue_size() == 2

    _run(scenario())


def test_timeout_sends_no_opponent_found_and_drains_the_queue():
    async def scenario():
        connection_manager, room_manager, game_manager, matchmaker = _build(
            {"alice": 1200}, timeout_seconds=0.02,
        )
        alice_id, alice_conn = _login(connection_manager, "alice")

        await matchmaker.handle_play(alice_id, PlayCommand())
        assert matchmaker.queue_size() == 1

        await asyncio.sleep(0.05)

        assert matchmaker.queue_size() == 0
        message = alice_conn.sent[-1]
        assert isinstance(message, ErrorMessage)
        assert "no opponent" in message.reason

    _run(scenario())


def test_match_before_timeout_never_sends_no_opponent_found():
    async def scenario():
        connection_manager, room_manager, game_manager, matchmaker = _build(
            {"alice": 1200, "bob": 1210}, timeout_seconds=0.02,
        )
        alice_id, alice_conn = _login(connection_manager, "alice")
        await matchmaker.handle_play(alice_id, PlayCommand())

        bob_id, bob_conn = _login(connection_manager, "bob")
        await matchmaker.handle_play(bob_id, PlayCommand())

        await asyncio.sleep(0.05)  # long enough for the (cancelled) timeout to have fired if it were going to

        assert not any(isinstance(m, ErrorMessage) for m in alice_conn.sent)
        game_manager.stop_all()
        await asyncio.sleep(0)

    _run(scenario())
