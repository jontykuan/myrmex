# 10: `bench-01` Dual-Stack Scaffold & Holdout Referee

**What to build:** Frozen `base-commit` scaffolds for `benchmarks/bench-01/ts` and `benchmarks/bench-01/py` with `.myrmex/gates.json`, seed `task_seed` pheromones for the 4 slices in `BENCHMARK.md`, and an isolated post-hoc Holdout runner.
**Blocked by:** None (frontier)
**Target files:** `benchmarks/bench-01/ts/`, `benchmarks/bench-01/py/`, `benchmarks/holdout/bench-01/`
**Size budget:** <= 20 LOC per slice stub

## Acceptance Criteria (Deterministic Contracts)
- [ ] Given `benchmarks/bench-01/ts` and `benchmarks/bench-01/py` at `base-commit`, When Tier 0 `base_build_test` runs, Then both suites exit `0` on baseline stubs.
- [ ] Given `.myrmex/gates.json` in both `ts/` and `py/`, When parsed, Then all `6` gate IDs in `BENCHMARK.md` map to valid CLI commands.
- [ ] Given `benchmarks/holdout/bench-01/` is run against unmodified `base-commit`, When Holdout Referee executes, Then `Holdout Pass Rate` equals `0%` (proving non-trivial requirements).

## Deterministic Verification
- Unit test path: `benchmarks/bench-01/ts/tests/`, `benchmarks/bench-01/py/tests/`
- Mutation target: `benchmarks/holdout/bench-01/` (external referee verification)
- Mutants to kill:
  - Holdout passing `> 0%` on unmodified `base-commit` stubs must fail verification.
