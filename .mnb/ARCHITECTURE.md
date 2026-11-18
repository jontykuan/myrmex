# `myrmex` Topological Architecture

Layer boundaries and forbidden imports for building `myrmex`.

## Layers

1. **Field & Ratchet Core** (`packages/mcp/src/core/`): Pure domain logic for pheromone decay math, net-score ranking, scope overlap detection, and gate escalation rules.
2. **Persistence & Git Adapters** (`packages/mcp/src/adapters/`): SQLite WAL storage and Git worktree/rebase/merge subprocess execution.
3. **MCP Server Surface** (`packages/mcp/src/server/`): JSON-RPC tool handlers (`sense_field`, `claim_slice`, `heartbeat_lease`, `emit_pheromone`, `verify_and_merge`).
4. **Headless Worker Runner** (`packages/runner/src/`): Autonomous LLM agent loop connecting to `myrmex-mcp` and local worktree tools.

## Forbidden Imports

- **Field & Ratchet Core** MUST NOT import Persistence, Git Adapters, MCP Server, or LLM SDKs.
- **Headless Worker Runner** MUST NOT import SQLite or Persistence Adapters directly; all state transitions flow through `myrmex-mcp` tools.
- **Benchmark Targets** (`benchmarks/`) MUST NOT import `packages/mcp` or `packages/runner`.
