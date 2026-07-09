# git repo: https://github.com/michal329/KungFuChess
"""
Reads a board fixture + command script from stdin, executes it, writes
output to stdout. No prompts/debug text -- VPL diffs exact output.
"""
import sys

from board import Board, BoardError
from controller import Controller

BOARD_HEADER = "Board:"
COMMANDS_HEADER = "Commands:"


def split_sections(raw_lines):
    board_start = next(i for i, l in enumerate(raw_lines) if l.strip() == BOARD_HEADER)
    commands_start = next(i for i, l in enumerate(raw_lines) if l.strip() == COMMANDS_HEADER)
    board_lines = raw_lines[board_start + 1:commands_start]
    command_lines = [l for l in raw_lines[commands_start + 1:] if l.strip() != ""]
    return board_lines, command_lines


def run_command(line, board, controller, output):
    parts = line.split()
    name = parts[0]
    if name == "print" and parts[1] == "board":
        output.append(str(board))
    elif name == "click":
        controller.handle_click(int(parts[1]), int(parts[2]))
    elif name == "wait":
        controller.advance_clock(int(parts[1]))


def main():
    raw_lines = sys.stdin.read().splitlines()
    board_lines, command_lines = split_sections(raw_lines)

    try:
        board = Board.parse(board_lines)
    except BoardError as e:
        print(f"ERROR {e.code}")
        return

    controller = Controller(board)
    output = []
    for line in command_lines:
        run_command(line, board, controller, output)

    if output:
        print("\n".join(output))


if __name__ == "__main__":
    main()