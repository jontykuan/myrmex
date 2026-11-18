# 09: Headless `myrmex-runner` Episodic Agent Loop

**What to build:** Standalone, container-portable worker runner executing one episodic `Sense -> Claim -> Act -> Verify` cycle per wake-up using `skills/myrmex-worker/SKILL.md`, MCP `stdio`, and `google-genai` (`gemini-4-hydrogen`) with `429` exponential backoff + jitter and token telemetry (`prompt`, `candidates`, `thoughts`).
**Blocked by:** `06-mcp-sense-and-emit`, `07-mcp-claim-and-heartbeat`, `08-mcp-verify-and-merge`
**Target files:** `packages/runner/src/worker.py`, `packages/runner/tests/test_worker.py`
**Size budget:** <= 20 LOC

## Acceptance Criteria (Deterministic Contracts)
- [ ] Given `sense_field` returns `candidates: []`, When `run_cycle()` executes, Then `llm_calls` equals `0` and exit status equals `"IDLE"`.
- [ ] Given a mock `google-genai` client returning a valid patch inside `worktree_path` and calling `verify_and_merge`, When `run_cycle()` executes, Then `telemetry_events` records `tokens_in`, `tokens_out` (including `thoughts_token_count`) > `0` and cycle returns `"MERGED"`.
- [ ] Given `google-genai` raises `429 RESOURCE_EXHAUSTED` once before succeeding, When `run_cycle()` executes, Then backoff retries without crashing and logs `rate_limit_wait_ms` > `0`.
- [ ] Given two consecutive `run_cycle()` calls, When the second cycle starts, Then message history length at start equals `0` (episodic memory cleared).

## Deterministic Verification
- Unit test path: `packages/runner/tests/test_worker.py`
- Mutation target: `packages/runner/src/worker.py`
- Mutants to kill:
  - Retaining conversation messages across `run_cycle()` boundaries must turn tests red.
  - Invoking LLM when `candidates` is empty must turn tests red.
