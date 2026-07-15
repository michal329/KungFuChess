"""GameState: every mutable value a game-in-progress needs, held as one
unit -- separate from GameEngine's own attributes (collaborators like
RuleEngine/CollisionResolver, and static per-game config like move/
jump/cooldown duration), which don't change once the game is
constructed and aren't part of "where the game currently stands".

Bundling everything mutable behind one GameState means a save/load or
replay feature is a matter of (de)serializing this one dataclass, and
a test can construct or swap in a whole fake game state without
touching GameEngine's constructor signature.

Deliberately a plain (non-frozen) dataclass, unlike kfchess.model's
value objects: this is mutable by design, and it depends on Board (an
engine-adjacent concern) -- kfchess.model stays free of any pending/
airborne/cooldown vocabulary so it can't live there without inverting
the dependency direction (model -> realtime).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from kfchess.model.board import Board
from kfchess.model.position import Position
from kfchess.realtime.motion import PendingJump, PendingMove


@dataclass
class GameState:
    board: Board
    current_time: int = 0
    pending: List[PendingMove] = field(default_factory=list)
    airborne: List[PendingJump] = field(default_factory=list)
    cooldowns: Dict[Position, int] = field(default_factory=dict)
    game_over: bool = False
    winner: Optional[str] = None
