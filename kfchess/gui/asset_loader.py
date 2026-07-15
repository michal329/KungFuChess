"""Loads and caches a chess piece's animation states from the assets
folder tree."""
from kfchess.gui.assets import piece_states_dir
from kfchess.gui.sprite_sequence import SpriteSequence


class AssetLoader:
    def __init__(self):
        self._cache: dict[str, dict[str, SpriteSequence]] = {}

    def load(self, piece_code: str) -> dict[str, SpriteSequence]:
        """Return {state_name: SpriteSequence} for every state of
        piece_code, e.g. 'NB' for a black knight. Loaded from disk once
        per piece_code; subsequent calls return the cached result."""
        if piece_code not in self._cache:
            states_folder = piece_states_dir(piece_code)
            self._cache[piece_code] = {
                state_folder.name: SpriteSequence(state_folder)
                for state_folder in sorted(states_folder.iterdir())
                if state_folder.is_dir()
            }
        return self._cache[piece_code]
