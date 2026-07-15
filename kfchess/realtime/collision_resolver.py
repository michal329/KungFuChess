"""CollisionResolver: what happens when a due move meets the board's
*current* occupants -- the part of real-time resolution that isn't
plain move legality (RuleEngine's job) or clock/queue bookkeeping
(GameEngine's job): friendly mid-route blocking, and airborne-enemy
interception.

Stateless, same idiom as RuleEngine elsewhere: constructed once with no
board reference of its own, given whatever it needs as call arguments.
GameEngine remains the sole board mutator and the only component that
fires events -- this class only decides, it never touches the board or
notifies observers.
"""
from __future__ import annotations

from typing import List, Optional

from kfchess.model.board import Board
from kfchess.model.piece import same_color
from kfchess.model.position import Position
from kfchess.realtime.motion import PendingJump, PendingMove
from kfchess.rules.piece_rules import line_path_cells


class CollisionResolver:
    def stop_before_friendly_block(self, pending_move: PendingMove, board: Board) -> Optional[Position]:
        """Where a due move should stop short, if a friendly piece is now
        blocking its route -- or None if that doesn't apply.

        Only meaningful for a straight-line, multi-cell move; a knight's
        jump or a single-step move (no intermediate square) returns None
        immediately.

        * Path fully clear -> None (ordinary path-clear handling in
          RuleEngine decides the outcome, same as before this rule
          existed).
        * First occupied cell holds an enemy -> None (an enemy mid-route
          is still a fully-dropped premove, via the ordinary path-clear
          check).
        * First occupied cell holds a friendly piece -> the last clear
          cell before it (which is ``pending_move.from_pos`` itself if
          the very first step is already blocked -- the piece simply
          doesn't move).
        """
        from_pos, to_pos = pending_move.from_pos, pending_move.to_pos
        path = line_path_cells(from_pos, to_pos)
        if not path:
            return None

        prev = from_pos
        for cell in path:
            occupant = board.get(cell)
            if occupant is not None:
                return prev if same_color(occupant, pending_move.piece) else None
            prev = cell
        return None  # path fully clear

    def airborne_defender(self, pos: Position, attacker_color: str, airborne: List[PendingJump]) -> Optional[PendingJump]:
        """The PendingJump defending *pos*, iff it belongs to the
        opposite color of *attacker_color* -- i.e. it intercepts the
        attacker arriving there. None if nothing is airborne at *pos*,
        or if it's a friendly piece (a friendly arrival is already
        rejected earlier by the ordinary friendly-fire check, so that
        case never reaches here in practice)."""
        for pending_jump in airborne:
            if pending_jump.pos == pos:
                return pending_jump if pending_jump.piece.color != attacker_color else None
        return None
