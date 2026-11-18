from pathlib import Path
import time
from typing import Any
from packages.mcp.src.adapters.sqlite_store import SqliteStateStore
from packages.mcp.src.server.field_tools import emit_pheromone, sense_field
from packages.mcp.src.server.lease_tools import claim_slice
from packages.mcp.src.server.merge_tools import verify_and_merge


class LocalMcpBridge:
    """Direct in-process McpClient adapter for single-VM / Colab runs."""

    def __init__(self, store: SqliteStateStore, repo_root: Path, target_branch: str = "main", worker_id: str = "w1") -> None:
        self._store = store
        self._repo = repo_root
        self._wt_root = repo_root / ".worktrees"
        self._branch = target_branch
        self._worker_id = worker_id

    def sense_field(self, worker_id: str, limit: int = 5) -> dict[str, Any]:
        return sense_field(self._store, worker_id=worker_id, limit=limit)

    def claim_slice(self, worker_id: str, slice_id: str, file_scope: list[str]) -> dict[str, Any]:
        return claim_slice(self._store, self._repo, self._wt_root, self._branch, worker_id, slice_id, file_scope)

    def verify_and_merge(self, worker_id: str, slice_id: str, commit_message: str) -> dict[str, Any]:
        return verify_and_merge(self._store, self._repo, self._branch, worker_id, slice_id, commit_message)

    def emit_pheromone(self, **kwargs: Any) -> dict[str, Any]:
        return emit_pheromone(self._store, **kwargs)

    def record_usage(self, tokens_in: int, tokens_out: int, duration_ms: int, rate_limit_wait_ms: int) -> None:
        self._store.log_telemetry(
            worker_id=self._worker_id,
            event_type="llm_usage",
            now=int(time.time()),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            duration_ms=duration_ms,
            metadata={"rate_limit_wait_ms": rate_limit_wait_ms},
        )
