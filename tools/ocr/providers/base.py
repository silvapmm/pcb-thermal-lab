#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file base.py
@brief Provider interface of the OCR tool: `transcribe(image_bytes, prompt, options) -> Result`.

@details A provider turns one page image into Markdown. It declares whether it sends the page to a remote service
(`online`), the environment variables of its key and its default model. Errors are raised as `ProviderError`
(messages are redacted on construction, so a key never travels in an exception).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from tools.ocr.keys import redact


class ProviderError(Exception):
    """!
    @brief A failed provider call. The message is redacted when the exception is built.
    """

    def __init__(self, message: object, status: int = 0, retryable: bool = False, quota_exhausted: bool = False,
                 retry_after: float | None = None):
        """!
        @brief Build the error.
        @param message         Text of the error (any key in it is removed).
        @param status          HTTP status, or 0 when not an HTTP error.
        @param retryable       True when waiting and trying again may work (429 per minute, 500, 503, timeout).
        @param quota_exhausted True when the daily quota is gone: stop and try tomorrow.
        @param retry_after     Pause the server asked for, in s (None when it gave none).
        @return None
        """
        super().__init__(redact(message))
        self.status = status
        self.retryable = retryable
        self.quota_exhausted = quota_exhausted
        self.retry_after = retry_after
        self.attempts = 1          # HTTP attempts made before the error was raised (set by the provider)


@dataclass
class Result:
    """!
    @brief The outcome of one transcription call.
    @details text is the Markdown (empty when blocked); finish_reason is the provider's own word ("STOP",
             "RECITATION", ...); recitation is True when the page was refused by a copyright filter; split is True when
             the page should be asked again as two half-page crops (an answer cut at the token limit);
             extra may hold "attempts" (HTTP attempts made) and "usage" ({"input_tokens", "output_tokens"}).
    """

    text: str
    finish_reason: str = "STOP"
    model: str = ""
    seconds: float = 0.0
    recitation: bool = False
    split: bool = False          # True when the answer was cut or refused and two half-page requests may fix it
    extra: dict = field(default_factory=dict)


class Provider(ABC):
    """!
    @brief Base class of the OCR providers.
    """

    name = "base"
    online = True            # True when the image leaves this machine
    key_env: tuple[str, ...] = ()
    default_model = ""

    @abstractmethod
    def transcribe(self, image_bytes: bytes, prompt: str, options: dict) -> Result:
        """!
        @brief Transcribe one page image.
        @param image_bytes PNG bytes of the page (or of a crop of it).
        @param prompt      Instruction text for the model.
        @param options     Dictionary: "model" (str), "temperature" (float), "timeout" (s), ...
        @return Result The Markdown and how the call ended.
        @throws ProviderError On a failed call, after the provider's own retries.
        """

    def list_models(self) -> list[str]:
        """!
        @brief Names of the models the key can use (optional).
        @return list[str] Model names; an empty list when the provider cannot list them.
        """
        return []
