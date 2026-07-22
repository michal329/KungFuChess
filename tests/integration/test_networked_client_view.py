"""End-to-end proof that epic 11's client migration actually preserves
travel-animation fidelity over the network: a real ``ServerApp``, a
real ``WebSocketClient``, and a real ``RemoteGameView`` all driven
together -- the queued move must show up in the client's local mirror
(``state.pending``, with the right timing) *before* it resolves, not
only once the piece has already landed, otherwise the whole point of
epic 11.1/11.2 (MoveQueuedEvent/Message) would be lost.
"""
import asyncio

from client.remote_game_view import RemoteGameView
from client.websocket_client import WebSocketClient
from kfchess.model.piece import PAWN, WHITE, Piece
from kfchess.model.position import Position
from protocol.commands import CreateRoomCommand, JoinRoomCommand, LoginCommand, MoveCommand
from protocol.messages import GameStartedMessage, RoomCreatedMessage, SnapshotMessage
from server.app import ServerApp


def test_move_is_visible_as_in_flight_before_it_resolves_on_a_real_networked_client():
    async def scenario():
        # A slow enough move_duration that we can observe the client's
        # mirror mid-flight, and a tick interval fine enough to catch it.
        app = ServerApp(
            host="localhost", port=0, db_path=":memory:",
            tick_interval_seconds=0.02, move_duration=200, cooldown_duration=0,
        )
        server = await app.start()
        port = server.sockets[0].getsockname()[1]
        uri = f"ws://localhost:{port}"

        try:
            async with WebSocketClient(uri) as white, WebSocketClient(uri) as black:
                await white.send_command(LoginCommand(username="alice"))
                await white.receive_message()
                await black.send_command(LoginCommand(username="bob"))
                await black.receive_message()

                await white.send_command(CreateRoomCommand())
                room_created = await white.receive_message()
                assert isinstance(room_created, RoomCreatedMessage)
                room_id = room_created.room_id

                await white.send_command(JoinRoomCommand(room_id=room_id))
                await black.send_command(JoinRoomCommand(room_id=room_id))

                white_started = await white.receive_message()
                assert isinstance(white_started, GameStartedMessage)
                white_snapshot = await white.receive_message()
                assert isinstance(white_snapshot, SnapshotMessage)
                await black.receive_message()  # GameStartedMessage
                await black.receive_message()  # SnapshotMessage

                view = RemoteGameView.from_snapshot(white_snapshot.payload)

                await white.send_command(MoveCommand(from_={"row": 6, "col": 0}, to={"row": 5, "col": 0}))

                # The very next message on this connection should be the
                # MoveQueuedMessage -- arriving well before the move
                # resolves (move_duration=200ms, tick_interval=20ms).
                queued = await white.receive_message()
                view.apply(queued)

                assert view.state.pending, "the move must be visible as in-flight immediately"
                pending = view.state.pending[0]
                assert pending.piece == Piece(PAWN, WHITE)
                assert pending.from_pos == Position(6, 0)
                assert pending.to_pos == Position(5, 0)
                assert pending.arrival_time - pending.start_time == 200
                # Not yet relocated on the board -- still mid-flight.
                assert view.state.board.get(Position(6, 0)) is not None
                assert view.state.board.get(Position(5, 0)) is None

                # Drain messages until the move actually resolves.
                from protocol.messages import MoveEventMessage
                resolved = None
                for _ in range(50):
                    message = await white.receive_message()
                    view.apply(message)
                    if isinstance(message, MoveEventMessage):
                        resolved = message
                        break
                assert resolved is not None

                assert view.state.pending == []
                assert view.state.board.get(Position(6, 0)) is None
                assert view.state.board.get(Position(5, 0)) == Piece(PAWN, WHITE)

                # Keep draining a bit so neither socket exits with a
                # backlog (see the epic 7 receive-queue backpressure note).
                for _ in range(3):
                    await asyncio.wait_for(white.receive_message(), timeout=3)
                    await asyncio.wait_for(black.receive_message(), timeout=3)
        finally:
            await app.stop()

    asyncio.run(scenario())
