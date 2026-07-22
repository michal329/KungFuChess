import asyncio

from protocol.commands import LoginCommand
from protocol.messages import ErrorMessage, RatingMessage
from protocol.serialization import decode_message
from server.auth import AuthService, DEFAULT_RATING, UserStore, hash_password, verify_password
from server.connection_manager import ConnectionManager


class FakeConnection:
    def __init__(self):
        self.sent = []

    async def send(self, message: str) -> None:
        self.sent.append(message)


def _run(coro):
    return asyncio.run(coro)


def _setup():
    store = UserStore()
    manager = ConnectionManager()
    connection = FakeConnection()
    connection_id = manager.register(connection)
    service = AuthService(store, manager)
    return store, manager, connection, connection_id, service


# --- password hashing -------------------------------------------------

def test_hash_password_round_trips():
    hashed = hash_password("hunter2")
    assert verify_password("hunter2", hashed)
    assert not verify_password("wrong", hashed)


def test_hash_password_uses_a_random_salt_each_time():
    assert hash_password("hunter2") != hash_password("hunter2")


# --- UserStore ----------------------------------------------------------

def test_new_user_has_default_rating_and_no_password():
    store = UserStore()
    user = store.create("alice")
    assert user.rating == DEFAULT_RATING
    assert user.password_hash is None


def test_rating_for_unknown_user_is_default():
    store = UserStore()
    assert store.rating_for("nobody") == DEFAULT_RATING


def test_record_game_result_updates_rating_and_bumps_the_right_counter():
    store = UserStore()
    store.create("alice")

    store.record_game_result("alice", 1216, "win")

    user = store.get("alice")
    assert user.rating == 1216
    assert user.wins == 1
    assert user.losses == 0
    assert user.draws == 0


def test_record_game_result_accumulates_across_games():
    store = UserStore()
    store.create("alice")

    store.record_game_result("alice", 1216, "win")
    store.record_game_result("alice", 1200, "loss")
    store.record_game_result("alice", 1200, "draw")

    user = store.get("alice")
    assert user.rating == 1200
    assert (user.wins, user.losses, user.draws) == (1, 1, 1)


# --- AuthService.handle_login -------------------------------------------

def test_username_only_login_creates_and_authenticates_a_new_user():
    store, manager, connection, connection_id, service = _setup()

    _run(service.handle_login(connection_id, LoginCommand(username="alice")))

    assert manager.username_for(connection_id) == "alice"
    assert store.get("alice") is not None
    message = decode_message(connection.sent[0])
    assert message == RatingMessage(username="alice", rating=DEFAULT_RATING)


def test_first_password_supplied_claims_the_account():
    store, manager, connection, connection_id, service = _setup()
    _run(service.handle_login(connection_id, LoginCommand(username="alice")))  # username-only first

    _run(service.handle_login(connection_id, LoginCommand(username="alice", password="hunter2")))

    user = store.get("alice")
    assert user.password_hash is not None
    assert verify_password("hunter2", user.password_hash)


def test_wrong_password_after_claiming_is_rejected():
    store, manager, connection, connection_id, service = _setup()
    _run(service.handle_login(connection_id, LoginCommand(username="alice", password="hunter2")))

    other_connection = FakeConnection()
    other_id = manager.register(other_connection)
    _run(service.handle_login(other_id, LoginCommand(username="alice", password="wrong")))

    assert manager.username_for(other_id) is None  # this attempt never authenticated
    message = decode_message(other_connection.sent[0])
    assert isinstance(message, ErrorMessage)


def test_username_only_login_rejected_once_a_password_is_set():
    store, manager, connection, connection_id, service = _setup()
    _run(service.handle_login(connection_id, LoginCommand(username="alice", password="hunter2")))

    other_connection = FakeConnection()
    other_id = manager.register(other_connection)
    _run(service.handle_login(other_id, LoginCommand(username="alice")))  # no password supplied this time

    assert manager.username_for(other_id) is None
    assert isinstance(decode_message(other_connection.sent[0]), ErrorMessage)


def test_correct_password_login_succeeds():
    store, manager, connection, connection_id, service = _setup()
    _run(service.handle_login(connection_id, LoginCommand(username="alice", password="hunter2")))
    connection.sent.clear()

    _run(service.handle_login(connection_id, LoginCommand(username="alice", password="hunter2")))

    assert manager.username_for(connection_id) == "alice"
    message = decode_message(connection.sent[0])
    assert message == RatingMessage(username="alice", rating=DEFAULT_RATING)
