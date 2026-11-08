from __future__ import annotations

import hashlib
import json
import os
import time
from abc import ABC, abstractmethod
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_PROVIDER = "gemini"
DEFAULT_MODEL = "gemini-3.5-flash-lite"
# Modern available models on Google AI Studio
FALLBACK_MODELS = ["gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-3.5-flash"]


def project_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in (here.parents[2], Path.cwd()):
        if (candidate / "pyproject.toml").exists():
            return candidate
    return Path.cwd()


def load_settings() -> tuple[str, str, str]:
    root = project_root()
    load_dotenv(root / ".env")
    load_dotenv()
    provider = (os.environ.get("LLM_PROVIDER") or DEFAULT_PROVIDER).strip().lower()
    key = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()
    model = (os.environ.get("KUKU_MODEL") or DEFAULT_MODEL).strip()
    return provider, key, model


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


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate USD cost based on known model rates per 1M tokens."""
    model_lower = model.lower()
    if "pro" in model_lower:
        rate_in, rate_out = 1.25, 5.00
    else:  # flash / flash-lite
        rate_in, rate_out = 0.075, 0.30
    cost = (input_tokens / 1_000_000.0) * rate_in + (output_tokens / 1_000_000.0) * rate_out
    return round(cost, 6)


class BaseLLMClient(ABC):
    """Abstract Base Class for swappable LLM providers."""

    def __init__(self, cache_dir: Path | str, model: str | None = None, provider: str = "base"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.model = model or DEFAULT_MODEL
        self.provider = provider
        self.calls = 0
        self.cached_hits = 0
        self.input_tokens = 0
        self.output_tokens = 0

    @abstractmethod
    def complete_json(self, system: str, user: str) -> dict:
        """Submit a prompt and return a parsed JSON dictionary."""
        raise NotImplementedError

    def _cache_path(self, system: str, user: str) -> Path:
        digest = hashlib.sha256(f"{self.provider}:{self.model}\n{system}\n{user}".encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def record_usage(self, in_tokens: int = 0, out_tokens: int = 0, cached: bool = False) -> None:
        if cached:
            self.cached_hits += 1
        else:
            self.calls += 1
            self.input_tokens += in_tokens
            self.output_tokens += out_tokens

        usage_path = self.cache_dir / "usage.json"
        usage: dict = {
            "provider": self.provider,
            "model": self.model,
            "calls": self.calls,
            "cached_hits": self.cached_hits,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.input_tokens + self.output_tokens,
            "estimated_cost_usd": estimate_cost_usd(self.model, self.input_tokens, self.output_tokens),
        }
        if usage_path.exists():
            try:
                prior = json.loads(usage_path.read_text(encoding="utf-8"))
                usage["calls"] = prior.get("calls", 0) + (0 if cached else 1)
                usage["cached_hits"] = prior.get("cached_hits", 0) + (1 if cached else 0)
                usage["input_tokens"] = prior.get("input_tokens", 0) + in_tokens
                usage["output_tokens"] = prior.get("output_tokens", 0) + out_tokens
                usage["total_tokens"] = usage["input_tokens"] + usage["output_tokens"]
                usage["estimated_cost_usd"] = estimate_cost_usd(self.model, usage["input_tokens"], usage["output_tokens"])
            except Exception:
                pass
        usage_path.write_text(json.dumps(usage, indent=2), encoding="utf-8")


class GeminiClient(BaseLLMClient):
    """Google Gemini provider implementation using google-genai SDK."""

    def __init__(self, cache_dir: Path | str, api_key: str | None = None, model: str | None = None):
        _provider, loaded_key, loaded_model = load_settings()
        selected_model = model or loaded_model or DEFAULT_MODEL
        super().__init__(cache_dir, model=selected_model, provider="gemini")
        self.api_key = api_key or loaded_key
        if not self.api_key:
            raise SystemExit("Set GEMINI_API_KEY in .env. A free key comes from Google AI Studio.")
        self._client = None

    def _sdk(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def complete_json(self, system: str, user: str) -> dict:
        cache_path = self._cache_path(system, user)
        if cache_path.exists():
            self.record_usage(cached=True)
            return json.loads(cache_path.read_text(encoding="utf-8"))

        from google.genai import types

        last_error: Exception | None = None
        models_to_try = [self.model]
        for fallback in FALLBACK_MODELS:
            if fallback != self.model and fallback not in models_to_try:
                models_to_try.append(fallback)

        for current_model in models_to_try:
            for attempt in range(4):
                try:
                    response = self._sdk().models.generate_content(
                        model=current_model,
                        contents=user,
                        config=types.GenerateContentConfig(
                            system_instruction=system,
                            temperature=0.3,
                            max_output_tokens=16384,
                            response_mime_type="application/json",
                        ),
                    )
                    text = getattr(response, "text", None) or ""
                    if not text:
                        raise RuntimeError(f"Empty model response: {response!r}"[:500])
                    data = parse_json_text(text)

                    in_tokens = 0
                    out_tokens = 0
                    usage_meta = getattr(response, "usage_metadata", None)
                    if usage_meta:
                        in_tokens = getattr(usage_meta, "prompt_token_count", 0) or 0
                        out_tokens = getattr(usage_meta, "candidates_token_count", 0) or 0

                    self.model = current_model
                    self.record_usage(in_tokens=in_tokens, out_tokens=out_tokens, cached=False)
                    cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                    return data
                except Exception as error:
                    last_error = error
                    message = str(error)
                    if "404" in message or "NOT_FOUND" in message or "not found" in message.lower():
                        # Try next valid model
                        break
                    if "429" in message or "RESOURCE_EXHAUSTED" in message or "503" in message:
                        time.sleep(2 + attempt * 6)
                        continue
                    if attempt == 0 and ("JSON" in message.upper() or "Expecting" in message):
                        time.sleep(1)
                        continue
                    break

        raise RuntimeError(f"Gemini call failed for {self.model}: {last_error}") from last_error


class MockLLMClient(BaseLLMClient):
    """Deterministic mock client for testing without external API credentials."""

    def __init__(self, cache_dir: Path | str, model: str = "mock-v1"):
        super().__init__(cache_dir, model=model, provider="mock")

    def complete_json(self, system: str, user: str) -> dict:
        cache_path = self._cache_path(system, user)
        if cache_path.exists():
            self.record_usage(cached=True)
            return json.loads(cache_path.read_text(encoding="utf-8"))

        self.record_usage(in_tokens=50, out_tokens=50, cached=False)
        data = {"headings": [], "beats": []}
        cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data


def get_client(
    provider: str | None = None,
    model: str | None = None,
    cache_dir: Path | str | None = None,
    api_key: str | None = None,
) -> BaseLLMClient:
    """Factory function for instantiating LLM clients driven by configuration."""
    loaded_provider, loaded_key, loaded_model = load_settings()
    active_provider = (provider or loaded_provider or DEFAULT_PROVIDER).strip().lower()
    active_model = model or loaded_model or DEFAULT_MODEL
    active_cache = Path(cache_dir) if cache_dir else Path("outputs/cache")

    if active_provider == "gemini":
        return GeminiClient(cache_dir=active_cache, api_key=api_key or loaded_key, model=active_model)
    elif active_provider == "mock":
        return MockLLMClient(cache_dir=active_cache, model=active_model)
    else:
        return GeminiClient(cache_dir=active_cache, api_key=api_key or loaded_key, model=active_model)
