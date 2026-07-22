"""Tracks live websocket connections and, once a client logs in, which
username owns which connection. Room/game membership itself lives in
``RoomManager``; ``server.broadcaster.Broadcaster`` asks that for who
should receive a given room's messages instead of this class knowing
about rooms at all.
"""
from __future__ import annotations

import asyncio
import itertools
from typing import Callable, Dict, List, Optional, Protocol


class SendableConnection(Protocol):
    async def send(self, message: str) -> None:
        ...


DisconnectHook = Callable[[str], None]


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: Dict[str, SendableConnection] = {}
        self._usernames: Dict[str, str] = {}
        self._send_locks: Dict[str, asyncio.Lock] = {}
        self._disconnect_hooks: List[DisconnectHook] = []
        self._ids = itertools.count(1)

    def register(self, connection: SendableConnection) -> str:
        connection_id = f"conn-{next(self._ids)}"
        self._connections[connection_id] = connection
        self._send_locks[connection_id] = asyncio.Lock()
        return connection_id

    def add_disconnect_hook(self, hook: DisconnectHook) -> None:
        """*hook* is called, synchronously, with a connection_id right
        after it's unregistered -- epic 9's way for ``GameManager`` to
        learn a player dropped without ``ConnectionManager`` needing to
        know anything about games. A hook that needs to do async work
        (it will -- a disconnect starts a timed wait) schedules its own
        task; this method itself stays synchronous, matching
        ``unregister``'s own signature."""
        self._disconnect_hooks.append(hook)

    def unregister(self, connection_id: str) -> None:
        # Hooks run first, while username_for(connection_id) can still
        # answer -- a hook (GameManager's, in particular) needs to know
        # who just disconnected.
        for hook in self._disconnect_hooks:
            hook(connection_id)
        self._connections.pop(connection_id, None)
        self._usernames.pop(connection_id, None)
        self._send_locks.pop(connection_id, None)

    def authenticate(self, connection_id: str, username: str) -> None:
        self._usernames[connection_id] = username

    def username_for(self, connection_id: str) -> Optional[str]:
        return self._usernames.get(connection_id)

    def connection_ids(self) -> List[str]:
        return list(self._connections.keys())

    async def send(self, connection_id: str, raw: str) -> None:
        """Serialized per connection: the Bus can publish several
        messages back-to-back (e.g. every tick), and ``Broadcaster``
        fires each one off as its own task rather than awaiting it
        inline (see ``server/broadcaster.py``) -- without a per-
        connection lock, two of those tasks could end up calling the
        same underlying websocket's ``send`` concurrently, which the
        ``websockets`` library does not support."""
        connection = self._connections.get(connection_id)
        lock = self._send_locks.get(connection_id)
        if connection is None or lock is None:
            return
        async with lock:
            # Re-check after acquiring the lock: unregister() may have
            # run while we were waiting for it.
            if connection_id not in self._connections:
                return
            await connection.send(raw)

    async def broadcast(self, raw: str) -> None:
        for connection_id in self.connection_ids():
            await self.send(connection_id, raw)
