"""Owns one ``GameEngine`` + one ``GameState`` per active room. This is
epic 7's whole point: nothing inside ``kfchess/engine`` had to change
to support "many simultaneous games" -- ``GameEngine`` already holds no
per-game state on ``self`` (CLAUDE.md rule 2 / EXPLANATION.md §5.4),
so a server-side manager driving N independent ``(engine, state)``
pairs is exactly what that design was for.

A room's ``room_id`` doubles as the game's correlator id for
``GameEventBridge`` -- there's a 1:1 relationship between a room and
its game in this scope, so no separate id-generation is needed.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from kfchess.engine.game_engine import (
    COOLDOWN_DURATION_MS,
    JUMP_DURATION_MS,
    MOVE_DURATION_MS,
    GameEngine,
)
from kfchess.engine.game_state import GameState
from kfchess.io.snapshot import dict_to_position, game_state_snapshot
from kfchess.io.standard_position import build_standard_board
from kfchess.model.piece import BLACK, WHITE
from protocol.commands import MoveCommand, ResignCommand
from protocol.messages import GameStartedMessage, SnapshotMessage
from protocol.serialization import encode_message
from server.bus import Bus
from server.connection_manager import ConnectionManager
from server.event_bridge import GameEventBridge
from server.messaging import send_error
from server.room_manager import Room, RoomManager

logger = logging.getLogger(__name__)

DEFAULT_TICK_INTERVAL_SECONDS = 0.05
DEFAULT_RECONNECT_TIMEOUT_SECONDS = 20.0
SPECTATOR = "spectator"


@dataclass
class _ActiveGame:
    engine: GameEngine
    state: GameState


@dataclass
class _PendingDisconnect:
    room_id: str
    old_connection_id: str
    color: str
    timeout_task: "asyncio.Task"


class GameManager:
    def __init__(
        self,
        bus: Bus,
        connection_manager: ConnectionManager,
        room_manager: RoomManager,
        tick_interval_seconds: float = DEFAULT_TICK_INTERVAL_SECONDS,
        move_duration: Optional[int] = None,
        jump_duration: Optional[int] = None,
        cooldown_duration: Optional[int] = None,
        reconnect_timeout_seconds: float = DEFAULT_RECONNECT_TIMEOUT_SECONDS,
    ) -> None:
        self._bus = bus
        self._connection_manager = connection_manager
        self._room_manager = room_manager
        self._tick_interval_seconds = tick_interval_seconds
        self._reconnect_timeout_seconds = reconnect_timeout_seconds
        self._engine_kwargs = {
            key: value
            for key, value in (
                ("move_duration", move_duration),
                ("jump_duration", jump_duration),
                ("cooldown_duration", cooldown_duration),
            )
            if value is not None
        }
        self._games: Dict[str, _ActiveGame] = {}
        self._tick_tasks: Dict[str, "asyncio.Task"] = {}
        self._pending_disconnects: Dict[str, _PendingDisconnect] = {}

    def has_game(self, room_id: str) -> bool:
        return room_id in self._games

    async def start_game(self, room: Room, player_connection_ids: List[str]) -> str:
        game_id = room.room_id
        board = build_standard_board()
        engine = GameEngine(board, **self._engine_kwargs)
        state = GameState(board=board)
        engine.add_observer(GameEventBridge(self._bus, game_id=game_id))
        self._games[game_id] = _ActiveGame(engine=engine, state=state)
        logger.info("game started: room_id=%s white=%s black=%s", game_id, room.white, room.black)

        color_by_connection = {room.white: WHITE, room.black: BLACK}
        for connection_id in player_connection_ids:
            color = color_by_connection.get(connection_id, SPECTATOR)
            await self._connection_manager.send(connection_id, encode_message(
                self._game_started_message(game_id, color)
            ))
            await self._send_snapshot(connection_id, state)

        self._tick_tasks[game_id] = asyncio.create_task(self._run_ticks(game_id))
        return game_id

    def _game_started_message(self, room_id: str, color: str) -> GameStartedMessage:
        return GameStartedMessage(
            room_id=room_id, color=color,
            move_duration=self._engine_kwargs.get("move_duration", MOVE_DURATION_MS),
            jump_duration=self._engine_kwargs.get("jump_duration", JUMP_DURATION_MS),
            cooldown_duration=self._engine_kwargs.get("cooldown_duration", COOLDOWN_DURATION_MS),
        )

    async def send_snapshot(self, room_id: str, connection_id: str) -> None:
        """Used when someone (a spectator, a player rejoining) joins a
        room whose game is already in progress -- the one full
        reconciliation point so they can't be missing anything the
        events they'll receive from here on assume they already saw."""
        active = self._games.get(room_id)
        if active is not None:
            await self._send_snapshot(connection_id, active.state)

    async def _send_snapshot(self, connection_id: str, state: GameState) -> None:
        await self._connection_manager.send(connection_id, encode_message(
            SnapshotMessage(payload=game_state_snapshot(state))
        ))

    async def handle_move(self, connection_id: str, command: MoveCommand) -> None:
        room = self._room_manager.room_for_connection(connection_id)
        if room is None:
            await send_error(self._connection_manager.send, connection_id, "you are not in a room")
            return

        active = self._games.get(room.room_id)
        if active is None:
            await send_error(self._connection_manager.send, connection_id, "the game hasn't started yet")
            return

        if room.white == connection_id:
            color = WHITE
        elif room.black == connection_id:
            color = BLACK
        else:
            await send_error(self._connection_manager.send, connection_id, "spectators cannot move pieces")
            return

        from_pos = dict_to_position(command.from_)
        to_pos = dict_to_position(command.to)
        piece = active.state.board.get(from_pos)
        if piece is None or piece.color != color:
            await send_error(self._connection_manager.send, connection_id, "you can only move your own pieces")
            return

        if from_pos == to_pos:
            active.engine.attempt_jump(active.state, from_pos)
        else:
            active.engine.attempt_move(active.state, from_pos, to_pos)

    async def handle_resign(self, connection_id: str, command: ResignCommand) -> None:
        room = self._room_manager.room_for_connection(connection_id)
        if room is None:
            await send_error(self._connection_manager.send, connection_id, "you are not in a room")
            return

        active = self._games.get(room.room_id)
        if active is None:
            await send_error(self._connection_manager.send, connection_id, "the game hasn't started yet")
            return

        if room.white == connection_id:
            color = WHITE
        elif room.black == connection_id:
            color = BLACK
        else:
            await send_error(self._connection_manager.send, connection_id, "spectators cannot resign")
            return

        active.engine.resign(active.state, color)

    def handle_disconnect(self, connection_id: str) -> None:
        """Registered as a ``ConnectionManager`` disconnect hook (see
        ``ServerApp``). Spectators and connections not seated in any
        room's game are ignored entirely -- only a player mid-game
        starts the 20-second countdown the architecture doc's Player
        Disconnect section describes."""
        room = self._room_manager.room_for_connection(connection_id)
        if room is None:
            return
        active = self._games.get(room.room_id)
        if active is None or active.state.game_over:
            return

        if room.white == connection_id:
            color = WHITE
        elif room.black == connection_id:
            color = BLACK
        else:
            return  # a spectator disconnecting needs no grace period

        username = self._connection_manager.username_for(connection_id)
        if username is None:
            return

        logger.info(
            "disconnect: username=%s connection=%s room_id=%s (%.0fs to reconnect)",
            username, connection_id, room.room_id, self._reconnect_timeout_seconds,
        )
        task = asyncio.create_task(self._auto_resign_after_timeout(username))
        self._pending_disconnects[username] = _PendingDisconnect(
            room_id=room.room_id, old_connection_id=connection_id, color=color, timeout_task=task,
        )

    async def _auto_resign_after_timeout(self, username: str) -> None:
        try:
            await asyncio.sleep(self._reconnect_timeout_seconds)
        except asyncio.CancelledError:
            return  # reconnected in time -- attempt_reconnect already cancelled us

        pending = self._pending_disconnects.pop(username, None)
        if pending is None:
            return
        active = self._games.get(pending.room_id)
        if active is None:
            return
        logger.info("auto-resign: username=%s room_id=%s never reconnected", username, pending.room_id)
        active.engine.resign(active.state, pending.color)

    async def attempt_reconnect(self, username: str, new_connection_id: str) -> bool:
        """Called after a successful login (see ``ServerApp``): if
        *username* had an in-progress game with a pending disconnect
        timer, re-seat it under *new_connection_id*, cancel the timer,
        and resend it the game-started message and a fresh snapshot so
        it can pick up exactly where it left off. Returns whether a
        reconnect actually happened."""
        pending = self._pending_disconnects.pop(username, None)
        if pending is None:
            return False

        pending.timeout_task.cancel()
        room = self._room_manager.get(pending.room_id)
        active = self._games.get(pending.room_id)
        if room is None or active is None or active.state.game_over:
            return False

        if room.white == pending.old_connection_id:
            room.white = new_connection_id
        elif room.black == pending.old_connection_id:
            room.black = new_connection_id
        else:
            return False

        logger.info("reconnect: username=%s room_id=%s connection=%s", username, pending.room_id, new_connection_id)
        await self._connection_manager.send(new_connection_id, encode_message(
            self._game_started_message(pending.room_id, pending.color)
        ))
        await self._send_snapshot(new_connection_id, active.state)
        return True

    async def _run_ticks(self, game_id: str) -> None:
        interval_ms = int(self._tick_interval_seconds * 1000)
        try:
            while True:
                await asyncio.sleep(self._tick_interval_seconds)
                active = self._games.get(game_id)
                if active is None or active.state.game_over:
                    return
                active.engine.tick(active.state, interval_ms)
        except asyncio.CancelledError:
            pass

    def stop_game(self, game_id: str) -> None:
        task = self._tick_tasks.pop(game_id, None)
        if task is not None:
            task.cancel()
        self._games.pop(game_id, None)
        for username, pending in list(self._pending_disconnects.items()):
            if pending.room_id == game_id:
                pending.timeout_task.cancel()
                del self._pending_disconnects[username]

    def stop_all(self) -> None:
        for game_id in list(self._games.keys()):
            self.stop_game(game_id)
