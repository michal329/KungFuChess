"""Dispatches an incoming raw JSON command to whichever handler is
registered for its ``command`` field. Handlers themselves (login,
move, create_room, ...) belong to the epics that own that behavior
(auth, game manager, room manager, ...); this module only owns the
dispatch mechanism, decoupled from ``ConnectionManager`` behind a bare
``send(connection_id, raw) -> Awaitable[None]`` callable so it's
testable without a real websocket.
"""
from __future__ import annotations

from typing import Awaitable, Callable, Dict

from protocol.commands import Command
from protocol.serialization import decode_command
from server.messaging import send_error

Send = Callable[[str, str], Awaitable[None]]
Handler = Callable[[str, Command], Awaitable[None]]


class CommandRouter:
    def __init__(self, send: Send) -> None:
        self._handlers: Dict[str, Handler] = {}
        self._send = send

    def register(self, command_name: str, handler: Handler) -> None:
        self._handlers[command_name] = handler

    async def dispatch(self, connection_id: str, raw: str) -> None:
        try:
            command = decode_command(raw)
        except ValueError as exc:
            # Covers both protocol.serialization.ProtocolError (unknown
            # command / missing field) and json.JSONDecodeError, which
            # is itself a ValueError subclass -- malformed input either
            # way just becomes an ErrorMessage back to the sender.
            await send_error(self._send, connection_id, str(exc))
            return

        handler = self._handlers.get(command.command)
        if handler is None:
            await send_error(self._send, connection_id, f"no handler registered for command: {command.command!r}")
            return
        await handler(connection_id, command)
