from kungfu_chess.io.board_parser import BoardParser
from kungfu_chess.model.position import Position
from kungfu_chess.rules.rule_engine import RuleEngine


def engine():
    return RuleEngine()


def board(lines):
    return BoardParser().parse(lines)


def test_valid_move_returns_ok():
    b = board([". . .", "wR . .", ". . ."])
    v = engine().validate_move(b, Position(1, 0), Position(1, 2))
    assert v.is_valid is True
    assert v.reason == "ok"


def test_outside_board_src():
    b = board(["wK ."])
    v = engine().validate_move(b, Position(5, 0), Position(0, 0))
    assert v.reason == "outside_board"


def test_outside_board_dst():
    b = board(["wK ."])
    v = engine().validate_move(b, Position(0, 0), Position(0, 9))
    assert v.reason == "outside_board"


def test_empty_source():
    b = board([". wK"])
    v = engine().validate_move(b, Position(0, 0), Position(0, 1))
    assert v.reason == "empty_source"


def test_friendly_destination():
    b = board(["wK wR"])
    v = engine().validate_move(b, Position(0, 0), Position(0, 1))
    assert v.reason == "friendly_destination"


def test_illegal_piece_move():
    b = board(["wK . .", ". . .", ". . ."])
    v = engine().validate_move(b, Position(0, 0), Position(0, 2))
    assert v.reason == "illegal_piece_move"
