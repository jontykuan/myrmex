import json
import os
from pathlib import Path
import subprocess
from typing import Any, Callable
import urllib.request

_TOOLS_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file relative to the worktree.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file relative to the worktree.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Run a shell command inside the worktree.",
            "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]},
        },
    },
]


def _safe_path(wt: Path, rel: str) -> Path:
    target = (wt / rel).resolve()
    if not str(target).startswith(str(wt.resolve())):
        raise ValueError(f"Path escapes worktree: {rel}")
    return target


def _post_chat(api_base: str, api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{api_base.rstrip('/')}/chat/completions"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return dict(json.loads(resp.read().decode("utf-8")))


class OpenAICompatLlmClient:
    """OpenAI-compatible LlmClient for local/Colab GPU servers (vLLM / Ollama / Gemma 4 27B)."""

    def __init__(
        self,
        model: str = "google/gemma-4-27b-it",
        api_base: str = "http://localhost:8000/v1",
        api_key: str | None = None,
        max_turns: int = 8,
        requester: Callable[[str, str, dict[str, Any]], dict[str, Any]] = _post_chat,
    ) -> None:
        self._model = model
        self._api_base = api_base
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "local")
        self._max_turns = max_turns
        self._requester = requester

    def _exec_tool(self, wt: Path, name: str, args: dict[str, Any]) -> str:
        if name == "read_file":
            return _safe_path(wt, str(args["path"])).read_text(encoding="utf-8")
        if name == "write_file":
            target = _safe_path(wt, str(args["path"]))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(str(args["content"]), encoding="utf-8")
            return f"wrote {args['path']}"
        if name == "run_shell":
            res = subprocess.run(str(args["command"]), cwd=wt, shell=True, text=True, capture_output=True)
            return f"exit={res.returncode}\n{res.stdout}\n{res.stderr}"[:3000]
        return f"unknown tool: {name}"

    def generate(self, messages: list[dict[str, str]], worktree_path: Path) -> dict[str, Any]:
        sys_msg = {"role": "system", "content": "You are a stateless myrmex-worker. Edit only files in scope, run tests via run_shell, and stop once ready for verify_and_merge."}
        convo: list[dict[str, Any]] = [sys_msg, *messages]
        t_in, t_out = 0, 0
        for _ in range(self._max_turns):
            resp = self._requester(self._api_base, self._api_key, {"model": self._model, "messages": convo, "tools": _TOOLS_SPEC})
            usage = resp.get("usage", {})
            t_in += int(usage.get("prompt_tokens", 0))
            t_out += int(usage.get("completion_tokens", 0))
            msg = resp["choices"][0]["message"]
            convo.append(msg)
            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                break
            for tc in tool_calls:
                fn = tc["function"]
                out = self._exec_tool(worktree_path, fn["name"], json.loads(fn["arguments"]))
                convo.append({"role": "tool", "tool_call_id": tc["id"], "content": out})
        return {
            "action": "verify_and_merge",
            "commit_message": f"feat: myrmex-worker ({self._model})",
            "usage": {"prompt_token_count": t_in, "candidates_token_count": t_out, "thoughts_token_count": 0},
        }
