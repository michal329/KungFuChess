"""A tiny shared helper: every command handler module (auth, room
manager, matchmaking, game manager) needs to turn "something went
wrong" into an ``ErrorMessage`` sent back to whoever asked. Kept here,
once, instead of every module re-implementing
``send(connection_id, encode_message(ErrorMessage(...)))`` -- and, since
every error a client ever sees passes through this one function, it's
also the one place errors need to be logged from.
"""
from __future__ import annotations

import logging
from typing import Awaitable, Callable

from protocol.messages import ErrorMessage
from protocol.serialization import encode_message

logger = logging.getLogger(__name__)

Send = Callable[[str, str], Awaitable[None]]


async def send_error(send: Send, connection_id: str, reason: str) -> None:
    logger.warning("error: connection=%s reason=%s", connection_id, reason)
    await send(connection_id, encode_message(ErrorMessage(reason=reason)))
