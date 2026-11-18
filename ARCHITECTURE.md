# `myrmex` — Conceptual Architecture

> **Status**: Conceptual Architecture (Pre-Implementation)  
> **Baseline**: Surpasses `mnb-g-worktree` and `mnb-gauntlet`  
> **Portability**: Runtime- and container-agnostic (local `stdio` + SQLite WAL first; `Streamable HTTP` for remote/Colab runners)

## 1. Structural Delta vs. `mnb`

| Axis | `mnb` (`mnb-g-worktree` + `mnb-gauntlet`) | `myrmex` |
| :--- | :--- | :--- |
| **Scheduling** | Centralized wave barrier: coordinator computes `.mnb/tickets` frontier, dispatches worktrees, blocks until all wave merges complete. | Asynchronous pressure field: stateless workers sense local gradients, claim uncontested slices, and merge atomically without barriers. |
| **Memory** | Coordinator context grows per wave and subagent report. | Environment as SSOT: state lives solely in SQLite (pheromones, leases) and Git (worktrees, commits). |
| **Conflict Handling** | Static DAG requires coordinator intervention on merge conflicts or cascading type errors. | Repulsive pheromones (`conflict_hotspot`, `blocked_unknown`) divert workers away from contested regions automatically. |
| **Quality Gates** | Fixed high-rigor gates upfront (Typecheck + Lint + Mutation Testing 0-survivor + CC <= 10) regardless of task risk. | Evolutionary gate ratchet: starts at Tier 0 physical invariants; escalates to Tier 1/2 gates only when empirical telemetry shows regression or failure clusters. |

## 2. Four-Plane Decoupled Topology

```text
[ 1. Control Plane: Architect Terminal (`agy` / CLI) ]
     Clarify spec, inspect field hotspots, intervene on `blocked_unknown`
                          │ MCP JSON-RPC (stdio / Streamable HTTP)
                          ▼
[ 2. State & Physics Plane: `myrmex-mcp` ]
     SQLite WAL (pheromones, leases, telemetry) + Git Worktree engine + Gate runner
                          ▲ MCP JSON-RPC (stdio / Streamable HTTP)
                          │
[ 3. Execution Plane: `myrmex-runner` ]
     Stateless headless loop (`Sense -> Claim -> Act -> Verify`), container-portable
                          │ Loads
                          ▼
[ 4. Behavioral Plane: `skills/myrmex-worker/SKILL.md` ]
     Declarative worker protocol
```

* **Phase 1 (Local)**: `myrmex-mcp` runs over `stdio` against a local SQLite WAL file and `.worktrees/` for zero-latency A/B benchmarking.
* **Phase 2 (Distributed / Container)**: `myrmex-mcp` exposes `Streamable HTTP` over a shared Git remote so external containers (Docker, Colab, CI) join the same field.

## 3. Disclosed References

* **Schemas, Decay Math, MCP Contracts, Gate Ratchet Rules**: [`PROTOCOL.md`](PROTOCOL.md)
* **Worker Execution Loop**: [`skills/myrmex-worker/SKILL.md`](skills/myrmex-worker/SKILL.md)
