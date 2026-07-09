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
    controller.handle_click(150, 150)  # schedule move to (1,1)
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
    controller.handle_click(250, 50)   # replace selection with wR at (0,2)
    controller.handle_click(250, 150)  # schedule move to (1,2)
    controller.advance_clock(1000)
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
    controller.handle_click(50, 50)
    controller.handle_click(250, 50)
    controller.advance_clock(1000)
    assert str(board) == ". . wR .\n. . . .\n. . . .\n. . . ."

def test_rook_cannot_capture_friendly():
    board = Board.parse(["wR . wR .", ". . . .", ". . . .", ". . . ."])
    controller = Controller(board)
    controller.handle_click(50, 50)
    controller.handle_click(250, 50)
    assert board.get(0, 0) is not None

def test_rook_blocked_by_friendly_cannot_reach_enemy_behind():
    board = Board.parse(["wR wP bR .", ". . . .", ". . . .", ". . . ."])
    controller = Controller(board)
    controller.handle_click(50, 50)
    controller.handle_click(250, 50)
    controller.advance_clock(1000)
    assert str(board) == "wR wP bR .\n. . . .\n. . . .\n. . . ."


# ---------- Pawn movement ----------

def test_white_pawn_moves_up_one_step():
    board = Board.parse([". . .", ". wP .", ". . ."])
    assert DEFAULT_RULE_SET.is_legal_move(Piece("w", "P"), (1, 1), (0, 1), board)

def test_black_pawn_moves_down_one_step():
    board = Board.parse([". . .", ". bP .", ". . ."])
    assert DEFAULT_RULE_SET.is_legal_move(Piece("b", "P"), (1, 1), (2, 1), board)

def test_white_pawn_cannot_move_down():
    board = Board.parse([". . .", ". wP .", ". . ."])
    assert not DEFAULT_RULE_SET.is_legal_move(Piece("w", "P"), (1, 1), (2, 1), board)

def test_black_pawn_cannot_move_up():
    board = Board.parse([". . .", ". bP .", ". . ."])
    assert not DEFAULT_RULE_SET.is_legal_move(Piece("b", "P"), (1, 1), (0, 1), board)

def test_pawn_cannot_move_two_cells():
    board = Board.parse([". . .", ". . .", ". wP ."])
    assert not DEFAULT_RULE_SET.is_legal_move(Piece("w", "P"), (2, 1), (0, 1), board)

def test_pawn_blocked_by_piece_ahead():
    board = Board.parse([". bP .", ". wP .", ". . ."])
    assert not DEFAULT_RULE_SET.is_legal_move(Piece("w", "P"), (1, 1), (0, 1), board)

def test_white_pawn_captures_diagonally():
    board = Board.parse(["bP . .", ". wP .", ". . ."])
    assert DEFAULT_RULE_SET.is_legal_move(Piece("w", "P"), (1, 1), (0, 0), board)

def test_black_pawn_captures_diagonally():
    board = Board.parse([". . .", ". bP .", ". . wP"])
    assert DEFAULT_RULE_SET.is_legal_move(Piece("b", "P"), (1, 1), (2, 2), board)

def test_pawn_cannot_capture_forward():
    board = Board.parse(["bP . .", "wP . .", ". . ."])
    assert not DEFAULT_RULE_SET.is_legal_move(Piece("w", "P"), (1, 0), (0, 0), board)

def test_pawn_cannot_capture_empty_diagonal():
    board = Board.parse([". . .", ". wP .", ". . ."])
    assert not DEFAULT_RULE_SET.is_legal_move(Piece("w", "P"), (1, 1), (0, 0), board)


# ---------- Pawn integration ----------

def test_white_pawn_moves_up_on_board():
    board = Board.parse([". . .", ". wP .", ". . ."])
    controller = Controller(board)
    controller.handle_click(150, 150)
    controller.handle_click(150, 50)
    controller.advance_clock(1000)
    assert str(board) == ". wP .\n. . .\n. . ."

def test_white_pawn_captures_enemy_diagonally_on_board():
    board = Board.parse(["bP . .", ". wP .", ". . ."])
    controller = Controller(board)
    controller.handle_click(150, 150)
    controller.handle_click(50, 50)
    controller.advance_clock(1000)
    assert str(board) == "wP . .\n. . .\n. . ."


# ---------- Timed movement ----------

def test_piece_not_moved_before_arrival():
    board = Board.parse(["wR . .", ". . .", ". . ."])
    controller = Controller(board)
    controller.handle_click(50, 50)
    controller.handle_click(250, 50)
    assert str(board) == "wR . .\n. . .\n. . ."

def test_piece_not_moved_before_full_duration():
    board = Board.parse(["wR . .", ". . .", ". . ."])
    controller = Controller(board)
    controller.handle_click(50, 50)
    controller.handle_click(250, 50)
    controller.advance_clock(500)
    assert str(board) == "wR . .\n. . .\n. . ."

def test_piece_arrives_exactly_at_duration():
    board = Board.parse(["wR . .", ". . .", ". . ."])
    controller = Controller(board)
    controller.handle_click(50, 50)
    controller.handle_click(250, 50)
    controller.advance_clock(1000)
    assert str(board) == ". . wR\n. . .\n. . ."

def test_piece_arrives_after_more_than_duration():
    board = Board.parse(["wR . .", ". . .", ". . ."])
    controller = Controller(board)
    controller.handle_click(50, 50)
    controller.handle_click(250, 50)
    controller.advance_clock(2000)
    assert str(board) == ". . wR\n. . .\n. . ."

def test_two_moves_arrive_in_order():
    board = Board.parse(["wR . . .", ". . . ."])
    controller = Controller(board)
    controller.handle_click(50, 50)
    controller.handle_click(150, 50)
    controller.advance_clock(1000)
    controller.handle_click(150, 50)
    controller.handle_click(350, 50)
    controller.advance_clock(1000)
    assert str(board) == ". . . wR\n. . . ."


# ---------- In-flight rules ----------

def test_in_flight_piece_cannot_be_selected():
    board = Board.parse(["wR . .", ". . .", ". . ."])
    controller = Controller(board)
    controller.handle_click(50, 50)   # select wR at (0,0)
    controller.handle_click(250, 50)  # schedule move to (0,2) -- in flight
    controller.handle_click(50, 50)   # try to select wR again -- ignored
    controller.handle_click(150, 50)  # would redirect if selected
    controller.advance_clock(1000)
    assert str(board) == ". . wR\n. . .\n. . ."

def test_in_flight_piece_cannot_replace_selection():
    board = Board.parse(["wR . . wR", ". . . ."])
    controller = Controller(board)
    controller.handle_click(50, 50)   # select wR at (0,0)
    controller.handle_click(150, 50)  # schedule move to (0,1) -- in flight
    controller.handle_click(50, 50)   # try re-select wR at (0,0) -- ignored
    controller.handle_click(350, 50)  # no selection active, nothing happens
    controller.advance_clock(1000)
    assert str(board) == ". wR . wR\n. . . ."

def test_piece_can_move_again_immediately_after_arrival():
    board = Board.parse(["wR . . .", ". . . ."])
    controller = Controller(board)
    controller.handle_click(50, 50)
    controller.handle_click(150, 50)
    controller.advance_clock(1000)    # wR arrives at (0,1)
    controller.handle_click(150, 50)  # select wR -- no cooldown
    controller.handle_click(350, 50)
    controller.advance_clock(1000)
    assert str(board) == ". . . wR\n. . . ."

def test_stationary_friendly_piece_can_still_be_selected_while_other_is_in_flight():
    board = Board.parse(["wR . wR", ". . .", ". . ."])
    controller = Controller(board)
    controller.handle_click(50, 50)   # select wR at (0,0)
    controller.handle_click(150, 50)  # schedule move to (0,1) -- in flight
    controller.handle_click(250, 50)  # select wR at (0,2) -- stationary
    controller.handle_click(250, 150) # schedule move to (1,2)
    controller.advance_clock(1000)
    assert board.get(1, 2) is not None

def test_two_pieces_cannot_target_same_destination():
    board = Board.parse(["wR . .", ". . .", "bR . ."])
    controller = Controller(board)
    controller.handle_click(50, 50)   # select wR at (0,0)
    controller.handle_click(250, 50)  # schedule wR to (0,2)
    controller.handle_click(50, 250)  # select bR at (2,0)
    controller.handle_click(250, 50)  # try bR to (0,2) -- same dst as wR, blocked
    controller.advance_clock(1000)
    assert str(board) == ". . wR\n. . .\nbR . ."  # bR stays, only wR moved


# ---------- RuleSet injection ----------

class AllowAllRuleSet(RuleSet):
    def is_legal_move(self, piece, src, dst, board):
        return True


def test_custom_ruleset_injected_into_controller():
    board = Board.parse(["wK . .", ". . .", ". . ."])
    controller = Controller(board, rule_set=AllowAllRuleSet())
    controller.handle_click(50, 50)
    controller.handle_click(250, 50)
    controller.advance_clock(1000)
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
    controller.advance_clock(1000)
    assert str(board) == ". . wR\n. . .\n. . ."
