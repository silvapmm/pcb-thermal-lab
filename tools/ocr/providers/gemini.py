#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file gemini.py
@brief Gemini (Google AI Studio) provider: page image to Markdown through generateContent.

@details The key travels in the `x-goog-api-key` header, never in the URL, so it cannot appear in an error text.
Retries with a growing pause on HTTP 429 (rate per minute), 500 and 503 and on network errors, or with the pause the
server asks for (`RetryInfo.retryDelay`, capped at MAX_SERVER_PAUSE); every retry is logged (status and pause, no
key), so a slow run is never silent. An HTTP 429 whose `QuotaFailure` names a daily quota (`quotaId` with
`PerDay`) raises `ProviderError(quota_exhausted=True)` at once: the error body is parsed as JSON in full, because
the quota id comes after the long message and a cut text loses it. A response with finishReason RECITATION
(HTTP 200, empty content) is returned as a `Result` with `recitation=True`: the caller decides what to do.
The HTTP call is one overridable method (`_post`) so that tests run without a network.
"""

from __future__ import annotations

import base64
import json
import logging
import re
import time
import urllib.error
import urllib.request

from tools.ocr.keys import load_key
from tools.ocr.providers.base import Provider, ProviderError, Result

API = "https://generativelanguage.googleapis.com/v1beta"
MAX_ERROR_BODY = 65536      # bytes of an error body that are read (a 429 body with its details is about 1 to 2 KB)
MAX_SERVER_PAUSE = 120.0    # s: the longest pause taken from the server's RetryInfo

log = logging.getLogger("tools.ocr")


def _quota_details(body: str) -> tuple[list[str], float | None]:
    """!
    @brief The quota ids and the retry delay of a Google API error body.
    @param body Error body (JSON from the API; any other text gives nothing).
    @return tuple[list[str], float|None] The `quotaId` values of the QuotaFailure details and the RetryInfo delay in s.
    """
    try:
        details = (json.loads(body).get("error") or {}).get("details") or []
    except (ValueError, AttributeError):
        return [], None
    ids, delay = [], None
    for d in details if isinstance(details, list) else []:
        if not isinstance(d, dict):
            continue
        for v in d.get("violations") or []:
            if isinstance(v, dict) and v.get("quotaId"):
                ids.append(str(v["quotaId"]))
        m = re.fullmatch(r"\s*([\d.]+)s\s*", str(d.get("retryDelay", "")))
        if m:
            delay = float(m.group(1))
    return ids, delay


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
        @param retries     Number of attempts for a retryable error (at least 1).
        @param first_pause Pause before the second attempt, in seconds; doubled after each failure.
        @param sleep       Function used to wait (replaced in tests).
        @return None
        """
        self._key = key
        self.retries = max(1, int(retries))
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
        @param message The response body (whole, up to MAX_ERROR_BODY): JSON details are parsed, the text is searched.
        @return ProviderError With `retryable`, `quota_exhausted` and `retry_after` (s, or None) set.
        """
        ids, delay = _quota_details(message)
        low = (message + " " + " ".join(ids)).lower()
        daily = code == 429 and ("perday" in low.replace(" ", "") or "per day" in low or "daily" in low)
        retryable = code in (429, 500, 503) and not daily
        # Show the API's own message, not the JSON around it, and say which quota it was.
        try:
            shown = str((json.loads(message).get("error") or {}).get("message", message))
        except (ValueError, AttributeError):
            shown = message
        # The quota id goes first, so that cutting a long message never loses it.
        quota = (" [quota: " + ", ".join(sorted(set(ids))) + "]") if ids else ""
        return ProviderError(f"HTTP {code}{quota}: {' '.join(shown.split())[:400]}", status=code,
                             retryable=retryable, quota_exhausted=daily, retry_after=delay)

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
                err = self._classify(e.code, e.read(MAX_ERROR_BODY).decode("utf-8", "replace"))
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                err = ProviderError(f"{type(e).__name__}: {e}", retryable=True)
            if not err.retryable or attempt == self.retries - 1:
                err.attempts = attempt + 1
                raise err
            # The server's own delay when it gives one (a per-minute 429 says how long), else the doubling pause.
            wait = min(MAX_SERVER_PAUSE, err.retry_after) if err.retry_after else pause
            log.warning("%s: attempt %d of %d failed (%s); waiting %.0f s", model, attempt + 1, self.retries,
                        str(err)[:120], wait)
            self._sleep(wait)
            pause *= 2
        cand = (resp.get("candidates") or [{}])[0]
        parts = (cand.get("content") or {}).get("parts") or []
        # Thought summaries (when a model returns them) are not part of the transcription.
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        finish = cand.get("finishReason", "")
        if not text and not cand:
            # No candidate at all: the prompt itself was blocked; keep the reason the API gives.
            finish = "NO_CANDIDATE:" + str((resp.get("promptFeedback") or {}).get("blockReason", "unknown"))
        return Result(text=text, finish_reason=finish or "STOP", model=model, seconds=round(time.time() - t0, 1),
                      recitation=(finish == "RECITATION"), extra={"attempts": attempt + 1})

    def list_models(self) -> list[str]:
        """!
        @brief The models that support generateContent for this key.
        @return list[str] Model names.
        @throws ProviderError On an HTTP error.
        """
        try:
            data = self._get(f"{API}/models?pageSize=200", 60)
        except urllib.error.HTTPError as e:
            raise self._classify(e.code, e.read(MAX_ERROR_BODY).decode("utf-8", "replace"))
        return [m["name"].split("/")[-1] for m in data.get("models", [])
                if "generateContent" in m.get("supportedGenerationMethods", [])]
