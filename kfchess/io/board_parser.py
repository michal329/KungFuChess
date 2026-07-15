"""Parses raw fixture text into a raw token grid, and validates +
builds a Board from it. Two steps kept separate: parse_board_fixture
does pure text extraction (no legality/width checks); build_board
validates and constructs the Board.
"""
from kfchess.io.errors import RowWidthMismatchError, UnknownTokenError
from kfchess.io.pieces_config import EMPTY_TOKEN, LEGAL_TOKENS
from kfchess.io.stream_reader import read_lines, read_section
from kfchess.model.board import Board
from kfchess.model.piece import Piece
from kfchess.model.position import Position

BOARD_MARKER = "Board:"
COMMANDS_MARKER = "Commands:"


def parse_board_fixture(stream):
    return parse_board_section(read_lines(stream))


def parse_board_section(lines):
    board_lines = read_section(lines, BOARD_MARKER, COMMANDS_MARKER)
    return [line.split() for line in board_lines]


def build_board(grid, legal_tokens=LEGAL_TOKENS) -> Board:
    if not grid:
        return Board(0, 0)

    width = len(grid[0])
    for row in grid:
        if len(row) != width:
            raise RowWidthMismatchError()
        for cell in row:
            if cell not in legal_tokens:
                raise UnknownTokenError()

    height = len(grid)
    board = Board(height, width)
    for row_index, row in enumerate(grid):
        for col_index, token in enumerate(row):
            if token != EMPTY_TOKEN:
                board.set(Position(row_index, col_index), Piece(kind=token[1:], color=token[0]))
    return board
