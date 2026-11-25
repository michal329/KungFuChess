# Kung Fu Chess

[![Tests](https://github.com/michal329/KungFuChess/actions/workflows/tests.yml/badge.svg)](https://github.com/michal329/KungFuChess/actions/workflows/tests.yml)

A real-time multiplayer chess game: an event-driven game engine, a
**WebSocket game server** (login, rooms, ELO matchmaking, SQLite user
store) and a pygame client, containerized with **Docker** and covered by
**291 automated tests**.

Real-time chess: no turns, pieces move on a per-piece cooldown, and a
move takes visible travel time -- dodging usually works by moving a
threatened piece away before an attacker arrives. A piece that's
already in flight has genuinely left its origin square: nothing can
capture it, or be blocked by it, there anymore -- only something
actually at rest can do either. A piece can also jump in place (click
it, then click its own square again) to briefly rise and land back; if
an enemy's queued move arrives on that square mid-jump, the enemy is
destroyed and the jumper survives. This build is a synthesis of three
independent implementations of the same game, merging the strongest
design decision from each (see "Design provenance" below).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

## Running

A game only exists on a server; there is no offline mode.

```bash
# 1. start the server (ws://localhost:8765, users stored in SQLite)
python server_main.py
#    or run it in Docker
docker compose up --build

# 2. start a client on a machine with a display, once per player.
#    It asks for a username and whether to create, join or matchmake,
#    then opens the board. Left click to select, left click a
#    destination to move, or click the same square again to jump.
python client_main.py ws://localhost:8765

# tests
pytest -v
pytest --cov=kfchess --cov-report=term-missing
```

## Server

`server/` is an asyncio WebSocket server:

- **Auth**: login with salted PBKDF2 password hashing (`auth.py`).
- **Rooms and matchmaking**: create or join a room, or matchmake against
  an opponent within ±100 ELO (`room_manager.py`, `matchmaking.py`).
- **ELO rating**: updated when a game ends by an `Observer` that reacts
  to the game-over event (`rating.py`, `rating_subscriber.py`).
- **Command routing and broadcasting**: client commands are routed to
  the right game, and engine events are broadcast to both players
  (`command_router.py`, `broadcaster.py`, `event_bridge.py`).
- The server owns the authoritative `GameEngine`; the client only sends
  commands and renders the events it receives.

[Server_Design.md](Server_Design.md) describes how the same architecture
would scale out to multiple game-server shards.

## Package layout

```
kfchess/
├── model/      Position, Piece, Board -- pure value objects, no logic
├── rules/      piece shape/path legality, registry-dispatched by kind
├── realtime/   PendingMove/PendingJump, CollisionResolver
├── events/     GameEvent hierarchy + Observer interface
├── engine/     GameEngine (stateless), GameState, game-over rules, move history
├── input/      pixel<->cell mapping, click-to-intent translation
├── io/         text fixture parsing/printing (Board:/Commands: DSL)
├── texttests/  the fixture DSL's parser + composition-root runner
└── gui/        pygame rendering, sprite/animation state machine
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the architectural rules this
layout enforces.

## Text fixture DSL

```
Board:
WR . . . . . . .
. . . . . . . .
...
Commands:
click <x> <y>
wait <ms>
print board
```

Board tokens are `<color><kind>`, e.g. `WK` (white king), `BP` (black
pawn), `.` for empty. `wait` advances the deterministic game clock by
exactly `<ms>` -- no wall-clock sleeping, so replays are exact and
fast. There's no separate `jump` command: two consecutive `click <x>
<y>` lines at the same pixel are a select-then-jump, exactly like a
real click sequence. `print history` prints every completed move so
far, one line per color (`W: WR(0,0)-(0,3) ...`) -- see "Move history"
below. See `tests/integration/scripts/` for worked examples and
`tests/integration/test_scripted_replays.py` for how they're driven
(through `kfchess/texttests/script_runner.py`).

## Move history

`kfchess/engine/move_history.py`'s `MoveHistory` is an `Observer` (see
`kfchess/events/events.py`) that logs every completed move, split by
color, purely by reacting to the `MoveCompletedEvent` `GameEngine`
already fires -- it adds no work to `GameEngine`'s own methods and
isn't referenced by them at all. Register one with
`engine.add_observer(history)` and read it back with
`history.moves_for(WHITE)` / `history.moves_for(BLACK)`, or render it
as text with `kfchess/io/history_printer.py`. Both `ScriptRunner` (text
mode, via `print history`) and the client's `NetworkGameLoop` (printed
to stdout on quit) wire one up automatically.

## Design provenance

Synthesized from three independent repos of the same game:

- **Engine statelessness** and the richest real-time mechanics
  (cooldown, transit lock, the jump/airborne-interception mechanic) --
  ported from the repo whose `GameEngine` took an explicit `state:
  GameState` on every method, with zero state on `self`. The jump
  trigger itself was changed from that repo's separate right-click
  gesture to clicking a selected piece's own square again, to match
  this build's actual rules. That repo also had an advance
  "opposite-color route lock" (rejecting a move outright at queue time
  if its lane overlapped another in-flight move); it was removed in
  favor of a simpler, uniform rule: nothing is reserved in advance, and
  a mover just stops one square short of whatever -- friend or enemy --
  is genuinely at rest there when the move resolves. A piece that's
  itself mid-flight doesn't count as "at rest" for this purpose (see
  `_VacatedOriginsView` in `kfchess/engine/game_engine.py`), and can't
  be captured at the origin it's already left, either.
- **Value-object data model** (`Position`/`Piece` dataclasses, `Board`
  as `dict[Position, Piece]`) and the `kfchess` single-package layout
  -- from the repo that avoided bare `"wP"`-style string tokens in the
  model/engine layers.
- **Registry-based piece rules** (`dict[kind -> rule_fn]`, never an
  if/elif chain) -- both other repos converged on this independently.
- **Scripted text-fixture regression harness** (the `Board:`/
  `Commands:` DSL) -- for deterministic, wall-clock-free testing of
  real-time behavior.
- **Sprite/animation asset convention**
  (`assets/pieces/<CODE>/states/<state>/{config.json,sprites/}`) --
  taken from the repo with the cleanest, non-duplicated asset tree.
