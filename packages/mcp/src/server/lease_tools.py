from pathlib import Path
import subprocess
import time
from typing import Any
from packages.mcp.src.adapters.git_worktree import create_worktree
from packages.mcp.src.adapters.sqlite_store import SqliteStateStore


def claim_slice(
    store: SqliteStateStore,
    repo_root: Path,
    wt_root: Path,
    target_branch: str,
    worker_id: str,
    slice_id: str,
    file_scope: list[str],
    ttl_sec: int = 180,
    now: int | None = None,
) -> dict[str, Any]:
    ts = now if now is not None else int(time.time())
    wt_path = wt_root / slice_id
    lease_res = store.acquire_lease(slice_id, worker_id, str(wt_path), file_scope, ts, ttl_sec)
    if lease_res["status"] != "CLAIMED":
        store.log_telemetry(worker_id, "claim", ts, slice_id=slice_id, outcome="CONFLICT_LEASED")
        return lease_res
    try:
        created = create_worktree(repo_root, wt_root, slice_id, target_branch)
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=created, text=True).strip()
    except Exception as exc:
        store.release_lease(slice_id)
        return {"status": "WORKTREE_ERROR", "error": str(exc)}
    store.log_telemetry(worker_id, "claim", ts, slice_id=slice_id, outcome="CLAIMED")
    return {
        "status": "CLAIMED",
        "worktree_path": str(created),
        "branch_name": f"myrmex/{slice_id}",
        "base_commit": head,
        "expires_at": lease_res["expires_at"],
    }


def heartbeat_lease(
    store: SqliteStateStore,
    worker_id: str,
    slice_id: str,
    extend_sec: int = 120,
    now: int | None = None,
) -> dict[str, Any]:
    ts = now if now is not None else int(time.time())
    return store.extend_lease(slice_id, worker_id, extend_sec, ts)
