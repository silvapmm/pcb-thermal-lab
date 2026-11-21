#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_user_manual.py
@brief The user manual (docs/USER_MANUAL.md) carries the version of the program, its contents list matches its chapters, every figure exists and is numbered, and its PDF builds.
"""

import importlib.util
import pathlib
import re

import pytest

import pcbthermal
from tools.manual import build_manual_pdf as builder
from tools.manual import callouts

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANUAL = ROOT / "docs" / "USER_MANUAL.md"


def _text():
    return MANUAL.read_text(encoding="utf-8")


def test_manual_stamp_is_the_program_version():
    # Bumped in the release commit, like the CHANGELOG and the README (docs/versions.md A1): the PDF cover reads the same version
    assert builder.manual_stamp(_text()) == pcbthermal.__version__


def test_contents_list_matches_the_chapters():
    text = _text()
    listed = builder.contents_entries(text)
    chapters = [c for c in builder.chapter_titles(text) if re.match(r"^\d+\.\s", c)]
    assert listed, "the Contents section lists no chapter"
    assert listed == chapters, f"Contents {listed} against headings {chapters}"
    assert [int(c.split(".")[0]) for c in chapters] == list(range(1, len(chapters) + 1))


def test_every_figure_exists_and_is_numbered_in_order():
    lines = _text().splitlines()
    numbers = []
    for k, line in enumerate(lines):
        m = re.match(r"^!\[[^\]]*\]\(([^)]+)\)$", line.strip())
        if not m:
            continue
        assert (MANUAL.parent / m.group(1)).is_file(), f"missing picture {m.group(1)}"
        caption = next(x.strip() for x in lines[k + 1:] if x.strip())
        n = re.match(r"^\*Figure (\d+)\. ", caption)
        assert n, f"picture {m.group(1)} has no 'Figure N.' caption"
        numbers.append(int(n.group(1)))
    assert numbers == list(range(1, len(numbers) + 1))
    # Every 'Figure N' quoted in the text names a figure that exists
    quoted = {int(x) for x in re.findall(r"Figure (\d+)", _text())}
    assert quoted <= set(numbers)


def test_every_annotated_picture_has_a_list_with_one_item_per_box():
    # A picture made by tools/manual/callouts.py stores its number of boxes; the numbered list under its caption must have as many items,
    # numbered 1, 2, 3, ... (the picture and the list come from one source, examples/make_manual_callouts.py, and must not drift apart)
    lines = _text().splitlines()
    checked = 0
    for k, line in enumerate(lines):
        m = re.match(r"^!\[[^\]]*\]\((images/[^)]+_callouts\.png)\)$", line.strip())
        if not m:
            continue
        boxes = callouts.count_in_png(str(MANUAL.parent / m.group(1)))
        assert boxes, f"{m.group(1)} carries no box count: draw it with tools/manual/callouts.py"
        j = k + 1
        while j < len(lines) and not lines[j].startswith("*Figure"):       # the caption, then a blank line, then the list
            j += 1
        while j < len(lines) and lines[j].strip():                          # the caption may take several lines
            j += 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        numbers = []
        while j < len(lines) and (re.match(r"^\d+\. ", lines[j]) or lines[j].startswith("   ")):
            n = re.match(r"^(\d+)\. ", lines[j])
            if n:
                numbers.append(int(n.group(1)))
            j += 1
        assert numbers == list(range(1, boxes + 1)), f"{m.group(1)}: {boxes} boxes, list numbered {numbers}"
        checked += 1
    assert checked >= 10                                    # the tour, the tool bar, the Results pages, the settings, the stack-up and the import steps


def test_manual_has_no_personal_path_and_the_readme_links_it():
    text = _text()
    assert not re.search(r"/Users/|/home/|C:\\\\Users", text)
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/USER_MANUAL.md" in readme and builder.RELEASE_ASSET in readme


@pytest.mark.skipif(importlib.util.find_spec("reportlab") is None, reason="reportlab (requirements-docs.txt) is not installed")
def test_pdf_builds_with_the_version_on_the_cover(tmp_path):
    out = tmp_path / "manual.pdf"
    pages = builder.build(MANUAL, out)
    assert pages > 30
    assert out.stat().st_size < 8e6                          # the release asset stays small (decision of the docs/user-manual branch)
    head = out.read_bytes()
    assert f"User manual of PCB Thermal Lab {pcbthermal.__version__}".encode() in head      # the subject of the PDF metadata


def test_pdf_build_refuses_a_stale_stamp(tmp_path):
    stale = tmp_path / "USER_MANUAL.md"
    stale.write_text(_text().replace(f"Program version {pcbthermal.__version__} ", "Program version 0.0.1 ", 1), encoding="utf-8")
    with pytest.raises(SystemExit, match="update the stamp"):
        builder.build(stale, tmp_path / "x.pdf")
