#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file openrouter.py
@brief OpenRouter provider: page image to Markdown through the OpenAI-compatible chat API, free vision models.

@details The key travels in the `Authorization: Bearer` header, never in the URL, so it cannot appear in an error
text. The page is a data URL in an `image_url` content part followed by the prompt. The free plan allows about 20
requests per minute and 50 per day without credits: the provider spaces its requests (`min_interval`, client side) and
the runner stops cleanly at the daily limit (`daily_limit` of data/models.json, counted in the ledger). The model
`auto` (the default) is resolved by ONE `GET /models` request: the models whose id ends in `:free`, whose input
modalities include `image` and whose prices are zero, ranked by `RANK` (document and vision models first) and then by
context length. When a model fails for a reason of its own (unknown, no image input, rate-limited upstream, 5xx after
the retries) the next model of the chain is tried, within `max_attempts` requests per page. Retries on 429 and 5xx
honour `Retry-After`. An error that names the daily limit or the credits raises `ProviderError(quota_exhausted=True)`
so the run stops and the page stays pending. The HTTP calls are two overridable methods (`_post`, `_get`) so that
tests run without a network.
"""

from __future__ import annotations

import base64
import json
import logging
import re
import time
import urllib.error
import urllib.request

from tools.ocr.keys import load_key, register_secret
from tools.ocr.providers.base import Provider, ProviderError, Result

API = "https://openrouter.ai/api/v1"
MAX_ERROR_BODY = 65536
MAX_SERVER_PAUSE = 90.0
DEFAULT_MAX_TOKENS = 8192
QUOTA_WORDS = ("per-day", "per day", "daily", "insufficient credit", "more credits", "credits")
# Order of preference of the free vision models: strongest document readers first. A pattern earlier in the list wins;
# inside one pattern the longer context wins. Whatever is really offered today decides (the list is queried).
EXCLUDE = re.compile(r"safety|guard|moderation|embed", re.I)     # classifiers: they accept images but do not transcribe
RANK = (r"dots|ocr", r"qwen.*vl", r"gemma-?[34]", r"pixtral", r"llama.*(vision|4)", r"mistral", r"gemini", r"nemotron.*vl", r"vl|vision")

log = logging.getLogger("tools.ocr")


def rank_models(models: list[dict]) -> list[str]:
    """!
    @brief Free vision models from a `GET /models` answer, best first.
    @param models The `data` list of the answer (dicts with id, architecture, pricing, context_length).
    @return list[str] Ids that end in `:free`, accept images and cost nothing, ranked by `RANK` then context length.
    """
    keep = []
    for m in models:
        mid = str(m.get("id", ""))
        mods = (m.get("architecture") or {}).get("input_modalities") or []
        price = m.get("pricing") or {}
        try:
            free = all(float(price.get(k) or 0) == 0 for k in ("prompt", "completion"))
        except (TypeError, ValueError):
            free = False
        if mid.endswith(":free") and "image" in mods and free and not EXCLUDE.search(mid):
            keep.append(m)

    def score(m: dict) -> tuple:
        """!
        @brief Sort key of a model.
        @param m Model dict.
        @return tuple (index of the first matching pattern, minus the context length).
        """
        mid = str(m["id"]).lower()
        idx = next((i for i, p in enumerate(RANK) if re.search(p, mid)), len(RANK))
        return (idx, -int(m.get("context_length") or 0), mid)

    return [str(m["id"]) for m in sorted(keep, key=score)]


class OpenRouterProvider(Provider):
    """!
    @brief Provider for the free vision models of OpenRouter (online).
    """

    name = "openrouter"
    online = True
    key_env = ("OPENROUTER_API_KEY",)
    default_model = "auto"
    header_model = True          # the page file records which model transcribed it

    def __init__(self, key: str | None = None, retries: int = 2, first_pause: float = 10.0, sleep=time.sleep,
                 min_interval: float = 3.2, max_attempts: int = 3, clock=time.monotonic):
        """!
        @brief Create the provider.
        @param key          API key; when None it is looked up (environment, then `.ocr_keys`) at the first call.
        @param retries      Attempts per model for a retryable error (at least 1).
        @param first_pause  Pause before the second attempt, in seconds; doubled after each failure.
        @param sleep        Function used to wait (replaced in tests).
        @param min_interval Seconds between two generation requests (the free plan allows about 20 per minute).
        @param max_attempts HTTP generation requests allowed for one page over the whole model chain.
        @param clock        Monotonic clock in seconds (replaced in tests).
        @return None
        """
        self._key = key
        self.retries = max(1, int(retries))
        self.first_pause = first_pause
        self._sleep = sleep
        self.min_interval = min_interval
        self.max_attempts = max(1, int(max_attempts))
        self._clock = clock
        self._last = None
        self._chain: list[str] | None = None

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

    def _headers(self) -> dict:
        """!
        @brief Request headers (the key is in `Authorization` only).
        @return dict The headers.
        """
        return {"Content-Type": "application/json", "Authorization": f"Bearer {self.key}",
                "X-Title": "pcb-thermal-lab OCR"}

    def _post(self, url: str, body: bytes, timeout: float) -> dict:
        """!
        @brief POST a JSON body and decode the JSON answer.
        @param url     Full URL (without the key).
        @param body    JSON bytes.
        @param timeout Seconds.
        @return dict The decoded response.
        @throws urllib.error.HTTPError On an HTTP error (the caller classifies it).
        """
        req = urllib.request.Request(url, data=body, method="POST", headers=self._headers())
        # The socket timeout is per read and OpenRouter sends keep-alive bytes while a free model queues, so a
        # request could last for ever: read in chunks and stop at a wall-clock deadline.
        deadline = time.monotonic() + timeout
        with urllib.request.urlopen(req, timeout=min(timeout, 30)) as r:
            chunks = []
            while True:
                try:
                    chunk = r.read(65536)
                except TimeoutError:
                    chunk = None
                if chunk == b"":
                    break
                if chunk:
                    chunks.append(chunk)
                if time.monotonic() > deadline:
                    raise TimeoutError(f"no complete answer in {timeout:.0f} s")
            return json.loads(b"".join(chunks))

    def _get(self, url: str, timeout: float) -> dict:
        """!
        @brief GET and decode a JSON answer.
        @param url     Full URL (without the key).
        @param timeout Seconds.
        @return dict The decoded response.
        @throws urllib.error.HTTPError On an HTTP error.
        """
        req = urllib.request.Request(url, method="GET", headers=self._headers())
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())

    def list_models(self) -> list[str]:
        """!
        @brief The free vision models offered now, best first (one `GET /models` request, cached in the instance).
        @return list[str] Model ids; empty when the request fails (the error is logged, redacted).
        """
        if self._chain is None:
            try:
                self._chain = rank_models((self._get(API + "/models", 60) or {}).get("data") or [])
            except urllib.error.HTTPError as e:
                log.error("model list: %s", self._classify(e.code, e.read(MAX_ERROR_BODY).decode("utf-8", "replace")))
                return []
            except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
                log.error("model list: %s", ProviderError(f"{type(e).__name__}: {e}"))
                return []
        return list(self._chain)

    @staticmethod
    def _classify(code: int, message: str, retry_after: str | None = None) -> ProviderError:
        """!
        @brief Turn an HTTP error into a ProviderError with the right flags.
        @param code        HTTP status.
        @param message     The response body (`{"error": {"message", "code"}}` or any text).
        @param retry_after Value of the `Retry-After` header in seconds (text), or None.
        @return ProviderError With `retryable`, `quota_exhausted` and `retry_after` (s, or None) set.
        """
        shown = message
        try:
            err = json.loads(message).get("error") or {}
            shown = str(err.get("message", message))
            if isinstance(err.get("metadata"), dict) and err["metadata"].get("raw"):
                shown += " | " + str(err["metadata"]["raw"])
        except (ValueError, AttributeError):
            pass
        low = shown.lower()
        # The daily cap of the free plan and an empty balance do not recover by waiting a minute: stop the run.
        quota = code in (402, 429) and any(w in low for w in QUOTA_WORDS)
        retryable = code in (408, 429, 500, 502, 503, 504) and not quota
        try:
            delay = float(retry_after) if retry_after else None
        except ValueError:
            delay = None
        return ProviderError(f"HTTP {code}: {' '.join(shown.split())[:400]}", status=code, retryable=retryable,
                             quota_exhausted=quota, retry_after=delay)

    def _throttle(self) -> None:
        """!
        @brief Wait so that two generation requests are at least `min_interval` seconds apart.
        @return None
        """
        now = self._clock()
        if self._last is not None and now - self._last < self.min_interval:
            self._sleep(self.min_interval - (now - self._last))
        self._last = self._clock()

    def transcribe(self, image_bytes: bytes, prompt: str, options: dict) -> Result:
        """!
        @brief Transcribe one page image with a free vision model.
        @param image_bytes PNG bytes.
        @param prompt      Instruction text.
        @param options     "model" (an id, or "auto" for the ranked chain), "timeout" (180 s), "max_tokens" (8192).
        @return Result Text and finish reason; `split=True` for `length`; `model` is the model that answered;
                `extra` holds "attempts" and "usage".
        @throws ProviderError After the chain is exhausted, or at once for the daily limit or a bad key.
        """
        want = options.get("model") or self.default_model
        # An explicit id is used alone; "auto" asks the list (one request) and keeps the best few as the chain.
        chain = [want] if want != "auto" else self.list_models()[:4]
        if not chain:
            raise ProviderError("no free vision model is offered by OpenRouter right now")
        data_url = "data:image/png;base64," + base64.b64encode(image_bytes).decode()
        t0, attempts, last = time.time(), 0, None
        for model in chain:
            body = json.dumps({"model": model, "max_tokens": int(options.get("max_tokens", DEFAULT_MAX_TOKENS)),
                               "messages": [{"role": "user", "content": [
                                   {"type": "image_url", "image_url": {"url": data_url}},
                                   {"type": "text", "text": prompt}]}]}).encode()
            pause = self.first_pause
            for k in range(self.retries):
                if attempts >= self.max_attempts:
                    break
                attempts += 1
                self._throttle()
                try:
                    resp = self._post(API + "/chat/completions", body, options.get("timeout", 180))
                    err = None
                    if isinstance(resp, dict) and resp.get("error") and not resp.get("choices"):
                        e = resp["error"]
                        err = self._classify(int(e.get("code") or 502) if str(e.get("code", "")).isdigit() else 502,
                                             json.dumps({"error": e}))
                except urllib.error.HTTPError as e:
                    hdr = e.headers.get("Retry-After") if e.headers is not None else None
                    err = self._classify(e.code, e.read(MAX_ERROR_BODY).decode("utf-8", "replace"), hdr)
                except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
                    err = ProviderError(f"{type(e).__name__}: {e}", retryable=True)
                if err is None:
                    return self._result(resp, model, attempts, time.time() - t0)
                last = err
                err.attempts = attempts
                if err.quota_exhausted or err.status in (401, 403):
                    raise err
                if not err.retryable or k == self.retries - 1 or attempts >= self.max_attempts:
                    break
                wait = min(MAX_SERVER_PAUSE, err.retry_after) if err.retry_after else pause
                log.warning("%s: attempt %d failed (%s); waiting %.0f s", model, attempts, str(err)[:120], wait)
                self._sleep(wait)
                pause *= 2
            log.info("%s failed (%s); trying the next model", model, str(last)[:100])
            if attempts >= self.max_attempts:
                break
        assert last is not None
        last.attempts = attempts
        raise last

    @staticmethod
    def _result(resp: dict, model: str, attempts: int, seconds: float) -> Result:
        """!
        @brief Build the Result from a chat completion answer.
        @param resp     The decoded answer.
        @param model    Model id that answered.
        @param attempts HTTP requests made for the page.
        @param seconds  Elapsed seconds.
        @return Result The text, finish reason and token usage.
        """
        ch = (resp.get("choices") or [{}])[0]
        content = (ch.get("message") or {}).get("content") or ""
        if isinstance(content, list):
            content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
        fin = str(ch.get("finish_reason") or ch.get("native_finish_reason") or "stop")
        usage = resp.get("usage") or {}
        return Result(text=str(content), finish_reason=fin, model=str(resp.get("model") or model),
                      seconds=round(seconds, 1), split=(fin == "length"), recitation=(fin == "content_filter"),
                      extra={"attempts": attempts,
                             "usage": {"input_tokens": int(usage.get("prompt_tokens") or 0),
                                       "output_tokens": int(usage.get("completion_tokens") or 0)}})
