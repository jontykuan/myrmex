import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time
from packages.mcp.src.adapters.sqlite_store import SqliteStateStore
from packages.runner.src.genai_client import GenAILlmClient, resolve_api_key
from packages.runner.src.local_mcp_bridge import LocalMcpBridge
from packages.runner.src.worker import WorkerConfig, run_cycle

DEFAULT_SEEDS = [
    ("slice-01-core-eval", ["src/scheduler.py", "tests/"]),
    ("slice-02-priority-queue", ["src/scheduler.py", "tests/"]),
    ("slice-03-input-parser", ["src/scheduler.py", "tests/"]),
    ("slice-04-window-bounds", ["src/scheduler.py", "tests/"]),
]

GATE_TIERS = {
    "base_build_test": (0, 1),
    "diff_must_add_tests": (1, 0),
    "strict_typecheck": (1, 0),
    "slice_loc_cap": (1, 0),
    "ast_complexity_cap": (2, 0),
    "mutation_test": (2, 0),
}


def seed_environment(store: SqliteStateStore, gates_file: Path) -> None:
    gates = json.loads(gates_file.read_text(encoding="utf-8"))
    for gate_id, cmd in gates.items():
        tier, active = GATE_TIERS.get(gate_id, (1, 0))
        store.upsert_gate_policy(gate_id, tier, cmd, active)
    now = int(time.time())
    for slice_id, scope in DEFAULT_SEEDS:
        store.emit_pheromone("architect", slice_id, "task_seed", 10.0, 0.0, None, {"file_scope": scope}, now)


def _worker_loop(db_path: Path, repo_root: Path, worker_id: str, api_key: str, model: str, max_cycles: int) -> list[str]:
    store = SqliteStateStore(db_path)
    mcp = LocalMcpBridge(store, repo_root, worker_id=worker_id)
    llm = GenAILlmClient(api_key=api_key, model=model)
    cfg = WorkerConfig(worker_id=worker_id, model=model)
    outcomes: list[str] = []
    for _ in range(max_cycles):
        res = run_cycle(mcp, llm, cfg)
        outcomes.append(str(res.get("status")))
        if res.get("status") == "IDLE":
            break
    store.close()
    return outcomes


def main() -> None:
    parser = argparse.ArgumentParser(description="Run myrmex colony locally or on Colab")
    parser.add_argument("--repo", type=Path, default=Path("benchmarks/bench-01/py"))
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--cycles", type=int, default=6)
    parser.add_argument("--model", default="gemini-4-hydrogen")
    args = parser.parse_args()

    api_key = resolve_api_key()
    db_path = args.repo / ".myrmex" / "state.db"
    store = SqliteStateStore(db_path)
    seed_environment(store, args.repo / ".myrmex" / "gates.json")
    store.close()

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(_worker_loop, db_path, args.repo.resolve(), f"ant-{i+1}", api_key, args.model, args.cycles)
            for i in range(args.workers)
        ]
        for i, fut in enumerate(futures):
            print(f"ant-{i+1}: {fut.result()}")


if __name__ == "__main__":
    main()
