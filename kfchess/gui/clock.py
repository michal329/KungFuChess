"""Tracks the game clock (the same ms value fed to GameEngine.tick())
for HUD display -- deliberately not wall-clock time, so it always
matches what the engine actually saw."""


class Clock:
    def __init__(self):
        self.elapsed_ms = 0

    def tick(self, ms: int) -> None:
        self.elapsed_ms += ms

    def as_mm_ss(self) -> str:
        seconds = self.elapsed_ms // 1000
        return f"{seconds // 60:02d}:{seconds % 60:02d}"
