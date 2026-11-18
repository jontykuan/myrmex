# `myrmex` Benchmark #1 — Tier 0→2 Evolution & A/B Contract

> **Target**: `benchmarks/bench-01/{ts,py}` (self-contained, zero-external-dependency rule engine / task scheduler)  
> **References**: [`ARCHITECTURE.md`](ARCHITECTURE.md) | [`PROTOCOL.md`](PROTOCOL.md) | [`skills/myrmex-worker/SKILL.md`](skills/myrmex-worker/SKILL.md)

## 1. Verification Objectives

1. **A/B Superiority**: Outperform `mnb` (`mnb-g-worktree` + `mnb-gauntlet`) on `Tokens per Solved Task` and `Wall-clock Duration` while matching or exceeding `Holdout Pass Rate`.
2. **Autonomous Gate Ratchet**: Start `exp/myrmex-colony` with Tier 0 active only (`git_clean_rebase`, `base_build_test`) and observe `telemetry_events` autonomously escalate through Tier 1 and Tier 2 via real failure signals.

## 2. Controlled Variables (A/B Parity)

| Variable | Control (`exp/mnb-baseline`) | Treatment (`exp/myrmex-colony`) |
| :--- | :--- | :--- |
| **Starting State** | Identical frozen `base-commit` in `bench-01/ts` and `bench-01/py` | Identical frozen `base-commit` in `bench-01/ts` and `bench-01/py` |
| **Model** | `gemini-4-hydrogen` (Google AI Studio / `agy`, identical decoding params) | `gemini-4-hydrogen` (Google AI Studio Free Tier via `google-genai` SDK) |
| **Workflow** | `/mnb-slice` → `/mnb-g-worktree` → `/mnb-gauntlet` | $N$ stateless `myrmex-runner` workers running `myrmex-worker` |
| **Initial Gates** | Full `mnb-gauntlet` rigour from step 1 | Tier 0 only (ratchet enabled per [`PROTOCOL.md`](PROTOCOL.md)) |
| **Holdout Visibility** | Hidden during execution | Hidden during execution |

## 3. Task Graph (`bench-01` Slices)

Both `ts/` and `py/` implement identical domain contracts across four vertical slices:

| Slice ID | Domain Scope | Engineered Stress Vector |
| :--- | :--- | :--- |
| `slice-01-core-eval` | Rule evaluation over typed facts | Shares core types/exports with `slice-02` to test `claim_slice` scope locking. |
| `slice-02-priority-queue` | Deterministic task scheduling & tie-breaking | Contends on shared seam with `slice-01` to trigger `conflict_hotspot` diversion. |
| `slice-03-input-parser` | Strict schema/union parsing & error normalization | Induces type-escape shortcuts (`as`/`any`), testing `type_error` → Tier 1 `strict_typecheck`. |
| `slice-04-window-bounds` | Time-window & boundary matching (`<` vs `<=`, empty sets) | Shallow happy-path tests pass Tier 0; visible integration failure triggers `post_merge_regression` → Tier 1 `diff_must_add_tests` → Tier 2 `mutation_test` / `ast_complexity_cap`. |

## 4. In-Colony Regression vs. Third-Party Holdout Referee

* **In-Colony Signal (`post_merge_regression`)**: After each `verify_and_merge` commits to `MYRMEX_TARGET_BRANCH`, `myrmex-mcp` runs the repository's **visible** test suite on the merged tip. A previously passing visible test turning red logs `post_merge_regression` to `telemetry_events` and emits `test_red`, driving the Tier 0→2 ratchet automatically.
* **External Referee (`Holdout Suite`)**: Stored in an isolated evaluation path excluded from both worktrees and agent context. Executed post-hoc against final and per-merge commits to record the immutable A/B scorecard without influencing colony evolution.

## 5. Portable Gate Mapping (`.myrmex/gates.json`)

| `gate_id` | `bench-01/ts` Command | `bench-01/py` Command |
| :--- | :--- | :--- |
| `base_build_test` | `npm test` | `pytest -q` |
| `diff_must_add_tests` | `node scripts/check-test-diff.mjs` | `python scripts/check_test_diff.py` |
| `strict_typecheck` | `npx tsc --noEmit && node scripts/ban-type-escapes.mjs` | `mypy --strict src tests` |
| `slice_loc_cap` | `node scripts/check-diff-loc.mjs 40` | `python scripts/check_diff_loc.py 40` |
| `ast_complexity_cap` | `npx eslint --rule "complexity: [error, 10]" src` | `radon cc src -n C -e` |
| `mutation_test` | `npx stryker run` | `mutmut run --CI` |

## 6. Evaluation Scorecard & Completion Criteria

A benchmark run is **complete** when all four slices are merged (or marked `blocked_unknown` exceeding `MYRMEX_BLOCK_THRESHOLD`) and the Holdout Suite finishes post-hoc evaluation.

* **Primary Metrics**:
  * `Tokens per Solved Task` (sum of `prompt_token_count` + `candidates_token_count` + `thoughts_token_count`, counted only when `Holdout Pass == 100%`)
  * `Holdout Pass Rate (%)` & `First-pass Gate Rate (%)`
  * `Active Compute Duration (s)` (wall-clock minus `429` rate-limit backoff) & `Merge Conflict / Rollback Count`
* **Evolution Proof Criterion**: `telemetry_events` in `exp/myrmex-colony` contains at least one autonomous `gate_escalate` event from Tier 0→1 and Tier 1→2 without human intervention.
