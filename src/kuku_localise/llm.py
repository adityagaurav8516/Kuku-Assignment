from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_MODEL = "gemini-3.5-flash-lite"


def project_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in (here.parents[2], Path.cwd()):
        if (candidate / "pyproject.toml").exists():
            return candidate
    return Path.cwd()


def load_settings() -> tuple[str, str]:
    root = project_root()
    load_dotenv(root / ".env")
    load_dotenv()
    key = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()
    if not key:
        raise SystemExit("Set GEMINI_API_KEY in .env. A free key comes from Google AI Studio.")
    model = (os.environ.get("KUKU_MODEL") or DEFAULT_MODEL).strip()
    return key, model


def parse_json_text(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned[: cleaned.rfind("```")]
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end < start:
            raise
        data = json.loads(cleaned[start : end + 1])
    if isinstance(data, list):
        return {"beats": data}
    if not isinstance(data, dict):
        raise ValueError("Model JSON was not an object")
    return data


class GeminiClient:
    def __init__(self, cache_dir: Path, api_key: str | None = None, model: str | None = None):
        loaded_key, loaded_model = load_settings()
        self.api_key = api_key or loaded_key
        self.model = model or loaded_model
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.calls = 0
        self._client = None

    def _sdk(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def complete_json(self, system: str, user: str) -> dict:
        digest = hashlib.sha256(f"{self.model}\n{system}\n{user}".encode("utf-8")).hexdigest()
        cache_path = self.cache_dir / f"{digest}.json"
        if cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8"))

        from google.genai import types

        last_error: Exception | None = None
        for attempt in range(4):
            try:
                response = self._sdk().models.generate_content(
                    model=self.model,
                    contents=user,
                    config=types.GenerateContentConfig(
                        system_instruction=system,
                        temperature=0.3,
                        max_output_tokens=16384,
                        response_mime_type="application/json",
                    ),
                )
                self.calls += 1
                text = getattr(response, "text", None) or ""
                if not text:
                    raise RuntimeError(f"Empty model response: {response!r}"[:500])
                data = parse_json_text(text)
                cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                usage_path = self.cache_dir / "usage.json"
                usage = {"model": self.model, "calls": 0}
                if usage_path.exists():
                    usage = json.loads(usage_path.read_text(encoding="utf-8"))
                usage["model"] = self.model
                usage["calls"] = int(usage.get("calls", 0)) + 1
                usage_path.write_text(json.dumps(usage, indent=2), encoding="utf-8")
                return data
            except Exception as error:
                last_error = error
                message = str(error)
                if "429" in message or "RESOURCE_EXHAUSTED" in message or "503" in message:
                    time.sleep(2 + attempt * 6)
                    continue
                if attempt == 0 and "JSON" in message.upper() or attempt == 0 and "Expecting" in message:
                    time.sleep(1)
                    continue
                break
        raise RuntimeError(f"Gemini call failed for {self.model}: {last_error}") from last_error
