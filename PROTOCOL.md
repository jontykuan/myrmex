# `myrmex-mcp` Protocol & Gate Specification

> **Version**: 0.1.0-draft  
> **Transport**: MCP JSON-RPC 2.0 (`stdio` local; `Streamable HTTP` remote)  
> **SSOT**: SQLite (WAL mode) + Git Worktrees

## 1. Environment Configuration

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `MYRMEX_REPO_ROOT` | `.` | Git repository root |
| `MYRMEX_DB_PATH` | `.myrmex/state.db` | SQLite WAL database path |
| `MYRMEX_TARGET_BRANCH` | `main` | Rebase and atomic merge target branch |
| `MYRMEX_WORKTREE_DIR` | `.worktrees` | Isolated worktree directory |
| `MYRMEX_DEFAULT_TTL_SEC` | `180` | Default lease TTL in seconds |
| `MYRMEX_BLOCK_THRESHOLD` | `5.0` | `blocked_unknown` intensity ceiling before hiding a target from `sense_field` |

## 2. SQLite Schema

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS pheromones (
  id          TEXT PRIMARY KEY,
  target_ref  TEXT NOT NULL,
  kind        TEXT NOT NULL CHECK (kind IN (
                'task_seed', 'test_red', 'type_error', 'smell_refactor',
                'conflict_hotspot', 'blocked_unknown'
              )),
  intensity   REAL NOT NULL,
  decay_rate  REAL NOT NULL,
  payload     TEXT,               -- Compact JSON diagnostic summary
  emitter_id  TEXT NOT NULL,
  created_at  INTEGER NOT NULL,
  updated_at  INTEGER NOT NULL,
  expires_at  INTEGER             -- NULL = explicit removal required
);

CREATE INDEX IF NOT EXISTS idx_pheromones_target ON pheromones(target_ref, kind);
CREATE INDEX IF NOT EXISTS idx_pheromones_expiry ON pheromones(expires_at);

CREATE TABLE IF NOT EXISTS leases (
  slice_id    TEXT PRIMARY KEY,
  worker_id   TEXT NOT NULL,
  worktree    TEXT NOT NULL,
  file_scope  TEXT NOT NULL,      -- JSON array of relative path globs
  acquired_at INTEGER NOT NULL,
  expires_at  INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_leases_expiry ON leases(expires_at);

CREATE TABLE IF NOT EXISTS gate_policies (
  gate_id           TEXT PRIMARY KEY,
  tier              INTEGER NOT NULL CHECK (tier IN (0, 1, 2)),
  command           TEXT NOT NULL,
  active            INTEGER NOT NULL CHECK (active IN (0, 1)),
  trigger_rule      TEXT,
  last_triggered_at INTEGER
);

CREATE TABLE IF NOT EXISTS telemetry_events (
  event_id      TEXT PRIMARY KEY,
  experiment_id TEXT,
  task_id       TEXT,
  worker_id     TEXT NOT NULL,
  event_type    TEXT NOT NULL,    -- sense | claim | emit | gate_pass | gate_fail | merge_ok | merge_conflict | gate_escalate
  slice_id      TEXT,
  tokens_in     INTEGER DEFAULT 0,
  tokens_out    INTEGER DEFAULT 0,
  duration_ms   INTEGER DEFAULT 0,
  outcome       TEXT,
  metadata_json TEXT,
  created_at    INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_telemetry_exp ON telemetry_events(experiment_id, task_id);
```

## 3. Field Scoring & Temporal Decay

At query time $t$ (Unix seconds):

1. **Expiry**: Filter out rows where `expires_at IS NOT NULL AND expires_at <= t`.
2. **Effective Intensity**:
   $$I_{\text{eff}}(p, t) = p.\text{intensity} \cdot e^{-p.\text{decay\_rate} \cdot (t - p.\text{updated\_at})}$$
3. **Net Attractiveness Score**:
   $$S(\text{target}, t) = \sum_{p \in \text{Attr}(\text{target})} I_{\text{eff}}(p, t) - \sum_{q \in \text{Repel}(\text{target})} I_{\text{eff}}(q, t)$$
   * $\text{Attr} = \{\text{task\_seed}, \text{test\_red}, \text{type\_error}, \text{smell\_refactor}\}$
   * $\text{Repel} = \{\text{conflict\_hotspot}, \text{blocked\_unknown}\}$
4. **Hard Exclusions**: Exclude targets with an active lease (`leases.expires_at > t`) or `blocked_unknown` sum $\ge \text{MYRMEX\_BLOCK\_THRESHOLD}$.

## 4. MCP Tool Contracts

### `sense_field`
Returns top-$K$ unleased candidates ordered by `net_score` descending, plus `active_gates`.

* **Input**: `{ "worker_id": string, "focus_scope"?: string, "limit"?: integer (1..20, default 5) }`
* **Output**: `{ "timestamp": integer, "candidates": [{ "target_ref": string, "net_score": number, "dominant_kind": string, "pheromones": [{ "kind": string, "effective_intensity": number, "payload": object|null }] }], "active_gates": [{ "gate_id": string, "tier": integer, "command": string }] }`

### `claim_slice`
Atomically acquires a lease inside `BEGIN IMMEDIATE` if no active lease overlaps `file_scope`, then creates the isolated worktree.

* **Input**: `{ "worker_id": string, "slice_id": string, "file_scope": string[] (min 1), "ttl_sec"?: integer (30..1800) }`
* **Output**: `{ "status": "CLAIMED" | "CONFLICT_LEASED" | "WORKTREE_ERROR", "worktree_path"?: string, "branch_name"?: string, "base_commit"?: string, "expires_at"?: integer, "conflict_owner"?: string }`

### `heartbeat_lease`
Extends `expires_at` on an active lease.

* **Input**: `{ "worker_id": string, "slice_id": string, "extend_sec"?: integer (30..600, default 120) }`
* **Output**: `{ "status": "EXTENDED" | "LEASE_EXPIRED", "expires_at"?: integer }`

### `emit_pheromone`
Writes or reinforces a pheromone signal; optionally releases the held lease.

* **Input**: `{ "worker_id": string, "target_ref": string, "kind": "task_seed"|"test_red"|"type_error"|"smell_refactor"|"conflict_hotspot"|"blocked_unknown", "intensity": number (0.1..100), "decay_rate"?: number (default 0.001), "ttl_sec"?: integer|null, "payload"?: object, "release_slice_id"?: string }`
* **Output**: `{ "pheromone_id": string, "updated_intensity": number }`

### `verify_and_merge`
Deterministic merge gate. Executes in strict order:
1. Verify active lease ownership (`LEASE_EXPIRED` on failure).
2. Verify `git diff --name-only` stays within `file_scope` (`SCOPE_VIOLATION` on failure).
3. Run `git rebase <MYRMEX_TARGET_BRANCH>` (`MERGE_CONFLICT` on failure; aborts rebase and emits `conflict_hotspot` with `decay_rate=0.01`).
4. Run `active_gates` ordered by `tier` ascending (`GATE_FAILED` on first non-zero exit; emits `type_error` or `test_red`, logs telemetry, evaluates gate ratchet).
5. Fast-forward/squash merge into `MYRMEX_TARGET_BRANCH`, delete slice attractive pheromones and lease, prune worktree, log `merge_ok`.

* **Input**: `{ "worker_id": string, "slice_id": string, "commit_message"?: string }`
* **Output**: `{ "status": "MERGED" | "MERGE_CONFLICT" | "GATE_FAILED" | "LEASE_EXPIRED" | "SCOPE_VIOLATION", "merged_commit"?: string, "failed_gate_id"?: string, "failure_summary"?: string (<=2000 chars), "escalated_gates"?: string[] }`

## 5. Evolutionary Gate Ratchet

Only **Tier 0** is active at initialization. `verify_and_merge` evaluates `telemetry_events` after each run and flips `gate_policies.active = 1` when a trigger rule fires:

| Tier | `gate_id` | Portable Check | Escalation Trigger (`trigger_rule`) |
| :--- | :--- | :--- | :--- |
| **0** | `git_clean_rebase` | Conflict-free rebase onto target branch | Active by default |
| **0** | `base_build_test` | Project build + unit test suite exits 0 | Active by default |
| **1** | `diff_must_add_tests` | Production diff includes test file diff | `post_merge_regression >= 2` in last 10 merges |
| **1** | `strict_typecheck` | Zero type escapes (`as`/`any`/`@ts-ignore` or `mypy --strict`) | Cumulative `type_error` events `>= 3` |
| **1** | `slice_loc_cap` | Net diff `<= 40 LOC` per merge | Cumulative `conflict_hotspot` events `>= 3` on same target |
| **2** | `ast_complexity_cap` | Cyclomatic complexity `<= 10` per function | `first_pass_gate_rate < 0.5` over last 8 attempts with Tier 1 active |
| **2** | `mutation_test` | Stryker / Mutmut 0 surviving mutants | `post_merge_regression >= 2` while Tier 1 is active |

Projects map `gate_id` to concrete CLI commands in `.myrmex/gates.json`. Unmapped gates are skipped (`UNCONFIGURED`).
