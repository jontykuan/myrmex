import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from packages.mcp.src.adapters.sqlite_store import SqliteStateStore


def test_initializes_wal_and_all_protocol_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    store = SqliteStateStore(db_path)
    with sqlite3.connect(db_path) as conn:
        mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        tables = {
            r[0]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        }
    assert mode.lower() == "wal"
    assert {"pheromones", "leases", "gate_policies", "telemetry_events"}.issubset(tables)
    store.close()


def test_atomic_claim_allows_only_one_winner_under_concurrency(tmp_path: Path) -> None:
    store = SqliteStateStore(tmp_path / "state.db")

    def attempt(worker_id: str) -> str:
        return store.acquire_lease(
            slice_id=f"s-{worker_id}",
            worker_id=worker_id,
            worktree=f".worktrees/s-{worker_id}",
            file_scope=["src/a.py"],
            now=1000,
            ttl_sec=60,
        )["status"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, ["w1", "w2"]))
    assert sorted(outcomes) == ["CLAIMED", "CONFLICT_LEASED"]
    store.close()


def test_emit_pheromone_atomically_releases_lease(tmp_path: Path) -> None:
    store = SqliteStateStore(tmp_path / "state.db")
    store.acquire_lease("s1", "w1", ".worktrees/s1", ["src/a.py"], now=1000, ttl_sec=60)
    res = store.emit_pheromone(
        worker_id="w1",
        target_ref="s1",
        kind="test_red",
        intensity=8.0,
        decay_rate=0.001,
        ttl_sec=None,
        payload={"test": "fails"},
        now=1010,
        release_slice_id="s1",
    )
    assert res["updated_intensity"] == 8.0
    assert store.get_lease("s1") is None
    assert len(store.list_pheromones()) == 1
    store.close()
