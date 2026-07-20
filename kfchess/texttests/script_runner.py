"""The composition root for the text fixture DSL: wires
board_parser -> GameState/GameEngine -> board_printer/history_printer.
This is what main.py calls into for scripted, deterministic (no
wall-clock) replays of real-time gameplay -- a "wait 500" command
advances the game clock by exactly 500ms rather than sleeping.

A MoveHistory is registered as an observer alongside the engine every
run -- GameEngine's own methods (attempt_move, tick, ...) never know
it exists; it just accumulates a record of every MoveCompletedEvent
"on the side," inspectable via the "print history" command.
"""
from kfchess.engine.game_engine import GameEngine
from kfchess.engine.game_state import GameState
from kfchess.engine.move_history import MoveHistory
from kfchess.io.board_parser import build_board, parse_board_section
from kfchess.io.board_printer import render as render_board
from kfchess.io.errors import BoardFixtureError
from kfchess.io.history_printer import render as render_history
from kfchess.texttests.script_parser import (
    CLICK,
    PRINT,
    PRINT_BOARD_TARGET,
    PRINT_HISTORY_TARGET,
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
        move_history = MoveHistory()
        engine.add_observer(move_history)
        outputs: list[str] = []

        handlers = {
            CLICK: lambda args: engine.handle_click(state, int(args[0]), int(args[1])),
            WAIT: lambda args: engine.tick(state, int(args[0])),
            PRINT: lambda args: self._handle_print(args, state, move_history, outputs),
        }

        for tokens in parse_commands_section(lines):
            if not tokens:
                continue
            handler = handlers.get(tokens[0])
            if handler:
                handler(tokens[1:])

        return outputs

    @staticmethod
    def _handle_print(args, state: GameState, move_history: MoveHistory, outputs: list[str]) -> None:
        if not args:
            return
        if args[0] == PRINT_BOARD_TARGET:
            outputs.append(render_board(state.board))
        elif args[0] == PRINT_HISTORY_TARGET:
            outputs.append(render_history(move_history))
