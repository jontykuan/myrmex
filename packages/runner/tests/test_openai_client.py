import json
from pathlib import Path
from typing import Any
from packages.runner.src.openai_client import OpenAICompatLlmClient


def test_openai_compat_executes_tool_calls_and_sums_usage(tmp_path: Path) -> None:
    turn = 0

    def fake_post(api_base: str, api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        nonlocal turn
        turn += 1
        if turn == 1:
            return {
                "usage": {"prompt_tokens": 50, "completion_tokens": 20},
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "tool_calls": [{
                            "id": "tc1",
                            "type": "function",
                            "function": {
                                "name": "write_file",
                                "arguments": json.dumps({"path": "out.py", "content": "x = 42\n"}),
                            },
                        }],
                    }
                }],
            }
        return {
            "usage": {"prompt_tokens": 80, "completion_tokens": 10},
            "choices": [{"message": {"role": "assistant", "content": "done"}}],
        }

    client = OpenAICompatLlmClient(model="google/gemma-4-27b-it", requester=fake_post)
    res = client.generate([{"role": "user", "content": "implement"}], tmp_path)
    assert (tmp_path / "out.py").read_text(encoding="utf-8") == "x = 42\n"
    assert res["usage"] == {"prompt_token_count": 130, "candidates_token_count": 30, "thoughts_token_count": 0}
