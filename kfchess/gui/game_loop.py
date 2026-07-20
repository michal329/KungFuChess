"""Owns the pygame window and the frame-by-frame loop wiring mouse
input -> GameEngine -> BoardRenderer. Left click selects/moves.
"""
import pygame

from kfchess.engine.game_engine import GameEngine
from kfchess.engine.game_state import GameState
from kfchess.engine.move_history import MoveHistory
from kfchess.gui.board_renderer import BoardRenderer
from kfchess.gui.clock import Clock
from kfchess.gui.config import FPS, WINDOW_HEIGHT_PX, WINDOW_WIDTH_PX
from kfchess.io.history_printer import render as render_history

WINDOW_TITLE = "Kung Fu Chess"
LEFT_BUTTON = 1


class GameLoop:
    def __init__(self, engine: GameEngine, state: GameState):
        self._engine = engine
        self._state = state
        self._clock = Clock()
        # Registered in run(), once pygame (and thus the engine's other
        # observers) are set up; exposed here so a caller can inspect it
        # during or after a game without needing the pygame window at all.
        self.move_history = MoveHistory()

    def run(self) -> None:
        pygame.init()
        surface = pygame.display.set_mode((WINDOW_WIDTH_PX, WINDOW_HEIGHT_PX))
        pygame.display.set_caption(WINDOW_TITLE)
        renderer = BoardRenderer(surface, cooldown_duration=self._engine.cooldown_duration)
        self._engine.add_observer(renderer)
        self._engine.add_observer(self.move_history)
        pygame_clock = pygame.time.Clock()

        running = True
        while running:
            dt_ms = pygame_clock.tick(FPS)
            for pygame_event in pygame.event.get():
                if pygame_event.type == pygame.QUIT:
                    running = False
                elif pygame_event.type == pygame.MOUSEBUTTONDOWN:
                    x, y = pygame_event.pos
                    if pygame_event.button == LEFT_BUTTON:
                        self._engine.handle_click(self._state, x, y)

            if not self._state.game_over:
                self._engine.tick(self._state, dt_ms)
                self._clock.tick(dt_ms)

            renderer.render(self._state, self._engine.selection)
            pygame.display.flip()

        pygame.quit()
        print(render_history(self.move_history))
