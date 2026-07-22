"""User accounts (SQLite) and the ``login`` command's phased rollout:
username-only at first, username+password once a user actually sets
one -- see the architecture doc's "Login" section. Credentials never
leave this module as plaintext except long enough to hash/verify them;
storage is always a salted PBKDF2 digest, never the password itself.

"Session" (epic 4.4) is deliberately not a separate token: a login just
calls ``ConnectionManager.authenticate(connection_id, username)``
(already built in epic 3) -- the connection *is* the session for as
long as the socket stays open. Reconnecting with a stored token to
resume a dropped session is a later epic (disconnect/reconnect
handling), not this one.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import sqlite3
from dataclasses import dataclass
from typing import Optional

from protocol.commands import LoginCommand
from protocol.messages import RatingMessage
from protocol.serialization import encode_message
from server.connection_manager import ConnectionManager
from server.messaging import send_error

logger = logging.getLogger(__name__)

DEFAULT_RATING = 1200
_PBKDF2_ITERATIONS = 200_000
_HASH_NAME = "sha256"


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(_HASH_NAME, password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    salt_hex, _, digest_hex = stored.partition("$")
    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(digest_hex)
    actual = hashlib.pbkdf2_hmac(_HASH_NAME, password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return hmac.compare_digest(actual, expected)


@dataclass(frozen=True)
class UserRecord:
    username: str
    password_hash: Optional[str]
    rating: int
    wins: int
    losses: int
    draws: int


class UserStore:
    """SQLite-backed user accounts. The database stores records, not
    game objects -- it is a storage service, not part of the Model
    layer (see the architecture doc's point on this)."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self) -> None:
        self._conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT,
                rating INTEGER NOT NULL DEFAULT {DEFAULT_RATING},
                wins INTEGER NOT NULL DEFAULT 0,
                losses INTEGER NOT NULL DEFAULT 0,
                draws INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        self._conn.commit()

    def get(self, username: str) -> Optional[UserRecord]:
        row = self._conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return self._row_to_record(row) if row is not None else None

    def create(self, username: str, password: Optional[str] = None) -> UserRecord:
        password_hash = hash_password(password) if password is not None else None
        self._conn.execute(
            "INSERT INTO users (username, password_hash, rating) VALUES (?, ?, ?)",
            (username, password_hash, DEFAULT_RATING),
        )
        self._conn.commit()
        return self.get(username)

    def set_password(self, username: str, password: str) -> None:
        self._conn.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (hash_password(password), username),
        )
        self._conn.commit()

    def rating_for(self, username: str) -> int:
        user = self.get(username)
        return user.rating if user is not None else DEFAULT_RATING

    def record_game_result(self, username: str, new_rating: int, outcome: str) -> None:
        """*outcome* is ``"win"``, ``"loss"``, or ``"draw"`` -- picks
        which counter to bump alongside the rating update. The column
        name comes from this fixed dict, never from *outcome* directly,
        so there's no SQL-injection surface despite the f-string
        (column names can't be bound as placeholder parameters)."""
        column = {"win": "wins", "loss": "losses", "draw": "draws"}[outcome]
        self._conn.execute(
            f"UPDATE users SET rating = ?, {column} = {column} + 1 WHERE username = ?",
            (new_rating, username),
        )
        self._conn.commit()

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> UserRecord:
        return UserRecord(
            username=row["username"],
            password_hash=row["password_hash"],
            rating=row["rating"],
            wins=row["wins"],
            losses=row["losses"],
            draws=row["draws"],
        )


class AuthService:
    def __init__(self, user_store: UserStore, connection_manager: ConnectionManager) -> None:
        self._user_store = user_store
        self._connection_manager = connection_manager

    async def handle_login(self, connection_id: str, command: LoginCommand) -> None:
        user = self._user_store.get(command.username)

        if user is None:
            # Brand new username: phase 1 behavior -- register it, with
            # a password only if one was actually supplied.
            user = self._user_store.create(command.username, password=command.password)
        elif user.password_hash is not None:
            # This username already has a password: phase 2 behavior --
            # it's now required and must match.
            if command.password is None or not verify_password(command.password, user.password_hash):
                logger.warning("login failed: username=%s connection=%s", command.username, connection_id)
                await send_error(self._connection_manager.send, connection_id, "invalid username or password")
                return
        elif command.password is not None:
            # No password set yet on this account, and the client supplied
            # one now: this login claims the username with that password
            # going forward.
            self._user_store.set_password(command.username, command.password)
            user = self._user_store.get(command.username)

        self._connection_manager.authenticate(connection_id, command.username)
        logger.info("login: username=%s connection=%s rating=%d", command.username, connection_id, user.rating)
        await self._connection_manager.send(connection_id, encode_message(
            RatingMessage(username=command.username, rating=user.rating)
        ))
