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
5. Real-time mechanics (pending moves, airborne jumps, cooldowns) live in
   `kfchess/realtime/` and `kfchess/engine/game_engine.py`'s orchestration --
   never duplicated elsewhere. A jump is only ever triggered by clicking a
   selected piece's own square again (`ClickController`) -- there is no
   separate jump gesture or pixel-based `GameEngine` entry point;
   `GameEngine.attempt_jump` takes a `Position`, not raw pixels. There is no
   advance route reservation of any kind: `attempt_move` never inspects
   other pending moves, and a mover only ever reacts to whatever -- friend
   or enemy -- is actually occupying its path when it resolves
   (`CollisionResolver.stop_before_block`), stopping one square short if
   so. Do not reintroduce a route/lane lock at queue time.
6. Rendering, asset loading, and pixel math (`kfchess/gui/`) never touch
   `kfchess.model` or `kfchess.engine` mutation methods directly -- they
   subscribe to `GameEvent`s via the `Observer` interface
   (`kfchess/events/events.py`) and otherwise only read `GameState`.
7. Every new mechanic ships with a unit test under `tests/unit/`, and if it
   changes cross-piece timing behavior, a scripted `.kfc` replay under
   `tests/integration/scripts/` exercised via `test_scripted_replays.py`.
8. Bookkeeping about what already happened (a move log, a captured-piece
   count, a move counter, ...) is an `Observer`, never a field added to
   `GameEngine` or logic added to its methods. `GameEngine` fires the
   event it already fires either way; the Observer is registered via
   `add_observer` and reacts afterward, so `GameEngine`'s own methods stay
   completely unaware such bookkeeping exists. `kfchess/engine/move_history.py`'s
   `MoveHistory` is the reference example. This is *not* where legality
   checking goes, though -- an `Observer` only ever runs after `GameEngine`
   has already decided and mutated the board, so it has no way to veto
   anything; legality stays synchronous, in `RuleEngine`, consulted from
   inside `attempt_move`/`_resolve_due_move` before any mutation happens.
9. A piece that's currently in flight (has a not-yet-resolved `PendingMove`)
   is not real-world "at" its origin anymore, even though the real `Board`
   keeps it recorded there until the move resolves (rendering and the
   text-mode printer both need that raw snapshot -- see rule 1's exception
   below). Nothing else may be blocked by it, or capture it, at that stale
   origin: `attempt_move` and `_resolve_due_move` both evaluate legality
   against a `_VacatedOriginsView` (in `game_engine.py`) that reports every
   other pending move's origin as empty, never against the raw `Board`
   directly. Do not "fix" a collision bug by reverting to raw `board.get()`
   in these two methods -- that's exactly what caused a piece to be
   captured at a square it had already left. The raw `Board` itself must
   stay untouched until a move actually resolves; that's what rule 1's
   "only `GameEngine` mutates a `Board`" is protecting, not contradicting.
