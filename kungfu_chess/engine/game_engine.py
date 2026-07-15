from dataclasses import dataclass
from kungfu_chess.rules.rule_engine import RuleEngine
from kungfu_chess.realtime.real_time_arbiter import RealTimeArbiter
from kungfu_chess.model.game_state import GameSnapshot


@dataclass(frozen=True)
class MoveResult:
    is_accepted: bool
    reason: str  # "ok" | "game_over" | "motion_in_progress" | reason from RuleEngine


class GameEngine:
    """Application-service layer.

    Guards (checked in order before delegating):
      1. game_over  → reject with "game_over"
      2. motion_in_progress → reject with "motion_in_progress"
      3. rule legality → reject with RuleEngine reason
    Time is advanced via wait(ms); never via an injected clock callable.
    """

    def __init__(self, board):
        self._board = board
        self._rule_engine = RuleEngine()
        self._arbiter = RealTimeArbiter(board)
        self._game_over = False

    # ------------------------------------------------------------------
    @property
    def game_over(self) -> bool:
        return self._game_over

    def request_move(self, src, dst) -> MoveResult:
        if self._game_over:
            return MoveResult(False, "game_over")
        if self._arbiter.has_active_motion():
            return MoveResult(False, "motion_in_progress")
        validation = self._rule_engine.validate_move(self._board, src, dst)
        if not validation.is_valid:
            return MoveResult(False, validation.reason)
        piece = self._board.get(src)
        self._arbiter.start_motion(piece, src, dst)
        return MoveResult(True, "ok")

    def wait(self, ms: int) -> None:
        """Advance simulated time by ms milliseconds."""
        events = self._arbiter.advance_time(ms)
        if events.king_captured:
            self._game_over = True

    def snapshot(self) -> GameSnapshot:
        return GameSnapshot(board=self._board, game_over=self._game_over)
