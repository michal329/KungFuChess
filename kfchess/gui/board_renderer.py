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

A position's cached entry also records which piece *code* it was built
for, and _machine_for rebuilds it if that no longer matches the actual
occupant. This is what a plain position-keyed cache would otherwise
miss: pawn promotion changes a piece's kind in place, at a position
that's neither vacated (which _prune_stale_machines would catch) nor
freshly arrived at (which MoveCompletedEvent's relocation would catch)
-- without this check the promoted square would silently go on
rendering pawn sprites forever.

Three things are deliberately *not* event-driven, because they need to
be continuously true for as long as they're true rather than toggled
once: a piece's on-screen position while it's mid-flight (state.pending
already says which pieces are moving, every frame, so render() just
reads it), a piece's rise-and-land bob while it's airborne
(state.airborne says the same), and the cooldown-drain overlay
(state.cooldowns already says exactly how much is left). Events are
still used for the one-shot transitions that state alone can't
reconstruct: which state-machine instance to carry over to a new cell
on arrival, and dropping into short_rest the instant a jump grounds.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

import pygame

from kfchess.engine.game_state import GameState
from kfchess.events.events import GameOverEvent, JumpLandedEvent, MoveCompletedEvent, Observer
from kfchess.gui.asset_loader import AssetLoader
from kfchess.gui.config import BOARD_IMAGE_PATH, CELL_SIZE_PX, HUD_HEIGHT_PX, WINDOW_WIDTH_PX
from kfchess.gui.motion_interpolation import cooldown_fraction, interpolated_pixel, jump_bob_offset, move_progress
from kfchess.gui.piece_state_machine import PieceStateMachine
from kfchess.model.board import Board
from kfchess.model.position import Position

HUD_TEXT_COLOR = (255, 255, 255)
HUD_BACKGROUND_COLOR = (30, 30, 30)
SELECTION_COLOR = (255, 215, 0)
COOLDOWN_OVERLAY_COLOR = (40, 90, 220, 130)  # translucent blue, drains as the cell rests
JUMP_BOB_PX = 14
GAME_OVER_DIM_COLOR = (0, 0, 0, 170)  # translucent black scrim over the whole board
GAME_OVER_TEXT_COLOR = (255, 255, 255)


class BoardRenderer(Observer):
    def __init__(self, surface: pygame.Surface, cooldown_duration: int):
        self._surface = surface
        self._cooldown_duration = cooldown_duration
        self._asset_loader = AssetLoader()
        self._board_image = pygame.transform.scale(
            pygame.image.load(str(BOARD_IMAGE_PATH)).convert(), (WINDOW_WIDTH_PX, WINDOW_WIDTH_PX)
        )
        # Each entry also carries the piece code the machine was built
        # for, so _machine_for can tell a stale (promoted) entry apart
        # from a genuinely reusable one -- see the class docstring.
        self._state_machines: Dict[Position, Tuple[str, PieceStateMachine]] = {}
        self._font = pygame.font.SysFont(None, 32)
        self._game_over_headline_font = pygame.font.SysFont(None, 96, bold=True)
        self._game_over_subtitle_font = pygame.font.SysFont(None, 44)
        self._game_over_text: Optional[str] = None

    def on_event(self, event) -> None:
        if isinstance(event, MoveCompletedEvent):
            cached = self._state_machines.pop(event.from_pos, None)
            if cached is not None:
                _, machine = cached
                machine.transition_to("move")
                self._state_machines[event.to_pos] = cached
        elif isinstance(event, JumpLandedEvent):
            cached = self._state_machines.get(event.pos)
            if cached is not None:
                cached[1].transition_to("short_rest")
        elif isinstance(event, GameOverEvent):
            self._game_over_text = "Draw" if event.winner is None else f"{event.winner} wins"

    def _prune_stale_machines(self, board: Board) -> None:
        stale = [pos for pos in self._state_machines if board.get(pos) is None]
        for pos in stale:
            del self._state_machines[pos]

    def _machine_for(self, position: Position, piece) -> PieceStateMachine:
        cached = self._state_machines.get(position)
        if cached is not None and cached[0] == piece.code:
            return cached[1]
        # No entry yet, or the piece here is a different kind/color than
        # whatever built the cached entry (promotion is the one case
        # that changes a piece in place without a capture/relocation to
        # trigger a fresh entry some other way) -- build fresh, starting
        # at "idle".
        machine = PieceStateMachine(self._asset_loader.load(piece.code))
        self._state_machines[position] = (piece.code, machine)
        return machine

    def render(self, state: GameState, selection: Optional[Position]) -> None:
        board = state.board
        self._prune_stale_machines(board)
        self._surface.blit(self._board_image, (0, 0))

        moving_from = {pm.from_pos: pm for pm in state.pending}
        airborne_at = {pj.pos: pj for pj in state.airborne}

        for position in board.occupied_positions():
            piece = board.get(position)
            machine = self._machine_for(position, piece)

            pending_move = moving_from.get(position)
            pending_jump = airborne_at.get(position)

            if pending_move is not None:
                if machine.current_state != "move":
                    machine.transition_to("move")
                progress = move_progress(pending_move.start_time, pending_move.arrival_time, state.current_time)
                pixel = interpolated_pixel(pending_move.from_pos, pending_move.to_pos, progress, CELL_SIZE_PX)
            elif pending_jump is not None:
                if machine.current_state != "jump":
                    machine.transition_to("jump")
                bob = jump_bob_offset(pending_jump.start_time, pending_jump.land_time, state.current_time, JUMP_BOB_PX)
                pixel = (position.col * CELL_SIZE_PX, position.row * CELL_SIZE_PX + bob)
            else:
                pixel = (position.col * CELL_SIZE_PX, position.row * CELL_SIZE_PX)

            frame = pygame.transform.smoothscale(machine.get_current_frame(), (CELL_SIZE_PX, CELL_SIZE_PX))
            self._surface.blit(frame, pixel)

            if pending_move is None and pending_jump is None:
                self._draw_cooldown_overlay(position, state)

        if selection is not None:
            rect = pygame.Rect(selection.col * CELL_SIZE_PX, selection.row * CELL_SIZE_PX, CELL_SIZE_PX, CELL_SIZE_PX)
            pygame.draw.rect(self._surface, SELECTION_COLOR, rect, width=4)

        if state.game_over:
            self._draw_game_over_banner()

        self._draw_hud()

    def _draw_cooldown_overlay(self, position: Position, state: GameState) -> None:
        expiry = state.cooldowns.get(position)
        if expiry is None:
            return
        fraction = cooldown_fraction(expiry, state.current_time, self._cooldown_duration)
        if fraction <= 0.0:
            return
        overlay_height = int(CELL_SIZE_PX * fraction)
        overlay = pygame.Surface((CELL_SIZE_PX, overlay_height), pygame.SRCALPHA)
        overlay.fill(COOLDOWN_OVERLAY_COLOR)
        x = position.col * CELL_SIZE_PX
        y = position.row * CELL_SIZE_PX
        self._surface.blit(overlay, (x, y))

    def _draw_game_over_banner(self) -> None:
        scrim = pygame.Surface((WINDOW_WIDTH_PX, WINDOW_WIDTH_PX), pygame.SRCALPHA)
        scrim.fill(GAME_OVER_DIM_COLOR)
        self._surface.blit(scrim, (0, 0))

        center_x, center_y = WINDOW_WIDTH_PX // 2, WINDOW_WIDTH_PX // 2

        headline = self._game_over_headline_font.render("GAME OVER", True, GAME_OVER_TEXT_COLOR)
        self._surface.blit(headline, headline.get_rect(center=(center_x, center_y - 30)))

        subtitle_text = self._game_over_text or ""
        if subtitle_text:
            subtitle = self._game_over_subtitle_font.render(subtitle_text, True, GAME_OVER_TEXT_COLOR)
            self._surface.blit(subtitle, subtitle.get_rect(center=(center_x, center_y + 50)))

    def _draw_hud(self) -> None:
        hud_rect = pygame.Rect(0, WINDOW_WIDTH_PX, WINDOW_WIDTH_PX, HUD_HEIGHT_PX)
        pygame.draw.rect(self._surface, HUD_BACKGROUND_COLOR, hud_rect)
        text = self._game_over_text or "Kung Fu Chess"
        label = self._font.render(text, True, HUD_TEXT_COLOR)
        self._surface.blit(label, (10, WINDOW_WIDTH_PX + (HUD_HEIGHT_PX - label.get_height()) // 2))
