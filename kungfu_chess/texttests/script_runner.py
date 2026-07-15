from kungfu_chess.io.board_parser import BoardParser
from kungfu_chess.io.board_printer import BoardPrinter
from kungfu_chess.engine.game_engine import GameEngine
from kungfu_chess.input.board_mapper import BoardMapper
from kungfu_chess.input.controller import Controller
from kungfu_chess.texttests.script_parser import parse_script

CELL_SIZE = 100  # px — matches spec CELL_SIZE constant


class ScriptRunner:
    """Executes a .kfc script and returns the list of 'print board' outputs.

    DSL units:
      click <x> <y>   — pixels, origin top-left of cell (0,0)
      wait <ms>       — milliseconds of simulated time
      print board     — captures current board text
    All commands route through the public API:
      click  → Controller.click
      wait   → GameEngine.wait(ms)
      print  → BoardPrinter.print(engine.snapshot())
    """

    def run(self, lines) -> list[str]:
        commands = parse_script(lines)
        board = None
        engine = None
        controller = None
        printer = BoardPrinter()
        outputs = []

        for cmd in commands:
            if cmd[0] == "board":
                board = BoardParser().parse(cmd[1])
                engine = GameEngine(board)
                mapper = BoardMapper(0, 0, CELL_SIZE)
                controller = Controller(board, engine, mapper)

            elif cmd[0] == "click":
                _, x, y = cmd
                controller.click(x, y)

            elif cmd[0] == "wait":
                engine.wait(int(cmd[1]))

            elif cmd[0] == "print_board":
                outputs.append(printer.print(engine.snapshot()))

        return outputs
