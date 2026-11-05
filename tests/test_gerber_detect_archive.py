#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_gerber_detect_archive.py
@brief Tests of the layer-function detector (X2 attributes, Excellon headers, KiCad, Altium/Protel and EAGLE file names) and of the safe ZIP reader of pcbthermal.gerber.
@details The detector table includes the pitfall of an earlier rule: `B_Paste` and `B_Mask` are bottom side. The archive tests build ZIP files in memory: a zip-slip name, an absolute
         name, a declared size above the limit, a zip bomb by compression ratio, too many members, a file that is not a ZIP, and detection that reads only the headers.
"""

import io
import zipfile

import pytest

from pcbthermal import gerber as G
from pcbthermal.gerber import archive

X2_TOP = "%TF.FileFunction,Copper,L1,Top*%\n%FSLAX46Y46*%\n"


@pytest.mark.parametrize("name,expected", [
    # KiCad
    ("board-F_Cu.gbr", ("copper", "top")), ("board-B_Cu.gbr", ("copper", "bottom")), ("board-In1_Cu.gbr", ("copper", "inner")), ("board-In2_Cu.gbr", ("copper", "inner")),
    ("board-F_Paste.gbr", ("paste", "top")), ("board-B_Paste.gbr", ("paste", "bottom")),
    ("board-F_Mask.gbr", ("soldermask", "top")), ("board-B_Mask.gbr", ("soldermask", "bottom")),
    ("board-F_Silkscreen.gbr", ("silkscreen", "top")), ("board-B_Silkscreen.gbr", ("silkscreen", "bottom")),
    ("board-Edge_Cuts.gbr", ("outline", None)), ("board-PTH.drl", ("drill", None)), ("board-NPTH.drl", ("drill", None)),
    # Altium / Protel
    ("PCB1.GTL", ("copper", "top")), ("PCB1.GBL", ("copper", "bottom")), ("PCB1.G1", ("copper", "inner")), ("PCB1.GP2", ("copper", "inner")),
    ("PCB1.GTP", ("paste", "top")), ("PCB1.GBP", ("paste", "bottom")), ("PCB1.GTS", ("soldermask", "top")), ("PCB1.GBS", ("soldermask", "bottom")),
    ("PCB1.GTO", ("silkscreen", "top")), ("PCB1.GBO", ("silkscreen", "bottom")), ("PCB1.GKO", ("outline", None)), ("PCB1.GM1", ("outline", None)), ("PCB1.DRL", ("drill", None)),
    # EAGLE
    ("board.cmp", ("copper", "top")), ("board.sol", ("copper", "bottom")), ("board.stc", ("soldermask", "top")), ("board.sts", ("soldermask", "bottom")),
    ("board.crc", ("paste", "top")), ("board.crs", ("paste", "bottom")), ("board.plc", ("silkscreen", "top")), ("board.pls", ("silkscreen", "bottom")),
    ("board.dim", ("outline", None)), ("board.drd", ("drill", None)),
    # Generic and fabricator names
    ("Gerber_TopLayer.GTL", ("copper", "top")), ("Gerber_BottomLayer.GBL", ("copper", "bottom")), ("project-top.gbr", ("copper", "top")), ("project-bottom.gbr", ("copper", "bottom")),
    ("Gerber_BoardOutlineLayer.GKO", ("outline", None)), ("project_bottom_paste.gbr", ("paste", "bottom")), ("project_top_soldermask.gbr", ("soldermask", "top")),
])
def test_names_without_content(name, expected):
    f = G.detect_function(name)
    assert (f.kind, f.side) == expected and f.source == "name"


def test_bottom_paste_and_mask_are_bottom_side_not_top():
    # The known pitfall: a rule that looked for copper words first filed B_Paste and B_Mask as top
    for n in ("a-B_Paste.gbr", "a-B_Mask.gbr", "b_paste.gbr", "x.GBP", "x.GBS"):
        assert G.detect_function(n).side == "bottom", n
    for n in ("a-F_Paste.gbr", "a-F_Mask.gbr", "f_paste.gbr", "x.GTP", "x.GTS"):
        assert G.detect_function(n).side == "top", n


def test_drill_plating_from_the_name():
    assert G.detect_function("a-PTH.drl").plated is True
    assert G.detect_function("a-NPTH.drl").plated is False
    assert G.detect_function("a.drl").plated is None


def test_inner_layer_ordinals_from_names():
    assert G.detect_function("a-In3_Cu.gbr").index == 3 and G.detect_function("a.G2").index == 2


def test_x2_beats_the_name():
    f = G.detect_function("whatever.txt", X2_TOP)
    assert (f.kind, f.side, f.index, f.source) == ("copper", "top", 1, "x2")
    inner = G.detect_function("a.gbr", "%TF.FileFunction,Copper,L3,Inr*%\n")
    assert (inner.side, inner.index) == ("inner", 3)
    bot = G.detect_function("F_Cu.gbr", "G04 #@! TF.FileFunction,Copper,L4,Bot*\n")           # the attribute in its comment form; the name lies
    assert (bot.side, bot.index) == ("bottom", 4)
    for text, kind, side in (("%TF.FileFunction,Paste,Bot*%", "paste", "bottom"), ("%TF.FileFunction,Soldermask,Top*%", "soldermask", "top"),
                             ("%TF.FileFunction,Legend,Bot*%", "silkscreen", "bottom"), ("%TF.FileFunction,Profile,NP*%", "outline", None),
                             ("%TF.FileFunction,Component,L1,Top*%", "component", "top")):
        f = G.detect_function("x.gbr", text)
        assert (f.kind, f.side) == (kind, side)
    d = G.detect_function("x.gbr", "%TF.FileFunction,NonPlated,1,4,NPTH,Drill*%")
    assert d.kind == "drill" and d.plated is False


def test_excellon_header_decides_the_drill_and_its_plating():
    f = G.detect_function("mystery.txt", "M48\n; #@! TF.FileFunction,NonPlated,1,2,NPTH\nMETRIC\n")
    assert (f.kind, f.plated, f.source) == ("drill", False, "excellon")
    g = G.detect_function("mystery.txt", "; comment\nM48\nMETRIC\n")
    assert g.kind == "drill" and g.source == "excellon" and g.plated is None


def test_unknown_names_stay_unknown_and_paths_are_reduced_to_the_name():
    assert G.detect_function("readme.pdf").kind == "unknown"
    assert G.detect_function("folder\\sub/board-B_Cu.gbr").side == "bottom"


def test_detect_file_reads_only_the_head(tmp_path):
    p = tmp_path / "x.gbr"
    p.write_text(X2_TOP + "X" * 5_000_000)
    assert G.detect_file(p).index == 1


def test_order_copper_layers_top_inner_bottom():
    items = [("b", G.detect_function("a-B_Cu.gbr")), ("i2", G.detect_function("a-In2_Cu.gbr")), ("t", G.detect_function("a-F_Cu.gbr")), ("i1", G.detect_function("a-In1_Cu.gbr"))]
    assert [n for n, _ in G.order_copper_layers(items)] == ["t", "i1", "i2", "b"]


# ---------------------------------------------------------------------------------------------------------------------------------
# Archives
# ---------------------------------------------------------------------------------------------------------------------------------

def make_zip(members):
    """!
    @brief A ZIP file in memory.
    @param members Dict name -> bytes.
    @return bytes The archive.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for n, data in members.items():
            zf.writestr(n, data)
    return buf.getvalue()


def test_archive_lists_members_with_functions_and_skips_junk():
    z = make_zip({"set/board-F_Cu.gbr": X2_TOP + "M02*\n", "set/board-B_Paste.gbr": "%FSLAX46Y46*%\nM02*\n", "set/board-PTH.drl": "M48\nMETRIC\n%\nM30\n",
                  "__MACOSX/set/._board-F_Cu.gbr": "junk", "set/.DS_Store": "junk", "set/readme.txt": "hello"})
    with G.GerberArchive(z) as a:
        assert sorted(a.names()) == ["set/board-B_Paste.gbr", "set/board-F_Cu.gbr", "set/board-PTH.drl", "set/readme.txt"]
        members = {m.name: m for m in a.members()}
        assert members["set/board-F_Cu.gbr"].function.index == 1 and members["set/board-B_Paste.gbr"].function.side == "bottom"
        assert members["set/board-PTH.drl"].function.kind == "drill" and members["set/readme.txt"].function.kind == "unknown"
        assert a.read_text("set/board-F_Cu.gbr").startswith("%TF.FileFunction")
    assert [m.name for m in G.inspect_archive(z)].count("set/board-F_Cu.gbr") == 1


def test_archive_from_a_path(tmp_path):
    p = tmp_path / "a.zip"
    p.write_bytes(make_zip({"x-F_Cu.gbr": X2_TOP}))
    assert G.inspect_archive(str(p))[0].function.kind == "copper"


@pytest.mark.parametrize("name", ["../evil.gbr", "a/../../evil.gbr", "/etc/passwd", "C:/evil.gbr", "a\\..\\evil.gbr", "dir/../x.gbr"])
def test_zip_slip_names_are_refused(name):
    with pytest.raises(G.UnsafeArchiveError, match="unsafe name"):
        G.GerberArchive(make_zip({"ok.gbr": "x", name: "y"}))


def test_not_a_zip_is_refused():
    with pytest.raises(G.UnsafeArchiveError, match="not a valid ZIP"):
        G.GerberArchive(b"this is not a zip file")


def test_declared_size_limit(monkeypatch):
    monkeypatch.setattr(archive, "MAX_UNCOMPRESSED_BYTES", 1000)
    with pytest.raises(G.UnsafeArchiveError, match="uncompressed bytes"):
        G.GerberArchive(make_zip({"a.gbr": "a" * 700 + str(list(range(200))), "b.gbr": "b" * 700 + str(list(range(200)))}))
    monkeypatch.setattr(archive, "MAX_UNCOMPRESSED_BYTES", 2 * 1024 ** 3)
    with pytest.raises(G.UnsafeArchiveError, match="declares"):
        G.GerberArchive(make_zip({"a.gbr": "a" * 700 + str(list(range(200)))}), max_member_bytes=500)
    assert archive.MAX_UNCOMPRESSED_BYTES == 2 * 1024 ** 3                       # the declared limit stated for the import


def test_zip_bomb_by_compression_ratio():
    with pytest.raises(G.UnsafeArchiveError, match="compression ratio"):
        G.GerberArchive(make_zip({"bomb.gbr": b"0" * 20_000_000}))


def test_too_many_members(monkeypatch):
    monkeypatch.setattr(archive, "MAX_MEMBERS", 5)
    with pytest.raises(G.UnsafeArchiveError, match="members"):
        G.GerberArchive(make_zip({f"f{i}.gbr": str(i) for i in range(6)}))


def test_detection_reads_only_the_head_of_a_member():
    # A member of about 3 MB of varied text: members() must not read it whole
    big = X2_TOP + "\n".join(f"X{i}Y{i}D03*" for i in range(250_000))
    z = make_zip({"big-F_Cu.gbr": big})
    with G.GerberArchive(z) as a:
        sizes = []
        real = a._zf.open

        class Spy:
            """!@brief File wrapper that records the bytes asked of read()."""

            def __init__(self, fh):
                """!
                @brief Wrap a file object.
                @param fh Opened member.
                """
                self.fh = fh

            def __enter__(self):
                """!
                @brief Enter the context.
                @return Spy self.
                """
                return self

            def __exit__(self, *e):
                """!
                @brief Leave the context.
                @param e Exception information.
                @return bool False.
                """
                self.fh.close()
                return False

            def read(self, n=-1):
                """!
                @brief Read and record the request.
                @param n Number of bytes.
                @return bytes The data.
                """
                sizes.append(n)
                return self.fh.read(n)

        a._zf.open = lambda info, *args, **kw: Spy(real(info, *args, **kw))
        m = a.members()[0]
    assert m.function.index == 1 and sizes == [archive.HEAD_BYTES]


def test_member_that_holds_more_than_it_declares_is_refused():
    z = make_zip({"a-F_Cu.gbr": "x" * 100 + str(list(range(100)))})
    with G.GerberArchive(z) as a:
        a._infos["a-F_Cu.gbr"].file_size = 10                                    # a header that lies
        with pytest.raises(G.UnsafeArchiveError, match="more or other bytes|more bytes"):
            a.read_text("a-F_Cu.gbr")
