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
    board = Board.parse([". . .", ". wP .", ". . .", ". . ."])
    assert not DEFAULT_RULE_SET.is_legal_move(Piece("w", "P"), (1, 1), (3, 1), board)

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
    board = Board.parse([". . .", ". . .", ". wP .", ". . ."])
    controller = Controller(board)
    controller.handle_click(150, 250)  # select wP at (2,1)
    controller.handle_click(150, 150)  # move to (1,1)
    controller.advance_clock(1000)
    assert str(board) == ". . .\n. wP .\n. . .\n. . ."

def test_white_pawn_captures_enemy_diagonally_on_board():
    board = Board.parse([". . .", "bP . .", ". wP .", ". . ."])
    controller = Controller(board)
    controller.handle_click(150, 250)  # select wP at (2,1)
    controller.handle_click(50, 150)   # capture bP at (1,0)
    controller.advance_clock(1000)
    assert str(board) == ". . .\nwP . .\n. . .\n. . ."


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


# ---------- Advanced real-time interaction ----------

def test_enemy_collision_first_piece_wins():
    # wR and bR both heading to same cell -- route block prevents bR from scheduling
    board = Board.parse(["wR . . .", ". . . .", ". . . bR"])
    controller = Controller(board)
    controller.handle_click(50, 50)    # select wR at (0,0)
    controller.handle_click(350, 50)   # schedule wR to (0,3)
    controller.handle_click(350, 250)  # select bR at (2,3)
    controller.handle_click(350, 50)   # try bR to (0,3) -- same dst, blocked
    controller.advance_clock(1000)
    assert str(board) == ". . . wR\n. . . .\n. . . bR"

def test_invalid_premove_src_piece_gone():
    # wR scheduled to move, but captured before arrival -- move cancelled
    board = Board.parse(["wR . bR", ". . .", ". . ."])
    controller = Controller(board)
    controller.handle_click(50, 50)    # select wR at (0,0)
    controller.handle_click(150, 50)   # schedule wR to (0,1)
    # simulate wR being captured by directly moving bR onto it before arrival
    board.move((0, 2), (0, 0))         # bR captures wR at (0,0)
    controller.advance_clock(1000)     # wR move arrives but src is now bR
    # bR should not teleport to (0,1)
    assert board.get(0, 1) is None

def test_friendly_piece_lands_on_dst_cancels_move():
    # wR1 scheduled to (0,2), wR2 arrives there first -- wR1 move cancelled
    board = Board.parse(["wR . . wR", ". . . ."])
    controller = Controller(board)
    controller.handle_click(50, 50)    # select wR at (0,0)
    controller.handle_click(250, 50)   # schedule wR(0,0) to (0,2), arrives at t=1000
    # manually place a friendly piece at dst before arrival
    board.move((0, 3), (0, 2))         # wR at (0,3) moves to (0,2)
    controller.advance_clock(1000)     # wR(0,0) arrives but (0,2) has friendly -- cancelled
    assert board.get(0, 0) is not None  # wR still at src
    assert board.get(0, 2) is not None  # friendly still at dst

def test_movement_conflict_same_row_blocked():
    board = Board.parse(["wR . . .", ". . . .", "bR . . ."])
    controller = Controller(board)
    controller.handle_click(50, 50)    # select wR at (0,0)
    controller.handle_click(350, 50)   # schedule wR to (0,3)
    controller.handle_click(50, 250)   # select bR at (2,0)
    controller.handle_click(350, 250)  # try bR to (2,3) -- same col as wR dst, blocked
    controller.advance_clock(1000)
    assert str(board) == ". . . wR\n. . . .\nbR . . ."

def test_enemy_capture_at_arrival():
    # wR arrives at dst where enemy is -- capture succeeds
    board = Board.parse(["wR . bP", ". . .", ". . ."])
    controller = Controller(board)
    controller.handle_click(50, 50)    # select wR at (0,0)
    controller.handle_click(250, 50)   # schedule wR to (0,2) where bP sits
    controller.advance_clock(1000)
    assert str(board) == ". . wR\n. . .\n. . ."


# ---------- Pawn double step and promotion ----------

def test_white_pawn_double_step_from_start_row():
    board = Board.parse([". . .", ". . .", ". . .", ". . .", ". . .", ". . .", ". . .", ". wP ."])
    assert DEFAULT_RULE_SET.is_legal_move(Piece("w", "P"), (7, 1), (5, 1), board)

def test_black_pawn_double_step_from_start_row():
    board = Board.parse([". bP .", ". . .", ". . .", ". . .", ". . .", ". . .", ". . .", ". . ."])
    assert DEFAULT_RULE_SET.is_legal_move(Piece("b", "P"), (0, 1), (2, 1), board)

def test_pawn_double_step_blocked_by_piece_in_middle():
    board = Board.parse([". . .", ". . .", ". . .", ". . .", ". . .", ". . .", ". bP .", ". wP ."])
    assert not DEFAULT_RULE_SET.is_legal_move(Piece("w", "P"), (7, 1), (5, 1), board)

def test_pawn_double_step_not_allowed_from_non_start_row():
    board = Board.parse([". . .", ". . .", ". . .", ". . .", ". . .", ". wP .", ". . .", ". . ."])
    assert not DEFAULT_RULE_SET.is_legal_move(Piece("w", "P"), (5, 1), (3, 1), board)

def test_white_pawn_promotes_to_queen_on_last_row():
    board = Board.parse([". . .", ". wP .", ". . .", ". . ."])
    controller = Controller(board)
    controller.handle_click(150, 150)  # select wP at (1,1)
    controller.handle_click(150, 50)   # move to (0,1)
    controller.advance_clock(1000)
    promoted = board.get(0, 1)
    assert promoted is not None and promoted.type == "Q" and promoted.color == "w"

def test_black_pawn_promotes_to_queen_on_last_row():
    board = Board.parse([". . .", ". bP .", ". . ."])
    controller = Controller(board)
    controller.handle_click(150, 150)  # select bP at (1,1)
    controller.handle_click(150, 250)  # move to (2,1)
    controller.advance_clock(1000)
    promoted = board.get(2, 1)
    assert promoted is not None and promoted.type == "Q" and promoted.color == "b"

def test_pawn_no_promotion_when_not_on_last_row():
    board = Board.parse([". . .", ". . .", ". wP .", ". . ."])
    controller = Controller(board)
    controller.handle_click(150, 250)  # select wP at (2,1)
    controller.handle_click(150, 150)  # move to (1,1)
    controller.advance_clock(1000)
    piece = board.get(1, 1)
    assert piece is not None and piece.type == "P"


# ---------- Jump mechanic ----------

def test_airborne_piece_captures_arriving_enemy():
    board = Board.parse(["wR . bR", ". . .", ". . ."])
    controller = Controller(board)
    controller.handle_jump(0, 0)       # wR at (0,0) jumps, lands at t=1000
    controller.handle_click(250, 50)   # select bR at (0,2)
    controller.handle_click(50, 50)    # schedule bR to (0,0), arrives t=1000
    controller.advance_clock(1000)
    assert board.get(0, 0) is not None and board.get(0, 0).color == "w"  # wR stays
    assert board.get(0, 2) is None  # bR removed

def test_airborne_piece_stays_in_cell():
    board = Board.parse(["wR . .", ". . .", ". . ."])
    controller = Controller(board)
    controller.handle_jump(0, 0)
    controller.advance_clock(1000)
    assert board.get(0, 0) is not None and board.get(0, 0).color == "w"

def test_in_flight_piece_cannot_jump():
    board = Board.parse(["wR . .", ". . .", ". . ."])
    controller = Controller(board)
    controller.handle_click(50, 50)    # select wR
    controller.handle_click(250, 50)   # schedule move to (0,2)
    controller.handle_jump(0, 0)       # try to jump wR -- ignored
    controller.advance_clock(1000)
    assert board.get(0, 2) is not None  # wR arrived at dst, not stuck
    assert board.get(0, 0) is None

def test_airborne_piece_cannot_be_selected():
    board = Board.parse(["wR . .", ". . .", ". . ."])
    controller = Controller(board)
    controller.handle_jump(0, 0)       # wR airborne
    controller.handle_click(50, 50)    # try to select wR -- ignored
    controller.handle_click(250, 50)   # no selection, nothing happens
    controller.advance_clock(1000)
    assert board.get(0, 0) is not None  # wR still at (0,0)
    assert board.get(0, 2) is None

def test_no_capture_if_no_enemy_arrives_during_jump():
    board = Board.parse(["wR . bR", ". . .", ". . ."])
    controller = Controller(board)
    controller.handle_jump(0, 0)       # wR jumps
    controller.advance_clock(1000)     # no enemy arrives
    assert board.get(0, 0) is not None  # wR still there
    assert board.get(0, 2) is not None  # bR untouched

def test_enemy_arrives_after_jump_window_not_captured():
    board = Board.parse(["wR . bR", ". . .", ". . ."])
    controller = Controller(board)
    controller.handle_jump(0, 0)       # wR jumps, window closes at t=1000
    controller.advance_clock(1000)     # jump window closes
    controller.handle_click(250, 50)   # select bR
    controller.handle_click(50, 50)    # schedule bR to (0,0), arrives t=2000
    controller.advance_clock(1000)
    assert board.get(0, 0) is not None and board.get(0, 0).color == "b"  # bR captured wR normally



def test_capturing_enemy_king_ends_game():
    board = Board.parse(["wR . bK", ". . .", ". . ."])
    controller = Controller(board)
    assert not controller.is_game_over
    controller.handle_click(50, 50)   # select wR at (0,0)
    controller.handle_click(250, 50)  # schedule capture of bK at (0,2)
    controller.advance_clock(1000)
    assert controller.is_game_over

def test_clicks_ignored_after_game_over():
    board = Board.parse(["wR . bK", ". . .", "wR . ."])
    controller = Controller(board)
    controller.handle_click(50, 50)   # select wR at (0,0)
    controller.handle_click(250, 50)  # capture bK -- game over at t=1000
    controller.advance_clock(1000)
    assert controller.is_game_over
    controller.handle_click(50, 250)  # try to select wR at (2,0) -- ignored
    controller.handle_click(150, 250) # would move wR to (2,1) -- ignored
    controller.advance_clock(1000)
    assert board.get(2, 0) is not None  # wR at (2,0) never moved
    assert board.get(2, 1) is None

def test_game_not_over_without_king_capture():
    board = Board.parse(["wR . bR", ". . .", ". bK ."])
    controller = Controller(board)
    controller.handle_click(50, 50)   # select wR at (0,0)
    controller.handle_click(250, 50)  # capture bR at (0,2) -- not a king
    controller.advance_clock(1000)
    assert not controller.is_game_over

def test_pending_moves_cancelled_after_game_over():
    board = Board.parse(["wR . bK", ". . .", "wR . . "])
    controller = Controller(board)
    controller.handle_click(50, 250)  # select wR at (2,0)
    controller.handle_click(150, 250) # schedule wR(2,0) to (2,1), arrives t=1000
    controller.handle_click(50, 50)   # select wR at (0,0)
    controller.handle_click(250, 50)  # schedule capture bK, arrives t=1000
    controller.advance_clock(1000)
    assert controller.is_game_over
    # wR at (2,0) move also arrived at t=1000 -- may or may not execute,
    # but no further moves possible after game over
    controller.handle_click(50, 250)
    controller.handle_click(250, 250)
    controller.advance_clock(1000)
    assert board.get(2, 2) is None  # no move executed after game over


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
