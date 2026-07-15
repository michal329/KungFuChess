# Architecture rules for this project

1. `GameEngine` is the ONLY thing that ever mutates a `Board`. `RuleEngine`,
   `CollisionResolver`, and `ClickController` only ever read it.
2. `GameEngine` holds no per-game state on `self`. Every action method takes
   `state: GameState` explicitly. This lets one engine drive many games and
   makes every method trivially unit-testable without setup/teardown races.
3. Piece legality is a registry (`dict[kind -> rule_fn]` in
   `kfchess/rules/piece_rules.py`), never an if/elif/switch on piece type.
   Adding a piece is one function plus one registry entry.
4. No bare strings for board contents in `kfchess.model` or `kfchess.engine`.
   Use `Piece(kind, color)` and `Position(row, col)` value objects. String
   `<color><kind>` tokens (e.g. `"WK"`) exist only at the `kfchess.io`
   boundary (fixture parsing/printing).
5. Real-time mechanics (pending moves, airborne jumps, cooldowns, the
   opposite-color route lock) live in `kfchess/realtime/` and
   `kfchess/engine/game_engine.py`'s orchestration -- never duplicated
   elsewhere.
6. Rendering, asset loading, and pixel math (`kfchess/gui/`) never touch
   `kfchess.model` or `kfchess.engine` mutation methods directly -- they
   subscribe to `GameEvent`s via the `Observer` interface
   (`kfchess/events/events.py`) and otherwise only read `GameState`.
7. Every new mechanic ships with a unit test under `tests/unit/`, and if it
   changes cross-piece timing behavior, a scripted `.kfc` replay under
   `tests/integration/scripts/` exercised via `test_scripted_replays.py`.
