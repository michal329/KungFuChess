from kfchess.gui.motion_interpolation import (
    cooldown_fraction,
    interpolated_pixel,
    jump_bob_offset,
    move_progress,
)
from kfchess.model.position import Position


def test_move_progress_at_start_is_zero():
    assert move_progress(start_time=0, arrival_time=1000, current_time=0) == 0.0


def test_move_progress_at_arrival_is_one():
    assert move_progress(start_time=0, arrival_time=1000, current_time=1000) == 1.0


def test_move_progress_is_linear_midway():
    assert move_progress(start_time=0, arrival_time=1000, current_time=250) == 0.25


def test_move_progress_clamps_past_arrival():
    assert move_progress(start_time=0, arrival_time=1000, current_time=5000) == 1.0


def test_move_progress_clamps_before_start():
    assert move_progress(start_time=500, arrival_time=1500, current_time=0) == 0.0


def test_move_progress_zero_duration_is_complete():
    assert move_progress(start_time=500, arrival_time=500, current_time=500) == 1.0


def test_interpolated_pixel_at_origin():
    pixel = interpolated_pixel(Position(0, 0), Position(0, 3), progress=0.0, cell_size=100)
    assert pixel == (0, 0)


def test_interpolated_pixel_at_destination():
    pixel = interpolated_pixel(Position(0, 0), Position(0, 3), progress=1.0, cell_size=100)
    assert pixel == (300, 0)


def test_interpolated_pixel_midway():
    pixel = interpolated_pixel(Position(0, 0), Position(0, 4), progress=0.5, cell_size=100)
    assert pixel == (200, 0)


def test_interpolated_pixel_diagonal():
    pixel = interpolated_pixel(Position(0, 0), Position(2, 2), progress=0.5, cell_size=100)
    assert pixel == (100, 100)


def test_jump_bob_zero_at_takeoff_and_landing():
    assert jump_bob_offset(start_time=0, land_time=1000, current_time=0, max_bob_px=14) == 0
    assert jump_bob_offset(start_time=0, land_time=1000, current_time=1000, max_bob_px=14) == 0


def test_jump_bob_peaks_upward_at_midpoint():
    offset = jump_bob_offset(start_time=0, land_time=1000, current_time=500, max_bob_px=14)
    assert offset == -14  # negative = up on screen


def test_cooldown_fraction_full_right_after_landing():
    assert cooldown_fraction(expiry_time=1000, current_time=0, cooldown_duration=1000) == 1.0


def test_cooldown_fraction_drains_to_zero_at_expiry():
    assert cooldown_fraction(expiry_time=1000, current_time=1000, cooldown_duration=1000) == 0.0


def test_cooldown_fraction_halfway():
    assert cooldown_fraction(expiry_time=1000, current_time=500, cooldown_duration=1000) == 0.5


def test_cooldown_fraction_never_negative_past_expiry():
    assert cooldown_fraction(expiry_time=1000, current_time=5000, cooldown_duration=1000) == 0.0
