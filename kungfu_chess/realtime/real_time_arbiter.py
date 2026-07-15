from kungfu_chess.realtime.motion import Motion, ArrivalEvents, travel_time_ms


class RealTimeArbiter:
    """Owns the single active Motion (common route: one at a time).

    Time is tracked internally in milliseconds.
    Spec API:
      has_active_motion() -> bool
      start_motion(piece, source, destination) -> None
      advance_time(ms) -> ArrivalEvents
    """

    def __init__(self, board):
        self._board = board
        self._elapsed_ms: int = 0
        self._active: Motion | None = None

    # ------------------------------------------------------------------
    def has_active_motion(self) -> bool:
        return self._active is not None

    def start_motion(self, piece, src, dst) -> None:
        duration = travel_time_ms(src, dst)
        piece.state = "moving"
        self._active = Motion(
            piece=piece,
            src=src,
            dst=dst,
            arrival_ms=self._elapsed_ms + duration,
        )

    def advance_time(self, ms: int) -> ArrivalEvents:
        self._elapsed_ms += ms
        if self._active is None or self._elapsed_ms < self._active.arrival_ms:
            return ArrivalEvents()
        return self._resolve_arrival()

    # ------------------------------------------------------------------
    def _resolve_arrival(self) -> ArrivalEvents:
        motion = self._active
        self._active = None

        target = self._board.get(motion.dst)
        king_captured = target is not None and target.type == "K"
        if target is not None:
            target.state = "captured"
            self._board.remove_piece(motion.dst)

        self._board.move_piece(motion.src, motion.dst)
        motion.piece.state = "idle"

        return ArrivalEvents(king_captured=king_captured, arrived=[motion])
