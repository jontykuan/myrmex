from pathlib import Path
from types import SimpleNamespace
import pytest
from packages.mcp.src.adapters.sqlite_store import SqliteStateStore
from packages.runner.src.genai_client import GenAILlmClient, resolve_api_key
from packages.runner.src.local_mcp_bridge import LocalMcpBridge


def test_resolve_api_key_prefers_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "secret-test-key")
    assert resolve_api_key() == "secret-test-key"


def test_genai_client_extracts_usage_including_thoughts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeModels:
        def generate_content(self, model: str, contents: str, config: object) -> object:
            return SimpleNamespace(
                usage_metadata=SimpleNamespace(
                    prompt_token_count=120,
                    candidates_token_count=30,
                    thoughts_token_count=45,
                )
            )

    fake_sdk = SimpleNamespace(models=FakeModels())
    client = GenAILlmClient(api_key="k", model="gemini-4-hydrogen", sdk_client=fake_sdk)
    res = client.generate([{"role": "user", "content": "hi"}], tmp_path)
    assert res["usage"] == {"prompt_token_count": 120, "candidates_token_count": 30, "thoughts_token_count": 45}


def test_local_mcp_bridge_sense_and_record_usage(tmp_path: Path) -> None:
    store = SqliteStateStore(tmp_path / "state.db")
    store.emit_pheromone("arch", "s1", "task_seed", 5.0, 0.0, None, None, now=1000)
    bridge = LocalMcpBridge(store, tmp_path, worker_id="w1")
    field = bridge.sense_field("w1")
    assert field["candidates"][0]["target_ref"] == "s1"
    bridge.record_usage(10, 20, 50, 0)
    rows = store._conn.execute("SELECT tokens_in, tokens_out FROM telemetry_events WHERE event_type='llm_usage'").fetchall()
    assert len(rows) == 1
    assert (rows[0]["tokens_in"], rows[0]["tokens_out"]) == (10, 20)
    store.close()
