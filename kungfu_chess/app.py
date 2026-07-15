"""
Entry point for text mode.

Usage:
    python -m kungfu_chess.app <script.kfc>   # run a .kfc file
    python -m kungfu_chess.app                # read from stdin
"""
import sys
from kungfu_chess.texttests.script_runner import ScriptRunner


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            lines = f.read().splitlines()
    else:
        lines = sys.stdin.read().splitlines()

    outputs = ScriptRunner().run(lines)
    if outputs:
        print("\n".join(outputs))


if __name__ == "__main__":
    main()
