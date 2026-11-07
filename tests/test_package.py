#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_package.py
@brief The project package `.pcbtz`: round trip of every member kind, unknown members, hostile ZIPs, atomic save, detection by content, the command line and the window actions.
"""

import hashlib
import json
import os
import stat
import struct
import time
import warnings
import zlib
import zipfile

import pytest

from pcbthermal import package as pkg
from pcbthermal.examples import example_board
from pcbthermal.model import ImportFile, ImportRecord
from pcbthermal.project import FORMAT_1, FORMAT_2, Project, ProjectFormatError, load_project, project_to_dict, save_project



def _png():
    """!
    @brief A valid 1 x 1 PNG made with the standard library.
    @return bytes.
    """
    def chunk(kind, data):
        """!@brief One PNG chunk with its CRC."""
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00"))
            + chunk(b"IEND", b""))


PNG = _png()
GBR = b"%FSLAX46Y46*%\n%MOMM*%\nD10*\nM02*\n"


def _record():
    """!
    @brief A small import record.
    @return ImportRecord.
    """
    return ImportRecord(name="my board", files=[ImportFile("top.gtl", len(GBR), hashlib.sha256(GBR).hexdigest(), "copper")], box_mm=[0, 0, 100, 80])


def _project(tmp_path, image=True, imports=False, sources=False):
    """!
    @brief A project with a background image on disk, optional imports and optional source files.
    @param tmp_path Folder for the image.
    @param image True to give the project a background image.
    @param imports True to attach an import record (format 2).
    @param sources True to attach source files (a Gerber, a drill, a placement file and a BOM).
    @return Project.
    """
    prj = Project(problem=example_board(), imports=[_record()] if imports else [])
    if image:
        img = tmp_path / "bg.png"
        img.write_bytes(PNG)
        prj.view["background"] = {"path": str(img), "w_mm": 50.0, "h_mm": 40.0}
    if sources:
        pkg.attach_sources(prj, [("top.gtl", GBR, "gerber", "Top copper"), ("board.drl", b"M48\nM30\n", "drill", "Plated drill"), ("pos.csv", b"Ref,X,Y\nU1,1,2\n", "placement", "Placement"),
                                 ("my_bom.csv", b"Ref,Value\nU1,10k\n", "bom", "Ignore")])
    return prj


def _raw_zip(path, members, manifest=True, infos=None, listed=None, fmt=1, compress=zipfile.ZIP_DEFLATED, bad_hash=()):
    """!
    @brief Build a ZIP by hand (also hostile ones).
    @param path Output path.
    @param members dict name -> bytes (the names are written as given).
    @param manifest False to leave manifest.json out.
    @param infos dict name -> ZipInfo to use for a member (symbolic links, special names).
    @param listed Names to list in the manifest (None: all members).
    @param fmt package_format of the manifest.
    @param compress Compression method.
    @param bad_hash Names listed with a wrong hash.
    @return None
    """
    entries = [{"name": n, "size": len(b), "sha256": "0" * 64 if n in bad_hash else hashlib.sha256(b).hexdigest()} for n, b in members.items() if listed is None or n in listed]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")                    # a duplicate name is the point of a test
        with zipfile.ZipFile(path, "w", compress) as zf:
            if manifest:
                zf.writestr("manifest.json", json.dumps({"package_format": fmt, "writer": "pcbthermal 9.9.9", "members": entries}))
            for n, b in members.items():
                zf.writestr((infos or {}).get(n, n), b)


def _good_members():
    """!
    @brief The members of a minimal valid package (the example board).
    @return dict name -> bytes.
    """
    return {"project.pcbt.json": json.dumps(project_to_dict(Project(problem=example_board())), indent=2).encode()}


def test_round_trip_every_member_kind(tmp_path):
    """!
    @brief Project, image, source files with kinds and functions, previews and an unknown member survive a save, a load and a second save.
    @param tmp_path Temporary folder.
    @return None
    """
    prj = _project(tmp_path, imports=True, sources=True)
    prj.package.renders["renders/copper.png"] = PNG
    prj.package.unknown["notes/readme.txt"] = b"hello"
    prj.package.manifest_extra["future"] = {"a": 1}
    path = tmp_path / "board.pcbtz"
    pkg.save_package(path, prj, include_sources=True)
    names = zipfile.ZipFile(path).namelist()
    assert names[0] == "manifest.json" and "project.pcbt.json" in names and "images/bg.png" in names and "renders/copper.png" in names and "notes/readme.txt" in names
    assert "sources/my_board/top.gtl" in names and "sources/my_board/my_bom.csv" in names      # original names
    man = json.loads(zipfile.ZipFile(path).read("manifest.json"))
    assert man["package_format"] == 1 and man["writer"].startswith("pcbthermal ") and man["future"] == {"a": 1}
    kinds = {m["name"]: (m.get("kind"), m.get("function")) for m in man["members"]}
    assert kinds["sources/my_board/board.drl"] == ("drill", "Plated drill") and kinds["sources/my_board/pos.csv"] == ("placement", "Placement")
    assert kinds["sources/my_board/my_bom.csv"][0] == "bom"
    back = pkg.load_package(path)
    assert back.package.warnings == [] and back.package.is_package
    assert back.view["background"]["path"] == "images/bg.png"
    assert back.package.images["images/bg.png"] == PNG
    assert back.package.sources["sources/my_board/top.gtl"] == GBR
    assert back.package.unknown["notes/readme.txt"] == b"hello" and back.package.renders["renders/copper.png"] == PNG
    assert back.package.source_meta["sources/my_board/board.drl"] == {"kind": "drill", "function": "Plated drill", "original": "board.drl", "origin": "folder"}
    assert back.imports == prj.imports
    again = tmp_path / "again.pcbtz"
    pkg.save_package(again, back)
    z1, z2 = zipfile.ZipFile(path), zipfile.ZipFile(again)
    for n in z1.namelist():
        if n != "manifest.json":
            assert z1.read(n) == z2.read(n) or n == "project.pcbt.json"
    assert json.loads(z1.read("project.pcbt.json")) == json.loads(z2.read("project.pcbt.json"))
    assert json.loads(z2.read("manifest.json"))["future"] == {"a": 1}


def test_project_member_is_the_plain_json(tmp_path):
    """!
    @brief The project member holds exactly what a `.pcbt.json` would hold (format 1 and format 2), apart from the image path.
    @param tmp_path Temporary folder.
    @return None
    """
    for imports, fmt in ((False, FORMAT_1), (True, FORMAT_2)):
        prj = _project(tmp_path, image=False, imports=imports)
        path = tmp_path / f"p{imports}.pcbtz"
        pkg.save_package(path, prj)
        text = zipfile.ZipFile(path).read("project.pcbt.json").decode()
        assert text == json.dumps(project_to_dict(prj), indent=2)
        assert json.loads(text)["format"] == fmt


def test_gerbers_only_when_asked(tmp_path):
    """!
    @brief The source files go into the package only with include_sources (default off).
    @param tmp_path Temporary folder.
    @return None
    """
    prj = _project(tmp_path, imports=True, sources=True)
    a, b = tmp_path / "a.pcbtz", tmp_path / "b.pcbtz"
    pkg.save_package(a, prj)
    assert not [n for n in zipfile.ZipFile(a).namelist() if n.startswith("sources/")]
    pkg.save_package(b, prj, include_sources=True)
    assert len([n for n in zipfile.ZipFile(b).namelist() if n.startswith("sources/")]) == 4
    # A package that stores them keeps them on the next plain save
    c = tmp_path / "c.pcbtz"
    pkg.save_package(c, pkg.load_package(b))
    assert len([n for n in zipfile.ZipFile(c).namelist() if n.startswith("sources/")]) == 4


def test_extract_sources_private_folder(tmp_path):
    """!
    @brief The stored files are extracted to a private folder under their original names, hash checked.
    @param tmp_path Temporary folder.
    @return None
    """
    prj = _project(tmp_path, imports=True, sources=True)
    path = tmp_path / "s.pcbtz"
    pkg.save_package(path, prj, include_sources=True)
    back = pkg.load_package(path)
    folder = back.package.extract_sources()
    try:
        assert os.path.basename(folder) == "my_board"                 # the session names the board after the folder: the set name, not the temporary name
        assert sorted(os.listdir(folder)) == ["board.drl", "my_bom.csv", "pos.csv", "top.gtl"]
        assert open(os.path.join(folder, "top.gtl"), "rb").read() == GBR
        assert stat.S_IMODE(os.stat(folder).st_mode) == 0o700
        back.package.sources["sources/my_board/top.gtl"] = b"changed"
        with pytest.raises(ProjectFormatError):
            back.package.extract_sources()
    finally:
        pkg.remove_extracted(folder)
    assert not os.path.exists(os.path.dirname(folder))


def test_moving_the_package_keeps_image_and_files(tmp_path):
    """!
    @brief After the package is copied elsewhere and the original image deleted, the image and the files are still there.
    @param tmp_path Temporary folder.
    @return None
    """
    prj = _project(tmp_path, imports=True, sources=True)
    path = tmp_path / "board.pcbtz"
    pkg.save_package(path, prj, include_sources=True)
    (tmp_path / "bg.png").unlink()
    moved = tmp_path / "elsewhere"
    moved.mkdir()
    os.replace(path, moved / "moved.pcbtz")
    back = pkg.load_package(moved / "moved.pcbtz")
    assert back.package.images["images/bg.png"] == PNG and back.package.sources["sources/my_board/top.gtl"] == GBR
    assert pkg.background_bytes(back, "images/bg.png") == PNG


def test_unknown_members_preserved(tmp_path):
    """!
    @brief A member this version does not know (even in a new folder) is read, kept and written back.
    @param tmp_path Temporary folder.
    @return None
    """
    members = _good_members()
    members["extra/thing.bin"] = b"\x00\x01"
    members["sources/odbpp/job.tgz"] = b"x"
    _raw_zip(tmp_path / "u.pcbtz", members)
    prj = pkg.load_package(tmp_path / "u.pcbtz")
    assert prj.package.unknown == {"extra/thing.bin": b"\x00\x01"} and "sources/odbpp/job.tgz" in prj.package.sources
    pkg.save_package(tmp_path / "u2.pcbtz", prj, include_sources=True)
    assert zipfile.ZipFile(tmp_path / "u2.pcbtz").read("extra/thing.bin") == b"\x00\x01"
    assert zipfile.ZipFile(tmp_path / "u2.pcbtz").read("sources/odbpp/job.tgz") == b"x"


def test_old_json_unchanged(tmp_path):
    """!
    @brief A `.pcbt.json` opens and saves exactly as before (same bytes), and loading it by content-detection does not make a package.
    @param tmp_path Temporary folder.
    @return None
    """
    prj = Project(problem=example_board())
    path = tmp_path / "a.pcbt.json"
    save_project(path, prj)
    raw = path.read_bytes()
    assert raw.decode() == json.dumps(project_to_dict(prj), indent=2)
    back = pkg.load_any(path)
    assert back.package is None
    pkg.save_any(path, back)
    assert path.read_bytes() == raw


def test_detection_by_content_not_extension(tmp_path):
    """!
    @brief A package named .json opens, a JSON file named .pcbtz opens, and a ZIP without manifest.json is refused with the import hint.
    @param tmp_path Temporary folder.
    @return None
    """
    pkg.save_package(tmp_path / "x.json", Project(problem=example_board()))
    assert pkg.is_package(tmp_path / "x.json") and pkg.load_any(tmp_path / "x.json").package is not None
    save_project(tmp_path / "y.pcbtz", Project(problem=example_board()))
    assert not pkg.is_package(tmp_path / "y.pcbtz") and pkg.load_any(tmp_path / "y.pcbtz").package is None
    _raw_zip(tmp_path / "g.zip", {"top.gtl": GBR}, manifest=False)
    with pytest.raises(ProjectFormatError, match="not a project package.*no manifest.json.*Import Gerber board"):
        pkg.load_any(tmp_path / "g.zip")


def _refused(tmp_path, members=None, match="", **kw):
    """!
    @brief Assert that a hand-made ZIP is refused.
    @param tmp_path Folder.
    @param members Members (default: a good project).
    @param match Regular expression the message must match.
    @param kw Arguments of _raw_zip.
    @return None
    """
    path = tmp_path / "bad.pcbtz"
    _raw_zip(path, members if members is not None else _good_members(), **kw)
    with pytest.raises(ProjectFormatError, match=match):
        pkg.load_any(path)


@pytest.mark.parametrize("name", ["../evil.txt", "a/../../evil.txt", "/etc/passwd", "a\\b.txt", "C:evil.txt", "a//b.txt"])
def test_unsafe_names_refused(tmp_path, name):
    """!
    @brief Zip-slip, absolute, backslash, drive-letter, empty-component and NUL names refuse the package.
    @param tmp_path Temporary folder.
    @param name The member name.
    @return None
    """
    members = _good_members()
    members[name] = b"x"
    _refused(tmp_path, members, "unsafe member name")


def test_symlink_member_refused(tmp_path):
    """!
    @brief A member that is a symbolic link refuses the package.
    @param tmp_path Temporary folder.
    @return None
    """
    members = _good_members()
    members["images/link"] = b"/etc/passwd"
    info = zipfile.ZipInfo("images/link")
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    _refused(tmp_path, members, "symbolic link", infos={"images/link": info})


def test_bomb_ratio_and_member_limits(tmp_path, monkeypatch):
    """!
    @brief A member of a huge compression ratio, too many members and a declared total above the limit are refused.
    @param tmp_path Temporary folder.
    @param monkeypatch pytest fixture (the limits are lowered so that the test is small).
    @return None
    """
    members = _good_members()
    members["images/zeros.bin"] = b"\x00" * (3 * 1024 * 1024)
    monkeypatch.setattr(pkg, "MAX_RATIO", 100.0)
    _refused(tmp_path, members, "compression ratio")
    monkeypatch.setattr(pkg, "MAX_RATIO", 1e9)
    monkeypatch.setattr(pkg, "MAX_TOTAL_BYTES", 1024 * 1024)
    _refused(tmp_path, members, "uncompressed bytes")
    monkeypatch.setattr(pkg, "MAX_TOTAL_BYTES", 2 * 1024 ** 3)
    many = _good_members()
    many.update({f"extra/{i}.txt": b"x" for i in range(10)})
    monkeypatch.setattr(pkg, "MAX_MEMBERS", 5)
    _refused(tmp_path, many, "members \\(limit 5\\)")


def test_duplicate_and_case_colliding_names_refused(tmp_path):
    """!
    @brief Two members of one name, or of names that differ only in case, refuse the package.
    @param tmp_path Temporary folder.
    @return None
    """
    path = tmp_path / "dup.pcbtz"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("manifest.json", json.dumps({"package_format": 1, "members": []}))
            zf.writestr("project.pcbt.json", b"{}")
            zf.writestr("images/a.png", b"1")
            zf.writestr("images/a.png", b"2")
    with pytest.raises(ProjectFormatError, match="two members named"):
        pkg.load_any(path)
    members = _good_members()
    members["images/A.png"], members["images/a.png"] = b"1", b"2"
    _refused(tmp_path, members, "differ only in case")


def test_truncated_and_corrupt(tmp_path):
    """!
    @brief A truncated ZIP and a member with a damaged CRC become a clean ProjectFormatError.
    @param tmp_path Temporary folder.
    @return None
    """
    good = tmp_path / "g.pcbtz"
    pkg.save_package(good, Project(problem=example_board()))
    raw = good.read_bytes()
    cut = tmp_path / "cut.pcbtz"
    cut.write_bytes(raw[: len(raw) // 2])
    assert pkg.is_package(cut)
    with pytest.raises(ProjectFormatError):
        pkg.load_any(cut)
    stored = tmp_path / "stored.pcbtz"
    _raw_zip(stored, _good_members(), compress=zipfile.ZIP_STORED)
    data = bytearray(stored.read_bytes())
    at = data.index(b'"format"') + 3                       # inside the stored project member: the stored bytes change, the CRC does not
    data[at] ^= 0x20
    stored.write_bytes(bytes(data))
    with pytest.raises(ProjectFormatError, match="cannot be read|does not match"):
        pkg.load_any(stored)


def test_manifest_checks(tmp_path):
    """!
    @brief Project hash mismatch refuses; an image mismatch drops the image with a warning; a listed member that is missing warns; a newer package format names its writer.
    @param tmp_path Temporary folder.
    @return None
    """
    _refused(tmp_path, match="does not match the manifest", bad_hash=("project.pcbt.json",))
    members = _good_members()
    members["images/bg.png"] = PNG
    _raw_zip(tmp_path / "m.pcbtz", members, bad_hash=("images/bg.png",))
    prj = pkg.load_any(tmp_path / "m.pcbtz")
    assert "images/bg.png" not in prj.package.images and any("images/bg.png" in w and "does not match" in w for w in prj.package.warnings)
    path = tmp_path / "miss.pcbtz"
    with zipfile.ZipFile(path, "w") as zf:
        m = _good_members()["project.pcbt.json"]
        zf.writestr("manifest.json", json.dumps({"package_format": 1, "members": [{"name": "project.pcbt.json", "size": len(m), "sha256": hashlib.sha256(m).hexdigest()},
                                                                                {"name": "images/gone.png", "size": 1, "sha256": "0" * 64}]}))
        zf.writestr("project.pcbt.json", m)
    prj = pkg.load_any(path)
    assert any("images/gone.png" in w and "missing" in w for w in prj.package.warnings)
    _refused(tmp_path, match="format 7.*newer.*pcbthermal 9.9.9", fmt=7)


def test_nested_zip_is_unknown_never_opened(tmp_path):
    """!
    @brief A ZIP inside the package is kept as bytes and never opened.
    @param tmp_path Temporary folder.
    @return None
    """
    inner = tmp_path / "inner.zip"
    with zipfile.ZipFile(inner, "w") as zf:
        zf.writestr("../../evil", b"x")
    members = _good_members()
    members["extra/inner.zip"] = inner.read_bytes()
    _raw_zip(tmp_path / "n.pcbtz", members)
    prj = pkg.load_any(tmp_path / "n.pcbtz")
    assert prj.package.unknown["extra/inner.zip"] == inner.read_bytes()


def test_member_lying_about_its_size(tmp_path):
    """!
    @brief A member with more bytes than its header declares is refused (the reader never takes more than the declared size).
    @param tmp_path Temporary folder.
    @return None
    """
    path = tmp_path / "lie.pcbtz"
    _raw_zip(path, _good_members(), compress=zipfile.ZIP_STORED)
    data = bytearray(path.read_bytes())
    # Shrink the declared sizes of the project member in its local and central headers: the CRC and the data then disagree with the header
    size = len(_good_members()["project.pcbt.json"])
    pat = size.to_bytes(4, "little")
    for i in range(len(data) - 4):
        if data[i:i + 4] == pat:
            data[i:i + 4] = (size - 10).to_bytes(4, "little")
    path.write_bytes(bytes(data))
    with pytest.raises(ProjectFormatError):
        pkg.load_any(path)


def test_failed_replace_keeps_old_file(tmp_path, monkeypatch):
    """!
    @brief A save interrupted before the rename leaves the old package whole and no temporary file.
    @param tmp_path Temporary folder.
    @param monkeypatch pytest fixture.
    @return None
    """
    path = tmp_path / "keep.pcbtz"
    pkg.save_package(path, Project(problem=example_board()))
    before = path.read_bytes()

    def boom(*a, **k):
        """!@brief Simulated crash at the rename."""
        raise OSError("simulated kill")
    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        pkg.save_package(path, _project(tmp_path))
    assert path.read_bytes() == before and os.listdir(tmp_path).count("keep.pcbtz") == 1
    assert not [n for n in os.listdir(tmp_path) if n.endswith(".tmp")]


def test_read_only_target_refused_and_bak(tmp_path):
    """!
    @brief A read-only package is not replaced; a JSON file replaced by a package (or the reverse) is kept as `.bak`.
    @param tmp_path Temporary folder.
    @return None
    """
    path = tmp_path / "ro.pcbtz"
    pkg.save_package(path, Project(problem=example_board()))
    os.chmod(path, 0o444)
    try:
        if os.access(path, os.W_OK):
            pytest.skip("running as a user that can write read-only files")
        with pytest.raises(PermissionError):
            pkg.save_package(path, Project(problem=example_board()))
    finally:
        os.chmod(path, 0o644)
    js = tmp_path / "was.json"
    save_project(js, Project(problem=example_board()))
    old = js.read_bytes()
    backup, _ = pkg.save_package(js, Project(problem=example_board()))
    assert backup and open(backup, "rb").read() == old
    backup2 = save_project(js, Project(problem=example_board()))             # package replaced by JSON
    assert backup2 and pkg.is_package(backup2)


def test_missing_image_noted_on_save(tmp_path):
    """!
    @brief A background image missing on the disk is reported by the save and its path kept.
    @param tmp_path Temporary folder.
    @return None
    """
    prj = Project(problem=example_board())
    prj.view["background"] = {"path": str(tmp_path / "nowhere.png"), "w_mm": 1, "h_mm": 1}
    _, notes = pkg.save_package(tmp_path / "m.pcbtz", prj)
    assert notes and "nowhere.png" in notes[0]


def test_save_any_keeps_format(tmp_path):
    """!
    @brief Save keeps the format of the open file; a package saved as plain JSON reports what is dropped.
    @param tmp_path Temporary folder.
    @return None
    """
    prj = _project(tmp_path, imports=True, sources=True)
    path = tmp_path / "k.pcbtz"
    pkg.save_any(path, prj, include_sources=True)
    back = pkg.load_any(path)
    pkg.save_any(path, back)
    assert pkg.is_package(path)
    _, notes = pkg.save_any(tmp_path / "plain.pcbt.json", back)
    assert any("image" in n for n in notes) and any("Gerber" in n or "source" in n for n in notes)
    assert not pkg.is_package(tmp_path / "plain.pcbt.json") and load_project(tmp_path / "plain.pcbt.json").imports == prj.imports


# ------------------------------------------------------------------------------------------------------------------------------------ command line
def test_cli_convert_both_ways_and_run(tmp_path, capsys):
    """!
    @brief `convert` writes a package from a project and back (saying what is dropped), and `run` reads a package.
    @param tmp_path Temporary folder.
    @param capsys pytest fixture.
    @return None
    """
    from pcbthermal import cli
    prj = _project(tmp_path, imports=True, sources=True)
    pkg.save_package(tmp_path / "in.pcbtz", prj, include_sources=True)
    assert cli.main(["convert", str(tmp_path / "in.pcbtz"), str(tmp_path / "plain.pcbt.json")]) == 0
    out = capsys.readouterr().out
    assert "dropped" in out and "image" in out and "source" in out.lower()
    assert load_project(tmp_path / "plain.pcbt.json").imports == prj.imports
    assert cli.main(["convert", str(tmp_path / "plain.pcbt.json"), str(tmp_path / "out.pcbtz")]) == 0
    assert pkg.is_package(tmp_path / "out.pcbtz") and not pkg.load_package(tmp_path / "out.pcbtz").package.sources
    assert cli.main(["convert", str(tmp_path / "in.pcbtz"), str(tmp_path / "keep.pcbtz"), "--with-gerbers"]) == 0
    assert pkg.load_package(tmp_path / "keep.pcbtz").package.sources
    capsys.readouterr()
    ex = tmp_path / "ex.pcbtz"
    pkg.save_package(ex, Project(problem=example_board()))
    assert cli.main(["run", str(ex), "--model", "analytic", "--out", str(tmp_path / "res"), "--no-plots", "--cell-mm", "2"]) == 0
    assert (tmp_path / "res").exists()


def test_cli_refuses_a_zip_without_manifest(tmp_path, capsys):
    """!
    @brief A plain ZIP given to `run` gives the message that points to the Gerber import, not a traceback.
    @param tmp_path Temporary folder.
    @param capsys pytest fixture.
    @return None
    """
    from pcbthermal import cli
    _raw_zip(tmp_path / "g.zip", {"top.gtl": GBR}, manifest=False)
    assert cli.main(["run", str(tmp_path / "g.zip"), "--out", str(tmp_path / "o")]) != 0
    assert "Import Gerber board" in capsys.readouterr().err


# ------------------------------------------------------------------------------------------------------------------------------------ window
@pytest.fixture
def window(qtbot):
    """!
    @brief A main window with private settings.
    @param qtbot pytest-qt fixture.
    @return MainWindow
    """
    from PySide6.QtCore import QSettings
    from pcbthermal.gui.main_window import MainWindow
    w = MainWindow(settings=QSettings(os.path.join(os.environ["PCBTHERMAL_CONFIG"], "w.ini"), QSettings.IniFormat))
    qtbot.addWidget(w)
    return w


def test_window_open_save_keep_format(window, tmp_path):
    """!
    @brief Open a package (by content), edit, Save keeps it a package with its image and files; the undo keeps the extras; the title and the image come from memory.
    @param window The MainWindow.
    @param tmp_path Temporary folder.
    @return None
    """
    prj = _project(tmp_path, imports=True, sources=True)
    path = tmp_path / "w.pcbtz"
    pkg.save_package(path, prj, include_sources=True)
    (tmp_path / "bg.png").unlink()
    window.open_file(str(path))
    assert window.doc.project.package.has_sources() and window.doc.project.package.is_package
    assert window.canvas.background_problem == "" and window.canvas._background is not None
    window.doc.edit("rename", lambda p: setattr(p.problem, "name", "renamed"))
    window.doc.stack.undo()
    assert window.doc.project.package.has_sources()
    window.save_file()
    assert pkg.is_package(path) and pkg.load_package(path).package.sources
    assert not [n for n in os.listdir(tmp_path) if n.endswith(".tmp")]


def test_window_missing_background_is_said(window, tmp_path):
    """!
    @brief A `.pcbt.json` whose background image is missing shows a message in the status bar instead of skipping it silently.
    @param window The MainWindow.
    @param tmp_path Temporary folder.
    @return None
    """
    prj = Project(problem=example_board())
    prj.view["background"] = {"path": str(tmp_path / "gone.png"), "w_mm": 10, "h_mm": 10}
    path = tmp_path / "m.pcbt.json"
    save_project(path, prj)
    window.open_file(str(path))
    assert "gone.png" in window.canvas.background_problem and "gone.png" in window.statusBar().currentMessage()


def test_window_export_package_does_not_change_the_document(window, tmp_path, monkeypatch):
    """!
    @brief Export package writes a copy (with the source files when the box is ticked, remembered), and the open project keeps its own path and state.
    @param window The MainWindow.
    @param tmp_path Temporary folder.
    @param monkeypatch pytest fixture.
    @return None
    """
    from PySide6.QtWidgets import QDialog, QFileDialog
    from pcbthermal.gui import package_actions as pa
    window.doc.open_problem(example_board(), "ex")
    pkg.attach_sources(window.doc.project, [("top.gtl", GBR, "gerber", "Top copper")], set_name="ex")
    out = tmp_path / "copy.pcbtz"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(out), "")))
    seen = {}

    def fake_exec(self):
        """!@brief Tick the box and accept."""
        seen["enabled"], seen["checked_at_start"] = self.sources.isEnabled(), self.sources.isChecked()
        self.sources.setChecked(True)
        return QDialog.Accepted
    monkeypatch.setattr(pa.ExportPackageDialog, "exec", fake_exec)
    assert pa.export_package(window)
    assert seen == {"enabled": True, "checked_at_start": False}                 # default OFF
    assert "sources/ex/top.gtl" in zipfile.ZipFile(out).namelist()
    assert window.doc.path is None and not window.doc.project.package.is_package
    assert str(window.settings.value(pa.SETTINGS_KEY)).lower() == "true"          # remembered
    seen.clear()
    assert pa.export_package(window)
    assert seen["checked_at_start"] is True
    tip = pa.SOURCES_TIP
    assert "Off by default" in tip


def test_window_save_as_both_types(window, tmp_path, monkeypatch):
    """!
    @brief Save As writes a package for `.pcbtz` and plain JSON for `.pcbt.json`, adding the suffix of the chosen filter.
    @param window The MainWindow.
    @param tmp_path Temporary folder.
    @param monkeypatch pytest fixture.
    @return None
    """
    from PySide6.QtWidgets import QFileDialog
    from pcbthermal.gui import package_actions as pa
    window.doc.open_problem(example_board(), "ex")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(tmp_path / "one"), "PCB Thermal project package (*.pcbtz)")))
    assert pa.save_as(window) and pkg.is_package(tmp_path / "one.pcbtz")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(tmp_path / "two"), "PCB Thermal project (*.pcbt.json)")))
    assert pa.save_as(window) and (tmp_path / "two.pcbt.json").exists() and not pkg.is_package(tmp_path / "two.pcbt.json")


def test_stored_sources_feed_a_reimport(window, tmp_path):
    """!
    @brief The stored files are extracted to a folder the import session reads, with the same detection as the original files.
    @param window The MainWindow.
    @param tmp_path Temporary folder.
    @return None
    """
    from pcbthermal.gui.import_session import ImportSession
    prj = _project(tmp_path, imports=True, sources=True)
    path = tmp_path / "r.pcbtz"
    pkg.save_package(path, prj, include_sources=True)
    window.open_file(str(path))
    folder = window.doc.project.package.extract_sources()
    try:
        s = ImportSession()
        s.set_files(folder)
        assert sorted(f.name for f in s.files) == ["board.drl", "my_bom.csv", "pos.csv", "top.gtl"]
        assert next(f for f in s.files if f.name == "top.gtl").role == "Top copper"
    finally:
        pkg.remove_extracted(folder)


def test_capture_reads_a_zip_before_the_session_closes(tmp_path):
    """!
    @brief The import window closes the session (and a ZIP archive with it) before any signal: the capture hooked on `before_close` reads the files first, with their roles and kinds.
    @param tmp_path Temporary folder.
    @return None
    """
    from types import SimpleNamespace
    from pcbthermal.gui import package_actions as pa
    from pcbthermal.gui.import_session import ImportSession
    zp = tmp_path / "set.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        zf.writestr("top.gtl", GBR)
        zf.writestr("pos.csv", "Ref,Val,Package,PosX,PosY,Rot,Side\n\"C1\",\"30p\",\"C_0603\",44.2,62.3,0.0,bottom\n")
        zf.writestr("parts_bom.csv", "Ref,Value\nU1,10k\n")
    session = ImportSession()
    session.set_files(zp)
    dlg = SimpleNamespace(session=session, record=None, before_close=[])
    cap = pa.capture_on_close(dlg)
    for fn in list(dlg.before_close):
        fn(dlg, 0)                                           # cancelled before a record exists: nothing is read
    assert cap.files == []
    dlg.record = object()
    for fn in list(dlg.before_close):
        fn(dlg, 1)                                           # what ImportBoardWindow.done does, before it releases the session
    session.close()
    got = {n: (k, fn) for n, _, k, fn, _ in cap.files}
    assert got["top.gtl"][0] == "gerber" and got["pos.csv"][0] == "placement" and got["parts_bom.csv"][0] == "bom"
    assert dict((n, b) for n, b, _, _, _ in cap.files)["top.gtl"] == GBR
    assert {o for *_, o in cap.files} == {"zip"}


def _drive_import(window, monkeypatch, state):
    """!
    @brief Answer File - Import Gerber board like a user: the window reads `state["source"]` (None: what the offer of the stored files opened), the re-import is a Replace,
           and the box that offers the stored files answers `state["use_stored"]`.
    @param window The MainWindow.
    @param monkeypatch pytest fixture.
    @param state dict with "source", "use_stored" and the list "folders" (what the session read, filled here).
    @return None
    """
    from PySide6.QtWidgets import QMessageBox
    from pcbthermal.gui import import_window as iw
    monkeypatch.setattr("pcbthermal.gui.main_window.QMessageBox.question", lambda *a, **k: QMessageBox.Discard)

    def fake_exec(dlg):
        """!@brief The import window: read, build, close. @param dlg The window. @return int"""
        dlg.confirm = lambda *a: True
        dlg.notify = lambda title, text: pytest.fail(f"{title}: {text}")
        if state["source"] is not None:
            dlg.open_path(str(state["source"]))
        state["folders"].append(dlg.session.source_text)
        dlg.ask_reimport = lambda d: (d.radios["replace"].setChecked(True), True)[1]
        return 1 if dlg.do_import() else 0
    monkeypatch.setattr(iw.ImportBoardWindow, "exec", fake_exec)

    def box_exec(box):
        """!@brief The offer of the stored files. @param box The message box. @return int"""
        box._answer = next((b for b in box.buttons() if b.text() == ("Use the stored files" if state["use_stored"] else "Choose other files")), None)
        return 0
    monkeypatch.setattr(QMessageBox, "exec", box_exec)
    monkeypatch.setattr(QMessageBox, "clickedButton", lambda box: getattr(box, "_answer", None))
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: pytest.fail(f"warning: {a[1:]}"))


@pytest.mark.parametrize("as_zip", [False, True])
def test_reimport_from_the_stored_files_through_the_window(window, tmp_path, monkeypatch, as_zip):
    """!
    @brief Review regression: an import, Export package with the files, Open, and two re-imports from the stored files through the window.
    @details Found by the review: the private folder of the stored files was removed right after `open_path`, so the import failed (FileNotFoundError when the parts read
             the placement file) and the capture lost the files; the record was renamed after the temporary folder and the package then held the files twice; a ZIP member
             was stored as its decoded text (a Latin-1 byte became U+FFFD). Now: the original bytes are stored, the re-import sees the same names and hashes as the first
             import (a ZIP is rebuilt for a set that came from one, with its folders), the set keeps its name and holds each file once, and no temporary folder is left.
    @param window The MainWindow.
    @param tmp_path Temporary folder.
    @param monkeypatch pytest fixture.
    @param as_zip True to import from a ZIP whose members sit in a sub-folder, False from a folder.
    @return None
    """
    import glob
    import tempfile
    from tests.helpers.synthetic_board import make_board
    src = make_board(tmp_path / "board")
    # Bytes no reader may change: a Latin-1 comment (not UTF-8) and CR LF line ends
    f_gbr = b"G04 R\xe9vision \xa9 2026*\r\n" + (src / "F.gbr").read_bytes().replace(b"\n", b"\r\n")
    (src / "F.gbr").write_bytes(f_gbr)
    originals = {f.name: f.read_bytes() for f in src.iterdir()}
    source = src
    if as_zip:
        source = tmp_path / "board.zip"
        with zipfile.ZipFile(source, "w", zipfile.ZIP_DEFLATED) as z:
            for name, data in originals.items():
                z.writestr("gerbers/" + name, data)
    before = set(glob.glob(os.path.join(tempfile.gettempdir(), pkg.EXTRACT_PREFIX + "*")))
    state = {"source": source, "use_stored": True, "folders": []}
    _drive_import(window, monkeypatch, state)
    window.show_import()
    first = sorted((f.name, f.sha256, f.function) for f in window.doc.project.imports[0].files)
    name = window.doc.project.imports[0].name
    stored = window.doc.project.package.sources
    assert {m.rsplit("/", 1)[-1]: b for m, b in stored.items()} == {k: v for k, v in originals.items() if k in {n.rsplit("/", 1)[-1] for n, _, _ in first}}
    out = tmp_path / "p.pcbtz"
    from pcbthermal.gui import package_actions as pa
    assert pa.write_copy(window, str(out), True)
    window.open_file(str(out))
    assert window.doc.project.package.sources["sources/board/F.gbr"] == f_gbr          # byte for byte after a save and an open
    for _ in range(2):
        state["source"] = None
        window.show_import()
        rec = window.doc.project.imports[0]
        assert sorted((f.name, f.sha256, f.function) for f in rec.files) == first and rec.name == name
        assert sorted(window.doc.project.package.sources) == sorted(stored) and window.doc.project.package.sources["sources/board/F.gbr"] == f_gbr
    assert len(state["folders"]) == 3 and all(pkg.EXTRACT_PREFIX in t for t in state["folders"][1:])
    assert set(glob.glob(os.path.join(tempfile.gettempdir(), pkg.EXTRACT_PREFIX + "*"))) == before    # the private folder went with the window


@pytest.mark.parametrize("ending", ["cancel", "other_files"])
def test_the_stored_files_folder_goes_on_cancel_and_on_other_files(window, tmp_path, monkeypatch, ending):
    """!
    @brief Review of the before-release hook: the private folder of the stored files is removed when the window is cancelled after the offer opened it, and when the user opens
           other files in the window (the hook runs before the worker); a cancel stores nothing new, and other files are what an Import then captures.
    @param window The MainWindow.
    @param tmp_path Temporary folder.
    @param monkeypatch pytest fixture.
    @param ending "cancel" or "other_files".
    @return None
    """
    import glob
    import tempfile
    from pcbthermal.gui import import_window as iw
    from pcbthermal.gui import package_actions as pa
    from tests.helpers.synthetic_board import make_board
    src = make_board(tmp_path / "board")
    state = {"source": src, "use_stored": True, "folders": []}
    _drive_import(window, monkeypatch, state)
    window.show_import()
    out = tmp_path / "p.pcbtz"
    assert pa.write_copy(window, str(out), True)
    window.open_file(str(out))
    stored = dict(window.doc.project.package.sources)
    record = window.doc.project.imports[0].to_dict()
    before = set(glob.glob(os.path.join(tempfile.gettempdir(), pkg.EXTRACT_PREFIX + "*")))
    other = make_board(tmp_path / "other")
    (other / "F.gbr").write_bytes((other / "F.gbr").read_bytes() + b"G04 another revision*\n")
    seen = {}

    def fake_exec(dlg):
        """!@brief Opened on the stored files by the offer; cancel, or open other files and import. @param dlg The window. @return int"""
        dlg.confirm = lambda *a: True
        dlg.notify = lambda title, text: pytest.fail(f"{title}: {text}")
        seen["stored_open"] = pkg.EXTRACT_PREFIX in dlg.session.source_text
        seen["extra"] = set(glob.glob(os.path.join(tempfile.gettempdir(), pkg.EXTRACT_PREFIX + "*"))) - before
        if ending == "cancel":
            dlg.reject()
            return 0
        dlg.open_path(str(other))
        seen["after_open"] = set(glob.glob(os.path.join(tempfile.gettempdir(), pkg.EXTRACT_PREFIX + "*"))) - before
        dlg.ask_reimport = lambda d: (d.radios["replace"].setChecked(True), True)[1]
        return 1 if dlg.do_import() else 0
    monkeypatch.setattr(iw.ImportBoardWindow, "exec", fake_exec)
    state["source"] = None
    window.show_import()
    assert seen["stored_open"] and len(seen["extra"]) == 1                       # the offer opened a private folder
    assert set(glob.glob(os.path.join(tempfile.gettempdir(), pkg.EXTRACT_PREFIX + "*"))) == before
    if ending == "cancel":
        assert window.doc.project.package.sources == stored and window.doc.project.imports[0].to_dict() == record
    else:
        assert seen["after_open"] == set()                                       # removed when the other files were opened, before the worker read them
        got = window.doc.project.package.sources
        assert got != stored and any(b.endswith(b"G04 another revision*\n") for b in got.values())


def test_extraction_names_are_safe_on_every_file_system(tmp_path):
    """!
    @brief Review regression: a hostile package cannot make the extraction write a Windows device name, a name Windows would merge (trailing dot or space), a name too long
           for the file system, or one file over another (two names that become the same safe name); NFC and NFD spellings of one name are refused like a case collision.
    @param tmp_path Temporary folder.
    @return None
    """
    import unicodedata
    names = ["sources/b/CON", "sources/b/nul.gbr", "sources/b/com1.drl", "sources/b/trail. ", "sources/b/" + "a" * 300 + ".gbr", "sources/b/x:y.gbr", "sources/b/x?y.gbr"]
    members = dict(_good_members(), **{n: n.encode() for n in names})
    path = tmp_path / "w.pcbtz"
    _raw_zip(path, members)
    extras = pkg.load_package(path).package
    folder = extras.extract_sources()
    try:
        got = sorted(os.listdir(folder))
        assert len(got) == len(names)                                                   # nothing overwritten
        assert all(len(g) <= pkg.MAX_NAME_CHARS and not g.endswith((".", " ")) for g in got)
        assert all(g.split(".", 1)[0].upper() not in pkg._WINDOWS_DEVICES for g in got)
    finally:
        pkg.remove_extracted(folder)
    nfc, nfd = (unicodedata.normalize(f, "sources/b/é.gbr") for f in ("NFC", "NFD"))
    _raw_zip(tmp_path / "n.pcbtz", dict(_good_members(), **{nfc: b"1", nfd: b"2"}))
    with pytest.raises(ProjectFormatError, match="normalisation"):
        pkg.load_package(tmp_path / "n.pcbtz")


def test_failed_save_over_a_json_leaves_no_new_backup(tmp_path, monkeypatch):
    """!
    @brief Review regression: a package save over a `.pcbt.json` that fails (the rename) keeps the old file and does not leave the `.bak` it made (each failed attempt left one more).
    @param tmp_path Temporary folder.
    @param monkeypatch pytest fixture.
    @return None
    """
    target = tmp_path / "t"
    save_project(target, Project(problem=example_board()))
    before = target.read_bytes()

    def boom(*a, **k):
        """!@brief A rename that fails. @param a Ignored. @param k Ignored."""
        raise OSError("disk full")
    monkeypatch.setattr(os, "replace", boom)
    for _ in range(2):
        with pytest.raises(OSError):
            pkg.save_package(target, Project(problem=example_board()))
    assert target.read_bytes() == before and sorted(os.listdir(tmp_path)) == ["t"]


def test_privacy_hints_name_the_kind_never_the_text(window, tmp_path):
    """!
    @brief Export package names the stored files that carry a user folder path, an e-mail address or a user/author field, and shows the kind of text, never the text.
    @param window The MainWindow.
    @param tmp_path Temporary folder.
    @return None
    """
    from pcbthermal.gui import package_actions as pa
    secret = b"G04 User: jdoe12 on C:\\Users\\jdoe12\\Desktop mail jdoe12@example.org*\n"
    hints = pkg.privacy_hints({"sources/b/a.gbr": secret + GBR, "sources/b/clean.gbr": GBR, "sources/b/k.gbr": b"G04 /home/someone/x*\n"})
    assert hints == [("a.gbr", ["a user folder path", "an e-mail address", "a user, author or computer name"]), ("k.gbr", ["a user folder path"])]
    pkg.attach_sources(window.doc.project, [("a.gbr", secret + GBR, "gerber", "Top copper")])
    dlg = pa.ExportPackageDialog(window, True, False)
    text = " ".join(w.text() for w in dlg.findChildren(type(dlg.findChild(__import__("PySide6.QtWidgets", fromlist=["QLabel"]).QLabel))))
    assert "a.gbr" in text and "e-mail address" in text and "jdoe12" not in text and "example.org" not in text


# ------------------------------------------------------------------------------------------------------------------------------------ second review
def test_every_reader_of_a_project_reads_a_package(tmp_path, capsys):
    """!
    @brief `load_project`, `model.load_problem` and the commands `transient` and `convergence` read a package (review: they said "not UTF-8 text").
    @param tmp_path Temporary folder.
    @param capsys pytest fixture.
    @return None
    """
    from pcbthermal import cli
    from pcbthermal.model import load_problem
    path = tmp_path / "b.pcbtz"
    pkg.save_package(path, Project(problem=example_board()))
    assert load_project(path).package.is_package
    assert load_problem(path).name == example_board().name
    assert cli.main(["transient", str(path), "--t-end", "2", "--steps", "2", "--no-plots", "--out", str(tmp_path / "o")]) == 0
    assert "not UTF-8" not in capsys.readouterr().err


def test_a_package_never_carries_away_a_file_it_did_not_hold(tmp_path):
    """!
    @brief A package whose JSON names a file outside it (any private file of the reader's disk) does not copy that file into the next package; a non-image is never
           read into a package (review: a re-save embedded `images/secret.txt`).
    @param tmp_path Temporary folder.
    @return None
    """
    secret = tmp_path / "secret.txt"
    secret.write_bytes(b"PRIVATE KEY")
    members = _good_members()
    d = json.loads(members["project.pcbt.json"])
    d["view"] = {"background": {"path": str(secret), "w_mm": 10, "h_mm": 10}}
    members["project.pcbt.json"] = json.dumps(d).encode()
    _raw_zip(tmp_path / "h.pcbtz", members)
    prj = pkg.load_any(tmp_path / "h.pcbtz")
    _, notes = pkg.save_package(tmp_path / "again.pcbtz", prj)
    assert not [n for n in zipfile.ZipFile(tmp_path / "again.pcbtz").namelist() if n.startswith("images/")]
    assert any("points outside" in n for n in notes)
    # A project of this machine whose background is not an image: refused with a note, the path is kept
    plain = Project(problem=example_board())
    plain.view["background"] = {"path": str(secret), "w_mm": 10, "h_mm": 10}
    _, notes = pkg.save_package(tmp_path / "p.pcbtz", plain)
    assert not [n for n in zipfile.ZipFile(tmp_path / "p.pcbtz").namelist() if n.startswith("images/")] and any("not a PNG" in n for n in notes)


def test_saving_an_unchanged_package_writes_the_same_bytes(tmp_path):
    """!
    @brief Open a package and save it again: the file is byte for byte the same (the creation time is kept and every member is dated by it).
    @param tmp_path Temporary folder.
    @return None
    """
    prj = _project(tmp_path, imports=True, sources=True)
    pkg.save_package(tmp_path / "a.pcbtz", prj, include_sources=True)
    again = pkg.load_package(tmp_path / "a.pcbtz")
    time.sleep(1.1)                                         # the clock moves on: the dates of the file must not follow it
    pkg.save_package(tmp_path / "b.pcbtz", again)
    assert (tmp_path / "a.pcbtz").read_bytes() == (tmp_path / "b.pcbtz").read_bytes()


def test_json_bomb_and_whole_package_ratio_refused(tmp_path, monkeypatch):
    """!
    @brief A project JSON of nested empty lists (a few kB that `json.loads` would make into GB) and a package that expands too much as a whole are refused before
           anything big is allocated.
    @param tmp_path Temporary folder.
    @param monkeypatch pytest fixture (the limits are lowered so that the test is small).
    @return None
    """
    monkeypatch.setattr(pkg, "MAX_PROJECT_TOKENS", 1000)
    members = _good_members()
    members["project.pcbt.json"] = b"[" + b"[]," * 2000 + b"[]]"
    _refused(tmp_path, members, "JSON items")
    monkeypatch.setattr(pkg, "MAX_PROJECT_TOKENS", 8_000_000)
    monkeypatch.setattr(pkg, "OVERALL_FREE_BYTES", 1024)
    many = _good_members()
    many.update({f"renders/{i}.bin": b"\x00" * 60000 for i in range(5)})     # each member is under RATIO_FREE_BYTES: only the whole-package rule sees them
    _refused(tmp_path, many, "expands")


def test_the_program_never_writes_a_package_it_would_refuse(tmp_path, monkeypatch):
    """!
    @brief A save whose package the reader would refuse raises and leaves the old file (the writer checks the reader's limits).
    @param tmp_path Temporary folder.
    @param monkeypatch pytest fixture.
    @return None
    """
    path = tmp_path / "k.pcbtz"
    pkg.save_package(path, Project(problem=example_board()))
    before = path.read_bytes()
    monkeypatch.setattr(pkg, "MAX_PROJECT_TOKENS", 10)
    with pytest.raises(ProjectFormatError, match="would not be readable"):
        pkg.save_package(path, Project(problem=example_board()))
    assert path.read_bytes() == before


def test_read_warnings_are_said(window, tmp_path, capsys, monkeypatch):
    """!
    @brief A member that does not match the manifest is dropped AND said: printed by the command line, shown by the window (review: collected and never shown).
    @param window The MainWindow.
    @param tmp_path Temporary folder.
    @param capsys pytest fixture.
    @param monkeypatch pytest fixture.
    @return None
    """
    from pcbthermal import cli
    from PySide6.QtWidgets import QMessageBox
    members = _good_members()
    members["images/bg.png"] = PNG
    _raw_zip(tmp_path / "t.pcbtz", members, bad_hash=("images/bg.png",))
    assert cli.main(["run", str(tmp_path / "t.pcbtz"), "--model", "analytic", "--out", str(tmp_path / "r"), "--no-plots", "--cell-mm", "2"]) == 0
    assert "Warning: package: images/bg.png" in capsys.readouterr().err
    seen = []
    # The box is built plain (a member name is never rich text), so it is the box's exec that is intercepted
    monkeypatch.setattr(QMessageBox, "exec", lambda self: seen.append(self.text()) or QMessageBox.Ok)
    window.open_file(str(tmp_path / "t.pcbtz"))
    assert seen and "images/bg.png" in seen[0]


def test_a_stored_background_survives_its_file(tmp_path):
    """!
    @brief Save as a package with an image from the disk, delete the image, save again: the package still holds it and no absolute path is written (review: the
           image was dropped and the path of the user's disk written in its place).
    @param tmp_path Temporary folder.
    @return None
    """
    prj = _project(tmp_path)
    pkg.save_package(tmp_path / "a.pcbtz", prj)
    (tmp_path / "bg.png").unlink()
    _, notes = pkg.save_package(tmp_path / "a.pcbtz", prj)
    back = pkg.load_package(tmp_path / "a.pcbtz")
    assert notes == [] and back.view["background"]["path"] == "images/bg.png" and back.package.images["images/bg.png"] == PNG
    assert str(tmp_path) not in zipfile.ZipFile(tmp_path / "a.pcbtz").read("project.pcbt.json").decode()
    assert pkg.background_bytes(prj, str(tmp_path / "bg.png")) == PNG          # the canvas draws it from memory
