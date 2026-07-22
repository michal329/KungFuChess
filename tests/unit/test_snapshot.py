import json

from kfchess.engine.game_state import GameState
from kfchess.io.board_parser import build_board
from kfchess.io.snapshot import (
    dict_to_piece,
    dict_to_position,
    game_state_from_snapshot,
    game_state_snapshot,
    position_to_dict,
)
from kfchess.model.piece import Piece
from kfchess.model.position import Position
from kfchess.realtime.motion import PendingJump, PendingMove


def test_position_dict_round_trips():
    pos = Position(3, 5)
    assert dict_to_position(position_to_dict(pos)) == pos


def test_game_state_snapshot_is_json_serializable_and_matches_board():
    board = build_board([["WK", "."], [".", "BK"]])
    state = GameState(board=board, current_time=1200)
    state.cooldowns[Position(0, 0)] = 2000
    state.pending.append(PendingMove(
        piece=Piece("Q", "W"), from_pos=Position(0, 0), to_pos=Position(1, 1),
        arrival_time=3000, start_time=1200,
    ))
    state.airborne.append(PendingJump(
        piece=Piece("N", "B"), pos=Position(1, 0),
        land_time=2200, start_time=1200,
    ))

    snapshot = game_state_snapshot(state)
    json.dumps(snapshot)  # must not raise: everything is JSON-safe

    assert snapshot["board"] == {"height": 2, "width": 2, "grid": [["WK", "."], [".", "BK"]]}
    assert snapshot["current_time"] == 1200
    assert snapshot["cooldowns"] == [{"pos": {"row": 0, "col": 0}, "expiry": 2000}]
    assert snapshot["pending"] == [{
        "piece": "WQ", "from": {"row": 0, "col": 0}, "to": {"row": 1, "col": 1},
        "start_time": 1200, "arrival_time": 3000,
    }]
    assert snapshot["airborne"] == [{
        "piece": "BN", "pos": {"row": 1, "col": 0},
        "start_time": 1200, "land_time": 2200,
    }]
    assert snapshot["game_over"] is False
    assert snapshot["winner"] is None


def test_game_state_snapshot_empty_board_has_no_pending_or_airborne():
    board = build_board([["."]])
    state = GameState(board=board)
    snapshot = game_state_snapshot(state)
    assert snapshot["pending"] == []
    assert snapshot["airborne"] == []
    assert snapshot["cooldowns"] == []


def test_dict_to_piece_round_trips_with_piece_token():
    from kfchess.io.board_printer import piece_token
    piece = Piece("Q", "W")
    assert dict_to_piece(piece_token(piece)) == piece


def test_game_state_from_snapshot_round_trips_game_state_snapshot():
    board = build_board([["WK", "."], [".", "BK"]])
    original = GameState(board=board, current_time=1200)
    original.cooldowns[Position(0, 0)] = 2000
    original.pending.append(PendingMove(
        piece=Piece("Q", "W"), from_pos=Position(0, 0), to_pos=Position(1, 1),
        arrival_time=3000, start_time=1200,
    ))
    original.airborne.append(PendingJump(
        piece=Piece("N", "B"), pos=Position(1, 0),
        land_time=2200, start_time=1200,
    ))

    rebuilt = game_state_from_snapshot(game_state_snapshot(original))

    assert rebuilt.board.get(Position(0, 0)) == Piece("K", "W")
    assert rebuilt.board.get(Position(1, 1)) == Piece("K", "B")
    assert rebuilt.board.dimensions() == (2, 2)
    assert rebuilt.current_time == 1200
    assert rebuilt.cooldowns == {Position(0, 0): 2000}
    assert rebuilt.pending == original.pending
    assert rebuilt.airborne == original.airborne
    assert rebuilt.game_over is False
    assert rebuilt.winner is None


def test_game_state_from_snapshot_carries_game_over_and_winner():
    board = build_board([["WK"]])
    state = GameState(board=board, game_over=True, winner="W")
    rebuilt = game_state_from_snapshot(game_state_snapshot(state))
    assert rebuilt.game_over is True
    assert rebuilt.winner == "W"
