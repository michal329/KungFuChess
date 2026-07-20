"""Parses the "Commands:" section of a fixture into token lists."""
from kfchess.io.board_parser import COMMANDS_MARKER
from kfchess.io.stream_reader import read_section

CLICK = "click"
WAIT = "wait"
PRINT = "print"
PRINT_BOARD_TARGET = "board"
PRINT_HISTORY_TARGET = "history"


def parse_commands_section(lines):
    command_lines = read_section(lines, COMMANDS_MARKER, None)
    return [line.split() for line in command_lines]
