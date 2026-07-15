"""Draws the board background, piece sprites, and a minimal HUD onto a
pygame surface. Subscribes to GameEvents to drive each occupied cell's
PieceStateMachine (which animation state it's currently playing) --
GameEngine notifies, this class only reacts; it never mutates game
state.

Animation state is keyed by board Position rather than piece identity
-- Piece is an immutable value object with no id field, so continuity
across a move is tracked by relocating a position's state-machine
entry from its origin to its destination on MoveCompletedEvent. Stale
entries (a piece removed outright, e.g. an airborne capture) are
pruned at the start of every render() against the board's actual
occupancy, rather than tracked per removal event -- simpler and can't
drift out of sync with the board.
"""
from __future__ import annotations

from typing import Optional

import pygame

from kfchess.events.events import GameOverEvent, JumpLandedEvent, MoveCompletedEvent, Observer
from kfchess.gui.asset_loader import AssetLoader
from kfchess.gui.config import BOARD_IMAGE_PATH, CELL_SIZE_PX, HUD_HEIGHT_PX, WINDOW_WIDTH_PX
from kfchess.gui.piece_state_machine import PieceStateMachine
from kfchess.model.board import Board
from kfchess.model.position import Position

HUD_TEXT_COLOR = (255, 255, 255)
HUD_BACKGROUND_COLOR = (30, 30, 30)
SELECTION_COLOR = (255, 215, 0)


class BoardRenderer(Observer):
    def __init__(self, surface: pygame.Surface):
        self._surface = surface
        self._asset_loader = AssetLoader()
        self._board_image = pygame.transform.scale(
            pygame.image.load(str(BOARD_IMAGE_PATH)).convert(), (WINDOW_WIDTH_PX, WINDOW_WIDTH_PX)
        )
        self._state_machines: dict[Position, PieceStateMachine] = {}
        self._font = pygame.font.SysFont(None, 32)
        self._game_over_text: Optional[str] = None

    def on_event(self, event) -> None:
        if isinstance(event, MoveCompletedEvent):
            machine = self._state_machines.pop(event.from_pos, None)
            if machine is not None:
                machine.transition_to("move")
                self._state_machines[event.to_pos] = machine
        elif isinstance(event, JumpLandedEvent):
            machine = self._state_machines.get(event.pos)
            if machine is not None:
                machine.transition_to("short_rest")
        elif isinstance(event, GameOverEvent):
            self._game_over_text = "Draw" if event.winner is None else f"{event.winner} wins"

    def _prune_stale_machines(self, board: Board) -> None:
        stale = [pos for pos in self._state_machines if board.get(pos) is None]
        for pos in stale:
            del self._state_machines[pos]

    def _machine_for(self, position: Position, piece) -> PieceStateMachine:
        machine = self._state_machines.get(position)
        if machine is None:
            machine = PieceStateMachine(self._asset_loader.load(piece.code))
            self._state_machines[position] = machine
        return machine

    def render(self, board: Board, selection: Optional[Position]) -> None:
        self._prune_stale_machines(board)
        self._surface.blit(self._board_image, (0, 0))

        for position in board.occupied_positions():
            piece = board.get(position)
            machine = self._machine_for(position, piece)
            frame = pygame.transform.smoothscale(machine.get_current_frame(), (CELL_SIZE_PX, CELL_SIZE_PX))
            self._surface.blit(frame, (position.col * CELL_SIZE_PX, position.row * CELL_SIZE_PX))

        if selection is not None:
            rect = pygame.Rect(selection.col * CELL_SIZE_PX, selection.row * CELL_SIZE_PX, CELL_SIZE_PX, CELL_SIZE_PX)
            pygame.draw.rect(self._surface, SELECTION_COLOR, rect, width=4)

        self._draw_hud()

    def _draw_hud(self) -> None:
        hud_rect = pygame.Rect(0, WINDOW_WIDTH_PX, WINDOW_WIDTH_PX, HUD_HEIGHT_PX)
        pygame.draw.rect(self._surface, HUD_BACKGROUND_COLOR, hud_rect)
        text = self._game_over_text or "Kung Fu Chess"
        label = self._font.render(text, True, HUD_TEXT_COLOR)
        self._surface.blit(label, (10, WINDOW_WIDTH_PX + (HUD_HEIGHT_PX - label.get_height()) // 2))
