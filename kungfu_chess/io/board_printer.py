from kungfu_chess.model.position import Position
from kungfu_chess.model.game_state import GameSnapshot

EMPTY_TOKEN = "."


class BoardPrinter:
    def print(self, board_or_snapshot) -> str:
        board = board_or_snapshot.board if isinstance(board_or_snapshot, GameSnapshot) else board_or_snapshot
        lines = []
        for r in range(board.rows):
            tokens = [
                EMPTY_TOKEN if (p := board.get(Position(r, c))) is None else f"{p.color}{p.type}"
                for c in range(board.cols)
            ]
            lines.append(" ".join(tokens))
        return "\n".join(lines)
