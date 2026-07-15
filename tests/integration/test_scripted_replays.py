"""Drives the .kfc scripts under tests/integration/scripts/ end to end
through the real text fixture DSL (ScriptRunner) -- deterministic,
wall-clock-free regression coverage of real-time gameplay.
"""
from pathlib import Path

from kfchess.texttests.script_runner import ScriptRunner

SCRIPTS_DIR = Path(__file__).parent / "scripts"


def _run(name: str) -> list[str]:
    lines = (SCRIPTS_DIR / name).read_text().splitlines()
    return ScriptRunner().run(lines)


def test_rook_moves_after_click_click_wait():
    outputs = _run("01_rook_move_and_capture.kfc")
    assert outputs[0] == "WR . . . . . . .\n" + "\n".join([". . . . . . . ."] * 6) + "\n. . . . . . . BK"
    assert outputs[1] == ". . . WR . . . .\n" + "\n".join([". . . . . . . ."] * 6) + "\n. . . . . . . BK"


def test_king_capture_via_scripted_replay():
    outputs = _run("02_king_capture_ends_game.kfc")
    assert outputs[0] == "WR . . BK"
    assert outputs[1] == ". . . WR"  # rook captured the king and now sits on col 3


def test_airborne_jump_intercepts_scripted():
    outputs = _run("03_airborne_jump_intercepts_arrival.kfc")
    assert outputs[0] == "WR BK"  # nothing resolved yet
    assert outputs[1] == ". BK"   # attacker removed outright, defender never moved
