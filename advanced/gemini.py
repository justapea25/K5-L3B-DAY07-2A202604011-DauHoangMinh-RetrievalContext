"""Minimal Gemini REST client (vision) with on-disk cache, retries and token accounting."""
from __future__ import annotations

import base64
import hashlib
import json
import time
import urllib.error
import urllib.request

from src.common import env

from .config import CACHE_DIR, GEMINI_MODEL, GEMINI_PRICE

BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class Gemini:
    def __init__(self, model: str = GEMINI_MODEL) -> None:
        self.key = env("GEMINI_API_KEY")
        self.model = model
        self.tokens_in = self.tokens_out = self.calls = self.cache_hits = 0
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def cost(self) -> float:
        return (self.tokens_in * GEMINI_PRICE[0] + self.tokens_out * GEMINI_PRICE[1]) / 1e6

    def describe(self, png: bytes, prompt: str, retries: int = 5) -> dict:
        key = hashlib.sha256(self.model.encode() + prompt.encode() + png).hexdigest()[:32]
        cache = CACHE_DIR / f"{key}.json"
        if cache.exists():
            self.cache_hits += 1
            return json.loads(cache.read_text(encoding="utf-8"))
        body = {"contents": [{"parts": [{"text": prompt},
                                        {"inline_data": {"mime_type": "image/png",
                                                         "data": base64.b64encode(png).decode()}}]}],
                "generationConfig": {"temperature": 0}}
        req_data = json.dumps(body).encode()
        delay = 4.0
        for attempt in range(retries):
            req = urllib.request.Request(f"{BASE}/{self.model}:generateContent", data=req_data,
                                         headers={"x-goog-api-key": self.key,
                                                  "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    out = json.loads(r.read())
                break
            except urllib.error.HTTPError as e:
                msg = e.read().decode()[:300]
                if e.code in (429, 500, 503) and attempt < retries - 1:
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise RuntimeError(f"Gemini HTTP {e.code}: {msg}") from None
        text = "".join(p.get("text", "") for p in out["candidates"][0]["content"]["parts"]).strip()
        usage = out.get("usageMetadata", {})
        res = {"text": text, "model_version": out.get("modelVersion", self.model),
               "tokens_in": usage.get("promptTokenCount", 0),
               "tokens_out": usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0)}
        self.calls += 1
        self.tokens_in += res["tokens_in"]
        self.tokens_out += res["tokens_out"]
        cache.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
        return res


class OpenAIVision:
    """Fallback vision extractor (gpt-4o-mini) used when Gemini fails (e.g. quota 429)."""

    PRICE = (0.15, 0.60)

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        from openai import OpenAI
        self.client = OpenAI(api_key=env("OPENAI_API_KEY"), timeout=180, max_retries=2)
        self.model = model
        self.tokens_in = self.tokens_out = self.calls = self.cache_hits = 0

    def cost(self) -> float:
        return (self.tokens_in * self.PRICE[0] + self.tokens_out * self.PRICE[1]) / 1e6

    def describe(self, png: bytes, prompt: str) -> dict:
        key = hashlib.sha256(self.model.encode() + prompt.encode() + png).hexdigest()[:32]
        cache = CACHE_DIR / f"oa_{key}.json"
        if cache.exists():
            self.cache_hits += 1
            return json.loads(cache.read_text(encoding="utf-8"))
        url = "data:image/png;base64," + base64.b64encode(png).decode()
        r = self.client.chat.completions.create(
            model=self.model, temperature=0,
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt},
                                                   {"type": "image_url", "image_url": {"url": url, "detail": "high"}}]}])
        res = {"text": r.choices[0].message.content.strip(), "model_version": r.model,
               "tokens_in": r.usage.prompt_tokens, "tokens_out": r.usage.completion_tokens}
        self.calls += 1
        self.tokens_in += res["tokens_in"]
        self.tokens_out += res["tokens_out"]
        cache.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
        return res


class VisionWithFallback:
    def __init__(self) -> None:
        self.primary, self.fallback = Gemini(), None
        self.fallback_used: list[str] = []

    def describe(self, png: bytes, prompt: str) -> dict:
        try:
            return self.primary.describe(png, prompt)
        except RuntimeError as e:
            if self.fallback is None:
                self.fallback = OpenAIVision()
            self.fallback_used.append(str(e)[:80])
            return self.fallback.describe(png, prompt)

    def stats(self) -> dict:
        out = {"primary": {"model": self.primary.model, "calls": self.primary.calls,
                           "cache_hits": self.primary.cache_hits, "tokens_in": self.primary.tokens_in,
                           "tokens_out": self.primary.tokens_out, "cost_usd_est": round(self.primary.cost(), 4)}}
        if self.fallback:
            f = self.fallback
            out["fallback"] = {"model": f.model, "calls": f.calls, "cache_hits": f.cache_hits,
                               "tokens_in": f.tokens_in, "tokens_out": f.tokens_out,
                               "cost_usd_est": round(f.cost(), 4), "reasons": self.fallback_used}
        return out
