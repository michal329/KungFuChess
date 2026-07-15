from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Position:
    row: int
    col: int

    def delta_to(self, other: "Position") -> tuple[int, int]:
        return other.row - self.row, other.col - self.col

    def translated(self, delta_row: int, delta_col: int) -> "Position":
        return Position(self.row + delta_row, self.col + delta_col)

    def __repr__(self) -> str:
        return f"Position({self.row}, {self.col})"
