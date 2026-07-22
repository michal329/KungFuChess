"""``play`` command: rating-keyed matchmaking queue. Pressing Play
searches for an opponent within ±100 ELO; if none is currently
waiting, the caller joins the queue and gets one minute to find one
before being told none was found -- both figures from the
architecture doc's Matchmaking section.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Callable, List, Optional

from protocol.commands import PlayCommand
from server.connection_manager import ConnectionManager
from server.game_manager import GameManager
from server.messaging import send_error
from server.room_manager import RoomManager

DEFAULT_RATING_RANGE = 100
DEFAULT_TIMEOUT_SECONDS = 60.0


@dataclass
class _QueueEntry:
    connection_id: str
    username: str
    rating: int


class Matchmaker:
    def __init__(
        self,
        connection_manager: ConnectionManager,
        room_manager: RoomManager,
        game_manager: GameManager,
        rating_lookup: Callable[[str], int],
        rating_range: int = DEFAULT_RATING_RANGE,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._connection_manager = connection_manager
        self._room_manager = room_manager
        self._game_manager = game_manager
        self._rating_lookup = rating_lookup
        self._rating_range = rating_range
        self._timeout_seconds = timeout_seconds
        self._queue: List[_QueueEntry] = []

    def queue_size(self) -> int:
        return len(self._queue)

    async def handle_play(self, connection_id: str, command: PlayCommand) -> None:
        username = self._connection_manager.username_for(connection_id)
        if username is None:
            await send_error(self._connection_manager.send, connection_id, "log in before matchmaking")
            return

        rating = self._rating_lookup(username)
        opponent = self._find_opponent(rating)
        if opponent is None:
            entry = _QueueEntry(connection_id=connection_id, username=username, rating=rating)
            self._queue.append(entry)
            asyncio.create_task(self._expire_after_timeout(entry))
            return

        self._queue.remove(opponent)
        await self._start_match(opponent, _QueueEntry(connection_id=connection_id, username=username, rating=rating))

    def _find_opponent(self, rating: int) -> Optional[_QueueEntry]:
        for entry in self._queue:
            if abs(entry.rating - rating) <= self._rating_range:
                return entry
        return None

    async def _expire_after_timeout(self, entry: _QueueEntry) -> None:
        await asyncio.sleep(self._timeout_seconds)
        if entry in self._queue:
            self._queue.remove(entry)
            await send_error(self._connection_manager.send, entry.connection_id, "no opponent found")

    async def _start_match(self, entry_a: _QueueEntry, entry_b: _QueueEntry) -> None:
        room = self._room_manager.create_room()
        self._room_manager.join_room(room.room_id, entry_a.connection_id)
        self._room_manager.join_room(room.room_id, entry_b.connection_id)
        await self._game_manager.start_game(room, [entry_a.connection_id, entry_b.connection_id])
