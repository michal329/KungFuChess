"""Owns the pygame window and the frame-by-frame loop wiring mouse
input -> GameEngine -> BoardRenderer. Left click selects/moves; right
click jumps.
"""
import pygame

from kfchess.engine.game_engine import GameEngine
from kfchess.engine.game_state import GameState
from kfchess.gui.board_renderer import BoardRenderer
from kfchess.gui.clock import Clock
from kfchess.gui.config import FPS, WINDOW_HEIGHT_PX, WINDOW_WIDTH_PX

WINDOW_TITLE = "Kung Fu Chess"
LEFT_BUTTON = 1
RIGHT_BUTTON = 3


class GameLoop:
    def __init__(self, engine: GameEngine, state: GameState):
        self._engine = engine
        self._state = state
        self._clock = Clock()

    def run(self) -> None:
        pygame.init()
        surface = pygame.display.set_mode((WINDOW_WIDTH_PX, WINDOW_HEIGHT_PX))
        pygame.display.set_caption(WINDOW_TITLE)
        renderer = BoardRenderer(surface)
        self._engine.add_observer(renderer)
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
                    elif pygame_event.button == RIGHT_BUTTON:
                        self._engine.handle_jump(self._state, x, y)

            if not self._state.game_over:
                self._engine.tick(self._state, dt_ms)
                self._clock.tick(dt_ms)

            renderer.render(self._state.board, self._engine.selection)
            pygame.display.flip()

        pygame.quit()
