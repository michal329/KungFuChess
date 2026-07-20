"""Formats a MoveHistory into text, one line per color, using the same
<color><kind> token convention as board_printer.py. Each move renders
as TOKEN(from_row,from_col)-(to_row,to_col), in the order it actually
completed.
"""
from kfchess.engine.move_history import MoveHistory, MoveRecord
from kfchess.model.piece import BLACK, WHITE


def _token(record: MoveRecord) -> str:
    piece = record.piece
    from_pos, to_pos = record.from_pos, record.to_pos
    return f"{piece.color}{piece.kind}({from_pos.row},{from_pos.col})-({to_pos.row},{to_pos.col})"


def render(history: MoveHistory) -> str:
    lines = []
    for color in (WHITE, BLACK):
        moves = " ".join(_token(record) for record in history.moves_for(color))
        lines.append(f"{color}: {moves}".rstrip())
    return "\n".join(lines)
