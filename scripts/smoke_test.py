"""Smoke test for a running Kung Fu Chess server.

Logs in over a real websocket and checks the server's reply. Used by
the Kubernetes CI job, before and after the server pod is deleted, to
show that the server answers and that user accounts survive a pod
restart (they live in SQLite on a PersistentVolumeClaim).

Usage:
    python scripts/smoke_test.py URI USERNAME PASSWORD expect-rating
    python scripts/smoke_test.py URI USERNAME PASSWORD expect-error

expect-rating: the login must succeed (the server replies "rating").
expect-error:  the login must be rejected (the server replies "error").

Exits 0 on the expected reply, 1 otherwise.
"""
import asyncio
import json
import sys

import websockets


async def login(uri: str, username: str, password: str) -> dict:
    async with websockets.connect(uri, open_timeout=10) as ws:
        await ws.send(json.dumps({"command": "login", "username": username, "password": password}))
        return json.loads(await asyncio.wait_for(ws.recv(), timeout=10))


def main() -> int:
    if len(sys.argv) != 5 or sys.argv[4] not in ("expect-rating", "expect-error"):
        print(__doc__)
        return 2
    uri, username, password, expectation = sys.argv[1:]
    expected_type = "rating" if expectation == "expect-rating" else "error"

    reply = asyncio.run(login(uri, username, password))
    print(f"login {username!r}: server replied {reply}")
    if reply.get("type") != expected_type:
        print(f"FAIL: expected a {expected_type!r} message")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
