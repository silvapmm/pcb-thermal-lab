#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_project_file_fuzz.py
@brief Mutation test of the project loader: a value of the wrong type or range in a project file loads or raises ProjectFormatError, never a raw TypeError.
@details Every leaf of the example projects and of a format 2 project with an import record is replaced, one at a time, by a string, a list, a dict, None,
         a float, a negative number, a huge number and NaN (the set is fixed, so the test is deterministic). The command line must print the message and
         exit with 2, without a traceback.
"""

import copy
import json
import os
import subprocess
import sys

import pytest

from pcbthermal.examples import example_board
from pcbthermal.model import ImportFile, ImportPart, ImportRecord, ImportedCopper
from pcbthermal.project import Project, ProjectFormatError, project_from_dict, project_to_dict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAD_VALUES = ["text", [1, "a"], {"k": 1}, None, 0.5, -3, 10 ** 30, float("nan"), True, []]


def _format2():
    """!
    @brief A format 2 project dict with one import record with every kind of field.
    @return dict.
    """
    rec = ImportRecord(
        name="boardX", files=[ImportFile("top.gtl", 1234, "ab" * 32, "copper")], box_mm=[0.0, 0.0, 40.0, 30.0],
        parts=[ImportPart("U1", "hull", [[1.0, 1.0], [5.0, 1.0], [5.0, 4.0]], 1.5, {"tj_max": 125.0})],
        copper=ImportedCopper(0.05, True, [{"name": "F.Cu", "role": "top", "index": 0,
                                            "mask": {"kind": "binary", "shape": [2, 2], "data": "eJw="}}]),
        settings={"drill_units": "mm"}, warnings=["w"], holes=[{"x_mm": 1.0, "y_mm": 2.0, "d_mm": 0.3, "kind": "via"}])
    return project_to_dict(Project(problem=example_board(), imports=[rec]))


def _sources():
    """!
    @brief The documents to mutate: the example projects and a format 2 project.
    @return list of (name, dict).
    """
    out = []
    ex = os.path.join(ROOT, "examples")
    for f in sorted(os.listdir(ex)):
        if f.endswith(".pcbt.json"):
            with open(os.path.join(ex, f), encoding="utf-8") as fh:
                out.append((f, json.load(fh)))
    out.append(("format2", _format2()))
    return out


def _paths(node, prefix=()):
    """!
    @brief Every path to a value or a container of a JSON document.
    @param node Document or sub-document.
    @param prefix Path so far.
    @return list of tuples of keys and indices.
    """
    res = []
    if isinstance(node, dict):
        for k, v in node.items():
            res.append(prefix + (k,))
            res += _paths(v, prefix + (k,))
    elif isinstance(node, list):
        for i, v in enumerate(node[:3]):                # The first elements are enough: the rest are the same kind
            res.append(prefix + (i,))
            res += _paths(v, prefix + (i,))
    return res


def _mutate(doc, path, value):
    """!
    @brief A copy of a document with one value replaced.
    @param doc Document.
    @param path Path of the value.
    @param value New value.
    @return The mutated copy.
    """
    d = copy.deepcopy(doc)
    node = d
    for k in path[:-1]:
        node = node[k]
    node[path[-1]] = copy.deepcopy(value)
    return d


def test_every_mutation_loads_or_raises_the_clear_error():
    """!
    @brief No mutation of a project value raises anything but ProjectFormatError (or loads).
    @return None.
    """
    leaks, n = {}, 0
    for name, doc in _sources():
        for path in _paths(doc):
            for value in BAD_VALUES:
                n += 1
                try:
                    project_from_dict(_mutate(doc, path, value))
                except ProjectFormatError as exc:
                    assert str(exc), "an empty message"
                except Exception as exc:                # Any other class is the defect this test exists for
                    leaks.setdefault(f"{name}:{'.'.join(map(str, path))}", f"{type(exc).__name__}: {exc}")
    assert n > 1000
    assert not leaks, f"{len(leaks)} leaks, first: {list(leaks.items())[:8]}"


def test_message_names_the_key_path():
    """!
    @brief The message names the key path and what was expected.
    @return None.
    """
    d = copy.deepcopy(_sources()[0][1])
    d["zones"][0]["polygon_mm"][0] = "text"
    with pytest.raises(ProjectFormatError, match=r"zones\[0\]\.polygon_mm"):
        project_from_dict(d)
    d = copy.deepcopy(_sources()[0][1])
    d["board"]["width_mm"] = "wide"
    with pytest.raises(ProjectFormatError, match=r"board\.width_mm.*number"):
        project_from_dict(d)


@pytest.mark.parametrize("sub", ["run", "transient"])
def test_command_line_prints_message_and_exits_2(tmp_path, sub):
    """!
    @brief A bad value in a project file gives a one-line error and exit code 2 on the command line, no traceback.
    @param tmp_path pytest folder.
    @param sub Sub-command.
    @return None.
    """
    d = copy.deepcopy(_sources()[0][1])
    d["zones"][0]["polygon_mm"] = "text"
    f = tmp_path / "bad.pcbt.json"
    f.write_text(json.dumps(d))
    r = subprocess.run([sys.executable, "-m", "pcbthermal", sub, str(f)], capture_output=True, text=True, cwd=ROOT, timeout=120)
    assert r.returncode == 2, r.stderr
    assert "Traceback" not in r.stderr and "zones[0].polygon_mm" in r.stderr


def test_values_the_program_writes_itself_still_load():
    """!
    @brief Review: values that the program writes or holds are accepted, through JSON and through the undo path (no JSON in between).
    @details `h_side` null is an insulated edge (Preferences "edges lose heat" off, or the editor): the first version of the checks refused it, so such a project
             could not be reopened and every undo raised. The undo snapshots can hold NumPy scalars (np.int64 is not an int, np.bool_ not a bool).
    @return None.
    """
    import numpy as np
    p = example_board()
    p.board.h_side = None
    d = project_to_dict(Project(problem=p))
    assert d["board"]["h_side"] is None
    assert project_from_dict(json.loads(json.dumps(d))).problem.board.h_side is None
    assert project_from_dict(copy.deepcopy(d), validate=False).problem.board.h_side is None
    p = example_board()
    p.board.layers, p.zones[0].layer, p.zones[0].fill, p.vias[0].filled = np.int64(p.board.layers), np.int64(0), np.float32(0.5), np.bool_(True)
    project_from_dict(project_to_dict(Project(problem=p)), validate=False)


@pytest.mark.parametrize("text", ['{"board": {"width_mm": ' + "1" * 5000 + ', "height_mm": 10}}',
                                  '{"board": {"width_mm": ' + "1" * 400 + ', "height_mm": 10}}',
                                  '{"name": ' + "1" * 400 + ', "board": {"width_mm": 10, "height_mm": 10}}',
                                  '{"zz": ' + "[" * 100000 + "]" * 100000 + ', "board": {"width_mm": 10, "height_mm": 10}}'])
def test_text_that_python_refuses_to_read_is_the_clear_error(tmp_path, text):
    """!
    @brief Review: an integer beyond the float range (OverflowError), more than 4300 digits (ValueError), deep nesting (RecursionError) give ProjectFormatError.
    @param tmp_path pytest folder.
    @param text File content.
    @return None.
    """
    from pcbthermal.project import load_project
    f = tmp_path / "bad.pcbt.json"
    f.write_text(text)
    with pytest.raises(ProjectFormatError):
        load_project(str(f))


def test_deeply_nested_unknown_key_of_format_2_is_the_clear_error():
    """!
    @brief Review: an unknown top-level key of format 2 is deep-copied to be kept; nested 900 levels it raised RecursionError, now ProjectFormatError.
    @return None.
    """
    d = _format2()
    deep = []
    for _ in range(900):
        deep = [deep]
    d["zz"] = deep
    with pytest.raises(ProjectFormatError):
        project_from_dict(d)


def test_bytes_that_are_not_utf8_are_the_clear_error(tmp_path):
    """!
    @brief Review: a file whose bytes are not UTF-8 gives ProjectFormatError, not a UnicodeDecodeError.
    @param tmp_path pytest folder.
    @return None.
    """
    from pcbthermal.project import load_project
    f = tmp_path / "bad.pcbt.json"
    f.write_bytes(b'{"board": {"width_mm": \xff\xfe}}')
    with pytest.raises(ProjectFormatError, match="UTF-8"):
        load_project(str(f))
