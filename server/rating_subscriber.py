"""RatingUpdateSubscriber: a Bus subscriber (epic 2's pattern) that
reacts to a game actually ending, computes both players' new ELO
rating, persists it, and sends each an updated ``RatingMessage`` --
epic 8, the last piece of "the server decides which game instance
should receive the request... [and] rating calculations" from the
architecture doc.

``Bus.publish`` is synchronous (called from `GameEngine` via
`GameEventBridge`), but persisting to SQLite and sending over a
websocket both need to happen from async code, so this follows the
same "schedule a task" bridge `server/broadcaster.py` already
established.
"""
from __future__ import annotations

import asyncio

from protocol.messages import GameEndedMessage, RatingMessage
from protocol.serialization import encode_message
from server.auth import UserStore
from server.connection_manager import ConnectionManager
from server.rating import compute_new_ratings
from server.room_manager import RoomManager

_GAME_TOPIC_PREFIX = "game."


class RatingUpdateSubscriber:
    def __init__(self, connection_manager: ConnectionManager, room_manager: RoomManager, user_store: UserStore) -> None:
        self._connection_manager = connection_manager
        self._room_manager = room_manager
        self._user_store = user_store

    def __call__(self, topic: str, message: object) -> None:
        if not isinstance(message, GameEndedMessage) or not topic.startswith(_GAME_TOPIC_PREFIX):
            return
        room_id = topic[len(_GAME_TOPIC_PREFIX):]
        asyncio.create_task(self._apply(room_id, message.winner))

    async def _apply(self, room_id: str, winner) -> None:
        room = self._room_manager.get(room_id)
        if room is None or room.white is None or room.black is None:
            return  # a room that never got a real opponent (or was cleaned up) has no one to rate

        white_username = self._connection_manager.username_for(room.white)
        black_username = self._connection_manager.username_for(room.black)
        if white_username is None or black_username is None:
            return  # an unauthenticated seat shouldn't happen, but nothing to rate if it did

        white_rating = self._user_store.rating_for(white_username)
        black_rating = self._user_store.rating_for(black_username)
        new_white, new_black = compute_new_ratings(white_rating, black_rating, winner)

        white_outcome = "draw" if winner is None else ("win" if winner == "W" else "loss")
        black_outcome = "draw" if winner is None else ("win" if winner == "B" else "loss")
        self._user_store.record_game_result(white_username, new_white, white_outcome)
        self._user_store.record_game_result(black_username, new_black, black_outcome)

        await self._connection_manager.send(room.white, encode_message(
            RatingMessage(username=white_username, rating=new_white)
        ))
        await self._connection_manager.send(room.black, encode_message(
            RatingMessage(username=black_username, rating=new_black)
        ))
