import subprocess
from pathlib import Path
from packages.mcp.src.adapters.git_worktree import (
    create_worktree,
    rebase_and_merge,
    remove_worktree,
    validate_scope,
)


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@myrmex.dev"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "myrmex"], cwd=repo, check=True, capture_output=True)
    (repo / "src").mkdir()
    (repo / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
    return repo


def test_create_and_remove_worktree(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    wt = create_worktree(repo, repo / ".worktrees", "s1", "main")
    assert wt.exists()
    assert (wt / "src" / "a.py").exists()
    remove_worktree(repo, wt, "myrmex/s1")
    assert not wt.exists()


def test_validate_scope_rejects_out_of_scope_changes(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    wt = create_worktree(repo, repo / ".worktrees", "s1", "main")
    (wt / "src" / "outside.py").write_text("y = 2\n", encoding="utf-8")
    assert validate_scope(wt, "main", ["src/a.py"]) == "SCOPE_VIOLATION"


def test_rebase_and_merge_aborts_cleanly_on_conflict(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    wt = create_worktree(repo, repo / ".worktrees", "s1", "main")
    (wt / "src" / "a.py").write_text("x = 2\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=wt, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "s1 change"], cwd=wt, check=True, capture_output=True)

    (repo / "src" / "a.py").write_text("x = 99\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "main change"], cwd=repo, check=True, capture_output=True)
    main_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()

    status, _ = rebase_and_merge(repo, wt, "myrmex/s1", "main", "merge s1")
    assert status == "MERGE_CONFLICT"
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip() == main_head
    assert not (wt / ".git" / "rebase-merge").exists()
