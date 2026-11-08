#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_package_size_preference.py
@brief The machine preference `package.max_mb` (the total size limit of a project package): default, range, the refusal that names the setting, the fixed limits that no
       setting lifts, the Preferences page and a user file.
"""

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from pcbthermal import defaults, package as pkg
from pcbthermal.fileschema import ProjectFormatError
from test_package import _good_members, _raw_zip


def _with_limit(monkeypatch, value):
    """!
    @brief Make the defaults say `package.max_mb = value`.
    @param monkeypatch pytest fixture.
    @param value The value (any type, to try bad ones).
    @return None
    """
    monkeypatch.setattr(defaults, "load", lambda: {"package": {"max_mb": value}})


def _big_members(mb):
    """!
    @brief A valid package's members plus a compressible member of `mb` MB (below the member and ratio limits when the limits are lifted by the caller).
    @param mb Size of the extra member in MB.
    @return dict name -> bytes.
    """
    m = _good_members()
    m["images/pad.bin"] = os.urandom(1024 ** 2) * mb               # random 1 MB repeated: farther apart than the deflate window, so about 1:1 and only the total can refuse
    return m


def test_the_shipped_value_is_512_and_is_in_a_section_of_its_own():
    """!@brief Shipped 512 MB, range 64 to 4096, the default when nothing is set."""
    assert defaults.shipped()["package"]["max_mb"] == 512
    assert (pkg.MIN_TOTAL_MB, pkg.MAX_TOTAL_MB) == (64, 4096)
    assert pkg.max_total_bytes() == 512 * 1024 ** 2


@pytest.mark.parametrize("value,expected", [(64, 64), (4096, 4096), (1000, 1000), (63, 512), (4097, 512), (0, 512), (-5, 512), (float("nan"), 512),
                                            (float("inf"), 512), ("big", 512), (None, 512)])
def test_the_range_is_enforced(monkeypatch, value, expected):
    """!
    @brief A value inside 64 to 4096 is the limit; one outside it, not a number or missing falls back on 512.
    @param monkeypatch pytest fixture.
    @param value The configured value.
    @param expected The limit in MB.
    @return None
    """
    _with_limit(monkeypatch, value)
    assert pkg.max_total_bytes() == expected * 1024 ** 2


def test_a_missing_section_falls_back(monkeypatch):
    """!@brief A defaults dictionary without the section gives 512 MB."""
    monkeypatch.setattr(defaults, "load", lambda: {})
    assert pkg.max_total_bytes() == 512 * 1024 ** 2


def test_a_package_above_the_limit_is_refused_naming_the_setting_and_raising_it_lets_it_read(tmp_path, monkeypatch):
    """!
    @brief 70 MB against a limit of 64 MB: plain message with the setting named; at 128 MB the same file opens.
    @param tmp_path Folder.
    @param monkeypatch pytest fixture.
    @return None
    """
    path = tmp_path / "big.pcbtz"
    _raw_zip(path, _big_members(70))
    _with_limit(monkeypatch, 64)
    with pytest.raises(ProjectFormatError, match=r"above the limit of 64 MB.*Preferences, Project package"):
        pkg.load_any(path)
    _with_limit(monkeypatch, 128)
    project = pkg.load_any(path)
    assert project.problem is not None


def test_the_writer_refuses_a_package_it_would_not_read(tmp_path, monkeypatch):
    """!
    @brief The writer's check uses the same limit: a package built above it is not written.
    @param tmp_path Folder.
    @param monkeypatch pytest fixture.
    @return None
    """
    from pcbthermal.examples import example_board
    from pcbthermal.project import Project
    _with_limit(monkeypatch, 64)
    # A source of 70 MB would be refused at the limit of 64 MB; the writer's own check is _validate on the finished ZIP
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("big.bin", os.urandom(1024 ** 2) * 70)
    with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as zf:
        with pytest.raises(ProjectFormatError, match="above the limit of 64 MB"):
            pkg._validate(zf)
    # and a small project is written and read back
    p = tmp_path / "ok.pcbtz"
    pkg.save_package(p, Project(problem=example_board()))
    assert pkg.load_any(p).problem is not None


def test_the_fixed_limits_hold_whatever_the_setting(tmp_path, monkeypatch):
    """!
    @brief With the limit at its maximum, a zip bomb (ratio above 200), too many members and a member above its fixed size are still refused.
    @param tmp_path Folder.
    @param monkeypatch pytest fixture.
    @return None
    """
    _with_limit(monkeypatch, 4096)
    bomb = _good_members()
    bomb["images/zeros.bin"] = b"\x00" * (3 * 1024 * 1024)
    path = tmp_path / "bomb.pcbtz"
    _raw_zip(path, bomb)
    with pytest.raises(ProjectFormatError, match="compression ratio"):
        pkg.load_any(path)
    many = _good_members()
    many.update({f"extra/{i}.txt": b"x" for i in range(pkg.MAX_MEMBERS + 1)})
    _raw_zip(path, many)
    with pytest.raises(ProjectFormatError, match="members"):
        pkg.load_any(path)
    # The per-member and token caps are constants, not read from the preference
    for name in ("MAX_RATIO", "MAX_PROJECT_RATIO", "MAX_MEMBERS", "MAX_PROJECT_TOKENS", "MAX_PROJECT_BYTES", "MAX_OTHER_BYTES", "MAX_OVERALL_RATIO"):
        assert isinstance(getattr(pkg, name), (int, float))
    assert pkg.MAX_RATIO == 200.0 and pkg.MAX_MEMBERS == 5000 and pkg.MAX_PROJECT_TOKENS == 8_000_000
    # Overall ratio: more than 64 MB of zeros-like data in one package compressing above 20 times as a whole
    members = _good_members()
    for i in range(3):
        members[f"images/z{i}.bin"] = b"\x00" * (40 * 1024 * 1024 // 1)
    _raw_zip(path, members)
    with pytest.raises(ProjectFormatError, match="compression ratio|expands"):
        pkg.load_any(path)


def test_a_user_file_with_the_key_is_read(tmp_path, monkeypatch):
    """!
    @brief A user_defaults.json holding only package.max_mb is the limit in force (the shipped file supplies the rest).
    @param tmp_path Folder.
    @param monkeypatch pytest fixture.
    @return None
    """
    monkeypatch.setenv("PCBTHERMAL_CONFIG", str(tmp_path))
    (tmp_path / "user_defaults.json").write_text(json.dumps({"package": {"max_mb": 100}}))
    assert pkg.max_total_bytes() == 100 * 1024 ** 2


def test_the_preferences_page_has_the_field_the_tooltip_and_the_note(qtbot, tmp_path, monkeypatch):
    """!
    @brief The Project package page has the field (64 to 4096, 512), a tooltip like the Gerber one, a memory note only above 512 MB, and a saved value is the limit.
    @param qtbot pytest-qt fixture.
    @param tmp_path Folder.
    @param monkeypatch pytest fixture.
    @return None
    """
    monkeypatch.setenv("PCBTHERMAL_CONFIG", str(tmp_path / "cfg"))
    from pcbthermal.gui.preferences import PreferencesDialog
    d = PreferencesDialog()
    qtbot.addWidget(d)
    assert "Project package" in [d.sections.item(i).text() for i in range(d.sections.count())]
    w = d.widgets[("package", "max_mb")]
    assert (w.minimum(), w.maximum(), w.value()) == (64, 4096, 512)
    tip = w.toolTip()
    assert "MB" in tip and "held in memory" in tip and "not saved in project files" in tip and "64 to 4096" in tip
    assert d.package_note.isHidden()
    w.setValue(1024)
    assert not d.package_note.isHidden() and "held in memory" in d.package_note.text()
    w.setValue(512)
    assert d.package_note.isHidden()
    w.setValue(256)
    d.save()
    assert pkg.max_total_bytes() == 256 * 1024 ** 2
