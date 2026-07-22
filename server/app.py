"""ServerApp: the server's composition root -- the one place that
constructs the Bus, ConnectionManager, UserStore/AuthService,
RoomManager, GameManager, Matchmaker, CommandRouter and
WebSocketServer and wires them together (see EXPLANATION.md §5.5) --
everywhere else in ``server/`` depends on interfaces/collaborators
handed to it from outside, never constructs its own.

The one piece of cross-cutting policy that doesn't belong to any
single manager -- "once both seats in a manually-created room are
filled, start the game" -- lives here rather than inside
``RoomManager`` (which has no idea games exist) or ``GameManager``
(which has no idea how rooms get filled).
"""
from __future__ import annotations

import logging
from typing import Optional

from protocol.commands import CreateRoomCommand, JoinRoomCommand, LeaveRoomCommand, LoginCommand, ResignCommand
from protocol.messages import RoomCreatedMessage
from protocol.serialization import encode_message
from server.auth import AuthService, UserStore
from server.broadcaster import Broadcaster
from server.bus import Bus, WILDCARD_TOPIC
from server.command_router import CommandRouter
from server.connection_manager import ConnectionManager
from server.game_manager import GameManager
from server.matchmaking import Matchmaker
from server.messaging import send_error
from server.rating_subscriber import RatingUpdateSubscriber
from server.room_manager import RoomManager, RoomNotFoundError
from server.subscribers import LoggingSubscriber, MoveLogSubscriber
from server.websocket_server import WebSocketServer

logger = logging.getLogger(__name__)


class ServerApp:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8765,
        db_path: str = ":memory:",
        tick_interval_seconds: float = 0.05,
        move_duration: Optional[int] = None,
        jump_duration: Optional[int] = None,
        cooldown_duration: Optional[int] = None,
        reconnect_timeout_seconds: float = 20.0,
    ) -> None:
        self.bus = Bus()
        self.connection_manager = ConnectionManager()
        self.user_store = UserStore(db_path=db_path)
        self.auth_service = AuthService(self.user_store, self.connection_manager)
        self.room_manager = RoomManager()
        self.game_manager = GameManager(
            self.bus, self.connection_manager, self.room_manager,
            tick_interval_seconds=tick_interval_seconds,
            move_duration=move_duration, jump_duration=jump_duration, cooldown_duration=cooldown_duration,
            reconnect_timeout_seconds=reconnect_timeout_seconds,
        )
        self.connection_manager.add_disconnect_hook(self.game_manager.handle_disconnect)
        self.matchmaker = Matchmaker(
            self.connection_manager, self.room_manager, self.game_manager,
            rating_lookup=self.user_store.rating_for,
        )

        self.logging_subscriber = LoggingSubscriber()
        self.move_log = MoveLogSubscriber()
        self.rating_updater = RatingUpdateSubscriber(self.connection_manager, self.room_manager, self.user_store)
        self.bus.subscribe(WILDCARD_TOPIC, self.logging_subscriber)
        self.bus.subscribe(WILDCARD_TOPIC, self.move_log)
        self.bus.subscribe(WILDCARD_TOPIC, self.rating_updater)
        self.bus.subscribe(WILDCARD_TOPIC, Broadcaster(self.connection_manager, self.room_manager))

        self.command_router = CommandRouter(send=self.connection_manager.send)
        self.command_router.register("login", self._handle_login)
        self.command_router.register("create_room", self._handle_create_room)
        self.command_router.register("join_room", self._handle_join_room)
        self.command_router.register("play", self.matchmaker.handle_play)
        self.command_router.register("move", self.game_manager.handle_move)
        self.command_router.register("resign", self.game_manager.handle_resign)
        self.command_router.register("leave_room", self._handle_leave_room)

        self.websocket_server = WebSocketServer(self.connection_manager, self.command_router, host=host, port=port)

    async def _handle_login(self, connection_id: str, command: LoginCommand) -> None:
        await self.auth_service.handle_login(connection_id, command)
        username = self.connection_manager.username_for(connection_id)
        if username is not None:
            # If this username had an in-progress game with a pending
            # disconnect timer, this re-seats it -- a no-op otherwise.
            await self.game_manager.attempt_reconnect(username, connection_id)

    async def _handle_create_room(self, connection_id: str, command: CreateRoomCommand) -> None:
        room = self.room_manager.create_room()
        logger.info("room created: room_id=%s by connection=%s", room.room_id, connection_id)
        await self.connection_manager.send(connection_id, encode_message(
            RoomCreatedMessage(room_id=room.room_id)
        ))

    async def _handle_join_room(self, connection_id: str, command: JoinRoomCommand) -> None:
        try:
            room = self.room_manager.join_room(command.room_id, connection_id)
        except RoomNotFoundError:
            await send_error(self.connection_manager.send, connection_id, f"no such room: {command.room_id!r}")
            return

        if self.game_manager.has_game(room.room_id):
            # A game's already running here (a spectator, or a player
            # joining after the fact) -- catch them up with a snapshot.
            await self.game_manager.send_snapshot(room.room_id, connection_id)
            return

        if room.white is not None and room.black is not None:
            await self.game_manager.start_game(room, [room.white, room.black])

    async def _handle_leave_room(self, connection_id: str, command: LeaveRoomCommand) -> None:
        room = self.room_manager.room_for_connection(connection_id)
        if room is None:
            return

        seated_in_active_game = self.game_manager.has_game(room.room_id) and connection_id in (room.white, room.black)
        if seated_in_active_game:
            # Leaving mid-game forfeits, same as a resign -- otherwise
            # a losing player could just walk away consequence-free,
            # leaving the opponent's seat pointed at a room that never
            # finishes. The seat itself is left alone (same as a
            # disconnect); only a spectator or an unstarted room's seat
            # is actually freed below.
            await self.game_manager.handle_resign(connection_id, ResignCommand())
            return

        self.room_manager.leave(connection_id)

    async def start(self):
        return await self.websocket_server.start()

    async def stop(self) -> None:
        await self.websocket_server.stop()
        self.game_manager.stop_all()
