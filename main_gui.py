# git repo: https://github.com/michal329/KungFuChess
"""Kung Fu Chess -- graphical entry point. Left click selects a piece,
then left click a destination to move it."""
from kfchess.engine.game_engine import GameEngine
from kfchess.engine.game_state import GameState
from kfchess.gui.game_loop import GameLoop
from kfchess.io.board_parser import build_board

STANDARD_START = [
    ["BR", "BN", "BB", "BQ", "BK", "BB", "BN", "BR"],
    ["BP", "BP", "BP", "BP", "BP", "BP", "BP", "BP"],
    [".", ".", ".", ".", ".", ".", ".", "."],
    [".", ".", ".", ".", ".", ".", ".", "."],
    [".", ".", ".", ".", ".", ".", ".", "."],
    [".", ".", ".", ".", ".", ".", ".", "."],
    ["WP", "WP", "WP", "WP", "WP", "WP", "WP", "WP"],
    ["WR", "WN", "WB", "WQ", "WK", "WB", "WN", "WR"],
]


def main():
    board = build_board(STANDARD_START)
    engine = GameEngine(board)
    state = GameState(board=board)
    GameLoop(engine, state).run()


if __name__ == "__main__":
    main()
