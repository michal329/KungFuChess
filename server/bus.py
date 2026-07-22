"""A minimal Pub/Sub bus: topic -> subscriber callables. Lives in
``server``, never in ``kfchess`` -- see CLAUDE.md-equivalent guidance
in the architecture doc ("Where does Pub/Sub belong? The Bus belongs
to the Server layer, not inside the Game Logic").

Deliberately synchronous and in-process: ``publish`` calls every
matching subscriber inline, in subscription order. A subscriber that
needs to reach an async context (e.g. pushing over a websocket) is
responsible for bridging that itself (see ``server.broadcaster``).
"""
from __future__ import annotations

from collections import defaultdict
from typing import Callable, DefaultDict, List

Subscriber = Callable[[str, object], None]

WILDCARD_TOPIC = "*"


class Bus:
    def __init__(self) -> None:
        self._subscribers: DefaultDict[str, List[Subscriber]] = defaultdict(list)

    def subscribe(self, topic: str, subscriber: Subscriber) -> None:
        """*topic* may be a concrete topic (e.g. ``"game.42"``) or
        ``WILDCARD_TOPIC`` to receive every message published on any
        topic -- used by cross-cutting subscribers like logging."""
        self._subscribers[topic].append(subscriber)

    def publish(self, topic: str, message: object) -> None:
        for subscriber in self._subscribers.get(topic, ()):
            subscriber(topic, message)
        if topic != WILDCARD_TOPIC:
            for subscriber in self._subscribers.get(WILDCARD_TOPIC, ()):
                subscriber(topic, message)
