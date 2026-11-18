from pathlib import Path
import sqlite3
import subprocess
import sys
from packages.mcp.src.adapters.sqlite_store import SqliteStateStore
from packages.mcp.src.server.lease_tools import claim_slice
from packages.mcp.src.server.merge_tools import verify_and_merge


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@myrmex.dev"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "myrmex"], cwd=repo, check=True, capture_output=True)
    (repo / "src").mkdir()
    (repo / "src" / "a.py").write_text("def val(): return 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
    return repo


def test_verify_and_merge_succeeds_and_cleans_state(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    db = tmp_path / "state.db"
    store = SqliteStateStore(db)
    store.upsert_gate_policy("base_build_test", 0, f'"{sys.executable}" -c "import sys; sys.exit(0)"', 1)
    store.emit_pheromone("arch", "s1", "task_seed", 5.0, 0.0, None, None, now=1000)
    claim = claim_slice(store, repo, repo / ".worktrees", "main", "w1", "s1", ["src/a.py"], now=1000)
    wt = Path(claim["worktree_path"])
    (wt / "src" / "a.py").write_text("def val(): return 2\n", encoding="utf-8")

    res = verify_and_merge(store, repo, "main", "w1", "s1", "feat: s1", now=1010)
    assert res["status"] == "MERGED"
    assert store.get_lease("s1") is None
    assert store.list_pheromones() == []
    assert not wt.exists()
    store.close()


def test_verify_and_merge_gate_failure_emits_pheromone_and_evaluates_ratchet(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    db = tmp_path / "state.db"
    store = SqliteStateStore(db)
    store.upsert_gate_policy("base_build_test", 0, f'"{sys.executable}" -c "import sys; sys.exit(1)"', 1)
    store.upsert_gate_policy("strict_typecheck", 1, f'"{sys.executable}" -c "import sys; sys.exit(0)"', 0)
    for i in range(3):
        store.log_telemetry("w0", "gate_fail", 900 + i, outcome="type_error")
    claim = claim_slice(store, repo, repo / ".worktrees", "main", "w1", "s1", ["src/a.py"], now=1000)
    (Path(claim["worktree_path"]) / "src" / "a.py").write_text("def val(): return 2\n", encoding="utf-8")
    head_before = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()

    res = verify_and_merge(store, repo, "main", "w1", "s1", "feat: s1", now=1010)
    assert res["status"] == "GATE_FAILED"
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip() == head_before
    assert "strict_typecheck" in res["escalated_gates"]
    assert any(p["kind"] == "test_red" for p in store.list_pheromones())
    store.close()


def test_verify_and_merge_detects_post_merge_regression(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    db = tmp_path / "state.db"
    store = SqliteStateStore(db)
    store.upsert_gate_policy("base_build_test", 0, f'"{sys.executable}" -c "import sys; sys.exit(0)"', 1)
    claim = claim_slice(store, repo, repo / ".worktrees", "main", "w1", "s1", ["src/a.py"], now=1000)
    (Path(claim["worktree_path"]) / "src" / "a.py").write_text("def val(): return 2\n", encoding="utf-8")

    res = verify_and_merge(
        store,
        repo,
        "main",
        "w1",
        "s1",
        "feat: s1",
        now=1010,
        post_merge_check=lambda _repo: False,
    )
    assert res["status"] == "MERGED"
    with sqlite3.connect(db) as conn:
        cnt = conn.execute("SELECT COUNT(*) FROM telemetry_events WHERE event_type = 'post_merge_regression'").fetchone()[0]
    assert cnt == 1
    assert any(p["kind"] == "test_red" for p in store.list_pheromones())
    store.close()
