# Server Design — Scaling Kung Fu Chess to 100M Users

This document answers the four scaling questions from the review, using
the distributed architecture diagram ("Distributed Game Server
Architecture" — API Gateway / WS Gateway / Matchmaker / Game Allocator /
Game Server Shards / NATS / Redis / PostgreSQL / K3s) as the target
design, and is explicit throughout about what's actually implemented in
this repository today versus what's proposed for scale.

## 0. Where we actually are today

The current codebase (`server/`, `protocol/`, `client/`) is **one `ServerApp` process**:
one `Bus`, one in-memory `RoomManager`, one `GameManager` holding every
active room's `GameEngine`/`GameState` in a Python dict, one SQLite file
via `UserStore`. It's a real, working, tested server (291 tests, a real
websocket integration test) — but it is deployment mode #1 of the two the
architecture doc distinguishes ("Architecture vs Deployment"): a single
process holding every role. Everything below is the design for mode #2:
the same layered architecture, physically spread across many processes
and machines. The `GameEngine` itself — the actual game rules — does not
change between the two modes; that separation is the entire point of
this project's architecture (see `ARCHITECTURE.md` rules 1–2).

**What ships with this document, working today:** a `Dockerfile` +
`docker-compose.yml` that containerize the existing single-process
server (`docker compose up --build`, then `python client_main.py
ws://localhost:8765` from a machine with a display). That's deployment
mode #1, containerized. The multi-shard design below is the proposed
target, not yet implemented in code — a deliberate choice: a small
thing that runs beats a large distributed system sketched out in code
that doesn't.

---

## 1. Database at 100M registered users: is SQLite suitable?

**No.** SQLite is genuinely the right choice for *this project's current
scope* (a single process, one file, zero operational overhead — see
`server/auth.py`'s `UserStore`), but it stops being appropriate long
before 100M users, for reasons that are structural, not just "it'll be
slow":

- **One writer at a time, period.** SQLite serializes all writes through
  a single file lock. The moment there's more than one server *process*
  (which there must be, well before 10M concurrent users — see §2), every
  one of them would need to write to that same file. Either they all
  share one file over a network filesystem (itself a slow, unreliable
  single point of failure), or each process gets its own file (now user
  data is split across machines with no consistency story at all).
- **No client/server protocol.** SQLite is an in-process library, not a
  service other machines connect to. A distributed fleet of Game Server
  Shards and API Gateway replicas needs a database they can all open a
  *network connection* to concurrently.
- **No replication, HA, or backup story built in.** At 100M users, losing
  the single database file is losing the business. Production databases
  at this scale need streaming replication, point-in-time recovery, and
  usually read replicas to spread query load.
- **No concurrent connection pooling.** Thousands of app processes each
  need a small, bounded number of real database connections (via
  something like PgBouncer) — SQLite has no concept of this at all.

**Recommendation: PostgreSQL**, exactly as the provided diagram shows,
for the durable data: `users`, `games`, `results`, `move history`.
Reasoning:
- Real MVCC concurrency — many simultaneous readers and writers without
  the single-writer bottleneck.
- Connection pooling (PgBouncer/pgbouncer-in-front) lets a fleet of
  stateless app processes share a small pool of real backend connections
  instead of each holding one open.
- Read replicas for horizontal read scaling (rating lookups, match
  history) without touching the write path.
- Partitioning for the tables that grow unbounded — `move_history` in
  particular, which grows by every move of every game, forever; a
  time-based or user-id-hash partition scheme keeps individual partitions
  a manageable size and keeps old data archivable/droppable.
- Mature backup/HA tooling (WAL streaming, point-in-time recovery) that
  a 100M-user product actually needs operationally.

**Migration path from the current code is small**, and this is worth
calling out explicitly: `UserStore`'s public interface
(`get`/`create`/`set_password`/`rating_for`/`record_game_result`) already
hides SQLite completely behind it — "the database stores records, not
game objects... it is not part of the Model layer," in the architecture
doc's own words. Only `UserStore`'s *internals* need to change (swap
`sqlite3` calls for `asyncpg`/SQLAlchemy against a connection pool);
`AuthService`, `RatingUpdateSubscriber`, and everything else that calls
`UserStore` doesn't need to change at all.

**Where Redis fits, distinct from Postgres:** Redis is not a
SQLite/Postgres alternative — it holds different data with different
durability requirements: sessions (`connection_id ↔ username`, which
`ConnectionManager` already models in memory today), the active-room
registry (`room_id → which shard owns it`), reconnect grace-period
timers (`GameManager`'s `_pending_disconnects` today), and the
matchmaking queue (`Matchmaker`'s in-memory list today). None of this
needs to survive a crash the way a user's rating does — it needs to be
*fast* and *shared across every Gateway/Shard process*, which is exactly
what today's in-memory dicts in `RoomManager`/`ConnectionManager`/
`Matchmaker` cannot be, the instant there's more than one process (§2).

---

## 2. 10M concurrent users: one process is not enough

**No, one server is nowhere near enough**, and the reasons split into
"raw capacity" and "a genuinely different problem: routing."

### 2.1 Why one process can't hold 10M connections

A single `ServerApp` today is one asyncio event loop on one process: one
CPU core doing the useful work (Python's GIL), memory overhead per open
websocket connection, and CPU for every active room's `GameEngine.tick()`.
Long before CPU or memory limits bite, **network bandwidth alone rules
it out** — see the exact numbers in §3: the outbound traffic for 10M
concurrently active players is on the order of tens of Gbps, far past
what one machine's NIC handles. This has to be many machines, each
running many Game Server Shard processes, from the start.

### 2.2 The real problem: routing, not just "more processes"

Splitting into many processes creates a problem a single process never
has: a client's actual **WebSocket connection** is held open by exactly
one specific WS Gateway process, but the room's authoritative
`GameEngine`/`GameState` lives in exactly one specific Game Server Shard
process — and those are two different, independently-scaled fleets.
Neither one has any built-in way to find the other.

**The fix is a shared registry (Redis) plus a shared bus (NATS)**, which
is the reason those two both appear in the diagram:

- **Redis holds the routing facts**: `room_id → shard address`,
  `connection_id → gateway address`, plus the matchmaking queue and
  session/reconnect state (§1). Any Gateway node, on receiving
  `create_room`/`join_room`/`play`, consults *this shared registry*, not
  its own local memory — which is exactly why any player can create or
  join any room regardless of which Gateway instance they happen to be
  connected to, and why matchmaking can pair two players who have never
  touched the same process.
- **NATS carries the actual traffic between Gateways and Shards.** Once a
  room is assigned to shard `S` (by the Game Allocator, below), every
  Gateway holding a socket for one of that room's members publishes that
  player's commands to a subject shard `S` subscribes to; `S` runs the
  *exact same, unmodified* `GameEngine.attempt_move`/`tick` this
  project's single-process version already runs, and publishes the
  resulting events back onto a per-room subject; every Gateway currently
  holding a member of that room is subscribed to it and forwards the
  message to its own local sockets. This is a direct generalization of
  code that already exists: `server/event_bridge.py` translating
  `GameEvent → Message`, `server/bus.py`'s in-process publish/subscribe,
  and `server/broadcaster.py`'s room-aware fan-out are exactly this
  mechanism, today, in one process. NATS is the same pattern with the
  process boundary removed.

### 2.3 Dividing roles between the different servers

| Role | Statefulness | How it scales |
|---|---|---|
| **API Gateway** | Stateless (REST: login, room history, matchmaking requests) | Trivially horizontal — any replica behind a load balancer can answer any request |
| **WS Gateway** | Holds live connections (stateful *per socket*, not per game) | Scale by connection count; a client is "sticky" to whichever instance holds its socket, tracked in Redis |
| **Matchmaker** | Coordinates a shared queue | Can be partitioned (e.g. by rating band or region) since the queue itself lives in Redis, not any one process's memory |
| **Game Allocator** | Picks a shard for a new room | Needs fast, cheap decisions (see §4 — churn is very high); a least-loaded pick backed by a Redis counter per shard, or an `Agones` `GameServerAllocation`, both fit |
| **Game Server Shards** | **Stateful** — owns the real, in-memory `GameEngine`/`GameState` for its assigned rooms | Horizontal — this is literally today's `GameManager` running as N independent copies instead of 1, each owning a disjoint subset of rooms |
| **PostgreSQL / Redis** | Shared backing stores | Scale independently of the compute fleet above (replicas, partitioning) |
| **Observability** | Cross-cutting | Every service ships logs/metrics to it; not part of the hot path |

The one invariant that never changes across any of this: **the client
never decides game rules, and neither does any Gateway** — only the
Game Server Shard's `GameEngine` instance is ever allowed to mutate a
`Board` (ARCHITECTURE.md rule 1), exactly as in the single-process version.

---

## 3. Network traffic for 10M concurrently active players

An active player moves roughly once every 2 seconds. Real message sizes,
measured directly from this project's actual `protocol/` encoding (not
estimated):

| Message | Bytes (measured) |
|---|---|
| `MoveCommand` (client → server) | 77 |
| `MoveQueuedMessage` (server → clients) | 135 |
| `MoveEventMessage` (server → clients) | 117 |
| `TimerMessage` (server → clients, per tick) | 40 |

**Inbound (commands):** 10,000,000 players ÷ 2s = **5,000,000
commands/sec** cluster-wide × 77 bytes ≈ 385 MB/s ≈ **3.1 Gbps**.

**Outbound (move results):** each move produces two messages
(`MoveQueuedMessage` then `MoveEventMessage`), each sent to both players
in a 1v1 room: (135 + 117) bytes × 2 recipients = 504 bytes per move ×
5,000,000 moves/sec ≈ 2.52 GB/s ≈ **20.2 Gbps**.

**The dominant cost turns out to be neither of these — it's the tick
clock.** The current implementation (`server/game_manager.py`'s
`_run_ticks`) calls `engine.tick()` on a fixed interval (50ms / 20Hz by
default) for every active room, and *every single tick* fires a
`TimerMessage` that gets broadcast to that room's members, whether or
not anything actually happened:

5,000,000 rooms (10M players ÷ 2) × 20 ticks/sec × 2 recipients × 40
bytes ≈ 8 GB/s ≈ **64 Gbps** — nearly **2.75× the gameplay traffic
combined**, just to keep clocks nominally in sync.

**This is a real finding about our own code, not a hypothetical.** It's
invisible at the scale this project currently runs at (a handful of
rooms in a test), and becomes the single largest cost at 10M-user scale.
The fix doesn't need new infrastructure, just a smaller, deliberate
change: stop broadcasting a `TimerMessage` every tick, and send one
only occasionally (e.g. once per second, for drift correction) — every
other message a client actually needs already carries the server's
absolute clock (`start_time`/`arrival_time` on `MoveQueuedMessage`, etc.),
which is all `kfchess.gui.motion_interpolation` needs to animate a move
smoothly between updates; it doesn't need a tick-for-tick lockstep clock.
Throttling to 1 Hz cuts that 64 Gbps down to **3.2 Gbps** — bringing the
realistic total to **3.1 + 20.2 + 3.2 ≈ 26.5 Gbps** aggregate.

**Is 26.5 Gbps a lot or a little?** Both, depending on what you compare
it to:
- **For one machine, it's enormous** — several times a typical server
  NIC (1/10/25 Gbps) — which is exactly why the WS Gateway tier has to be
  scaled by *bandwidth*, not just by connection count or CPU. This traffic
  physically cannot live on one box.
- **Per user, it's tiny**: 26.5 Gbps ÷ 10,000,000 users ≈ **2.6 kbps per
  player** — less than a voice call, negligible next to video. Spread
  across, say, 100 WS Gateway instances, each carries roughly 265 Mbps —
  well within a single commodity cloud instance's networking.
- **For the internet, or a datacenter fabric, it's routine** — comparable
  to a single mid-size video-streaming edge node, far below what a
  cloud region's backbone handles as a matter of course. The challenge
  here was never "does the internet have enough bandwidth" — it's
  "is the traffic actually spread across enough independent Gateway
  processes," which is exactly the horizontal-scaling story in §2.

---

## 4. Games lasting 30–90 seconds: what this means for the Dockers

With ~5,000,000 concurrent rooms (§3) each living roughly a minute on
average, the whole cluster is completing on the order of **~83,000
games every second** (5,000,000 rooms ÷ ~60s average lifetime). That
churn rate — not raw concurrency — is what actually shapes the Game
Server Shard and Game Allocator roles:

- **Shards must be long-lived, pre-warmed processes that accept many
  short games over their lifetime — never "one container per game."**
  Spinning up a fresh container per game would mean paying container
  startup latency (hundreds of ms to a few seconds) against a 30–90s
  game — a significant, wasteful fraction of the game's own duration.
  This is exactly the "fleet" model `Agones` provides: already-running
  Game Server Shard pods each accept a *new room allocation* from the
  Game Allocator without restarting, the same way today's single
  `GameManager` accepts a new room into its `self._games` dict without
  restarting the process.
- **Game Allocator decisions have to be cheap**, because they run
  constantly (~83,000 times/sec cluster-wide): a fast heuristic (least-
  loaded shard, tracked via a Redis counter incremented/decremented on
  allocate/release) beats any expensive scheduling computation.
- **Finished-game cleanup is not optional at this churn rate — it's
  existential.** This project already has a known gap: `GameManager`
  never garbage-collects a finished room's entry unless something
  explicitly calls `stop_game`. At single-digit-room scale that's a
  curiosity; at ~83,000 games ending *per second*, failing to free a
  finished game's `GameEngine`/`GameState` immediately on `GameOverEvent`
  would leak the equivalent of the *entire* concurrent working set roughly
  every minute. `stop_game` needs to be wired directly to game-end, not
  left as a manual call.
- **Database writes from game-end events need to be async and batched,
  not synchronous per game.** Every one of those ~83,000 game-ends per
  second wants a rating update (§2's `RatingUpdateSubscriber`, already
  built) and ideally a persisted result + move history. A shard blocking
  its own event loop on a synchronous Postgres write per game-end would
  throttle its ability to keep ticking its *other* active games. The
  right shape: publish a "game ended" fact onto the bus (NATS) and let a
  separate, horizontally-scaled pool of write-behind workers batch-insert
  into PostgreSQL, keeping the Shard's hot path (ticking live games)
  uncoupled from database latency.
- **Autoscaling has to react fast.** A 30–90s game lifetime means load
  can shift quickly (a wave of matches starting or ending together); the
  Game Allocator / fleet autoscaler needs frequent, low-latency
  visibility into each shard's active-room count, not a slowly-averaged
  metric — this is squarely what the Observability box in the diagram
  needs to feed, quickly, back into scaling decisions.

---

## 5. Summary

| Question | Short answer |
|---|---|
| Is SQLite suitable at 100M users? | No — single-writer, no network access, no replication/HA. PostgreSQL for durable data; Redis for ephemeral/shared routing state. `UserStore`'s existing interface makes this a storage-layer swap, not an application-layer rewrite. |
| Is one server enough for 10M concurrent? | No. Needs a fleet of stateless Gateways + stateful Game Server Shards, coordinated through a shared registry (Redis) and a shared bus (NATS) — a direct generalization of this project's existing in-process `Bus`/`GameEventBridge`/`Broadcaster`. |
| How much traffic, and is it a lot? | ~26.5 Gbps aggregate with a naive tick-broadcast fixed (down from ~87 Gbps unfixed) — huge for one machine, ~2.6 kbps per player, routine for a datacenter fabric once spread across enough Gateway instances. |
| What does a 30–90s game mean for the Dockers? | Extremely high room churn (~83k games/sec) demands long-lived pre-warmed shard fleets, cheap allocator decisions, prompt in-memory cleanup on game-end, and async/batched database writes — none of which matter at small scale, all of which matter enormously here. |

**What's delivered now:** `Dockerfile` + `docker-compose.yml`,
containerizing today's real, working single-process server (`docker
compose up --build`). **What's proposed, not yet built:** the sharded,
NATS/Redis/PostgreSQL/K3s design above. Per the guidance this document
was written against — small and working beats large and unfinished.
