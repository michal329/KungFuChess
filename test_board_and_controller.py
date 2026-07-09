import pytest

from board import Board, RowWidthMismatchError, UnknownTokenError, Piece
from controller import Controller
from rules import RuleSet, DEFAULT_RULE_SET


# ---------- Board.parse ----------

def test_parse_rectangular_board():
    board = Board.parse(["wK . . bK", ". . . .", "wR . . bR"])
    assert board.rows == 3
    assert board.cols == 4
    assert str(board) == "wK . . bK\n. . . .\nwR . . bR"


def test_parse_piece_tokens_and_colors():
    board = Board.parse(["wK . bQ", ". wN .", "bP . wR"])
    king = board.get(0, 0)
    assert king.color == "w" and king.type == "K"
    assert board.get(0, 1) is None


def test_reject_unknown_token():
    with pytest.raises(UnknownTokenError):
        Board.parse(["wK xZ", ". ."])


def test_reject_row_width_mismatch():
    with pytest.raises(RowWidthMismatchError):
        Board.parse(["wK . .", ". bK"])


# ---------- Piece.parse ----------

def test_piece_parse_valid():
    p = Piece.parse("wK")
    assert p.color == "w"
    assert p.type == "K"


def test_piece_parse_invalid_raises():
    with pytest.raises(UnknownTokenError):
        Piece.parse("xZ")


# ---------- Controller click handling ----------

def make_board():
    return Board.parse(["wK . .", ". . .", ". . ."])


def test_select_piece_by_center_click():
    board = make_board()
    controller = Controller(board)
    controller.handle_click(50, 50)
    controller.handle_click(150, 150)
    controller.advance_clock(1000)
    assert str(board) == ". . .\n. wK .\n. . ."


def test_click_empty_cell_does_not_select():
    board = make_board()
    controller = Controller(board)
    controller.handle_click(150, 150)
    controller.handle_click(250, 250)
    assert str(board) == "wK . .\n. . .\n. . ."


def test_click_outside_board_is_ignored():
    board = make_board()
    controller = Controller(board)
    controller.handle_click(350, 50)
    controller.handle_click(-10, 50)
    assert str(board) == "wK . .\n. . .\n. . ."


def test_clicking_another_friendly_piece_replaces_selection():
    board = Board.parse(["wR . wR", ". . .", ". . ."])
    controller = Controller(board)
    controller.handle_click(50, 50)
    controller.handle_click(250, 50)
    controller.handle_click(250, 150)
    assert str(board) == "wR . .\n. . wR\n. . ."


# ---------- Movement rules (geometry only) ----------

def make_piece(t):
    return Piece("w", t)


def empty_board():
    return Board.parse([". . . . . . . .", ". . . . . . . .",
                        ". . . . . . . .", ". . . . . . . .",
                        ". . . . . . . .", ". . . . . . . .",
                        ". . . . . . . .", ". . . . . . . ."])


# King
def test_king_legal_one_step():
    assert DEFAULT_RULE_SET.is_legal_move(make_piece("K"), (4, 4), (5, 5), empty_board())

def test_king_illegal_two_steps():
    assert not DEFAULT_RULE_SET.is_legal_move(make_piece("K"), (4, 4), (6, 4), empty_board())


# Rook
def test_rook_legal_straight():
    assert DEFAULT_RULE_SET.is_legal_move(make_piece("R"), (0, 0), (0, 7), empty_board())

def test_rook_illegal_diagonal():
    assert not DEFAULT_RULE_SET.is_legal_move(make_piece("R"), (0, 0), (3, 3), empty_board())


# Bishop
def test_bishop_legal_diagonal():
    assert DEFAULT_RULE_SET.is_legal_move(make_piece("B"), (0, 0), (4, 4), empty_board())

def test_bishop_illegal_straight():
    assert not DEFAULT_RULE_SET.is_legal_move(make_piece("B"), (0, 0), (0, 4), empty_board())


# Queen
def test_queen_legal_straight():
    assert DEFAULT_RULE_SET.is_legal_move(make_piece("Q"), (3, 3), (3, 7), empty_board())

def test_queen_legal_diagonal():
    assert DEFAULT_RULE_SET.is_legal_move(make_piece("Q"), (3, 3), (6, 6), empty_board())

def test_queen_illegal_knight_shape():
    assert not DEFAULT_RULE_SET.is_legal_move(make_piece("Q"), (3, 3), (5, 4), empty_board())


# Knight
def test_knight_legal_l_shape():
    assert DEFAULT_RULE_SET.is_legal_move(make_piece("N"), (4, 4), (2, 5), empty_board())

def test_knight_illegal_straight():
    assert not DEFAULT_RULE_SET.is_legal_move(make_piece("N"), (4, 4), (4, 6), empty_board())


# ---------- Blocker tests ----------

def test_rook_blocked_by_piece_in_path():
    board = Board.parse(["wR wP . .", ". . . .", ". . . .", ". . . ."])
    assert not DEFAULT_RULE_SET.is_legal_move(make_piece("R"), (0, 0), (0, 3), board)

def test_rook_not_blocked_when_path_clear():
    board = Board.parse(["wR . . .", ". . . .", ". . . .", ". . . ."])
    assert DEFAULT_RULE_SET.is_legal_move(make_piece("R"), (0, 0), (0, 3), board)

def test_bishop_blocked_by_piece_in_path():
    board = Board.parse([". . . .", ". wP . .", ". . . .", ". . . wB"])
    assert not DEFAULT_RULE_SET.is_legal_move(make_piece("B"), (3, 3), (0, 0), board)

def test_bishop_not_blocked_when_path_clear():
    board = Board.parse([". . . .", ". . . .", ". . . .", ". . . wB"])
    assert DEFAULT_RULE_SET.is_legal_move(make_piece("B"), (3, 3), (0, 0), board)

def test_queen_blocked_straight():
    board = Board.parse(["wQ wP . .", ". . . .", ". . . .", ". . . ."])
    assert not DEFAULT_RULE_SET.is_legal_move(make_piece("Q"), (0, 0), (0, 3), board)

def test_queen_blocked_diagonal():
    board = Board.parse([". . . .", ". wP . .", ". . . .", ". . . wQ"])
    assert not DEFAULT_RULE_SET.is_legal_move(make_piece("Q"), (3, 3), (0, 0), board)

def test_knight_jumps_over_blockers():
    board = Board.parse(["wN wP wP .", "wP wP wP .", ". wP . .", ". . . ."])
    assert DEFAULT_RULE_SET.is_legal_move(make_piece("N"), (0, 0), (2, 1), board)


# ---------- Capture tests ----------

def test_rook_can_capture_enemy():
    board = Board.parse(["wR . bR .", ". . . .", ". . . .", ". . . ."])
    controller = Controller(board)
    controller.handle_click(50, 50)   # select wR at (0,0)
    controller.handle_click(250, 50)  # capture bR at (0,2)
    assert str(board) == ". . wR .\n. . . .\n. . . .\n. . . ."

def test_rook_cannot_capture_friendly():
    board = Board.parse(["wR . wR .", ". . . .", ". . . .", ". . . ."])
    controller = Controller(board)
    controller.handle_click(50, 50)   # select wR at (0,0)
    controller.handle_click(250, 50)  # try to capture wR at (0,2) -- friendly, replaces selection
    assert board.get(0, 0) is not None  # original wR still there

def test_rook_blocked_by_friendly_cannot_reach_enemy_behind():
    board = Board.parse(["wR wP bR .", ". . . .", ". . . .", ". . . ."])
    controller = Controller(board)
    controller.handle_click(50, 50)   # select wR at (0,0)
    controller.handle_click(250, 50)  # bR at (0,2) blocked by wP at (0,1)
    assert str(board) == "wR wP bR .\n. . . .\n. . . .\n. . . ."


# ---------- RuleSet injection ----------

class AllowAllRuleSet(RuleSet):
    def is_legal_move(self, piece, src, dst, board):
        return True


def test_custom_ruleset_injected_into_controller():
    board = Board.parse(["wK . .", ". . .", ". . ."])
    controller = Controller(board, rule_set=AllowAllRuleSet())
    controller.handle_click(50, 50)
    controller.handle_click(250, 50)
    assert str(board) == ". . wK\n. . .\n. . ."


# ---------- Integration ----------

def test_illegal_move_not_executed():
    board = Board.parse(["wK . .", ". . .", ". . ."])
    controller = Controller(board)
    controller.handle_click(50, 50)
    controller.handle_click(250, 50)
    assert str(board) == "wK . .\n. . .\n. . ."


def test_legal_move_is_executed():
    board = Board.parse(["wR . .", ". . .", ". . ."])
    controller = Controller(board)
    controller.handle_click(50, 50)
    controller.handle_click(250, 50)
    assert str(board) == ". . wR\n. . .\n. . ."
