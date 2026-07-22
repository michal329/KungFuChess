"""Serializes a ``GameState`` into a plain, JSON-safe dict -- the same
kind of boundary crossing ``board_parser``/``board_printer`` already do
for the text-mode fixtures, just aimed at the network instead of a
file. Piece/position vocabulary never leaves this module as anything
but a ``<color><kind>`` token or a ``{"row", "col"}`` dict: nothing
downstream (``protocol``, ``server``, ``client``) needs to import
``kfchess.model`` to consume a snapshot.

Read-only: nothing here mutates a ``Board`` or a ``GameState``, so it
never competes with ``GameEngine`` for board-mutation authority.
"""
from __future__ import annotations

from typing import Dict, List

from kfchess.engine.game_state import GameState
from kfchess.io.board_parser import build_board
from kfchess.io.board_printer import piece_token, token_grid
from kfchess.model.board import Board
from kfchess.model.piece import Piece
from kfchess.model.position import Position
from kfchess.realtime.motion import PendingJump, PendingMove


def position_to_dict(position: Position) -> Dict[str, int]:
    return {"row": position.row, "col": position.col}


def dict_to_position(data: Dict[str, int]) -> Position:
    return Position(data["row"], data["col"])


def board_snapshot(board: Board) -> Dict:
    height, width = board.dimensions()
    return {"height": height, "width": width, "grid": token_grid(board)}


def pending_move_snapshot(pending_move: PendingMove) -> Dict:
    return {
        "piece": piece_token(pending_move.piece),
        "from": position_to_dict(pending_move.from_pos),
        "to": position_to_dict(pending_move.to_pos),
        "start_time": pending_move.start_time,
        "arrival_time": pending_move.arrival_time,
    }


def pending_jump_snapshot(pending_jump: PendingJump) -> Dict:
    return {
        "piece": piece_token(pending_jump.piece),
        "pos": position_to_dict(pending_jump.pos),
        "start_time": pending_jump.start_time,
        "land_time": pending_jump.land_time,
    }


def cooldowns_snapshot(cooldowns: Dict[Position, int]) -> List[Dict]:
    return [{"pos": position_to_dict(pos), "expiry": expiry} for pos, expiry in cooldowns.items()]


def game_state_snapshot(state: GameState) -> Dict:
    """A full point-in-time view of *state*, suitable as the payload of
    a ``SnapshotMessage`` sent the moment a client joins a game."""
    return {
        "board": board_snapshot(state.board),
        "current_time": state.current_time,
        "cooldowns": cooldowns_snapshot(state.cooldowns),
        "pending": [pending_move_snapshot(pm) for pm in state.pending],
        "airborne": [pending_jump_snapshot(pj) for pj in state.airborne],
        "game_over": state.game_over,
        "winner": state.winner,
    }


def dict_to_piece(token: str) -> Piece:
    return Piece(kind=token[1:], color=token[0])


def dict_to_pending_move(data: Dict) -> PendingMove:
    return PendingMove(
        piece=dict_to_piece(data["piece"]),
        from_pos=dict_to_position(data["from"]),
        to_pos=dict_to_position(data["to"]),
        arrival_time=data["arrival_time"],
        start_time=data["start_time"],
    )


def dict_to_pending_jump(data: Dict) -> PendingJump:
    return PendingJump(
        piece=dict_to_piece(data["piece"]),
        pos=dict_to_position(data["pos"]),
        land_time=data["land_time"],
        start_time=data["start_time"],
    )


def game_state_from_snapshot(payload: Dict) -> GameState:
    """The reverse of ``game_state_snapshot`` -- reconstructs a real,
    independent ``GameState`` (backed by a real ``Board``) from the
    plain dict a ``SnapshotMessage`` carries. This is the network
    analogue of ``kfchess.io.board_parser.build_board`` reconstructing
    a ``Board`` from a text fixture: both build fresh model objects
    from an *external* source of truth, never from a local click or
    legality decision -- see ``client/remote_game_view.py``, the only
    intended caller, for why that distinction matters (CLAUDE.md rule 1
    is about local mutation authority; this is a client mirroring a
    game it does not own)."""
    board = build_board(payload["board"]["grid"])
    state = GameState(board=board, current_time=payload["current_time"])
    state.cooldowns = {
        dict_to_position(entry["pos"]): entry["expiry"] for entry in payload["cooldowns"]
    }
    state.pending = [dict_to_pending_move(pm) for pm in payload["pending"]]
    state.airborne = [dict_to_pending_jump(pj) for pj in payload["airborne"]]
    state.game_over = payload["game_over"]
    state.winner = payload["winner"]
    return state
