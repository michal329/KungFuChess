"""End-to-end proof that epics 1-3 actually fit together: a real
websocket client sends a MoveCommand to a real websocket server, the
server drives an actual GameEngine, and the resulting GameEvent comes
back out over the wire as a MoveEventMessage -- with nothing in
between except protocol/, server/bus.py, server/event_bridge.py,
server/broadcaster.py, server/command_router.py, and
server/websocket_server.py.

There is no Game Manager yet (a later epic), so this test wires a
single command handler locally instead of relying on production code
that doesn't exist yet.
"""
import asyncio

from client.websocket_client import WebSocketClient
from kfchess.engine.game_engine import GameEngine
from kfchess.engine.game_state import GameState
from kfchess.io.snapshot import dict_to_position
from kfchess.model.board import Board
from kfchess.model.piece import ROOK, WHITE, Piece
from kfchess.model.position import Position
from protocol.commands import MoveCommand
from protocol.messages import MoveEventMessage
from server.broadcaster import Broadcaster
from server.bus import Bus, WILDCARD_TOPIC
from server.command_router import CommandRouter
from server.connection_manager import ConnectionManager
from server.event_bridge import GameEventBridge
from server.websocket_server import WebSocketServer


def test_move_command_reaches_engine_and_move_event_comes_back_over_the_wire():
    async def scenario():
        board = Board(8, 8)
        board.set(Position(0, 0), Piece(ROOK, WHITE))
        engine = GameEngine(board, move_duration=0)
        state = GameState(board=board)

        bus = Bus()
        connection_manager = ConnectionManager()
        engine.add_observer(GameEventBridge(bus, game_id="1"))
        bus.subscribe(WILDCARD_TOPIC, Broadcaster(connection_manager))

        async def on_move(connection_id, command: MoveCommand) -> None:
            from_pos = dict_to_position(command.from_)
            to_pos = dict_to_position(command.to)
            if from_pos == to_pos:
                engine.attempt_jump(state, from_pos)
            else:
                engine.attempt_move(state, from_pos, to_pos)
            engine.tick(state, 0)

        router = CommandRouter(send=connection_manager.send)
        router.register("move", on_move)

        server = WebSocketServer(connection_manager, router, host="localhost", port=0)
        started = await server.start()
        port = started.sockets[0].getsockname()[1]

        try:
            async with WebSocketClient(f"ws://localhost:{port}") as client:
                await client.send_command(MoveCommand(
                    from_={"row": 0, "col": 0}, to={"row": 0, "col": 3},
                ))
                received = [await client.receive_message() for _ in range(2)]
        finally:
            await server.stop()

        move_events = [m for m in received if isinstance(m, MoveEventMessage)]
        assert move_events == [MoveEventMessage(
            piece="WR", from_={"row": 0, "col": 0}, to={"row": 0, "col": 3}, arrival_time=0,
        )]

    asyncio.run(scenario())
