from pathlib import Path
import subprocess
import time
from typing import Any, Callable
from packages.mcp.src.adapters.git_worktree import rebase_and_merge, remove_worktree, validate_scope
from packages.mcp.src.adapters.sqlite_store import SqliteStateStore
from packages.mcp.src.core.ratchet import evaluate_ratchet


def _run_active_gates(wt_path: Path, gates: list[dict[str, Any]]) -> tuple[str | None, str]:
    for gate in gates:
        if not gate["active"]:
            continue
        res = subprocess.run(gate["command"], cwd=wt_path, shell=True, text=True, capture_output=True)
        if res.returncode != 0:
            msg = (res.stderr or res.stdout or f"exit {res.returncode}")[:2000]
            return str(gate["gate_id"]), msg
    return None, ""


def _ratchet_summary(store: SqliteStateStore) -> dict[str, Any]:
    rows = store._conn.execute("SELECT event_type, outcome FROM telemetry_events ORDER BY created_at DESC LIMIT 50").fetchall()
    type_errs = sum(1 for r in rows if r["outcome"] == "type_error")
    regressions = sum(1 for r in rows[:20] if r["event_type"] == "post_merge_regression")
    conflicts = sum(1 for r in rows if r["event_type"] == "merge_conflict")
    attempts = [r for r in rows[:8] if r["event_type"] in ("merge_ok", "gate_fail")]
    rate = (sum(1 for r in attempts if r["event_type"] == "merge_ok") / len(attempts)) if attempts else 1.0
    return {
        "type_error_count": type_errs,
        "recent_regressions": regressions,
        "max_file_conflicts": conflicts,
        "tier1_attempts": len(attempts),
        "tier1_first_pass_rate": rate,
    }


def _apply_ratchet(store: SqliteStateStore, worker_id: str, now: int) -> list[str]:
    escalated = evaluate_ratchet(store.list_gate_policies(), _ratchet_summary(store))
    store.activate_gates(escalated, now)
    for gid in escalated:
        store.log_telemetry(worker_id, "gate_escalate", now, outcome=gid)
    return escalated


def verify_and_merge(
    store: SqliteStateStore,
    repo_root: Path,
    target_branch: str,
    worker_id: str,
    slice_id: str,
    commit_message: str = "feat: myrmex slice",
    now: int | None = None,
    post_merge_check: Callable[[Path], bool] | None = None,
) -> dict[str, Any]:
    ts = now if now is not None else int(time.time())
    lease = store.get_lease(slice_id)
    if not lease or lease["worker_id"] != worker_id or int(lease["expires_at"]) <= ts:
        return {"status": "LEASE_EXPIRED"}
    wt_path = Path(lease["worktree"])
    if validate_scope(wt_path, target_branch, lease["file_scope"]) == "SCOPE_VIOLATION":
        return {"status": "SCOPE_VIOLATION"}

    failed_gate, summary = _run_active_gates(wt_path, store.list_gate_policies())
    if failed_gate:
        kind = "type_error" if "type" in failed_gate else "test_red"
        store.emit_pheromone(worker_id, slice_id, kind, 8.0, 0.001, None, {"gate": failed_gate, "err": summary}, ts)
        store.log_telemetry(worker_id, "gate_fail", ts, slice_id=slice_id, outcome=kind)
        return {"status": "GATE_FAILED", "failed_gate_id": failed_gate, "failure_summary": summary, "escalated_gates": _apply_ratchet(store, worker_id, ts)}

    status, head = rebase_and_merge(repo_root, wt_path, f"myrmex/{slice_id}", target_branch, commit_message)
    if status == "MERGE_CONFLICT":
        store.emit_pheromone(worker_id, slice_id, "conflict_hotspot", 5.0, 0.01, 300, {"slice": slice_id}, ts)
        store.log_telemetry(worker_id, "merge_conflict", ts, slice_id=slice_id, outcome="MERGE_CONFLICT")
        return {"status": "MERGE_CONFLICT", "escalated_gates": _apply_ratchet(store, worker_id, ts)}

    store.clear_attractive_pheromones(slice_id)
    store.release_lease(slice_id)
    remove_worktree(repo_root, wt_path, f"myrmex/{slice_id}")
    store.log_telemetry(worker_id, "merge_ok", ts, slice_id=slice_id, outcome=head)
    if post_merge_check and not post_merge_check(repo_root):
        store.log_telemetry("sentinel", "post_merge_regression", ts, slice_id=slice_id, outcome="REGRESSION")
        store.emit_pheromone("sentinel", slice_id, "test_red", 9.0, 0.0, None, {"reason": "post_merge_regression"}, ts)
        _apply_ratchet(store, "sentinel", ts)
    return {"status": "MERGED", "merged_commit": head}
