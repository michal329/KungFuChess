from dataclasses import dataclass


@dataclass(frozen=True)
class GameSnapshot:
    """Read-only view of game state passed to Renderer and BoardPrinter."""
    board: object   # Board — typed as object to avoid circular imports
    game_over: bool
