"""First Bus subscribers (epic 2.4): logging and an in-memory move
log. Both are plain callables matching ``server.bus.Subscriber``
(``(topic, message) -> None``), registered via ``Bus.subscribe``.

``MoveLogSubscriber`` is an in-memory stand-in -- real persistence
(SQLite) is a later epic (auth/rooms/ratings storage); this class only
exists so the Bus already has a working, testable move-log consumer
today, matching the shape the real one will have.

``LoggingSubscriber`` covers every message that already flows through
the Bus (moves, jumps, timers, game-end -- see
``server/event_bridge.py``) for free, just by subscribing to the
wildcard topic. The administrative events the architecture doc also
wants logged (login, room created, game started, disconnect, reconnect,
errors) never touch the Bus -- they're sent point-to-point -- so they're
logged directly at their own call sites instead (``server/auth.py``,
``server/app.py``, ``server/game_manager.py``, ``server/messaging.py``);
see EXPLANATION.md's Logging section for the full list.
"""
from __future__ import annotations

import logging
from typing import List

from protocol.messages import MoveEventMessage

logger = logging.getLogger(__name__)


class LoggingSubscriber:
    """Subscribe to ``server.bus.WILDCARD_TOPIC`` to log every message
    published on any topic, at INFO level."""

    def __init__(self, logger: logging.Logger = logger) -> None:
        self._logger = logger

    def __call__(self, topic: str, message: object) -> None:
        self._logger.info("[%s] %r", topic, message)


class MoveLogSubscriber:
    def __init__(self) -> None:
        self._moves: List[MoveEventMessage] = []

    def __call__(self, topic: str, message: object) -> None:
        if isinstance(message, MoveEventMessage):
            self._moves.append(message)

    def moves(self) -> List[MoveEventMessage]:
        return list(self._moves)
