"""Frames and timing for one animation state (e.g. .../NB/states/idle/),
loaded from the config.json + sprites/1..5.png convention shared by
every piece/state folder under assets/pieces/.
"""
from __future__ import annotations

import json
import pathlib

import pygame

DEFAULT_FPS = 10
DEFAULT_IS_LOOP = True
DEFAULT_NEXT_STATE_WHEN_FINISHED = "idle"


class SpriteSequence:
    def __init__(self, state_folder: pathlib.Path):
        state_folder = pathlib.Path(state_folder)

        config_path = state_folder / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
            self.fps: float = config["graphics"]["frames_per_sec"]
            self.is_loop: bool = config["graphics"]["is_loop"]
            self.next_state_when_finished: str = config["physics"]["next_state_when_finished"]
        else:
            self.fps = DEFAULT_FPS
            self.is_loop = DEFAULT_IS_LOOP
            self.next_state_when_finished = DEFAULT_NEXT_STATE_WHEN_FINISHED

        sprite_paths = sorted(
            (state_folder / "sprites").glob("*.png"),
            key=lambda p: int(p.stem),
        )
        self.frames: list[pygame.Surface] = [pygame.image.load(str(p)).convert_alpha() for p in sprite_paths]

    def get_frame(self, elapsed_sec: float) -> pygame.Surface:
        frame_index = int(elapsed_sec * self.fps)
        if self.is_loop:
            frame_index %= len(self.frames)
        else:
            frame_index = min(frame_index, len(self.frames) - 1)
        return self.frames[frame_index]
