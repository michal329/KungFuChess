from kfchess.io.board_printer import render
from kfchess.io.standard_position import STANDARD_START, build_standard_board


def test_build_standard_board_matches_the_grid_literal():
    board = build_standard_board()
    assert render(board) == "\n".join(" ".join(row) for row in STANDARD_START)


def test_build_standard_board_is_8x8():
    board = build_standard_board()
    assert board.dimensions() == (8, 8)


def test_build_standard_board_has_both_kings():
    from kfchess.model.piece import BLACK, KING, WHITE

    board = build_standard_board()
    kings = [p for p in (board.get(pos) for pos in board.all_positions()) if p and p.kind == KING]
    colors = {k.color for k in kings}
    assert colors == {WHITE, BLACK}
