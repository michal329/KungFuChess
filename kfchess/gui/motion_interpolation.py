"""Pure pixel/timing math for animating in-flight pieces -- deliberately
free of any pygame import, so it's testable without a display. Board
positions/timings in, pixel offsets out; kfchess.gui.board_renderer is
the only thing that turns these into actual drawing.
"""
from __future__ import annotations

import math

from kfchess.model.position import Position


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def move_progress(start_time: int, arrival_time: int, current_time: int) -> float:
    """0.0 at start_time, 1.0 at arrival_time, clamped either side (a
    stale/already-resolved move or a not-yet-reached one)."""
    total = arrival_time - start_time
    if total <= 0:
        return 1.0
    return _clamp01((current_time - start_time) / total)


def interpolated_pixel(from_pos: Position, to_pos: Position, progress: float, cell_size: int) -> tuple[int, int]:
    """The on-screen top-left pixel of a piece partway through a move
    from from_pos to to_pos, at the given 0..1 progress."""
    from_x, from_y = from_pos.col * cell_size, from_pos.row * cell_size
    to_x, to_y = to_pos.col * cell_size, to_pos.row * cell_size
    x = from_x + (to_x - from_x) * progress
    y = from_y + (to_y - from_y) * progress
    return int(round(x)), int(round(y))


def jump_bob_offset(start_time: int, land_time: int, current_time: int, max_bob_px: int) -> int:
    """Vertical pixel offset (negative = up) for a piece currently
    airborne, tracing a single hop: 0 at takeoff, -max_bob_px at the
    midpoint, back to 0 at landing -- the "rises and lands back" look."""
    progress = move_progress(start_time, land_time, current_time)
    return -int(round(max_bob_px * math.sin(progress * math.pi)))


def cooldown_fraction(expiry_time: int, current_time: int, cooldown_duration: int) -> float:
    """1.0 the instant a cooldown starts, draining linearly to 0.0 the
    instant it expires. 0.0 for an already-expired (or nonexistent)
    cooldown -- callers should skip drawing anything in that case."""
    if cooldown_duration <= 0:
        return 0.0
    remaining = expiry_time - current_time
    return _clamp01(remaining / cooldown_duration)
