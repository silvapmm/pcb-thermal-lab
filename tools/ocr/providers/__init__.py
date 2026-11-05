#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file __init__.py
@brief Registry of the OCR providers. A new provider is a class with `name`, `online`, `key_env`,
       `default_model` and `transcribe()` (see base.py) added to REGISTRY.
"""

from __future__ import annotations

from tools.ocr.providers.base import Provider, ProviderError, Result
from tools.ocr.providers.anthropic import AnthropicProvider
from tools.ocr.providers.gemini import GeminiProvider
from tools.ocr.providers.local import LocalProvider

REGISTRY: dict[str, type[Provider]] = {"gemini": GeminiProvider, "anthropic": AnthropicProvider, "local": LocalProvider}


def get_provider(name: str) -> Provider:
    """!
    @brief Create a provider by name.
    @param name Key of REGISTRY ("gemini", "anthropic", "local").
    @return Provider A new instance.
    @throws KeyError If the name is unknown.
    """
    if name not in REGISTRY:
        raise KeyError(f"unknown provider '{name}'; known: {', '.join(sorted(REGISTRY))}")
    return REGISTRY[name]()


__all__ = ["Provider", "ProviderError", "Result", "REGISTRY", "get_provider"]
