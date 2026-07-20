"""BoardRenderer tests run headless via SDL's dummy video driver, set
before pygame is ever initialized, so this suite needs no real display
and works the same in CI as on a desktop.
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402  (must follow the SDL env vars above)
import pytest  # noqa: E402

from kfchess.engine.game_engine import GameEngine  # noqa: E402
from kfchess.engine.game_state import GameState  # noqa: E402
from kfchess.gui.board_renderer import BoardRenderer  # noqa: E402
from kfchess.model.board import Board  # noqa: E402
from kfchess.model.piece import PAWN, QUEEN, WHITE, Piece  # noqa: E402
from kfchess.model.position import Position  # noqa: E402


@pytest.fixture
def surface():
    pygame.init()
    yield pygame.display.set_mode((800, 860))
    pygame.quit()


def test_promoted_pawn_switches_to_queen_sprites(surface):
    """Regression test: a piece changing kind in place (promotion) --
    with no capture and no vacated/freshly-occupied square to trigger a
    fresh cache entry any other way -- must not keep rendering the
    pawn's sprites forever. See BoardRenderer._machine_for."""
    board = Board(8, 8)
    board.set(Position(1, 0), Piece(PAWN, WHITE))
    engine = GameEngine(board, move_duration=1000)
    state = GameState(board=board)
    renderer = BoardRenderer(surface, cooldown_duration=engine.cooldown_duration)
    engine.add_observer(renderer)

    renderer.render(state, None)  # seeds a pawn-sprite machine at (1,0), as every real frame would

    engine.attempt_move(state, Position(1, 0), Position(0, 0))
    engine.tick(state, 1000)
    assert state.board.get(Position(0, 0)) == Piece(QUEEN, WHITE)

    renderer.render(state, None)

    cached_code, machine = renderer._state_machines[Position(0, 0)]
    assert cached_code == "QW"
    assert machine.states is renderer._asset_loader.load("QW")


def test_non_promoting_move_keeps_reusing_its_machine(surface):
    """The fix must not defeat the whole point of the cache: an
    ordinary move (no kind change) should still carry its animation
    state machine forward, not rebuild from scratch every frame."""
    board = Board(8, 8)
    piece = Piece(PAWN, WHITE)
    board.set(Position(3, 0), piece)  # white advances toward row 0; row 2 isn't the back rank
    engine = GameEngine(board, move_duration=1000)
    state = GameState(board=board)
    renderer = BoardRenderer(surface, cooldown_duration=engine.cooldown_duration)
    engine.add_observer(renderer)

    renderer.render(state, None)
    assert engine.attempt_move(state, Position(3, 0), Position(2, 0))  # one step forward, no promotion
    engine.tick(state, 1000)
    renderer.render(state, None)

    cached_code, machine = renderer._state_machines[Position(2, 0)]
    assert cached_code == "PW"
    assert machine.states is renderer._asset_loader.load("PW")
