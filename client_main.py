# git repo: https://github.com/michal329/KungFuChess
"""Kung Fu Chess -- the graphical client entry point. This is the only
way to play the game: there is no offline/local mode, by design -- a
game only ever exists on a server (see server_main.py).

Usage:
    python client_main.py [ws://host:port]

Prompts for a username and a create/join/matchmake choice in the
terminal, then opens the pygame window, driven entirely by moves
relayed over the websocket.
"""
import asyncio
import logging
import sys

from client.network_game_loop import NetworkGameLoop

DEFAULT_URI = "ws://localhost:8765"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    uri = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URI
    asyncio.run(NetworkGameLoop(uri).run())


if __name__ == "__main__":
    main()
