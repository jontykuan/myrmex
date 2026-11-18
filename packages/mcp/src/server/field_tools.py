import time
from typing import Any
from packages.mcp.src.adapters.sqlite_store import SqliteStateStore
from packages.mcp.src.core.scoring import score_field


def sense_field(
    store: SqliteStateStore,
    worker_id: str,
    focus_scope: str | None = None,
    limit: int = 5,
    now: int | None = None,
    block_threshold: float = 5.0,
) -> dict[str, Any]:
    ts = now if now is not None else int(time.time())
    leased = {l["slice_id"] for l in store.list_active_leases(ts)}
    candidates = score_field(store.list_pheromones(), leased, ts, block_threshold)
    if focus_scope:
        candidates = [c for c in candidates if str(c["target_ref"]).startswith(focus_scope)]
    gates = [{"gate_id": g["gate_id"], "tier": g["tier"], "command": g["command"]} for g in store.list_gate_policies() if g["active"]]
    store.log_telemetry(worker_id, "sense", ts, outcome="OK")
    return {"timestamp": ts, "candidates": candidates[:limit], "active_gates": gates}


def emit_pheromone(
    store: SqliteStateStore,
    worker_id: str,
    target_ref: str,
    kind: str,
    intensity: float,
    decay_rate: float = 0.001,
    ttl_sec: int | None = None,
    payload: dict[str, Any] | None = None,
    release_slice_id: str | None = None,
    now: int | None = None,
) -> dict[str, Any]:
    ts = now if now is not None else int(time.time())
    res = store.emit_pheromone(worker_id, target_ref, kind, intensity, decay_rate, ttl_sec, payload, ts, release_slice_id)
    store.log_telemetry(worker_id, "emit", ts, slice_id=target_ref, outcome=kind)
    return res
