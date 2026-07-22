"""NetworkGameEngine: the duck-typed stand-in for ``GameEngine`` that
``ClickController`` talks to on the client (see
``kfchess/input/click_controller.py`` -- it only ever calls
``is_selectable``/``attempt_move``/``attempt_jump`` on whatever it's
constructed with, never on a specific class). Passing this instead of
a real ``GameEngine`` is the entire "client migration": nothing in
``ClickController`` itself changes.

Unlike the real ``GameEngine``, this never mutates anything.
``attempt_move``/``attempt_jump`` only ever *send* a ``MoveCommand``
over the wire and return ``True`` optimistically -- the server is the
sole legality authority (the architecture doc: "the client should not
validate game rules"). Whatever actually happens comes back later as a
``MoveQueuedMessage``/``MoveEventMessage``/etc, applied by
``client/remote_game_view.py``, which is the only thing that ever
mutates the client's local ``GameState``. A rejected attempt simply
never produces one of those -- the piece just never appears to move.

``is_selectable``/``is_in_transit``/``is_airborne``/``is_in_cooldown``
are read-only predicates over ``GameState`` -- exactly what
``GameEngine``'s own versions are -- reimplemented here rather than
routed through a real ``GameEngine`` instance, so there's no real
``GameEngine`` sitting around whose ``attempt_move``/``tick`` could be
called by mistake and mutate a board nothing else is supposed to
touch.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Optional

from kfchess.input.board_mapper import BoardMapper
from kfchess.input.click_controller import ClickController
from kfchess.io.snapshot import position_to_dict
from kfchess.model.position import Position
from protocol.commands import MoveCommand

if TYPE_CHECKING:
    from kfchess.engine.game_state import GameState
    from client.websocket_client import WebSocketClient


class NetworkGameEngine:
    def __init__(self, client: "WebSocketClient", mapper: BoardMapper) -> None:
        self._client = client
        self._click_controller = ClickController(self, mapper)

    @property
    def selection(self) -> Optional[Position]:
        return self._click_controller.selection

    def handle_click(self, state: "GameState", x: int, y: int) -> None:
        self._click_controller.handle_click(state, x, y)

    def is_selectable(self, state: "GameState", pos: Position) -> bool:
        piece = state.board.get(pos)
        return piece is not None and not self._is_busy(state, pos)

    def is_in_transit(self, state: "GameState", pos: Position) -> bool:
        return any(pm.from_pos == pos for pm in state.pending)

    def is_airborne(self, state: "GameState", pos: Position) -> bool:
        return any(pj.pos == pos for pj in state.airborne)

    def is_in_cooldown(self, state: "GameState", pos: Position) -> bool:
        expiry = state.cooldowns.get(pos)
        return expiry is not None and expiry > state.current_time

    def _is_busy(self, state: "GameState", pos: Position) -> bool:
        return self.is_in_transit(state, pos) or self.is_airborne(state, pos) or self.is_in_cooldown(state, pos)

    def attempt_move(self, state: "GameState", from_pos: Position, to_pos: Position) -> bool:
        if state.game_over:
            return False
        self._send(MoveCommand(from_=position_to_dict(from_pos), to=position_to_dict(to_pos)))
        return True

    def attempt_jump(self, state: "GameState", pos: Position) -> bool:
        if state.game_over:
            return False
        self._send(MoveCommand(from_=position_to_dict(pos), to=position_to_dict(pos)))
        return True

    def _send(self, command: MoveCommand) -> None:
        asyncio.create_task(self._client.send_command(command))
