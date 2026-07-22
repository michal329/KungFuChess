"""The client's Application Layer (epic 3.3): sends commands, receives
messages, over one persistent websocket connection. Deliberately
generic and rule-blind -- it never inspects a command/message beyond
what's needed to (de)serialize it (see architecture doc section 6:
"the client should only receive user input, send commands, display
received information -- it should not validate game rules").

Not yet wired into ``kfchess.gui``/``kfchess.input`` -- that migration
(``ClickController`` sending commands here instead of calling
``GameEngine`` directly) is a later epic.
"""
from __future__ import annotations

import websockets

from protocol.commands import Command
from protocol.messages import Message
from protocol.serialization import decode_message, encode_command


class WebSocketClient:
    def __init__(self, uri: str) -> None:
        self._uri = uri
        self._connection = None

    async def connect(self) -> None:
        self._connection = await websockets.connect(self._uri)

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    async def send_command(self, command: Command) -> None:
        await self._connection.send(encode_command(command))

    async def receive_message(self) -> Message:
        raw = await self._connection.recv()
        return decode_message(raw)

    async def __aenter__(self) -> "WebSocketClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()
