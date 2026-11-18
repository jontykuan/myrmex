# 01: Pheromone Decay & Net Score

**What to build:** Pure scoring function that filters expired pheromones, applies exponential decay, excludes blocked or leased targets, and ranks candidates by net attractiveness.
**Blocked by:** None (frontier)
**Target files:** `packages/mcp/src/core/scoring.py`, `packages/mcp/tests/core/test_scoring.py`
**Size budget:** <= 20 LOC

## Acceptance Criteria (Deterministic Contracts)
- [ ] Given pheromone `{target_ref: "slice-1", kind: "test_red", intensity: 10.0, decay_rate: 0.0, updated_at: 1000, expires_at: null}` and query `t = 1100`, When scoring runs with `block_threshold = 5.0`, Then `candidates[0]` deep_equals `{target_ref: "slice-1", net_score: 10.0, dominant_kind: "test_red"}`.
- [ ] Given pheromone `{target_ref: "slice-1", kind: "task_seed", intensity: 10.0, decay_rate: 0.01, updated_at: 1000, expires_at: 1050}` at `t = 1050`, When scoring runs, Then `candidates` equals `[]`.
- [ ] Given `blocked_unknown` effective intensity `5.0` on `"slice-1"` and `block_threshold = 5.0`, When scoring runs, Then `"slice-1"` is excluded from `candidates`.

## Deterministic Verification
- Unit test path: `packages/mcp/tests/core/test_scoring.py`
- Mutation target: `packages/mcp/src/core/scoring.py`
- Mutants to kill:
  - Changing `expires_at <= t` to `expires_at < t` must turn tests red.
  - Changing `blocked_sum >= block_threshold` to `>` must turn tests red.
  - Inverting repulsive pheromone subtraction to addition must turn tests red.
