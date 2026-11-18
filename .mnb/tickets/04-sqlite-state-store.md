# 04: SQLite WAL State Store

**What to build:** Persistence adapter initializing `PROTOCOL.md` tables in WAL mode and providing atomic `BEGIN IMMEDIATE` lease claim, pheromone upsert, and telemetry logging.
**Blocked by:** `01-pheromone-decay-score`, `02-scope-overlap-check`, `03-gate-ratchet-evaluator`
**Target files:** `packages/mcp/src/adapters/sqlite_store.py`, `packages/mcp/tests/adapters/test_sqlite_store.py`
**Size budget:** <= 20 LOC

## Acceptance Criteria (Deterministic Contracts)
- [ ] Given a fresh DB path, When store initializes, Then `PRAGMA journal_mode` equals `"wal"` and tables `pheromones`, `leases`, `gate_policies`, `telemetry_events` exist.
- [ ] Given an active lease on `["src/a.py"]`, When two concurrent `claim` calls target `["src/a.py"]`, Then exactly `1` succeeds and `1` returns `CONFLICT_LEASED`.
- [ ] Given `emit_pheromone` with `release_slice_id = "s1"`, When executed, Then pheromone row exists and lease `"s1"` is deleted in the same transaction.

## Deterministic Verification
- Unit test path: `packages/mcp/tests/adapters/test_sqlite_store.py`
- Mutation target: `packages/mcp/src/adapters/sqlite_store.py`
- Mutants to kill:
  - Omitting `BEGIN IMMEDIATE` or skipping overlap check before insert must turn tests red.
  - Leaving lease row present when `release_slice_id` is passed must turn tests red.
