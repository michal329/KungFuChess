import pathlib
import pytest
from kungfu_chess.texttests.script_runner import ScriptRunner

SCRIPTS_DIR = pathlib.Path(__file__).parent / "scripts"


def run(name):
    return ScriptRunner().run((SCRIPTS_DIR / name).read_text().splitlines())


def _all_scripts():
    return sorted(SCRIPTS_DIR.glob("*.kfc"))


@pytest.mark.parametrize("script_path", _all_scripts(), ids=lambda p: p.stem)
def test_script_runs_without_error(script_path):
    outputs = ScriptRunner().run(script_path.read_text().splitlines())
    assert len(outputs) >= 1
    for output in outputs:
        assert isinstance(output, str) and output


def test_01_board_parsing():
    outputs = run("01_board_parsing.kfc")
    assert outputs[0] == "wR . bK\n. wK ."


def test_02_click_to_move_board_unchanged_before_arrival():
    outputs = run("02_click_to_move.kfc")
    # print before click, print after click (still in flight), print after wait
    assert outputs[0] == "wK . .\n. . ."   # initial
    assert outputs[1] == "wK . .\n. . ."   # in-flight: board unchanged
    assert outputs[2] == ". wK .\n. . ."   # arrived


def test_03_rook_moves():
    outputs = run("03_rook_moves.kfc")
    assert outputs[0] == ". . . wR"


def test_04_invalid_move_leaves_board_unchanged():
    outputs = run("04_invalid_moves.kfc")
    # King cannot jump 2 squares — board must be unchanged
    assert outputs[0] == "wK . .\n. . ."


def test_05_capture():
    outputs = run("05_capture.kfc")
    assert outputs[0] == ". . wR"


def test_06_game_over():
    outputs = run("06_game_over.kfc")
    assert outputs[0] == ". . wR"


def test_rook_move_script():
    outputs = run("rook_move.kfc")
    assert outputs[0] == ". . . wR\n. . . ."


def test_king_capture_script():
    outputs = run("king_capture.kfc")
    assert outputs[0] == ". wK"
