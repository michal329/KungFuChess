# git repo: https://github.com/michal329/KungFuChess
"""Kung Fu Chess -- text mode entry point.

Usage:
    python main.py <script.kfc>   # run a .kfc script file
    python main.py                # read a .kfc script from stdin
"""
import sys

from kfchess.texttests.script_runner import ScriptRunner


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
