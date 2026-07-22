"""Rooms: manual create/join, independent of matchmaking (epic 6) and
of whether a game has actually started for a room (epic 7's
``GameManager`` decides that separately -- a ``Room`` here has no
notion of a game_id at all, on purpose, so this module stays ignorant
of ``GameEngine``/``GameState`` entirely).

Seat assignment follows the architecture doc's rule literally: first
player to join is White, second is Black, everyone after that is a
spectator.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional


class RoomNotFoundError(KeyError):
    def __init__(self, room_id: str) -> None:
        super().__init__(f"no such room: {room_id!r}")


@dataclass
class Room:
    room_id: str
    white: Optional[str] = None
    black: Optional[str] = None
    spectators: List[str] = field(default_factory=list)

    def has(self, connection_id: str) -> bool:
        return connection_id in (self.white, self.black) or connection_id in self.spectators


class RoomManager:
    def __init__(self) -> None:
        self._rooms: Dict[str, Room] = {}

    def create_room(self) -> Room:
        room_id = uuid.uuid4().hex[:8]
        room = Room(room_id=room_id)
        self._rooms[room_id] = room
        return room

    def get(self, room_id: str) -> Optional[Room]:
        return self._rooms.get(room_id)

    def join_room(self, room_id: str, connection_id: str) -> Room:
        room = self._rooms.get(room_id)
        if room is None:
            raise RoomNotFoundError(room_id)

        if room.has(connection_id):
            return room  # already seated -- joining again is a no-op, not a re-seat

        if room.white is None:
            room.white = connection_id
        elif room.black is None:
            room.black = connection_id
        else:
            room.spectators.append(connection_id)
        return room

    def room_for_connection(self, connection_id: str) -> Optional[Room]:
        for room in self._rooms.values():
            if room.has(connection_id):
                return room
        return None

    def leave(self, connection_id: str) -> Optional[Room]:
        room = self.room_for_connection(connection_id)
        if room is None:
            return None
        if room.white == connection_id:
            room.white = None
        elif room.black == connection_id:
            room.black = None
        else:
            room.spectators.remove(connection_id)
        return room
