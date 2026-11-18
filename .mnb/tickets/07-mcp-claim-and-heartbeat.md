# 07: MCP `claim_slice` & `heartbeat_lease` Handlers

**What to build:** MCP tool handlers for atomic `claim_slice` (lease + worktree provisioning) and `heartbeat_lease` TTL extension.
**Blocked by:** `02-scope-overlap-check`, `04-sqlite-state-store`, `05-git-worktree-adapter`
**Target files:** `packages/mcp/src/server/lease_tools.py`, `packages/mcp/tests/server/test_lease_tools.py`
**Size budget:** <= 20 LOC

## Acceptance Criteria (Deterministic Contracts)
- [ ] Given unleased slice `"s1"` with `file_scope=["src/a.py"]`, When `claim_slice(worker_id="w1", slice_id="s1", file_scope=["src/a.py"], ttl_sec=60)` runs, Then `status` equals `"CLAIMED"`, `worktree_path` exists on disk, and `telemetry_events` logs `1` `claim` row.
- [ ] Given `"s1"` leased by `"w1"`, When `"w2"` calls `claim_slice` with overlapping `file_scope`, Then `status` equals `"CONFLICT_LEASED"` and worktree creation calls equal `0`.
- [ ] Given active lease `"s1"` owned by `"w1"`, When `heartbeat_lease(worker_id="w1", slice_id="s1", extend_sec=120)` runs, Then `status` equals `"EXTENDED"` and `expires_at` increases by `120`.

## Deterministic Verification
- Unit test path: `packages/mcp/tests/server/test_lease_tools.py`
- Mutation target: `packages/mcp/src/server/lease_tools.py`
- Mutants to kill:
  - Creating a worktree before confirming atomic lease acquisition must turn tests red.
  - Allowing `"w2"` to extend `"w1"`'s lease must turn tests red.
