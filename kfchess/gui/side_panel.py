"""Tracks captured pieces per color by diffing board occupancy against
the starting position each frame -- there is no dedicated CaptureEvent
(a capture is just an ordinary MoveCompletedEvent whose destination
happened to hold an enemy), so this is inferred rather than pushed."""
from kfchess.model.board import Board
from kfchess.model.piece import BLACK, WHITE


class SidePanel:
    def __init__(self, starting_board: Board):
        self._starting_counts = self._count_by_color(starting_board)

    @staticmethod
    def _count_by_color(board: Board) -> dict:
        counts = {WHITE: 0, BLACK: 0}
        for position in board.occupied_positions():
            counts[board.get(position).color] += 1
        return counts

    def captured_counts(self, current_board: Board) -> dict:
        """{color: number of that color's pieces no longer on the board}."""
        current = self._count_by_color(current_board)
        return {color: self._starting_counts[color] - current[color] for color in (WHITE, BLACK)}
