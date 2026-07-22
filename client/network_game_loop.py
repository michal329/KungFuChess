"""NetworkGameLoop: the composition root for the graphical entry point
(``client_main.py``) -- the one place that wires ``NetworkGameEngine``,
``RemoteGameView``, and the reused ``kfchess.gui``/``kfchess.input``
pieces together (EXPLANATION.md §5.5). There is no offline/local play
in this project -- a game only ever exists on a server, so this is the
*only* graphical composition root.

A single asyncio event loop drives both pygame's frame loop and the
websocket connection cooperatively -- no threads, no locks. A
background task continuously drains incoming messages into a queue;
the pygame loop drains that queue once per frame. That background task
must never stop for as long as the connection is open -- a client that
stops reading can stall its own connection's close (see
``server/game_manager.py``'s "production gotcha" note /
EXPLANATION.md's backpressure entry) -- so it keeps running for the
entire life of ``_play``, cancelled only on the way out.

Login and room selection are plain terminal prompts before the pygame
window opens (see EXPLANATION.md for why a full in-window lobby was
deliberately deferred). ``pygame.time.Clock.tick`` is not used for
frame pacing here -- it blocks synchronously (SDL's delay), which
would starve the receive task -- instead frame pacing uses
``asyncio.sleep``, the async-native equivalent.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional, Tuple

import pygame
import websockets.exceptions

from client.network_game_engine import NetworkGameEngine
from client.remote_game_view import RemoteGameView
from client.websocket_client import WebSocketClient
from kfchess.engine.move_history import MoveHistory
from kfchess.gui.board_renderer import BoardRenderer
from kfchess.gui.config import CELL_SIZE_PX, FPS, WINDOW_HEIGHT_PX, WINDOW_WIDTH_PX
from kfchess.input.board_mapper import BoardMapper
from kfchess.io.history_printer import render as render_history
from protocol.commands import CreateRoomCommand, JoinRoomCommand, LoginCommand, PlayCommand
from protocol.messages import (
    ErrorMessage,
    GameStartedMessage,
    Message,
    RatingMessage,
    RoomCreatedMessage,
    SnapshotMessage,
)

WINDOW_TITLE = "Kung Fu Chess (online)"
LEFT_BUTTON = 1

logger = logging.getLogger(__name__)


class NetworkGameLoop:
    def __init__(self, uri: str) -> None:
        self._uri = uri

    async def run(self) -> None:
        client = WebSocketClient(self._uri)
        await client.connect()
        logger.info("connected: uri=%s", self._uri)
        try:
            await self._login(client)
            await self._join_or_matchmake(client)
            game_started, view = await self._await_game_start(client)
            await self._play(client, game_started, view)
        finally:
            await client.close()
            logger.info("disconnected: uri=%s", self._uri)

    async def _login(self, client: WebSocketClient) -> None:
        username = input("Username: ").strip()
        password = input("Password (leave blank if none): ").strip() or None
        await client.send_command(LoginCommand(username=username, password=password))
        message = await client.receive_message()
        if isinstance(message, ErrorMessage):
            logger.warning("login failed: username=%s reason=%s", username, message.reason)
            raise SystemExit(f"Login failed: {message.reason}")
        assert isinstance(message, RatingMessage)
        logger.info("login: username=%s rating=%d", message.username, message.rating)
        print(f"Logged in as {message.username} (rating {message.rating})")

    async def _join_or_matchmake(self, client: WebSocketClient) -> None:
        choice = input("(c)reate room, (j)oin room, or (p)lay matchmaking? ").strip().lower()
        if choice == "c":
            await client.send_command(CreateRoomCommand())
            created = await client.receive_message()
            if isinstance(created, ErrorMessage):
                logger.warning("create_room failed: reason=%s", created.reason)
                raise SystemExit(f"Could not create room: {created.reason}")
            assert isinstance(created, RoomCreatedMessage)
            logger.info("room created: room_id=%s", created.room_id)
            print(f"Room created: {created.room_id} -- share this with your opponent")
            await client.send_command(JoinRoomCommand(room_id=created.room_id))
        elif choice == "j":
            room_id = input("Room ID: ").strip()
            await client.send_command(JoinRoomCommand(room_id=room_id))
        else:
            await client.send_command(PlayCommand())

    async def _await_game_start(self, client: WebSocketClient) -> Tuple[GameStartedMessage, RemoteGameView]:
        print("Waiting for the game to start...")
        game_started: Optional[GameStartedMessage] = None
        while game_started is None:
            message = await client.receive_message()
            if isinstance(message, ErrorMessage):
                logger.warning("error while waiting for game start: reason=%s", message.reason)
                raise SystemExit(f"Error: {message.reason}")
            if isinstance(message, GameStartedMessage):
                game_started = message

        logger.info("game started: room_id=%s color=%s", game_started.room_id, game_started.color)
        snapshot = await client.receive_message()
        while not isinstance(snapshot, SnapshotMessage):
            snapshot = await client.receive_message()

        return game_started, RemoteGameView.from_snapshot(snapshot.payload)

    async def _play(self, client: WebSocketClient, game_started: GameStartedMessage, view: RemoteGameView) -> None:
        pygame.init()
        surface = pygame.display.set_mode((WINDOW_WIDTH_PX, WINDOW_HEIGHT_PX))
        pygame.display.set_caption(f"{WINDOW_TITLE} -- playing as {game_started.color}")

        engine = NetworkGameEngine(client, BoardMapper(CELL_SIZE_PX))
        renderer = BoardRenderer(surface, cooldown_duration=game_started.cooldown_duration)
        move_history = MoveHistory()
        view.add_observer(renderer)
        view.add_observer(move_history)

        incoming: "asyncio.Queue[Message]" = asyncio.Queue()
        receiver_task = asyncio.create_task(self._pump_incoming(client, incoming))

        frame_duration = 1.0 / FPS
        last_frame = time.monotonic()
        running = True
        try:
            while running:
                for pygame_event in pygame.event.get():
                    if pygame_event.type == pygame.QUIT:
                        running = False
                    elif pygame_event.type == pygame.MOUSEBUTTONDOWN and pygame_event.button == LEFT_BUTTON:
                        x, y = pygame_event.pos
                        engine.handle_click(view.state, x, y)

                while not incoming.empty():
                    view.apply(incoming.get_nowait())

                renderer.render(view.state, engine.selection)
                pygame.display.flip()

                now = time.monotonic()
                await asyncio.sleep(max(0.0, frame_duration - (now - last_frame)))
                last_frame = time.monotonic()
        finally:
            receiver_task.cancel()
            try:
                await receiver_task
            except asyncio.CancelledError:
                pass
            pygame.quit()
            print(render_history(move_history))

    async def _pump_incoming(self, client: WebSocketClient, queue: "asyncio.Queue[Message]") -> None:
        try:
            while True:
                queue.put_nowait(await client.receive_message())
        except asyncio.CancelledError:
            pass
        except websockets.exceptions.ConnectionClosed:
            pass
