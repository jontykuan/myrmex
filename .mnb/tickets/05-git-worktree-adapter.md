# 05: Git Worktree & Merge Adapter

**What to build:** Deterministic Git adapter for isolated worktree creation, `file_scope` diff validation, rebase onto target branch, and squash/fast-forward merge.
**Blocked by:** None (frontier)
**Target files:** `packages/mcp/src/adapters/git_worktree.py`, `packages/mcp/tests/adapters/test_git_worktree.py`
**Size budget:** <= 20 LOC

## Acceptance Criteria (Deterministic Contracts)
- [ ] Given a clean repo at `base_commit`, When `create_worktree("s1")` runs, Then `.worktrees/s1` exists on branch `myrmex/s1` at `base_commit`.
- [ ] Given worktree `"s1"` modifies `"src/outside.py"` outside `file_scope = ["src/a.py"]`, When `validate_scope` runs, Then return value equals `SCOPE_VIOLATION`.
- [ ] Given worktree `"s1"` conflicts with `main` on rebase, When `rebase_and_merge` runs, Then rebase is aborted cleanly, `main` HEAD is unchanged, and return value equals `MERGE_CONFLICT`.

## Deterministic Verification
- Unit test path: `packages/mcp/tests/adapters/test_git_worktree.py`
- Mutation target: `packages/mcp/src/adapters/git_worktree.py`
- Mutants to kill:
  - Failing to run `git rebase --abort` on conflict must turn tests red.
  - Allowing any modified file outside `file_scope` must turn tests red.
