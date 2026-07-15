"""Tracks a piece's current animation state over wall-clock time,
separate from the deterministic game clock GameEngine.tick() advances.
A non-looping state that finishes playing all its frames once
auto-transitions to its next_state_when_finished (from config.json),
which may itself be non-looping and chain into a further transition.
"""
import time

from kfchess.gui.sprite_sequence import SpriteSequence


class PieceStateMachine:
    def __init__(self, states: dict[str, SpriteSequence], start_state: str = "idle"):
        self.states = states
        self.current_state = start_state
        self._entered_at = time.time()

    def transition_to(self, state_name: str) -> None:
        self.current_state = state_name
        self._entered_at = time.time()

    def get_current_frame(self):
        sequence = self.states[self.current_state]
        elapsed = time.time() - self._entered_at

        if not sequence.is_loop and elapsed >= len(sequence.frames) / sequence.fps:
            self.transition_to(sequence.next_state_when_finished)
            sequence = self.states[self.current_state]
            elapsed = time.time() - self._entered_at

        return sequence.get_frame(elapsed)
