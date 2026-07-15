from kungfu_chess.input.board_mapper import BoardMapper
from kungfu_chess.model.position import Position


def mapper(cell_size=60, origin_x=0, origin_y=0):
    return BoardMapper(origin_x, origin_y, cell_size)


def test_top_left_pixel_maps_to_cell_0_0():
    assert mapper().pixel_to_cell(0, 0) == Position(0, 0)


def test_pixel_inside_second_cell_maps_correctly():
    assert mapper().pixel_to_cell(61, 0) == Position(0, 1)


def test_row_determined_by_y():
    assert mapper().pixel_to_cell(0, 61) == Position(1, 0)


def test_negative_x_returns_none():
    assert mapper().pixel_to_cell(-1, 0) is None


def test_negative_y_returns_none():
    assert mapper().pixel_to_cell(0, -1) is None


def test_non_zero_origin_offset():
    m = BoardMapper(origin_x=10, origin_y=20, cell_size=60)
    assert m.pixel_to_cell(10, 20) == Position(0, 0)
    assert m.pixel_to_cell(70, 20) == Position(0, 1)
