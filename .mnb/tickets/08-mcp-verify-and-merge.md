# 08: MCP `verify_and_merge` Deterministic Gate Pipeline

**What to build:** MCP handler executing lease check, scope check, rebase, ordered active gates, post-merge visible regression check, and ratchet escalation.
**Blocked by:** `03-gate-ratchet-evaluator`, `04-sqlite-state-store`, `05-git-worktree-adapter`, `07-mcp-claim-and-heartbeat`
**Target files:** `packages/mcp/src/server/merge_tools.py`, `packages/mcp/tests/server/test_merge_tools.py`
**Size budget:** <= 20 LOC

## Acceptance Criteria (Deterministic Contracts)
- [ ] Given `"s1"` passing rebase and all active Tier 0 gates, When `verify_and_merge` runs, Then `status` equals `"MERGED"`, `main` advances by `1` commit, `"s1"` lease and attractive pheromones are deleted, and `.worktrees/s1` is removed.
- [ ] Given an active gate exiting `1`, When `verify_and_merge` runs, Then `status` equals `"GATE_FAILED"`, `main` HEAD is unchanged, `type_error` or `test_red` pheromone is emitted, and `escalated_gates` reflects any triggered ratchet rules.
- [ ] Given a merged commit whose visible test suite on `main` fails a previously passing test, When post-merge check runs, Then `telemetry_events` logs `post_merge_regression` and `test_red` is emitted.

## Deterministic Verification
- Unit test path: `packages/mcp/tests/server/test_merge_tools.py`
- Mutation target: `packages/mcp/src/server/merge_tools.py`
- Mutants to kill:
  - Merging to `main` when a gate exits non-zero must turn tests red.
  - Failing to invoke ratchet evaluator after `gate_fail` or `post_merge_regression` must turn tests red.
