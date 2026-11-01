#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_gerber_tolerances.py
@brief Tests of the general reader tolerances (G93X0Y0, M71/M72 with a zero suffix, a stray % before M48, hyphenated macro names), of the layer-function detector fixes
       (masks and assembly drawings are not copper, numbered copper over the set, a Gerber head is never a drill file, names give low confidence), of the editable file-size
       limit and of the convention reported for the parts matched by TO.C.
@details Synthetic files only, with anonymised names. The optional run on the research samples is switched on by the environment variable `PCBT_GERBER_SAMPLES` (a folder of
         third-party sets, never in the repository) and skipped when it is absent.
"""

import io
import os
import random
import zipfile
from pathlib import Path

import pytest

from pcbthermal import defaults
from pcbthermal import gerber as G
from pcbthermal.gerber import limits, parts as P

HEAD = "M48\nMETRIC,TZ\nT1C0.8\n%\nT1\nX1.0Y2.0\nX3.0Y4.0\nM30\n"


def holes(text):
    """!
    @brief The (x, y) positions of the holes of a drill text.
    @param text Drill file content.
    @return list of (x, y) tuples in mm.
    """
    return [(round(h.x, 6), round(h.y, 6)) for h in G.read_drill(text, "t.drl").holes]


# ---------------------------------------------------------------------------------------------------------------------------- Excellon tolerances
def test_g93_with_zero_offset_is_accepted_and_any_other_offset_is_refused():
    """!@brief G93X0Y0 (Xpedition NC drill) is the identity; another offset, or a bare G93, is refused with the message of the origin shift."""
    text = "M48\nMETRIC,TZ\nT1C0.8\n%\nG93X0Y0\nT1\nX1.0Y2.0\nM30\n"
    assert holes(text) == [(1.0, 2.0)]
    assert holes(text.replace("G93X0Y0", "G93X0.0Y-0")) == [(1.0, 2.0)]
    for bad in ("G93X1000Y0", "G93X0Y5", "G93", "G93X0Y0Z3"):
        with pytest.raises(G.UnsupportedFeatureError, match="G93"):
            G.read_drill(text.replace("G93X0Y0", bad), "t.drl")


def test_m71_and_m72_with_a_zero_suffix():
    """!@brief M71,TZ and M72,LZ give the unit and the zeros as METRIC,TZ does; the bare codes still work."""
    assert holes("M48\nM71\nT1C0.8\n%\nT1\nX1.0Y2.0\nM30\n") == [(1.0, 2.0)]
    assert holes("M48\nM72,LZ\nT1C0.03\n%\nT1\nX1.0Y2.0\nM30\n") == [(25.4, 50.8)]
    # As METRIC,TZ: TZ keeps the trailing zeros (leading omitted), so "X1" of a 3.3 file is 0.001; LZ keeps the leading ones (trailing omitted), so "X1" is padded to 1.000 x 100
    assert holes("M48\nM71,TZ\nT1C0.8\n%\nT1\nX1Y2\nM30\n") == [(0.001, 0.002)]
    assert holes("M48\nM71,LZ\nT1C0.8\n%\nT1\nX1Y2\nM30\n") == [(100.0, 200.0)]


def test_a_stray_percent_line_before_m48_is_skipped_by_the_detector_and_the_reader():
    """!@brief PADS and Fritzing write a lone % before M48: the file is still a drill file and its holes are read."""
    text = "%\nM48\nMETRIC,TZ\nT1C0.8\n%\nT1\nX1.0Y2.0\nM30\n"
    assert G.detect_function("board.xyz", text).kind == "drill"
    assert G.detect_function("board.xyz", text.replace("\n", "\r\n")).kind == "drill"
    assert G.detect_function("board.xyz", "; comment\n%\nM48\nMETRIC\n").source == "excellon"
    assert holes(text) == [(1.0, 2.0)]
    assert holes("%\nM48\nINCH\nT1C0.03\n%\nT1\nX1.0Y1.0\nM30\n") == [(25.4, 25.4)]


def test_a_drill_file_without_a_header_is_refused_with_a_clear_message():
    """!@brief An Allegro drill file without M48 and without a unit is refused naming the cause (the tool sizes are in comments)."""
    with pytest.raises(G.UnsupportedFeatureError, match="M48"):
        G.read_drill("T1\nX100Y200\n", "alg.drl")


# ---------------------------------------------------------------------------------------------------------------------------- Gerber tolerances
def macro_file(am_name, ad_name):
    """!
    @brief A tiny Gerber file with one aperture macro and one flash.
    @param am_name Name in the AM statement.
    @param ad_name Name in the AD statement.
    @return str File content.
    """
    return f"%FSLAX24Y24*%\n%MOMM*%\n%AM{am_name}*\n1,1,1.0,0,0*%\n%ADD10{ad_name}*%\n%LPD*%\nD10*\nX10000Y10000D03*\nM02*\n"


def test_hyphenated_and_dotted_macro_names_are_accepted_with_a_warning_when_they_match():
    """!@brief Upverter names macros "Rect-W1" or "a.b": accepted with a warning when AM and AD agree exactly; a conformant name warns nothing; a mismatch is refused as before."""
    for name in ("Rect-W1", "my.macro", "R-1.5"):
        lay = G.parse_layer(macro_file(name, name), "t.gbr")
        assert len(lay.flashes()) == 1 and any("non-conformant" in w and name in w for w in lay.warnings)
    assert G.parse_layer(macro_file("Disc", "Disc"), "t.gbr").warnings == []
    with pytest.raises(G.UnsupportedFeatureError, match="non-standard"):
        G.parse_layer(macro_file("Rect-W1", "Rect-W2"), "t.gbr")


def test_image_mirror_is_still_refused_with_its_message():
    """!@brief %MIA1B0*% (mirrored assembly films) changes the geometry: refused naming the command."""
    with pytest.raises(G.UnsupportedFeatureError, match="MIA1B0"):
        G.parse_layer("%FSLAX24Y24*%\n%MOMM*%\n%MIA1B0*%\n%ADD10C,0.5*%\nD10*\nX10000Y10000D03*\nM02*\n", "mirror.gbr")


# ---------------------------------------------------------------------------------------------------------------------------- the detector
@pytest.mark.parametrize("name,kind", [
    ("Top Solder.gbr", "soldermask"), ("Bottom_SM.gbr", "soldermask"), ("board_top_asb.gbr", "other"), ("board_bottom_ast.gbr", "other"), ("Assembly_Top.art", "other"),
    ("board-fab-top.gbr", "other"), ("top.gbr", "copper"),
])
def test_masks_and_assembly_drawings_with_a_side_word_are_not_copper(name, kind):
    """!
    @brief A side word without a copper word used to make any file copper.
    @param name Anonymised file name.
    @param kind Expected kind.
    @return None.
    """
    assert G.detect_function(name).kind == kind


def test_numbered_copper_names_are_ordered_over_the_set():
    """!@brief Layer1..Layer4 are not all inner layers: the lowest is the top, the highest the bottom, the others inner in order; a known top or bottom leaves them inner."""
    names = [f"Layer{i}.gdo" for i in (3, 1, 4, 2)]
    assert all(G.detect_function(n).side == "inner" for n in names)           # one file alone cannot tell
    out = G.detect_set([(n, "") for n in names])
    assert [(n, out[n].side, out[n].index) for n in sorted(out)] == [("Layer1.gdo", "top", None), ("Layer2.gdo", "inner", 1), ("Layer3.gdo", "inner", 2), ("Layer4.gdo", "bottom", None)]
    assert all(f.confidence == "low" for f in out.values())
    mixed = G.detect_set([("a-F_Cu.gbr", ""), ("Layer2.gdo", ""), ("Layer3.gdo", "")])
    assert mixed["Layer2.gdo"].side == "inner" and mixed["Layer3.gdo"].side == "inner"
    assert G.detect_set([("Layer2.gdo", "")])["Layer2.gdo"].side == "inner"


def test_a_gerber_head_is_never_a_drill_file():
    """!@brief DRILL.gdo of Xpedition is a Gerber drawing of the holes: "other", not a drill file; an Excellon head or an X2 drill function is unchanged."""
    gerber_head = "%FSLAX24Y24*%\n%MOIN*%\n%ADD10C,0.02*%\nD10*\nX1Y1D03*\nM02*\n"
    assert G.detect_function("DRILL.gdo", gerber_head).kind == "other"
    assert G.detect_function("DRILL.gdo", "").kind == "drill"                    # the name alone still says drill (low confidence)
    assert G.detect_function("board.drl", "M48\nMETRIC\n").kind == "drill"
    f = G.detect_function("DRILL.gdo", "%TF.FileFunction,Plated,1,4,PTH*%\n" + gerber_head)
    assert f.kind == "drill" and f.plated is True and f.source == "x2"


def test_names_alone_give_low_confidence_and_the_file_statements_high():
    """!@brief The confidence follows the source: X2 and the Excellon header are high, any name rule is low; the X2 result is the same tuple as before."""
    assert G.detect_function("a-F_Cu.gbr").confidence == "low"
    assert G.detect_function("x.gbr", "%TF.FileFunction,Copper,L1,Top*%\n").confidence == "high"
    assert G.detect_function("x.txt", "M48\nMETRIC\n").confidence == "high"
    assert tuple(G.detect_function("x.gbr", "%TF.FileFunction,Copper,L2,Inr*%\n")) == ("copper", "inner", 2, None, "x2")


def zip_of(files):
    """!
    @brief A ZIP file in memory.
    @param files dict name -> text.
    @return bytes.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, text in files.items():
            zf.writestr(name, text)
    return buf.getvalue()


def test_archive_members_resolve_numbered_copper():
    """!@brief inspect_archive applies the set rule, so a ZIP of Layer1..Layer3 does not list three inner layers."""
    data = zip_of({f"Layer{i}.gdo": "%FSLAX24Y24*%\n%MOMM*%\nM02*\n" for i in (1, 2, 3)})
    assert {m.name: m.function.side for m in G.inspect_archive(data)} == {"Layer1.gdo": "top", "Layer2.gdo": "inner", "Layer3.gdo": "bottom"}


# ---------------------------------------------------------------------------------------------------------------------------- the size limit
def sparse(path, size):
    """!
    @brief Create a sparse file of a given size without writing its bytes.
    @param path File path.
    @param size Size in bytes.
    @return Path The path.
    """
    with open(path, "wb") as fh:
        fh.truncate(size)
    return path


def test_the_default_limit_is_256_mb_and_a_file_just_over_it_is_refused_from_its_size(tmp_path):
    """!@brief A sparse file of 256 MB + 1 byte is refused by read_layer and read_drill_file before anything is read; one at the limit passes the size check."""
    assert limits.max_file_bytes() == 256 * limits.MB
    with pytest.raises(G.GerberError, match="above the limit of 256 MB"):
        G.read_layer(sparse(tmp_path / "big.gbr", 256 * limits.MB + 1))
    with pytest.raises(G.GerberError, match="above the limit"):
        G.read_drill_file(sparse(tmp_path / "big.drl", 256 * limits.MB + 1))
    limits.check_path(sparse(tmp_path / "at.gbr", 256 * limits.MB))              # exactly at the limit: not refused by the size check


def test_max_bytes_overrides_the_preference(tmp_path):
    """!@brief The optional argument of the readers overrides the preference (tests and research scripts)."""
    f = tmp_path / "a.gbr"
    f.write_text("%FSLAX24Y24*%\n%MOMM*%\nM02*\n")
    with pytest.raises(G.GerberError, match="above the limit"):
        G.read_layer(f, max_bytes=10)
    assert G.read_layer(f, max_bytes=10_000) is not None
    d = tmp_path / "a.drl"
    d.write_text(HEAD)
    with pytest.raises(G.GerberError, match="above the limit"):
        G.read_drill_file(d, max_bytes=5)
    assert len(G.read_drill_file(d).holes) == 2


def test_changing_the_preference_changes_the_refusal(tmp_path, monkeypatch):
    """!@brief gerber.max_file_mb of the defaults is the limit: 16 MB refuses a 17 MB sparse file, 4096 MB accepts it; a value out of range or not a number falls back on 256."""
    f = sparse(tmp_path / "x.gbr", 17 * limits.MB)
    monkeypatch.setattr(defaults, "load", lambda: {"gerber": {"max_file_mb": 16}})
    assert limits.max_file_bytes() == 16 * limits.MB
    with pytest.raises(G.GerberError, match="above the limit of 16 MB"):
        limits.check_path(f)
    monkeypatch.setattr(defaults, "load", lambda: {"gerber": {"max_file_mb": 4096}})
    limits.check_path(f)
    for bad in (1, 5000, "abc", None):
        monkeypatch.setattr(defaults, "load", lambda bad=bad: {"gerber": {"max_file_mb": bad}})
        assert limits.max_file_bytes() == 256 * limits.MB
    monkeypatch.undo()
    assert defaults.shipped()["gerber"]["max_file_mb"] == 256


def test_a_zip_member_follows_the_limit(monkeypatch):
    """!@brief The member limit of an archive is the preference too; a member that declares more is refused when the archive is opened."""
    data = zip_of({"a.gbr": "%FSLAX24Y24*%\n" + "G04 x*\n" * 100000})
    assert G.inspect_archive(data)
    monkeypatch.setattr(limits, "max_file_bytes", lambda: 1000)
    with pytest.raises(G.UnsafeArchiveError, match="declares"):
        G.inspect_archive(data)


def test_the_preferences_dialog_edits_the_limit(qtbot, tmp_path, monkeypatch):
    """!@brief The Preferences window has the field in the Gerber import box with a tooltip, its range is 16 to 4096 and a saved value is the limit in force."""
    monkeypatch.setenv("PCBTHERMAL_CONFIG", str(tmp_path / "cfg"))
    from pcbthermal.gui.preferences import PreferencesDialog
    d = PreferencesDialog()
    qtbot.addWidget(d)
    w = d.widgets[("gerber", "max_file_mb")]
    assert (w.minimum(), w.maximum(), w.value()) == (16, 4096, 256)
    tip = w.toolTip()
    assert "MB" in tip and "0.01 to 2 MB" in tip and "twice" in tip and "not saved in project files" in tip
    w.setValue(64)
    d.save()
    assert limits.max_file_bytes() == 64 * limits.MB


# ---------------------------------------------------------------------------------------------------------------------------- parts: convention
def paste_with_refs(side, refs_xy):
    """!
    @brief A paste layer with one rectangular opening per (reference, x, y).
    @param side "Top" or "Bot".
    @param refs_xy List of (reference, x, y) in mm.
    @return Layer.
    """
    t = f"%TF.FileFunction,Paste,{side}*%\n%FSLAX46Y46*%\n%MOMM*%\n%LPD*%\n"
    for ref, x, y in refs_xy:
        pts = [(x - 0.4, y - 0.3), (x + 0.4, y - 0.3), (x + 0.4, y + 0.3), (x - 0.4, y + 0.3)]
        t += f"%TO.C,{ref}*%\nG36*\nX{round(pts[0][0] * 1e6)}Y{round(pts[0][1] * 1e6)}D02*\n"
        t += "".join(f"X{round(a * 1e6)}Y{round(b * 1e6)}D01*\n" for a, b in pts[1:] + pts[:1]) + "G37*\n%TD*%\n"
    return G.parse_layer(t + "M02*\n", "paste.gbr")


def test_the_convention_of_parts_matched_by_to_c_is_checked_from_the_openings():
    """!@brief With TO.C the positions come from the openings, but info["convention"] is no longer "as is" by default: it is detected from the openings, forced, or "not checked"."""
    xy = [(f"B{i}", 10.0 + 4 * i, 5.0) for i in range(4)]
    lay = paste_with_refs("Bot", xy)
    plc = [dict(ref=r, package="R_0603_1608Metric", x=x, y=y, rot=0, side="bottom", value="1k") for r, x, y in xy]
    assert P.build_parts({"bottom": lay}, plc).info["convention"] == "as is"
    negated = [dict(p, x=-p["x"]) for p in plc]
    assert P.build_parts({"bottom": lay}, negated).info["convention"] == "negated X"
    assert P.build_parts({"bottom": lay}, negated, bottom="as is").info["convention"] == "as is"
    assert P.build_parts({"bottom": lay}, None).info["convention"] == "not checked"
    top = paste_with_refs("Top", [("T1", 1.0, 1.0)])
    one = [dict(ref="T1", package="R_0603_1608Metric", x=1.0, y=1.0, rot=0, side="top", value="")]
    assert P.build_parts({"top": top}, one).info["convention"] == "not checked"      # no bottom part: nothing to check it with


# ---------------------------------------------------------------------------------------------------------------------------- hostile input
def test_mutated_files_end_in_a_reader_error_only():
    """!@brief 200 random mutations of Excellon and Gerber files that use the new tolerances raise only GerberError (or read)."""
    rng = random.Random(20261101)
    seeds = ["%\nM48\nM71,TZ\nT1C0.8\n%\nG93X0Y0\nT1\nX1.0Y2.0\nM30\n", macro_file("Rect-W1", "Rect-W1"), HEAD]
    alphabet = list("%MG*,.-TZLXY0123456789\n;DC ")
    for _ in range(200):
        s = list(rng.choice(seeds))
        for _ in range(rng.randint(1, 6)):
            i = rng.randrange(len(s))
            op = rng.random()
            if op < 0.4:
                s[i] = rng.choice(alphabet)
            elif op < 0.7:
                del s[i]
            else:
                s.insert(i, rng.choice(alphabet))
        text = "".join(s)
        for fn in (lambda t: G.read_drill(t, "m.drl"), lambda t: G.parse_layer(t, "m.gbr"), lambda t: G.detect_function("m.xyz", t)):
            try:
                fn(text)
            except G.GerberError:
                pass


# ---------------------------------------------------------------------------------------------------------------------------- optional: the research samples
SAMPLES = os.environ.get("PCBT_GERBER_SAMPLES")


@pytest.mark.skipif(not SAMPLES or not Path(SAMPLES).is_dir(), reason="PCBT_GERBER_SAMPLES is not set to a folder of sample sets")
def test_research_samples_read_without_a_raw_error():
    """!@brief Every drill-looking file of the samples either reads or ends in a GerberError; nothing else escapes."""
    for p in sorted(Path(SAMPLES).rglob("*")):
        if not p.is_file() or p.stat().st_size > 20 * limits.MB:
            continue
        if G.detect_file(p).kind != "drill":
            continue
        try:
            G.read_drill_file(p)
        except G.GerberError:
            pass
