# `myrmex` Domain Glossary

Ubiquitous language for the `myrmex` system.

- **Colony**: The complete decentralized multi-agent system composed of autonomous workers interacting solely through a shared environment.
- **Worker (Ant)**: An autonomous, episodic cognitive agent with its own reasoning loop and tools. Clears episodic memory between tasks and coordinates exclusively via the pressure field.
- **Gate (Physics)**: Deterministic, non-cognitive environment verification (rebase, build, tests, static analysis, mutation testing) that accepts or rejects a worker's output.
- **Pheromone**: A persistent, time-decaying environmental signal attached to a target slice or file scope, carrying either attractive demand or repulsive contention state.
- **Pressure Field**: The net attractiveness landscape computed from all active, non-expired pheromones minus active leases.
- **Lease**: An exclusive, time-bounded atomic lock granting one worker sole write access to a declared file scope inside an isolated worktree.
- **Slice**: A vertical, end-to-end unit of work bounded to a specific file scope and acceptance contract.
- **Ratchet**: The monotonic escalation mechanism that activates stricter gate tiers when empirical telemetry crosses failure thresholds.
- **In-Colony Regression**: A previously passing visible test turning red after a merge onto the target branch, driving automatic gate escalation.
- **Holdout Suite**: An external, hidden acceptance test suite invisible to all agents during execution, used solely for post-hoc benchmark scoring.
