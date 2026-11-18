from pathlib import Path
from typing import Any
from packages.runner.src.worker import WorkerConfig, run_cycle


class FakeMcpClient:
    def __init__(self, candidates: list[dict[str, Any]], worktree_path: Path) -> None:
        self._candidates = candidates
        self._wt = worktree_path
        self.telemetry: list[dict[str, Any]] = []
        self.merged = False

    def sense_field(self, worker_id: str, limit: int = 5) -> dict[str, Any]:
        return {"candidates": self._candidates[:limit], "active_gates": []}

    def claim_slice(self, worker_id: str, slice_id: str, file_scope: list[str]) -> dict[str, Any]:
        self._wt.mkdir(parents=True, exist_ok=True)
        return {"status": "CLAIMED", "worktree_path": str(self._wt)}

    def verify_and_merge(self, worker_id: str, slice_id: str, commit_message: str) -> dict[str, Any]:
        self.merged = True
        return {"status": "MERGED", "merged_commit": "abc123"}

    def emit_pheromone(self, **kwargs: Any) -> dict[str, Any]:
        return {"pheromone_id": "p1", "updated_intensity": 1.0}

    def record_usage(self, tokens_in: int, tokens_out: int, duration_ms: int, rate_limit_wait_ms: int) -> None:
        self.telemetry.append({
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "duration_ms": duration_ms,
            "rate_limit_wait_ms": rate_limit_wait_ms,
        })


class FakeGenAIClient:
    def __init__(self, fail_error: str | None = None) -> None:
        self.calls = 0
        self.history_lengths_at_start: list[int] = []
        self._fail_error = fail_error

    def generate(self, messages: list[dict[str, str]], worktree_path: Path) -> dict[str, Any]:
        self.history_lengths_at_start.append(len(messages))
        self.calls += 1
        if self._fail_error and self.calls == 1:
            raise RuntimeError(self._fail_error)
        (worktree_path / "out.txt").write_text("done\n", encoding="utf-8")
        return {
            "action": "verify_and_merge",
            "commit_message": "feat: done",
            "usage": {"prompt_token_count": 100, "candidates_token_count": 40, "thoughts_token_count": 20},
        }


def test_idle_when_no_candidates(tmp_path: Path) -> None:
    mcp = FakeMcpClient([], tmp_path / "wt")
    llm = FakeGenAIClient()
    res = run_cycle(mcp, llm, WorkerConfig(worker_id="w1", backoff_base_sec=0.0))
    assert res["status"] == "IDLE"
    assert llm.calls == 0


def test_merged_logs_tokens_including_thoughts_and_handles_429(tmp_path: Path) -> None:
    mcp = FakeMcpClient([{"target_ref": "s1", "dominant_kind": "task_seed", "net_score": 10.0}], tmp_path / "wt")
    llm = FakeGenAIClient(fail_error="429 RESOURCE_EXHAUSTED")
    res = run_cycle(mcp, llm, WorkerConfig(worker_id="w1", backoff_base_sec=0.01))
    assert res["status"] == "MERGED"
    assert mcp.telemetry[0]["tokens_in"] == 100
    assert mcp.telemetry[0]["tokens_out"] == 60
    assert mcp.telemetry[0]["rate_limit_wait_ms"] > 0


def test_retries_transient_503_unavailable(tmp_path: Path) -> None:
    mcp = FakeMcpClient([{"target_ref": "s1", "dominant_kind": "task_seed", "net_score": 10.0}], tmp_path / "wt")
    llm = FakeGenAIClient(fail_error="503 UNAVAILABLE")
    res = run_cycle(mcp, llm, WorkerConfig(worker_id="w1", backoff_base_sec=0.01))
    assert res["status"] == "MERGED"
    assert llm.calls == 2


def test_clears_episodic_memory_between_cycles(tmp_path: Path) -> None:
    mcp = FakeMcpClient([{"target_ref": "s1", "dominant_kind": "task_seed", "net_score": 10.0}], tmp_path / "wt")
    llm = FakeGenAIClient()
    run_cycle(mcp, llm, WorkerConfig(worker_id="w1", backoff_base_sec=0.0))
    run_cycle(mcp, llm, WorkerConfig(worker_id="w1", backoff_base_sec=0.0))
    assert llm.history_lengths_at_start == [1, 1]
