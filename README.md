# Kung Fu Chess

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

```bash
# text mode: reads a Board:/Commands: fixture from stdin or a file
python main.py < tests/integration/scripts/01_rook_move_and_capture.kfc
python main.py path/to/script.kfc

# graphical mode: standard starting position. Left click to select,
# then left click a destination to move, or click the same square
# again to jump in place.
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
├── engine/     GameEngine (stateless), GameState, game-over rules, move history
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
`tests/integration/test_scripted_replays.py` for how they're driven.

## Move history

`kfchess/engine/move_history.py`'s `MoveHistory` is an `Observer` (see
`kfchess/events/events.py`) that logs every completed move, split by
color, purely by reacting to the `MoveCompletedEvent` `GameEngine`
already fires -- it adds no work to `GameEngine`'s own methods and
isn't referenced by them at all. Register one with
`engine.add_observer(history)` and read it back with
`history.moves_for(WHITE)` / `history.moves_for(BLACK)`, or render it
as text with `kfchess/io/history_printer.py`. Both `ScriptRunner` (text
mode, via `print history`) and `GameLoop` (`.move_history`, printed to
stdout on quit) wire one up automatically.

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
