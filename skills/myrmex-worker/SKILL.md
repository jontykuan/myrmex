---
name: myrmex-worker
description: Execute one stateless stigmergic work cycle via myrmex-mcp. Trigger when waking up as a myrmex-runner worker to sense the pressure field, claim an unleased slice, differentiate into specifier/builder/cleaner, and merge through deterministic gates.
---

# `myrmex-worker` Execution Protocol

Stateless worker loop over [`PROTOCOL.md`](../../PROTOCOL.md). Communicate exclusively through `myrmex-mcp` field primitives and isolated Git worktrees.

## 1. Sense
Call `sense_field(worker_id, focus_scope?, limit=5)`.
* **Empty `candidates`**: Exit cleanly.
* **Non-empty `candidates`**: Record `active_gates` so all changes satisfy every active gate on the first pass.

**Done when**: Top candidate `target_ref`, `dominant_kind`, and `active_gates` are known.

## 2. Claim
Iterate `candidates` by `net_score` descending and call `claim_slice(worker_id, slice_id, file_scope)`.
* **`CONFLICT_LEASED`**: Move immediately to the next candidate.
* **`CLAIMED`**: Switch working directory to `worktree_path`. Edit only files matching `file_scope`.

**Done when**: An isolated `worktree_path` is acquired, or all candidates are exhausted (exit cleanly).

## 3. Act
Differentiate behavior by `dominant_kind`:
* **`task_seed` (Explorer)**: Write minimal **red** test(s) inside `file_scope`. Verify red locally (`exit != 0`). For a single-function slice, implement minimal green code and proceed to Step 4; otherwise call `emit_pheromone(target_ref, kind="test_red", intensity=8.0, payload={...}, release_slice_id=slice_id)` and exit cleanly.
* **`test_red` | `type_error` (Builder)**: Read `pheromones[].payload`. Write the minimal patch inside `file_scope` to pass all `active_gates` locally.
* **`smell_refactor` (Cleaner)**: Refactor inside `file_scope` to reduce complexity while keeping all `active_gates` green.

Call `heartbeat_lease(worker_id, slice_id)` whenever local execution exceeds 60% of remaining TTL.

**Done when**: Local checks for all `active_gates` exit 0 inside `worktree_path`, or a blocker is confirmed.

## 4. Verify & Release
Call `verify_and_merge(worker_id, slice_id, commit_message)`.
* **`MERGED`**: Exit cleanly (or start next cycle at Step 1).
* **`GATE_FAILED`**: Read `failure_summary`. Fix and retry `verify_and_merge` at most once; if still failing, call `emit_pheromone` with diagnostic `payload` and `release_slice_id=slice_id`, then exit.
* **`MERGE_CONFLICT`**: Exit cleanly so `conflict_hotspot` diverts contention.
* **Unresolvable blocker**: Call `emit_pheromone(target_ref, kind="blocked_unknown", intensity=3.0, payload={"reason": "..."}, release_slice_id=slice_id)` and exit.

**Done when**: `verify_and_merge` returns `MERGED` or the lease is explicitly released via `emit_pheromone` / clean exit.
