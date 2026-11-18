from dataclasses import dataclass
from pathlib import Path
import random
import time
from typing import Any, Protocol


class McpClient(Protocol):
    def sense_field(self, worker_id: str, limit: int = 5) -> dict[str, Any]: ...
    def claim_slice(self, worker_id: str, slice_id: str, file_scope: list[str]) -> dict[str, Any]: ...
    def verify_and_merge(self, worker_id: str, slice_id: str, commit_message: str) -> dict[str, Any]: ...
    def emit_pheromone(self, **kwargs: Any) -> dict[str, Any]: ...
    def record_usage(self, tokens_in: int, tokens_out: int, duration_ms: int, rate_limit_wait_ms: int) -> None: ...


class LlmClient(Protocol):
    def generate(self, messages: list[dict[str, str]], worktree_path: Path) -> dict[str, Any]: ...


@dataclass(frozen=True)
class WorkerConfig:
    worker_id: str
    model: str = "gemini-4-hydrogen"
    max_retries: int = 3
    backoff_base_sec: float = 1.0


def _call_with_backoff(llm: LlmClient, messages: list[dict[str, str]], wt: Path, cfg: WorkerConfig) -> tuple[dict[str, Any], int]:
    wait_ms = 0
    for attempt in range(cfg.max_retries + 1):
        try:
            return llm.generate(messages, wt), wait_ms
        except Exception as exc:
            if "429" not in str(exc) or attempt == cfg.max_retries:
                raise
            delay = cfg.backoff_base_sec * (2**attempt) + random.uniform(0, cfg.backoff_base_sec * 0.25)
            time.sleep(delay)
            wait_ms += int(delay * 1000) + 1
    raise RuntimeError("unreachable")


def _claim_first(mcp: McpClient, worker_id: str, candidates: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]] | None:
    for cand in candidates:
        scope = cand.get("file_scope") or [f"{cand['target_ref']}/**"]
        claim = mcp.claim_slice(worker_id, str(cand["target_ref"]), scope)
        if claim["status"] == "CLAIMED":
            return cand, claim
    return None


def run_cycle(mcp: McpClient, llm: LlmClient, cfg: WorkerConfig) -> dict[str, Any]:
    t0 = time.monotonic()
    field = mcp.sense_field(cfg.worker_id, limit=5)
    candidates = field.get("candidates", [])
    if not candidates:
        return {"status": "IDLE"}
    claimed = _claim_first(mcp, cfg.worker_id, candidates)
    if not claimed:
        return {"status": "NO_CLAIMABLE_SLICE"}
    cand, claim = claimed
    messages = [{"role": "user", "content": f"slice={cand['target_ref']} kind={cand['dominant_kind']} gates={field.get('active_gates', [])}"}]
    reply, wait_ms = _call_with_backoff(llm, messages, Path(claim["worktree_path"]), cfg)
    usage = reply.get("usage", {})
    t_in = int(usage.get("prompt_token_count", 0))
    t_out = int(usage.get("candidates_token_count", 0)) + int(usage.get("thoughts_token_count", 0))
    mcp.record_usage(t_in, t_out, int((time.monotonic() - t0) * 1000), wait_ms)
    if reply.get("action") == "emit_pheromone":
        return mcp.emit_pheromone(worker_id=cfg.worker_id, target_ref=cand["target_ref"], release_slice_id=cand["target_ref"], **reply.get("pheromone", {}))
    return mcp.verify_and_merge(cfg.worker_id, str(cand["target_ref"]), str(reply.get("commit_message", "feat: slice")))
