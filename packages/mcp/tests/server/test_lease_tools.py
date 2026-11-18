from pathlib import Path
import sqlite3
import subprocess
from packages.mcp.src.adapters.sqlite_store import SqliteStateStore
from packages.mcp.src.server.lease_tools import claim_slice, heartbeat_lease


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@myrmex.dev"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "myrmex"], cwd=repo, check=True, capture_output=True)
    (repo / "src").mkdir()
    (repo / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
    return repo


def test_claim_slice_creates_worktree_and_logs_telemetry(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    db = tmp_path / "state.db"
    store = SqliteStateStore(db)
    res = claim_slice(store, repo, repo / ".worktrees", "main", "w1", "s1", ["src/a.py"], ttl_sec=60, now=1000)
    assert res["status"] == "CLAIMED"
    assert Path(res["worktree_path"]).exists()
    with sqlite3.connect(db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM telemetry_events WHERE event_type = 'claim'").fetchone()[0]
    assert count == 1
    store.close()


def test_claim_slice_conflict_skips_worktree_creation(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    store = SqliteStateStore(tmp_path / "state.db")
    claim_slice(store, repo, repo / ".worktrees", "main", "w1", "s1", ["src/a.py"], ttl_sec=60, now=1000)
    res = claim_slice(store, repo, repo / ".worktrees", "main", "w2", "s2", ["src/a.py"], ttl_sec=60, now=1010)
    assert res["status"] == "CONFLICT_LEASED"
    assert not (repo / ".worktrees" / "s2").exists()
    store.close()


def test_heartbeat_lease_extends_expiry(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    store = SqliteStateStore(tmp_path / "state.db")
    c = claim_slice(store, repo, repo / ".worktrees", "main", "w1", "s1", ["src/a.py"], ttl_sec=60, now=1000)
    h = heartbeat_lease(store, "w1", "s1", extend_sec=120, now=1010)
    assert h["status"] == "EXTENDED"
    assert h["expires_at"] == c["expires_at"] + 120
    store.close()
