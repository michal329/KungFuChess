"""Broadcaster: a Bus subscriber (epic 2.4) that pushes every message
published on the bus out over the websocket connections it knows about
(epic 3). ``Bus.publish`` is synchronous -- it's called straight out
of ``GameEngine.tick()``/``attempt_move()`` via ``GameEventBridge`` --
so this schedules the actual (async) send as a task on the currently
running event loop rather than awaiting it inline.

Room-aware by default: every message published through
``GameEventBridge`` (§4.12) is tagged ``"game.<room_id>"`` (see
``server/event_bridge.py``), so this resolves that room_id via
``RoomManager`` and sends only to that room's White/Black/spectators --
players in one room no longer see another room's moves. If
*room_manager* isn't given, or a topic doesn't start with ``"game."``,
this falls back to the old broadcast-to-everyone behavior.
"""
from __future__ import annotations

import asyncio
from typing import List, Optional

import websockets.exceptions

from protocol.serialization import encode_message
from server.connection_manager import ConnectionManager
from server.room_manager import RoomManager

_GAME_TOPIC_PREFIX = "game."


class Broadcaster:
    def __init__(self, connection_manager: ConnectionManager, room_manager: Optional[RoomManager] = None) -> None:
        self._connection_manager = connection_manager
        self._room_manager = room_manager

    def __call__(self, topic: str, message: object) -> None:
        raw = encode_message(message)
        asyncio.create_task(self._safe_broadcast(topic, raw))

    def _recipients_for(self, topic: str) -> List[str]:
        if self._room_manager is not None and topic.startswith(_GAME_TOPIC_PREFIX):
            room_id = topic[len(_GAME_TOPIC_PREFIX):]
            room = self._room_manager.get(room_id)
            if room is None:
                return []
            return [connection_id for connection_id in (room.white, room.black, *room.spectators) if connection_id is not None]
        return self._connection_manager.connection_ids()

    async def _safe_broadcast(self, topic: str, raw: str) -> None:
        try:
            for connection_id in self._recipients_for(topic):
                await self._connection_manager.send(connection_id, raw)
        except websockets.exceptions.ConnectionClosed:
            # A client disconnected between the moment this task was
            # scheduled and its turn to actually send -- nothing to do.
            pass
