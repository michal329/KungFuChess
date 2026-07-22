import asyncio
import json

from protocol.commands import MoveCommand, PlayCommand
from protocol.messages import ErrorMessage
from protocol.serialization import decode_message, encode_command
from server.command_router import CommandRouter


def _run(coro):
    return asyncio.run(coro)


def test_dispatch_routes_to_registered_handler():
    sent = []

    async def fake_send(connection_id, raw):
        sent.append((connection_id, raw))

    router = CommandRouter(send=fake_send)
    received = []

    async def on_move(connection_id, command):
        received.append((connection_id, command))

    router.register("move", on_move)

    cmd = MoveCommand(from_={"row": 0, "col": 0}, to={"row": 1, "col": 1})
    _run(router.dispatch("conn-1", encode_command(cmd)))

    assert received == [("conn-1", cmd)]
    assert sent == []


def test_dispatch_unknown_command_sends_error():
    sent = []

    async def fake_send(connection_id, raw):
        sent.append((connection_id, raw))

    router = CommandRouter(send=fake_send)

    _run(router.dispatch("conn-1", json.dumps({"command": "teleport"})))

    assert len(sent) == 1
    connection_id, raw = sent[0]
    assert connection_id == "conn-1"
    assert isinstance(decode_message(raw), ErrorMessage)


def test_dispatch_no_handler_registered_sends_error():
    sent = []

    async def fake_send(connection_id, raw):
        sent.append((connection_id, raw))

    router = CommandRouter(send=fake_send)
    _run(router.dispatch("conn-1", encode_command(PlayCommand())))

    assert len(sent) == 1
    assert isinstance(decode_message(sent[0][1]), ErrorMessage)


def test_dispatch_malformed_json_sends_error():
    sent = []

    async def fake_send(connection_id, raw):
        sent.append((connection_id, raw))

    router = CommandRouter(send=fake_send)
    _run(router.dispatch("conn-1", "not json"))

    assert len(sent) == 1
    assert isinstance(decode_message(sent[0][1]), ErrorMessage)
