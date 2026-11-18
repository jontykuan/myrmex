from pathlib import Path
import sqlite3
from packages.mcp.src.adapters.sqlite_store import SqliteStateStore
from packages.mcp.src.server.field_tools import emit_pheromone, sense_field


def test_sense_field_orders_by_net_score_and_returns_active_gates(tmp_path: Path) -> None:
    db = tmp_path / "state.db"
    store = SqliteStateStore(db)
    store.upsert_gate_policy("base_build_test", 0, "pytest -q", 1)
    store.emit_pheromone("arch", "s-low", "task_seed", 3.0, 0.0, None, None, now=1000)
    store.emit_pheromone("arch", "s-high", "task_seed", 9.0, 0.0, None, None, now=1000)

    res = sense_field(store, worker_id="w1", limit=1, now=1000, block_threshold=5.0)
    assert len(res["candidates"]) == 1
    assert res["candidates"][0]["target_ref"] == "s-high"
    assert [g["gate_id"] for g in res["active_gates"]] == ["base_build_test"]
    store.close()


def test_emit_pheromone_updates_field_and_logs_telemetry(tmp_path: Path) -> None:
    db = tmp_path / "state.db"
    store = SqliteStateStore(db)
    emit_pheromone(store, worker_id="w1", target_ref="s1", kind="test_red", intensity=8.0, now=1000)

    res = sense_field(store, worker_id="w1", limit=5, now=1000, block_threshold=5.0)
    assert res["candidates"][0]["dominant_kind"] == "test_red"
    with sqlite3.connect(db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM telemetry_events WHERE event_type = 'emit'").fetchone()[0]
    assert count == 1
    store.close()
