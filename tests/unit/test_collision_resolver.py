from kfchess.model.piece import BLACK, ROOK, WHITE, Piece
from kfchess.model.position import Position
from kfchess.realtime.collision_resolver import CollisionResolver
from kfchess.realtime.motion import PendingJump, PendingMove


def test_stop_before_friendly_block(empty_board):
    piece = Piece(ROOK, WHITE)
    empty_board.set(Position(0, 0), piece)
    empty_board.set(Position(0, 2), Piece(ROOK, WHITE))  # friendly mid-route
    pending_move = PendingMove(piece, Position(0, 0), Position(0, 4), arrival_time=1000)
    stop = CollisionResolver().stop_before_block(pending_move, empty_board)
    assert stop == Position(0, 1)


def test_stop_before_enemy_block(empty_board):
    """A blocker mid-route stops the mover short regardless of color --
    there's no special-casing for friend vs. enemy here; only the final
    destination cell distinguishes a capture from a friendly-fire
    rejection, and that's RuleEngine's job, not this one."""
    piece = Piece(ROOK, WHITE)
    empty_board.set(Position(0, 0), piece)
    empty_board.set(Position(0, 2), Piece(ROOK, BLACK))  # enemy mid-route
    pending_move = PendingMove(piece, Position(0, 0), Position(0, 4), arrival_time=1000)
    stop = CollisionResolver().stop_before_block(pending_move, empty_board)
    assert stop == Position(0, 1)


def test_no_stop_when_path_clear(empty_board):
    piece = Piece(ROOK, WHITE)
    empty_board.set(Position(0, 0), piece)
    pending_move = PendingMove(piece, Position(0, 0), Position(0, 4), arrival_time=1000)
    assert CollisionResolver().stop_before_block(pending_move, empty_board) is None


def test_no_stop_for_adjacent_move(empty_board):
    piece = Piece(ROOK, WHITE)
    empty_board.set(Position(0, 0), piece)
    pending_move = PendingMove(piece, Position(0, 0), Position(0, 1), arrival_time=1000)
    assert CollisionResolver().stop_before_block(pending_move, empty_board) is None


def test_stop_at_origin_when_first_step_blocked(empty_board):
    piece = Piece(ROOK, WHITE)
    empty_board.set(Position(0, 0), piece)
    empty_board.set(Position(0, 1), Piece(ROOK, WHITE))
    pending_move = PendingMove(piece, Position(0, 0), Position(0, 4), arrival_time=1000)
    assert CollisionResolver().stop_before_block(pending_move, empty_board) == Position(0, 0)


def test_stop_at_origin_when_first_step_blocked_by_enemy(empty_board):
    piece = Piece(ROOK, WHITE)
    empty_board.set(Position(0, 0), piece)
    empty_board.set(Position(0, 1), Piece(ROOK, BLACK))
    pending_move = PendingMove(piece, Position(0, 0), Position(0, 4), arrival_time=1000)
    assert CollisionResolver().stop_before_block(pending_move, empty_board) == Position(0, 0)


def test_airborne_defender_intercepts_enemy():
    defender = PendingJump(Piece(ROOK, BLACK), Position(3, 3), land_time=500)
    result = CollisionResolver().airborne_defender(Position(3, 3), attacker_color=WHITE, airborne=[defender])
    assert result is defender


def test_airborne_defender_ignores_friendly():
    defender = PendingJump(Piece(ROOK, WHITE), Position(3, 3), land_time=500)
    result = CollisionResolver().airborne_defender(Position(3, 3), attacker_color=WHITE, airborne=[defender])
    assert result is None


def test_airborne_defender_none_when_nothing_airborne():
    assert CollisionResolver().airborne_defender(Position(3, 3), attacker_color=WHITE, airborne=[]) is None
