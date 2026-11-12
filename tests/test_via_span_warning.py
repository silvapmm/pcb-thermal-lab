#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_via_span_warning.py
@brief The import warns about vias whose drill file says they do not span the whole board (blind, buried, micro): the models treat every via as a through via.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from pcbthermal.gui.import_session import ImportSession
from tests.helpers.synthetic_board import make_board


def _build(folder, inner, function):
    """!
    @brief Import a synthetic set whose drill file carries a given X2 file function.
    @param folder Folder for the fabrication files.
    @param inner Number of inner copper layers (the board has inner + 2).
    @param function Text after `TF.FileFunction,` in the drill file, for example "Plated,1,2,PTH".
    @return The ImportSession after `build_problem`.
    """
    d = make_board(folder, inner=inner)
    f = d / "drill.drl"
    f.write_text(f.read_text().replace("Plated,1,2,PTH", function))
    sx = ImportSession()
    sx.set_files(d)
    sx.load()
    sx.cell_mm = 1.0
    sx.build_problem()
    return sx


def _span_lines(sx):
    """!
    @brief The lines of the import record that talk about the layer span of vias.
    @param sx ImportSession after the build.
    @return list of text lines.
    """
    return [w for w in sx.record.warnings if "layer span" in w]


def test_blind_vias_of_a_four_layer_set_are_counted_and_named(tmp_path):
    """!
    @brief A drill file spanning layers 1 to 2 on a 4-layer set: its two vias are reported as treated as through vias.
    @param tmp_path pytest folder.
    """
    sx = _build(tmp_path / "a", 2, "Plated,1,2,PTH")
    lines = _span_lines(sx)
    assert len(lines) == 1
    assert lines[0].startswith("2 of the 2 vias") and "through vias" in lines[0] and "unsafe" in lines[0]


def test_through_vias_give_no_span_warning(tmp_path):
    """!
    @brief The full span (1 to 4 on four layers, 1 to 2 on two) and a file without a span add no line.
    @param tmp_path pytest folder.
    """
    assert _span_lines(_build(tmp_path / "a", 2, "Plated,1,4,PTH")) == []
    assert _span_lines(_build(tmp_path / "b", 0, "Plated,1,2,PTH")) == []
    assert _span_lines(_build(tmp_path / "c", 2, "Plated,PTH")) == []


def test_a_buried_span_is_not_the_whole_board_either(tmp_path):
    """!
    @brief Layers 2 to 3 of a 4-layer set is a buried via.
    @param tmp_path pytest folder.
    """
    assert len(_span_lines(_build(tmp_path / "a", 2, "Plated,2,3,Blind"))) == 1
