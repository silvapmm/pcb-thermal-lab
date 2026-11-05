#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file anthropic.py
@brief Anthropic (Claude) provider: page image to Markdown through the Messages API.

@details The key travels in the `x-api-key` header, never in the URL, so it cannot appear in an error text.
The page is a base64 PNG image block followed by the prompt. Retries (4 attempts) on HTTP 429 (with the
`retry-after` header when given), 500, 502, 503, 529 (overloaded) and on network errors, with a pause that doubles;
every retry is logged (status and pause, no key). An error that says the credit balance, the usage limit or the
spend limit is gone raises `ProviderError(quota_exhausted=True)` at once, so the run stops and the page stays
pending. `stop_reason` `max_tokens` returns a `Result` with `split=True` (the pipeline asks again as two half-page
crops); `refusal` returns `recitation=True` (the same path, then the fallback models). The token usage of the
response is returned in `extra["usage"]` and goes to the ledger. The HTTP call is one overridable method (`_post`)
so that tests run without a network.
"""

from __future__ import annotations

import base64
import json
import logging
import time
import urllib.error
import urllib.request

from tools.ocr.keys import load_key, register_secret
from tools.ocr.providers.base import Provider, ProviderError, Result

API = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
MAX_ERROR_BODY = 65536      # bytes of an error body that are read
MAX_SERVER_PAUSE = 120.0    # s: the longest pause taken from the retry-after header
DEFAULT_MAX_TOKENS = 8192   # a dense page of equations is well below this; a cut answer is split in two halves
QUOTA_WORDS = ("credit balance", "usage limit", "spend limit", "spending limit", "billing")

log = logging.getLogger("tools.ocr")


class AnthropicProvider(Provider):
    """!
    @brief Provider for the Claude models (online).
    """

    name = "anthropic"
    online = True
    key_env = ("ANTHROPIC_API_KEY",)
    default_model = "claude-sonnet-5-5"

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
        req = urllib.request.Request(url, data=body, method="POST", headers={
            "Content-Type": "application/json", "x-api-key": self.key, "anthropic-version": API_VERSION})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())

    @staticmethod
    def _classify(code: int, message: str, retry_after: str | None = None) -> ProviderError:
        """!
        @brief Turn an HTTP error into a ProviderError with the right flags.
        @param code        HTTP status.
        @param message     The response body (JSON `{"type":"error","error":{"type","message"}}` or any text).
        @param retry_after Value of the `retry-after` header in seconds (text), or None.
        @return ProviderError With `retryable`, `quota_exhausted` and `retry_after` (s, or None) set.
        """
        kind, shown = "", message
        try:
            err = json.loads(message).get("error") or {}
            kind, shown = str(err.get("type", "")), str(err.get("message", message))
        except (ValueError, AttributeError):
            pass
        low = (kind + " " + shown).lower()
        # A depleted balance or a spend limit does not recover by waiting a minute: stop the run.
        quota = code in (400, 402, 403, 429) and any(w in low for w in QUOTA_WORDS)
        retryable = code in (429, 500, 502, 503, 529) and not quota
        delay = None
        try:
            delay = float(retry_after) if retry_after else None
        except ValueError:
            delay = None
        return ProviderError(f"HTTP {code} [{kind or 'no type'}]: {' '.join(shown.split())[:400]}", status=code,
                             retryable=retryable, quota_exhausted=quota, retry_after=delay)

    def transcribe(self, image_bytes: bytes, prompt: str, options: dict) -> Result:
        """!
        @brief Transcribe one page image with a Claude model.
        @param image_bytes PNG bytes.
        @param prompt      Instruction text.
        @param options     "model" (default `default_model`), "temperature" (0.0), "timeout" (180 s),
                           "max_tokens" (8192).
        @return Result Text and stop reason; `split=True` for max_tokens, `recitation=True` for a refusal;
                `extra` holds "attempts" and "usage".
        @throws ProviderError After the retries, or at once for a spent balance or a non-retryable error.
        """
        model = options.get("model") or self.default_model
        body = json.dumps({"model": model, "max_tokens": int(options.get("max_tokens", DEFAULT_MAX_TOKENS)),
                           "temperature": options.get("temperature", 0.0),
                           "messages": [{"role": "user", "content": [
                               {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                            "data": base64.b64encode(image_bytes).decode()}},
                               {"type": "text", "text": prompt}]}]}).encode()
        pause = self.first_pause
        t0 = time.time()
        for attempt in range(self.retries):
            try:
                resp = self._post(API, body, options.get("timeout", 180))
                break
            except urllib.error.HTTPError as e:
                hdr = e.headers.get("retry-after") if e.headers is not None else None
                err = self._classify(e.code, e.read(MAX_ERROR_BODY).decode("utf-8", "replace"), hdr)
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                err = ProviderError(f"{type(e).__name__}: {e}", retryable=True)
            if not err.retryable or attempt == self.retries - 1:
                err.attempts = attempt + 1
                raise err
            wait = min(MAX_SERVER_PAUSE, err.retry_after) if err.retry_after else pause
            log.warning("%s: attempt %d of %d failed (%s); waiting %.0f s", model, attempt + 1, self.retries,
                        str(err)[:120], wait)
            self._sleep(wait)
            pause *= 2
        text = "".join(b.get("text", "") for b in (resp.get("content") or [])
                       if isinstance(b, dict) and b.get("type") == "text")
        stop = str(resp.get("stop_reason") or "")
        usage = resp.get("usage") or {}
        return Result(text=text, finish_reason=stop or "end_turn", model=model, seconds=round(time.time() - t0, 1),
                      recitation=(stop == "refusal"), split=(stop == "max_tokens"),
                      extra={"attempts": attempt + 1,
                             "usage": {"input_tokens": int(usage.get("input_tokens") or 0),
                                       "output_tokens": int(usage.get("output_tokens") or 0)}})
