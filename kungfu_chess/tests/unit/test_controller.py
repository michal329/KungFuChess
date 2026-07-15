from kungfu_chess.io.board_parser import BoardParser
from kungfu_chess.engine.game_engine import GameEngine
from kungfu_chess.input.board_mapper import BoardMapper
from kungfu_chess.input.controller import Controller, ControllerResult
from kungfu_chess.model.position import Position

CELL = 100  # matches spec CELL_SIZE


def make_controller(lines):
    board = BoardParser().parse(lines)
    engine = GameEngine(board)
    mapper = BoardMapper(0, 0, CELL)
    ctrl = Controller(board, engine, mapper)
    return board, engine, ctrl


def click(ctrl, row, col):
    return ctrl.click(col * CELL, row * CELL)


def test_first_click_on_piece_selects_it():
    _, _, ctrl = make_controller(["wR ."])
    result = click(ctrl, 0, 0)
    assert result.reason == "selected"
    assert ctrl.selected == Position(0, 0)


def test_first_click_on_empty_returns_empty_source():
    _, _, ctrl = make_controller([". wR"])
    result = click(ctrl, 0, 0)
    assert result.reason == "empty_source"
    assert ctrl.selected is None


def test_clicking_selected_cell_deselects():
    _, _, ctrl = make_controller(["wR ."])
    click(ctrl, 0, 0)
    result = click(ctrl, 0, 0)
    assert result.reason == "deselected"
    assert ctrl.selected is None


def test_out_of_bounds_click_cancels_selection():
    _, _, ctrl = make_controller(["wR ."])
    click(ctrl, 0, 0)
    result = ctrl.click(9999, 9999)
    assert result.reason == "cancelled"
    assert ctrl.selected is None


def test_second_click_submits_move_and_returns_ok():
    _, _, ctrl = make_controller(["wR . ."])
    click(ctrl, 0, 0)
    result = click(ctrl, 0, 2)
    assert result.reason == "ok"
    assert ctrl.selected is None


def test_illegal_move_returns_reason_and_clears_selection():
    _, _, ctrl = make_controller(["wK . ."])
    click(ctrl, 0, 0)
    result = click(ctrl, 0, 2)
    assert result.reason == "illegal_piece_move"
    assert ctrl.selected is None


def test_click_returns_controller_result_instance():
    _, _, ctrl = make_controller(["wR ."])
    result = click(ctrl, 0, 0)
    assert isinstance(result, ControllerResult)
