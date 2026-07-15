"""Game-over rules (Strategy pattern):

    GameOverRule (ABC)  -- board-agnostic interface, one method: check().
      |-- KingCaptureRule -- the game ends the instant an armed King is gone.

GameEngine is injected with a GameOverRule (constructor DI, defaults to
KingCaptureRule) so future win conditions -- checkmate, resignation,
draw-by-repetition -- plug in without touching GameEngine itself.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from kfchess.model.board import Board
from kfchess.model.piece import KING


@dataclass(frozen=True)
class GameResult:
    is_over: bool
    winner: Optional[str] = None  # WHITE, BLACK, or None (draw / ongoing)


class GameOverRule(ABC):
    @abstractmethod
    def check(self, board: Board) -> GameResult:
        ...


class KingCaptureRule(GameOverRule):
    """The game ends the moment an armed side's King is captured.

    "Armed" is the key idea: this rule is stateful, and its first
    check() call establishes which colors actually started the game
    with a King on the board. Only an armed color can subsequently
    "lose" by having its King disappear. A color that never had a King
    to begin with -- common in isolated single-piece test boards that
    exercise unrelated movement logic -- can never end the game.

    GameEngine primes each rule once at construction time, using the
    pristine starting board, before any move can execute.

    A King is "captured" simply by no longer appearing anywhere on the
    board -- pieces are never soft-deleted, so absence is exact. If
    both armed Kings are gone at once (e.g. a same-tick double
    capture), the result is a draw (winner=None).

    One instance is scoped to one game; don't share a KingCaptureRule
    across two GameEngine instances.
    """

    def __init__(self) -> None:
        self._white_armed: Optional[bool] = None
        self._black_armed: Optional[bool] = None

    def check(self, board: Board) -> GameResult:
        white_alive = self._king_present(board, "W")
        black_alive = self._king_present(board, "B")

        if self._white_armed is None:
            self._white_armed = white_alive
            self._black_armed = black_alive

        white_lost = bool(self._white_armed) and not white_alive
        black_lost = bool(self._black_armed) and not black_alive

        if not white_lost and not black_lost:
            return GameResult(is_over=False)
        if white_lost and black_lost:
            return GameResult(is_over=True, winner=None)
        return GameResult(is_over=True, winner="B" if white_lost else "W")

    @staticmethod
    def _king_present(board: Board, color: str) -> bool:
        for position in board.occupied_positions():
            piece = board.get(position)
            if piece is not None and piece.kind == KING and piece.color == color:
                return True
        return False
