# git repo: https://github.com/michal329/KungFuChess
"""Kung Fu Chess -- websocket server entry point.

Usage:
    python server_main.py [--host HOST] [--port PORT] [--db PATH] [--log-level LEVEL]
"""
import argparse
import asyncio
import logging

from server.app import ServerApp


async def _serve(app: ServerApp) -> None:
    await app.start()
    await asyncio.Future()  # run until the process is killed


def main() -> None:
    parser = argparse.ArgumentParser(description="Kung Fu Chess websocket server")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--db", default="kfchess_server.db")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    app = ServerApp(host=args.host, port=args.port, db_path=args.db)
    print(f"Kung Fu Chess server listening on ws://{args.host}:{args.port}")
    asyncio.run(_serve(app))


if __name__ == "__main__":
    main()
