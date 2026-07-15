# Kung Fu Chess

Real-time chess: no turns, pieces move on a per-piece cooldown, and a
piece can jump to briefly defend its own cell mid-air. This build is a
synthesis of three independent implementations of the same game,
merging the strongest design decision from each (see "Design
provenance" below).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

## Running

```bash
# text mode: reads a Board:/Commands: fixture from stdin or a file
python main.py < tests/integration/scripts/01_rook_move_and_capture.kfc
python main.py path/to/script.kfc

# graphical mode: standard starting position, left click to move,
# right click to jump
python main_gui.py

# tests
pytest -v
pytest --cov=kfchess --cov-report=term-missing
```

## Package layout

```
kfchess/
├── model/      Position, Piece, Board -- pure value objects, no logic
├── rules/      piece shape/path legality, registry-dispatched by kind
├── realtime/   PendingMove/PendingJump, CollisionResolver
├── events/     GameEvent hierarchy + Observer interface
├── engine/     GameEngine (stateless), GameState, game-over rules
├── input/      pixel<->cell mapping, click-to-intent translation
├── io/         text fixture parsing/printing (Board:/Commands: DSL)
├── texttests/  the fixture DSL's parser + composition-root runner
└── gui/        pygame rendering, sprite/animation state machine
```

See [CLAUDE.md](CLAUDE.md) for the architectural rules this layout
enforces.

## Text fixture DSL

```
Board:
WR . . . . . . .
. . . . . . . .
...
Commands:
click <x> <y>
jump <x> <y>
wait <ms>
print board
```

Board tokens are `<color><kind>`, e.g. `WK` (white king), `BP` (black
pawn), `.` for empty. `wait` advances the deterministic game clock by
exactly `<ms>` -- no wall-clock sleeping, so replays are exact and
fast. See `tests/integration/scripts/` for worked examples and
`tests/integration/test_scripted_replays.py` for how they're driven.

## Design provenance

Synthesized from three independent repos of the same game:

- **Engine statelessness** and the richest real-time mechanics (jump,
  cooldown, transit lock, the opposite-color route lock, airborne
  interception) -- ported from the repo whose `GameEngine` took an
  explicit `state: GameState` on every method, with zero state on
  `self`.
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
