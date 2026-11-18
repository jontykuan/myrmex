# 03: Evolutionary Gate Ratchet Evaluator

**What to build:** Pure evaluation function that inspects recent `telemetry_events` counts and returns inactive `gate_id`s whose escalation thresholds are met.
**Blocked by:** None (frontier)
**Target files:** `packages/mcp/src/core/ratchet.py`, `packages/mcp/tests/core/test_ratchet.py`
**Size budget:** <= 20 LOC

## Acceptance Criteria (Deterministic Contracts)
- [ ] Given inactive `strict_typecheck` and `3` cumulative `type_error` telemetry events, When ratchet evaluates, Then return value deep_equals `["strict_typecheck"]`.
- [ ] Given inactive `diff_must_add_tests` and `2` `post_merge_regression` events in the last `10` merges, When ratchet evaluates, Then return value contains `"diff_must_add_tests"`.
- [ ] Given active Tier 1 gates, `first_pass_gate_rate = 0.4` over last `8` attempts, and inactive `ast_complexity_cap`, When ratchet evaluates, Then return value contains `"ast_complexity_cap"`.

## Deterministic Verification
- Unit test path: `packages/mcp/tests/core/test_ratchet.py`
- Mutation target: `packages/mcp/src/core/ratchet.py`
- Mutants to kill:
  - Flipping `>= 3` to `> 3` on `type_error` count must turn tests red.
  - Flipping `< 0.5` to `<= 0.5` or ignoring Tier 1 active precondition must turn tests red.
