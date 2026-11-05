#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file keys.py
@brief API keys of the OCR providers: lookup (environment, then `.ocr_keys`), permission check and redaction.

@details A key is read first from the environment variable that the provider declares and then from the file
`.ocr_keys` in the project root (the main checkout when the tool runs from a worktree). The file holds one
`provider=KEY` per line (`#` starts a comment) and must not be readable by group or others (mode 600).
Every key that is read is registered, and `redact()` removes registered keys and key-like strings from any text
that could reach a screen, a log or an exception message. A key is never printed.
"""

from __future__ import annotations

import os
import re
import stat
import subprocess
from pathlib import Path

KEY_FILE_NAME = ".ocr_keys"
REPO_ROOT = Path(__file__).resolve().parents[2]

# Patterns of key-like strings that are removed from messages even when the key was not registered
# (an error text from a server may echo a key that came from somewhere else).
KEY_PATTERNS = (
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    # The newer AI Studio keys start with "AQ." and may hold more dots further on: dots are part of the class,
    # otherwise a key whose first segment is shorter than 30 characters would not be matched at all.
    re.compile(r"\bAQ\.[A-Za-z0-9_.-]{30,}"),
    # Anthropic keys: "sk-ant-api03-...", but also "sk-ant-usr-..." and any other family after "sk-ant-".
    re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?i)(api[_-]?key|x-goog-api-key|x-api-key)(\s*[=:]\s*)['\"]?[A-Za-z0-9_.-]{16,}"),
)

_REGISTERED: set[str] = set()


class KeyError_(Exception):
    """!
    @brief The key is missing or the key file is unsafe (the message never contains a key).
    """


def register_secret(secret: str) -> None:
    """!
    @brief Remember a secret so that `redact()` removes it from every text.
    @param secret The secret string (ignored when shorter than 8 characters, to avoid mangling ordinary text).
    @return None
    """
    if secret and len(secret) >= 8:
        _REGISTERED.add(secret)


def redact(text: object) -> str:
    """!
    @brief Replace every registered secret and every key-like string in a text by `[KEY]`.
    @param text Any object; it is converted with str().
    @return str The text without secrets.
    """
    out = str(text)
    # Longest first so that a secret that contains another one is removed whole.
    for s in sorted(_REGISTERED, key=len, reverse=True):
        out = out.replace(s, "[KEY]")
    out = KEY_PATTERNS[0].sub("[KEY]", out)
    out = KEY_PATTERNS[1].sub("[KEY]", out)
    out = KEY_PATTERNS[2].sub("[KEY]", out)
    out = KEY_PATTERNS[3].sub(lambda m: m.group(1) + m.group(2) + "[KEY]", out)
    return out


def project_roots() -> list[Path]:
    """!
    @brief The folders searched for `.ocr_keys`: this checkout first, then the main checkout of the repository.
    @return list[Path] Distinct folders, in search order. A worktree finds the main checkout through
            `git rev-parse --git-common-dir`.
    """
    roots = [REPO_ROOT]
    try:
        r = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=REPO_ROOT, capture_output=True,
                           text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            common = Path(r.stdout.strip())
            if not common.is_absolute():
                common = REPO_ROOT / common
            main = common.resolve().parent
            if main not in roots:
                roots.append(main)
    except (OSError, subprocess.SubprocessError):
        pass  # no git: the current checkout is all we have
    return roots


def check_permissions(path: Path) -> None:
    """!
    @brief Refuse a key file that group or others can read or write.
    @param path Path of the key file.
    @return None
    @throws KeyError_ If the mode has any group or other bit set.
    """
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise KeyError_(f"{path} has mode {mode:o}: other users could read it. Run: chmod 600 {path}")


def parse_key_file(path: Path) -> dict[str, str]:
    """!
    @brief Read a `provider=KEY` file after the permission check.
    @param path Path of the key file.
    @return dict[str, str] Provider name (lower case) to key. The keys are registered for redaction.
    @throws KeyError_ If the permissions are unsafe.
    """
    check_permissions(path)
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        value = value.strip().strip("'\"")
        if value:
            out[name.strip().lower()] = value
            register_secret(value)
    return out


def load_key(provider: str, env_vars: tuple[str, ...], roots: list[Path] | None = None) -> str:
    """!
    @brief Find the API key of a provider.
    @param provider Provider name as written in `.ocr_keys` (for example "gemini").
    @param env_vars Environment variable names the provider accepts, in order.
    @param roots    Folders to search for `.ocr_keys` (default: `project_roots()`).
    @return str The key (also registered for redaction).
    @throws KeyError_ If no key is found or the key file is unsafe.
    """
    for name in env_vars:
        value = os.environ.get(name, "").strip()
        if value:
            register_secret(value)
            return value
    for root in (roots if roots is not None else project_roots()):
        path = root / KEY_FILE_NAME
        if path.is_file():
            keys = parse_key_file(path)
            if provider.lower() in keys:
                return keys[provider.lower()]
    raise KeyError_(f"no key for '{provider}': set {' or '.join(env_vars)} or add the line "
                    f"'{provider}=KEY' to {KEY_FILE_NAME} in the project root (mode 600)")
