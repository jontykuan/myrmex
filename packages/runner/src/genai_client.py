import getpass
import os
from pathlib import Path
import subprocess
from typing import Any


def resolve_api_key() -> str:
    """Resolve GEMINI_API_KEY securely from env, Colab userdata, or masked prompt."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key
    try:
        from google.colab import userdata  # type: ignore[import-not-found]
        key = (userdata.get("GEMINI_API_KEY") or "").strip()
        if key:
            return key
    except Exception:
        pass
    return getpass.getpass("Enter GEMINI_API_KEY (input hidden): ").strip()


def _safe_path(wt: Path, rel: str) -> Path:
    target = (wt / rel).resolve()
    if not str(target).startswith(str(wt.resolve())):
        raise ValueError(f"Path escapes worktree: {rel}")
    return target


class GenAILlmClient:
    """google-genai LlmClient adapter targeting gemini-4-hydrogen."""

    def __init__(self, api_key: str | None = None, model: str = "gemini-4-hydrogen", sdk_client: Any = None) -> None:
        self._model = model
        if sdk_client is not None:
            self._client = sdk_client
        else:
            from google import genai
            self._client = genai.Client(api_key=api_key or resolve_api_key())

    def generate(self, messages: list[dict[str, str]], worktree_path: Path) -> dict[str, Any]:
        def read_file(path: str) -> str:
            return _safe_path(worktree_path, path).read_text(encoding="utf-8")

        def write_file(path: str, content: str) -> str:
            target = _safe_path(worktree_path, path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return f"wrote {path}"

        def run_shell(command: str) -> str:
            res = subprocess.run(command, cwd=worktree_path, shell=True, text=True, capture_output=True)
            return f"exit={res.returncode}\n{res.stdout}\n{res.stderr}"[:3000]

        prompt = "\n".join(m["content"] for m in messages)
        sys_inst = "You are a stateless myrmex-worker. Edit only files in scope, run tests via run_shell, and stop once ready for verify_and_merge."
        try:
            from google.genai import types
            cfg: Any = types.GenerateContentConfig(system_instruction=sys_inst, tools=[read_file, write_file, run_shell])
        except ImportError:
            cfg = {"system_instruction": sys_inst, "tools": [read_file, write_file, run_shell]}
        resp = self._client.models.generate_content(model=self._model, contents=prompt, config=cfg)
        meta = getattr(resp, "usage_metadata", None)
        return {
            "action": "verify_and_merge",
            "commit_message": "feat: myrmex-worker slice update",
            "usage": {
                "prompt_token_count": int(getattr(meta, "prompt_token_count", 0) or 0),
                "candidates_token_count": int(getattr(meta, "candidates_token_count", 0) or 0),
                "thoughts_token_count": int(getattr(meta, "thoughts_token_count", 0) or 0),
            },
        }
