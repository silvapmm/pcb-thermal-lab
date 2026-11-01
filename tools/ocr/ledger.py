#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file ledger.py
@brief The ledger of requests (usage.json) and the queue file (QUEUE.md) of the OCR tool.

@details The ledger is a JSON list, one entry per page attempt: date, provider, model, file, page, ok, seconds,
words, requests, note. It is the same file the first scripts wrote (older entries have no provider or requests:
they count as "gemini" and one request). The queue is the Markdown table `| # | file | page | why |` of
`papers/gemini/QUEUE.md`; lines `file.pdf page` or `file.pdf:page` are accepted too.
"""

from __future__ import annotations

import datetime
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path


class Ledger:
    """!
    @brief Append-only record of page attempts, saved atomically after each entry.
    """

    def __init__(self, path: Path):
        """!
        @brief Open (or start) a ledger.
        @param path Path of usage.json.
        @return None
        """
        self.path = Path(path)
        self.entries: list[dict] = json.loads(self.path.read_text()) if self.path.is_file() else []

    def add(self, **entry) -> dict:
        """!
        @brief Append an entry (today's date is filled in) and save the file.
        @param entry Fields of the entry (provider, model, file, page, ok, seconds, words, requests, note).
        @return dict The stored entry.
        """
        entry.setdefault("date", str(datetime.date.today()))
        self.entries.append(entry)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.entries, indent=1))
        os.replace(tmp, self.path)
        return entry

    def requests_today(self, provider: str, today: str | None = None) -> int:
        """!
        @brief Number of requests sent today to a provider.
        @param provider Provider name.
        @param today    Date text (default: today).
        @return int Sum of the `requests` fields (1 for old entries).
        """
        today = today or str(datetime.date.today())
        return sum(e.get("requests", 1) for e in self.entries
                   if e.get("date") == today and e.get("provider", "gemini") == provider)

    def done(self, provider: str | None = None) -> set[tuple[str, int]]:
        """!
        @brief Pages already transcribed successfully.
        @param provider Restrict to a provider, or None for all.
        @return set[tuple[str, int]] Pairs (file stem, page).
        """
        return {(e["file"], e["page"]) for e in self.entries
                if e.get("ok") and (provider is None or e.get("provider", "gemini") == provider)}


@dataclass
class QueueItem:
    """!
    @brief One line of the queue: a PDF stem and a 1-based page.
    """

    file: str
    page: int
    why: str = ""


def parse_queue(text: str) -> list[QueueItem]:
    """!
    @brief Read the queue lines of a QUEUE.md-like text.
    @param text File content.
    @return list[QueueItem] Items in file order.
    """
    items = []
    for line in text.splitlines():
        m = re.match(r"\|\s*\d+\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*([^|]*?)\s*\|?\s*$", line)
        if not m:
            m2 = re.match(r"^\s*([^\s|#:]+?)(?:\.pdf)?\s*[: ]\s*(\d+)\s*$", line)
            if not m2:
                continue
            items.append(QueueItem(m2.group(1), int(m2.group(2))))
            continue
        items.append(QueueItem(re.sub(r"\.pdf$", "", m.group(1)), int(m.group(2)), m.group(3)))
    return items
