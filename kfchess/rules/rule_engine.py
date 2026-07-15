"""RuleEngine: the single entry point for "is this move legal", given
only board geometry and piece shape rules -- no notion of real-time
state (cooldowns, in-flight moves, jumps). Those live one layer up in
kfchess.engine.game_engine, which asks RuleEngine first and then
applies real-time constraints on top.
"""
from __future__ import annotations

from dataclasses import dataclass

from kfchess.model.board import Board
from kfchess.model.piece import Piece
from kfchess.model.position import Position
from kfchess.rules.piece_rules import is_legal_shape, is_path_clear

REASON_OUTSIDE_BOARD = "outside_board"
REASON_NO_PIECE = "no_piece_at_source"
REASON_FRIENDLY_DESTINATION = "destination_occupied_by_own_color"
REASON_WRONG_SHAPE = "illegal_shape"
REASON_PATH_BLOCKED = "path_blocked"


@dataclass(frozen=True)
class MoveLegality:
    is_legal: bool
    reason: str | None = None


class RuleEngine:
    def evaluate(self, board: Board, from_position: Position, to_position: Position, piece: Piece) -> MoveLegality:
        if not board.is_inside(from_position) or not board.is_inside(to_position):
            return MoveLegality(False, REASON_OUTSIDE_BOARD)
        if board.get(from_position) is None:
            return MoveLegality(False, REASON_NO_PIECE)

        destination_piece = board.get(to_position)
        if destination_piece is not None and destination_piece.color == piece.color:
            return MoveLegality(False, REASON_FRIENDLY_DESTINATION)

        delta_row, delta_col = from_position.delta_to(to_position)
        is_capture = destination_piece is not None
        board_height, _ = board.dimensions()

        if not is_legal_shape(
            piece.kind, delta_row, delta_col,
            color=piece.color, is_capture=is_capture,
            from_row=from_position.row, board_height=board_height,
        ):
            return MoveLegality(False, REASON_WRONG_SHAPE)

        if not is_path_clear(board, piece.kind, from_position, delta_row, delta_col):
            return MoveLegality(False, REASON_PATH_BLOCKED)

        return MoveLegality(True)
