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


def test_friendly_block_stops_move_short_scripted():
    outputs = _run("03_friendly_block_stops_move_short.kfc")
    assert outputs[0] == "WR . . . .\n. . . . .\n. . WR . .\n. . . . .\n. . . . ."
    # the second rook has arrived at (0,2), sitting in the first rook's path;
    # the first rook hasn't resolved yet (still needs 4000ms, only 2000 have passed)
    assert outputs[1] == "WR . WR . .\n. . . . .\n. . . . .\n. . . . .\n. . . . ."
    # the first rook now resolves and stops short, one cell before the block
    assert outputs[2] == ". WR WR . .\n. . . . .\n. . . . .\n. . . . .\n. . . . ."


def test_jump_dodge_and_capture_scripted():
    """click <same square> twice = select then jump in place; while
    airborne, an arriving enemy is captured outright and the jumper
    survives -- see kfchess.input.click_controller and
    kfchess.engine.game_engine.GameEngine.attempt_jump."""
    outputs = _run("04_jump_dodge_and_capture.kfc")
    assert outputs[0] == "WR BK"  # nothing resolved yet
    assert outputs[1] == ". BK"   # attacker removed outright, defender never moved


def test_move_history_recorded_per_color_scripted():
    """MoveHistory is registered as an observer by ScriptRunner itself --
    GameEngine's own methods never reference it; "print history" is
    purely inspecting what accumulated on the side."""
    outputs = _run("05_move_history_per_color.kfc")
    assert outputs[0] == "W:\nB:"  # both moves queued, neither has arrived yet
    assert outputs[1] == "W: WR(0,0)-(0,3)\nB: BK(7,7)-(7,6)"
