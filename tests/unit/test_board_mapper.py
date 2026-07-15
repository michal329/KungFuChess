import pytest

from kfchess.input.board_mapper import BoardMapper
from kfchess.model.position import Position


def test_pixel_to_cell():
    mapper = BoardMapper(cell_size=100)
    assert mapper.pixel_to_cell(150, 250) == Position(row=2, col=1)


def test_cell_to_pixel():
    mapper = BoardMapper(cell_size=100)
    assert mapper.cell_to_pixel(2, 1) == (100, 200)


def test_rejects_non_positive_cell_size():
    with pytest.raises(ValueError):
        BoardMapper(cell_size=0)


def test_from_board_pixels_takes_smaller_axis():
    mapper = BoardMapper.from_board_pixels(board_width_px=810, board_height_px=800, num_cols=8, num_rows=8)
    assert mapper.cell_size == 100
