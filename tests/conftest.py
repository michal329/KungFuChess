import pytest

from kfchess.model.board import Board


@pytest.fixture
def empty_board():
    return Board(8, 8)
