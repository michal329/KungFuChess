from kungfu_chess.model.board import Board, RowWidthMismatchError, UnknownTokenError
from kungfu_chess.model.piece import Piece
from kungfu_chess.model.position import Position

EMPTY_TOKEN = "."
VALID_COLORS = {"w", "b"}
VALID_PIECE_TYPES = {"K", "Q", "R", "B", "N", "P"}


class BoardParser:
    def __init__(self):
        self._next_id = 0

    def parse(self, lines):
        rows = [line.split() for line in lines if line.strip() != ""]
        if not rows:
            return Board(0, 0)

        width = len(rows[0])
        for row_tokens in rows:
            if len(row_tokens) != width:
                raise RowWidthMismatchError()

        board = Board(len(rows), width)
        for r, row_tokens in enumerate(rows):
            for c, token in enumerate(row_tokens):
                if token == EMPTY_TOKEN:
                    continue
                board.add_piece(Position(r, c), self._parse_piece(token))
        return board

    def _parse_piece(self, token):
        if len(token) != 2 or token[0] not in VALID_COLORS or token[1] not in VALID_PIECE_TYPES:
            raise UnknownTokenError(token)
        piece = Piece(id=self._next_id, color=token[0], type=token[1], cell=None)
        self._next_id += 1
        return piece