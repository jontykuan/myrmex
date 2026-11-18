from fnmatch import fnmatch
from pathlib import Path
import subprocess


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True)


def create_worktree(repo: Path, wt_root: Path, slice_id: str, target_branch: str) -> Path:
    wt_root.mkdir(parents=True, exist_ok=True)
    wt_path = wt_root / slice_id
    res = _git(repo, "worktree", "add", str(wt_path), "-B", f"myrmex/{slice_id}", target_branch)
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip())
    return wt_path


def remove_worktree(repo: Path, wt_path: Path, branch: str) -> None:
    _git(repo, "worktree", "remove", str(wt_path), "--force")
    _git(repo, "branch", "-D", branch)


def validate_scope(wt_path: Path, target_branch: str, file_scope: list[str]) -> str:
    diff = _git(wt_path, "diff", "--name-only", target_branch).stdout.splitlines()
    untracked = _git(wt_path, "ls-files", "--others", "--exclude-standard").stdout.splitlines()
    changed = {p.strip() for p in diff + untracked if p.strip()}
    for path in changed:
        if not any(fnmatch(path, pat) or path.startswith(pat.rstrip("/*") + "/") for pat in file_scope):
            return "SCOPE_VIOLATION"
    return "OK"


def rebase_and_merge(
    repo: Path,
    wt_path: Path,
    branch: str,
    target_branch: str,
    commit_message: str,
) -> tuple[str, str]:
    if _git(wt_path, "status", "--porcelain").stdout.strip():
        _git(wt_path, "add", "-A")
        _git(wt_path, "commit", "-m", commit_message)
    if _git(wt_path, "rebase", target_branch).returncode != 0:
        _git(wt_path, "rebase", "--abort")
        return "MERGE_CONFLICT", ""
    if _git(repo, "merge", "--ff-only", branch).returncode != 0:
        return "MERGE_CONFLICT", ""
    head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    return "MERGED", head
