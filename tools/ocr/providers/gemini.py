#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file gemini.py
@brief Gemini (Google AI Studio) provider: page image to Markdown through generateContent.

@details The key travels in the `x-goog-api-key` header, never in the URL, so it cannot appear in an error text.
Retries with a growing pause on HTTP 429 (rate per minute), 500 and 503 and on network errors; an HTTP 429 that
names a daily quota raises `ProviderError(quota_exhausted=True)` at once. A response with finishReason RECITATION
(HTTP 200, empty content) is returned as a `Result` with `recitation=True`: the caller decides what to do.
The HTTP call is one overridable method (`_post`) so that tests run without a network.
"""

from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request

from tools.ocr.keys import load_key
from tools.ocr.providers.base import Provider, ProviderError, Result

API = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider(Provider):
    """!
    @brief Provider for the Gemini models of Google AI Studio (online).
    """

    name = "gemini"
    online = True
    key_env = ("GEMINI_API_KEY", "GOOGLE_API_KEY")
    default_model = "gemini-3.1-flash-lite"

    def __init__(self, key: str | None = None, retries: int = 4, first_pause: float = 20.0, sleep=time.sleep):
        """!
        @brief Create the provider.
        @param key         API key; when None it is looked up (environment, then `.ocr_keys`) at the first call.
        @param retries     Number of attempts for a retryable error.
        @param first_pause Pause before the second attempt, in seconds; doubled after each failure.
        @param sleep       Function used to wait (replaced in tests).
        @return None
        """
        self._key = key
        self.retries = retries
        self.first_pause = first_pause
        self._sleep = sleep

    @property
    def key(self) -> str:
        """!
        @brief The API key, looked up on first use.
        @return str The key (never print it).
        """
        if self._key is None:
            self._key = load_key(self.name, self.key_env)
        else:
            from tools.ocr.keys import register_secret
            register_secret(self._key)
        return self._key

    def _post(self, url: str, body: bytes, timeout: float) -> dict:
        """!
        @brief POST a JSON body with the key in the header and decode the JSON answer.
        @param url     Full URL (without the key).
        @param body    JSON bytes.
        @param timeout Seconds.
        @return dict The decoded response.
        @throws urllib.error.HTTPError On an HTTP error (the caller classifies it).
        """
        req = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Content-Type": "application/json", "x-goog-api-key": self.key})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())

    def _get(self, url: str, timeout: float) -> dict:
        """!
        @brief GET a JSON document with the key in the header.
        @param url     Full URL (without the key).
        @param timeout Seconds.
        @return dict The decoded response.
        """
        req = urllib.request.Request(url, headers={"x-goog-api-key": self.key})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())

    @staticmethod
    def _classify(code: int, message: str) -> ProviderError:
        """!
        @brief Turn an HTTP error into a ProviderError with the right flags.
        @param code    HTTP status.
        @param message Start of the response body.
        @return ProviderError With `retryable` and `quota_exhausted` set.
        """
        low = message.lower()
        daily = code == 429 and ("perday" in low.replace(" ", "") or "per day" in low or "daily" in low)
        retryable = code in (429, 500, 503) and not daily
        return ProviderError(f"HTTP {code}: {' '.join(message.split())[:300]}", status=code,
                             retryable=retryable, quota_exhausted=daily)

    def transcribe(self, image_bytes: bytes, prompt: str, options: dict) -> Result:
        """!
        @brief Transcribe one page image with a Gemini model.
        @param image_bytes PNG bytes.
        @param prompt      Instruction text.
        @param options     "model" (default `default_model`), "temperature" (0.0), "timeout" (180 s).
        @return Result Text and finish reason; `recitation=True` when the filter blocked the page.
        @throws ProviderError After the retries, or at once for a daily quota or a non-retryable error.
        """
        model = options.get("model") or self.default_model
        url = f"{API}/models/{model}:generateContent"
        body = json.dumps({"contents": [{"parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(image_bytes).decode()}}]}],
            "generationConfig": {"temperature": options.get("temperature", 0.0)}}).encode()
        pause = self.first_pause
        t0 = time.time()
        for attempt in range(self.retries):
            try:
                resp = self._post(url, body, options.get("timeout", 180))
                break
            except urllib.error.HTTPError as e:
                err = self._classify(e.code, e.read().decode("utf-8", "replace")[:600])
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                err = ProviderError(f"{type(e).__name__}: {e}", retryable=True)
            if not err.retryable or attempt == self.retries - 1:
                raise err
            self._sleep(pause)
            pause *= 2
        cand = (resp.get("candidates") or [{}])[0]
        parts = (cand.get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts)
        finish = cand.get("finishReason", "")
        if not text and not cand:
            finish = "NO_CANDIDATE"
        return Result(text=text, finish_reason=finish or "STOP", model=model, seconds=round(time.time() - t0, 1),
                      recitation=(finish == "RECITATION"))

    def list_models(self) -> list[str]:
        """!
        @brief The models that support generateContent for this key.
        @return list[str] Model names.
        @throws ProviderError On an HTTP error.
        """
        try:
            data = self._get(f"{API}/models?pageSize=200", 60)
        except urllib.error.HTTPError as e:
            raise self._classify(e.code, e.read().decode("utf-8", "replace")[:300])
        return [m["name"].split("/")[-1] for m in data.get("models", [])
                if "generateContent" in m.get("supportedGenerationMethods", [])]
