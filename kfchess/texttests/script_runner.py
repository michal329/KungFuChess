"""The composition root for the text fixture DSL: wires
board_parser -> GameState/GameEngine -> board_printer. This is what
main.py calls into for scripted, deterministic (no wall-clock)
replays of real-time gameplay -- a "wait 500" command advances the
game clock by exactly 500ms rather than sleeping.
"""
from kfchess.engine.game_engine import GameEngine
from kfchess.engine.game_state import GameState
from kfchess.io.board_parser import build_board, parse_board_section
from kfchess.io.board_printer import render
from kfchess.io.errors import BoardFixtureError
from kfchess.texttests.script_parser import (
    CLICK,
    JUMP,
    PRINT,
    PRINT_BOARD_TARGET,
    WAIT,
    parse_commands_section,
)


class ScriptRunner:
    def run(self, lines: list[str]) -> list[str]:
        grid = parse_board_section(lines)
        try:
            board = build_board(grid)
        except BoardFixtureError as error:
            return [error.code]

        engine = GameEngine(board)
        state = GameState(board=board)
        outputs: list[str] = []

        handlers = {
            CLICK: lambda args: engine.handle_click(state, int(args[0]), int(args[1])),
            JUMP: lambda args: engine.handle_jump(state, int(args[0]), int(args[1])),
            WAIT: lambda args: engine.tick(state, int(args[0])),
            PRINT: lambda args: self._handle_print(args, state, outputs),
        }

        for tokens in parse_commands_section(lines):
            if not tokens:
                continue
            handler = handlers.get(tokens[0])
            if handler:
                handler(tokens[1:])

        return outputs

    @staticmethod
    def _handle_print(args, state: GameState, outputs: list[str]) -> None:
        if args and args[0] == PRINT_BOARD_TARGET:
            outputs.append(render(state.board))
