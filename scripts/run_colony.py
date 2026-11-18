import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import time
from packages.mcp.src.adapters.sqlite_store import SqliteStateStore
from packages.runner.src.genai_client import GenAILlmClient, resolve_api_key
from packages.runner.src.local_mcp_bridge import LocalMcpBridge
from packages.runner.src.openai_client import OpenAICompatLlmClient
from packages.runner.src.worker import LlmClient, WorkerConfig, run_cycle

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


def seed_environment(store: SqliteStateStore, gates_file: Path, rel_prefix: str = "") -> None:
    gates = json.loads(gates_file.read_text(encoding="utf-8"))
    for gate_id, cmd in gates.items():
        tier, active = GATE_TIERS.get(gate_id, (1, 0))
        store.upsert_gate_policy(gate_id, tier, cmd, active)
    now = int(time.time())
    prefix = f"{rel_prefix.strip('/')}/" if rel_prefix.strip("/") else ""
    for slice_id, scope in DEFAULT_SEEDS:
        scoped = [f"{prefix}{p}" for p in scope]
        store.emit_pheromone("architect", slice_id, "task_seed", 10.0, 0.0, None, {"file_scope": scoped}, now)


def _worker_loop(
    db_path: Path,
    git_root: Path,
    target_branch: str,
    worker_id: str,
    provider: str,
    api_base: str,
    api_key: str,
    model: str,
    max_cycles: int,
) -> list[str]:
    store = SqliteStateStore(db_path)
    mcp = LocalMcpBridge(store, git_root, target_branch=target_branch, worker_id=worker_id)
    llm: LlmClient = (
        OpenAICompatLlmClient(model=model, api_base=api_base)
        if provider == "openai-compat"
        else GenAILlmClient(api_key=api_key, model=model)
    )
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
    parser.add_argument("--provider", choices=["genai", "openai-compat"], default="genai")
    parser.add_argument("--api-base", default="http://localhost:8000/v1")
    parser.add_argument("--model", default="gemini-4-hydrogen")
    args = parser.parse_args()

    api_key = "" if args.provider == "openai-compat" else resolve_api_key()
    target_dir = args.repo.resolve()
    git_root = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=target_dir, text=True).strip())
    target_branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=git_root, text=True).strip()
    rel_prefix = target_dir.relative_to(git_root).as_posix()

    db_path = target_dir / ".myrmex" / "state.db"
    store = SqliteStateStore(db_path)
    seed_environment(store, target_dir / ".myrmex" / "gates.json", rel_prefix=rel_prefix)
    store.close()

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(
                _worker_loop, db_path, git_root, target_branch, f"ant-{i+1}", args.provider, args.api_base, api_key, args.model, args.cycles
            )
            for i in range(args.workers)
        ]
        for i, fut in enumerate(futures):
            print(f"ant-{i+1}: {fut.result()}")


if __name__ == "__main__":
    main()
