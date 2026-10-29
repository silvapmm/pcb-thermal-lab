#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_theory.py
@brief Checks of the theory folder: every figure and link in the topics exists, every bibliography key used in a topic is defined, and every topic has the required sections.
@details Run: .venv/bin/python -m pytest -q research/theory/tests (from the repository root).
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOPICS = sorted((ROOT / "topics").glob("*.md"))
SECTIONS = ("## 1.", "Related topics", "Sources", "What was read and what was not verified")


def keys_defined():
    """!
    @brief The bibliography keys defined as `### [Key]` headings.
    @return set of str.
    """
    text = (ROOT / "BIBLIOGRAPHY.md").read_text()
    return set(re.findall(r"^### \[([^\]]+)\]", text, flags=re.M))


def test_there_are_37_topics():
    """!
    @brief The folder holds the 37 topic files, numbered without gaps.
    @return None.
    """
    assert [p.name[:2] for p in TOPICS] == [f"{i:02d}" for i in range(1, 38)]


def test_every_image_and_link_exists():
    """!
    @brief Every relative image and Markdown link of the README and the topics points to a file that exists.
    @return None.
    """
    for md in [ROOT / "README.md"] + TOPICS:
        for target in re.findall(r"\]\(([^)#]+)\)", md.read_text()):
            if target.startswith("http"):
                continue
            assert (md.parent / target).exists(), f"{md.name}: missing {target}"


def test_every_bibliography_key_is_defined():
    """!
    @brief Every `[Key]` used in the Sources of a topic (and in the keys of the own-computation table) is defined in the bibliography.
    @return None.
    """
    defined = keys_defined()
    own = set(re.findall(r"`\[(L-[a-z0-9]+)\]`", (ROOT / "BIBLIOGRAPHY.md").read_text()))
    for md in TOPICS:
        text = md.read_text()
        sources = text.split("Sources", 1)[1]
        for key in re.findall(r"\[([A-Za-z0-9][A-Za-z0-9\-]*)\](?!\()", sources):
            if key.startswith("L-"):
                assert key in own, f"{md.name}: {key} not in the own-computation table"
            else:
                assert key in defined, f"{md.name}: {key} not defined in BIBLIOGRAPHY.md"


def test_every_topic_has_its_sections():
    """!
    @brief Every topic has a picture, the related topics, the sources and the closing line on what was read.
    @return None.
    """
    for md in TOPICS:
        text = md.read_text()
        assert "![" in text, f"{md.name}: no picture"
        for needle in SECTIONS:
            assert needle in text, f"{md.name}: lacks {needle}"


def test_planned_topics_say_so():
    """!
    @brief The topics of planned work carry the status line.
    @return None.
    """
    for md in TOPICS:
        if md.name.endswith("-planned.md"):
            assert "Status: planned" in md.read_text() or "Status: partly" in md.read_text(), md.name
