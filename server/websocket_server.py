"""The persistent-connection server skeleton (architecture doc section
7/8/10): accepts websocket connections, hands each one a connection id
via ``ConnectionManager``, and forwards every inbound frame to a
``CommandRouter``. Owns none of the actual game/auth/room behavior --
just the socket lifecycle.
"""
from __future__ import annotations

from typing import Optional

import websockets

from server.command_router import CommandRouter
from server.connection_manager import ConnectionManager


class WebSocketServer:
    def __init__(
        self,
        connection_manager: ConnectionManager,
        command_router: CommandRouter,
        host: str = "localhost",
        port: int = 8765,
    ) -> None:
        self._connection_manager = connection_manager
        self._command_router = command_router
        self._host = host
        self._port = port
        self._server: Optional[object] = None  # websockets.asyncio.server.Server once started

    async def _handle_connection(self, websocket) -> None:
        connection_id = self._connection_manager.register(websocket)
        try:
            async for raw in websocket:
                await self._command_router.dispatch(connection_id, raw)
        finally:
            self._connection_manager.unregister(connection_id)

    async def start(self):
        self._server = await websockets.serve(self._handle_connection, self._host, self._port)
        return self._server

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def serve_forever(self) -> None:
        """Entry point for a real deployment: run until cancelled."""
        import asyncio

        await self.start()
        await asyncio.Future()
