# 06: MCP `sense_field` & `emit_pheromone` Handlers

**What to build:** MCP server tool handlers for `sense_field` and `emit_pheromone` wired to SQLite store and scoring core.
**Blocked by:** `01-pheromone-decay-score`, `04-sqlite-state-store`
**Target files:** `packages/mcp/src/server/field_tools.py`, `packages/mcp/tests/server/test_field_tools.py`
**Size budget:** <= 20 LOC

## Acceptance Criteria (Deterministic Contracts)
- [ ] Given two `task_seed` pheromones with intensities `3.0` and `9.0` and one active `base_build_test` gate, When `sense_field(worker_id="w1", limit=1)` runs, Then `candidates` length equals `1` with `target_ref` matching intensity `9.0` and `active_gates` includes `base_build_test`.
- [ ] Given `emit_pheromone(worker_id="w1", target_ref="s1", kind="test_red", intensity=8.0)`, When invoked, Then `sense_field` reflects `dominant_kind == "test_red"` and `telemetry_events` logs `1` `emit` row.

## Deterministic Verification
- Unit test path: `packages/mcp/tests/server/test_field_tools.py`
- Mutation target: `packages/mcp/src/server/field_tools.py`
- Mutants to kill:
  - Ignoring `limit` parameter or returning ascending instead of descending `net_score` must turn tests red.
  - Skipping `telemetry_events` insert on `emit_pheromone` must turn tests red.
