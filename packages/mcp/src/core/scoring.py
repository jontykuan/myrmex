import math
from typing import Any

ATTRACTIVE = {"task_seed", "test_red", "type_error", "smell_refactor"}
REPULSIVE = {"conflict_hotspot", "blocked_unknown"}


def _effective(row: dict[str, Any], now: int) -> float:
    return float(row["intensity"]) * math.exp(-float(row["decay_rate"]) * max(0, now - int(row["updated_at"])))


def score_field(
    pheromones: list[dict[str, Any]],
    leased_targets: set[str],
    now: int,
    block_threshold: float,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[tuple[str, float, Any]]] = {}
    for row in pheromones:
        exp = row.get("expires_at")
        if (exp is not None and int(exp) <= now) or row["target_ref"] in leased_targets:
            continue
        grouped.setdefault(row["target_ref"], []).append((row["kind"], _effective(row, now), row.get("payload")))

    results: list[dict[str, Any]] = []
    for target, items in grouped.items():
        blocked = sum(eff for k, eff, _ in items if k == "blocked_unknown")
        if blocked >= block_threshold:
            continue
        attr = [(k, eff, p) for k, eff, p in items if k in ATTRACTIVE]
        if not attr:
            continue
        net = sum(eff for _, eff, _ in attr) - sum(eff for k, eff, _ in items if k in REPULSIVE)
        dominant = max(attr, key=lambda x: x[1])[0]
        results.append({
            "target_ref": target,
            "net_score": net,
            "dominant_kind": dominant,
            "pheromones": [{"kind": k, "effective_intensity": eff, "payload": p} for k, eff, p in items],
        })
    return sorted(results, key=lambda r: r["net_score"], reverse=True)
