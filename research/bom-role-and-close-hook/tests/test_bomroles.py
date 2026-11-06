#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_bomroles.py
@brief Tests of the research prototype `lib/bomroles.py` on invented tables (no third-party file): header finding, grouped designators, DNP flags, hostile input and the role rule.
@details Run: .venv/bin/python -m pytest -q research/bom-role-and-close-hook/tests
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import bomroles as br  # noqa: E402

KICAD = '"Reference","Value","Footprint","Qty","DNP"\n"C1,C2","100n","C_0402_1005Metric",2,\n"U1","RP2040","Package_DFN_QFN:QFN-56-1EP_7x7mm",1,\n"TP1","TP","TestPoint:TestPoint_Pad_D1.0mm",1,"DNP"\n'
JLC = "Comment,Designator,Footprint,LCSC Part #\n10k,R1 R2 R3,R_0402_1005Metric,C25744\nAO3400,Q1,SOT-23,C20917\n"
PREAMBLE = "My board - BILL OF MATERIALS,\n2000/01/01,\n,\nTOP SIDE,\nNo,Part Name,Qty,Part Number,Footprint,Type,Components,\n1,LED - Red,3,X1,0402p,SM,D1 D2 D3,\n,\nBOTTOM SIDE,\nNo,Part Name,Qty,Part Number,Footprint,Type,Components,\n2,TEST,1,,1x TP SM,DNI,TP1,\n"


def test_kicad_columns_and_group():
    """!@brief A KiCad table: grouped designators are split and the DNP cell is read."""
    t = br.read_bom(KICAD)
    assert [r["ref"] for r in t["rows"]] == ["C1", "C2", "U1", "TP1"]
    assert t["rows"][3]["dnp"] and not t["rows"][0]["dnp"]
    assert t["columns"]["package"] == "Footprint"


def test_jlcpcb_columns():
    """!@brief JLCPCB's Comment/Designator/LCSC Part # headers map to value/ref/lcsc."""
    t = br.read_bom(JLC)
    assert t["columns"] == {"value": "Comment", "ref": "Designator", "package": "Footprint", "lcsc": "LCSC Part #"}
    assert [r["ref"] for r in t["rows"]] == ["R1", "R2", "R3", "Q1"]


def test_preamble_and_two_sections():
    """!@brief A preamble and a second section (BOTTOM SIDE) with its own header are read; DNI is a do-not-place flag."""
    t = br.read_bom(PREAMBLE)
    assert t["sections"] == 2
    assert [r["ref"] for r in t["rows"]] == ["D1", "D2", "D3", "TP1"]
    assert t["rows"][3]["dnp"]


def test_ranges_and_limits():
    """!@brief A range expands once, an absurd range is kept as written, a text without a header is refused."""
    assert br.expand_designators("R1-R4 C9") == ["R1", "R2", "R3", "R4", "C9"]
    assert br.expand_designators("R1-R9999999") == ["R1-R9999999"]
    with pytest.raises(ValueError):
        br.read_bom("a,b,c\n1,2,3\n")


def test_hostile_cells_are_text():
    """!@brief Formula-like and very long cells are only text; nothing is evaluated."""
    t = br.read_bom("Reference,Value\n=1+1,=cmd|' /C calc'!A0\nR1," + "x" * 100000 + "\n")
    assert t["rows"][0]["ref"] == "=1+1" and len(t["rows"]) == 2


@pytest.mark.parametrize("ref,value,package,role", [
    ("R1", "10k", "R_0402_1005Metric", "source"), ("C3", "100n", "C_0402_1005Metric", "none"), ("U1", "RP2040", "QFN-56-1EP_7x7mm", "component"),
    ("Q1", "AO3400", "SOT-23", "component"), ("D1", "SS14", "D_SMA", "component"), ("J1", "USB_C", "USB_C_Receptacle", "none"),
    ("TP1", "TP", "TestPoint_Pad_D1.0mm", "none"), ("L1", "2.2uH", "L_1210_3225Metric", "source"), ("BL_GND1", "MountingHole_Pad", "Molex156Pin", "none"),
    ("X9", "", "", "none"),
])
def test_role_rule(ref, value, package, role):
    """!@brief The rule on the usual cases."""
    assert br.classify(ref, value, package)["role"] == role


def test_program_keeps_a_bom_key_and_a_bom_file_function():
    """!@brief The program as it is round-trips `from_file["bom"]` of a part and a file whose function text is a new one (project format 2 forward compatibility, INTEGRATION.md 2)."""
    sys.path.append(str(Path(__file__).resolve().parents[3]))
    from pcbthermal.model import ImportFile, ImportPart
    p = ImportPart(designator="U1", from_file={"value": "RP2040", "bom": {"role": "component", "dnp": False, "mpn": "X"}}, edits={"role": "Source"})
    q = ImportPart.from_dict(p.to_dict())
    assert q.from_file["bom"] == p.from_file["bom"] and q.edits == {"role": "Source"}
    f = ImportFile(name="b.csv", size=3, sha256="0" * 64, function="BOM (bill of materials)")
    assert ImportFile.from_dict(f.to_dict()).function == "BOM (bill of materials)"


def test_silent_and_tie():
    """!@brief No signal means unknown; one against one is unknown, not a guess."""
    assert br.classify("ZZ9")["role"] == "unknown"
    c = br.classify("R5", "", "C_0402_1005Metric")                 # a resistor name on a capacitor footprint: prefix says source, footprint says none
    assert c["role"] == "unknown" and c["conflict"]
