import asyncio

from server.connection_manager import ConnectionManager


class FakeConnection:
    def __init__(self):
        self.sent = []

    async def send(self, message: str) -> None:
        self.sent.append(message)


def _run(coro):
    return asyncio.run(coro)


def test_register_returns_distinct_ids():
    manager = ConnectionManager()
    id_a = manager.register(FakeConnection())
    id_b = manager.register(FakeConnection())
    assert id_a != id_b


def test_send_delivers_only_to_that_connection():
    manager = ConnectionManager()
    conn_a, conn_b = FakeConnection(), FakeConnection()
    id_a = manager.register(conn_a)
    manager.register(conn_b)

    _run(manager.send(id_a, "hello"))

    assert conn_a.sent == ["hello"]
    assert conn_b.sent == []


def test_broadcast_reaches_every_registered_connection():
    manager = ConnectionManager()
    conn_a, conn_b = FakeConnection(), FakeConnection()
    manager.register(conn_a)
    manager.register(conn_b)

    _run(manager.broadcast("all"))

    assert conn_a.sent == ["all"]
    assert conn_b.sent == ["all"]


def test_unregister_removes_connection_and_its_username():
    manager = ConnectionManager()
    connection_id = manager.register(FakeConnection())
    manager.authenticate(connection_id, "alice")

    manager.unregister(connection_id)

    assert connection_id not in manager.connection_ids()
    assert manager.username_for(connection_id) is None


def test_authenticate_maps_connection_to_username():
    manager = ConnectionManager()
    connection_id = manager.register(FakeConnection())
    assert manager.username_for(connection_id) is None

    manager.authenticate(connection_id, "alice")

    assert manager.username_for(connection_id) == "alice"


def test_send_to_unknown_connection_is_a_no_op():
    manager = ConnectionManager()
    _run(manager.send("no-such-id", "hello"))  # must not raise


def test_disconnect_hook_fires_on_unregister():
    manager = ConnectionManager()
    connection_id = manager.register(FakeConnection())
    seen = []
    manager.add_disconnect_hook(seen.append)

    manager.unregister(connection_id)

    assert seen == [connection_id]


def test_disconnect_hook_can_still_see_the_username():
    """The hook must fire before the username mapping is torn down --
    GameManager's disconnect handler needs to know who just left."""
    manager = ConnectionManager()
    connection_id = manager.register(FakeConnection())
    manager.authenticate(connection_id, "alice")
    seen_usernames = []
    manager.add_disconnect_hook(lambda cid: seen_usernames.append(manager.username_for(cid)))

    manager.unregister(connection_id)

    assert seen_usernames == ["alice"]


def test_multiple_disconnect_hooks_all_fire():
    manager = ConnectionManager()
    connection_id = manager.register(FakeConnection())
    calls = []
    manager.add_disconnect_hook(lambda cid: calls.append("first"))
    manager.add_disconnect_hook(lambda cid: calls.append("second"))

    manager.unregister(connection_id)

    assert calls == ["first", "second"]
