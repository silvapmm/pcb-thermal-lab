#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_bom.py
@brief The BOM reader (`pcbthermal.gerber.bom`) on invented tables of the common exporters (KiCad, JLCPCB, Altium, EasyEDA, PCBWay, Pulsonix styles), encodings, the not-fitted marks, hostile
       input (a fuzz of 2000 mutated tables must end in a table or a `BomError`), the role rule, and, when the local boards library is present, the counts of the study of
       `research/bom-role-and-close-hook` (1180 parts, the roles and the agreement of the signals) and the real Pulsonix BOM.
"""

import collections
import os
import random
import time
from pathlib import Path

import pytest

from pcbthermal.gerber import GerberError
from pcbthermal.gerber import bom

KICAD = '"Reference","Value","Footprint","Qty","DNP"\n"C1,C2","100n","C_0402_1005Metric",2,\n"U1","RP2040","Package_DFN_QFN:QFN-56-1EP_7x7mm",1,\n"TP1","TP","TestPoint:TestPoint_Pad_D1.0mm",1,"DNP"\n'
JLC = "Comment,Designator,Footprint,LCSC Part #\n10k,R1 R2 R3,R_0402_1005Metric,C25744\nAO3400,Q1,SOT-23,C20917\n"
ALTIUM = 'Comment;Description;Designator;Footprint;LibRef;Quantity\n100nF;"Capacitor 100 nF";"C1, C2, C3";C0402;CAP;3\nSTM32F4;MCU;U1;LQFP64;MCU;1\n'
EASYEDA = "Designator\tFootprint\tQuantity\tManufacturer Part\tSupplier Part\tFitted\nR1,R2\tR0402\t2\tRC0402\tC25744\tYes\nR3\tR0402\t1\tRC0402\tC25744\tNo\n"
PCBWAY = "Item,Qty,Reference(s),Part Number,Package,Type\n1,2,R1 R2,RC0402,0402,SMD\n2,1,U1,STM32,LQFP64,SMD\n"
PREAMBLE = ("My board - BILL OF MATERIALS,\n2000/01/01,\n,\nTOP SIDE,\nNo,Part Name,Qty,Part Number,Footprint,Type,Components,\n1,LED - Red,3,X1,0402p,SM,D1 D2 D3,\n,\n"
            "BOTTOM SIDE,\nNo,Part Name,Qty,Part Number,Footprint,Type,Components,\n2,TEST,1,,1x TP SM,DNI,TP1,\n,\nASSOCIATED PARTS,\nNo,Part Name,Qty,Part Number,Footprint,Type,Components,\n"
            "3,Battery,1,CR,,DNI,,\n")


def refs(t):
    """!
    @brief The designators of a table.
    @param t BomTable.
    @return list of str.
    """
    return [r.ref for r in t.rows]


def test_kicad_columns_group_and_dnp():
    t = bom.read_bom(KICAD.encode())
    assert refs(t) == ["C1", "C2", "U1", "TP1"]
    assert t.rows[3].not_fitted == "dnp" and not t.rows[0].not_fitted
    assert t.columns["package"] == "Footprint" and t.sections == 1 and t.delimiter == ","


def test_jlcpcb_columns():
    t = bom.read_bom(JLC.encode())
    assert t.columns == {"value": "Comment", "ref": "Designator", "package": "Footprint", "lcsc": "LCSC Part #"}
    assert refs(t) == ["R1", "R2", "R3", "Q1"] and t.rows[0].lcsc == "C25744"


def test_altium_semicolon_with_quoted_comma_designators():
    t = bom.read_bom(ALTIUM.encode())
    assert t.delimiter == ";" and refs(t) == ["C1", "C2", "C3", "U1"]
    assert t.rows[0].description == "Capacitor 100 nF" and not t.rows[0].not_fitted        # "nF" in a description is a unit, not a mark


def test_easyeda_tab_with_a_fitted_column():
    t = bom.read_bom(EASYEDA.encode())
    assert t.delimiter == "\t" and refs(t) == ["R1", "R2", "R3"]
    assert [r.not_fitted for r in t.rows] == ["", "", "populate"]
    assert t.columns["lcsc"] == "Supplier Part" and t.columns["mpn"] == "Manufacturer Part"


def test_pcbway_reference_header():
    t = bom.read_bom(PCBWAY.encode())
    assert t.columns["ref"] == "Reference(s)" and refs(t) == ["R1", "R2", "U1"]


def test_preamble_and_three_sections_with_the_dni_type():
    t = bom.read_bom(PREAMBLE.encode())
    assert t.sections == 3
    assert refs(t) == ["D1", "D2", "D3", "TP1"]                                           # the associated part has no designator: no row
    assert [r.not_fitted for r in t.rows] == ["", "", "", "type"]


@pytest.mark.parametrize("encoding, prefix", [("utf-8", b""), ("utf-8", b"\xef\xbb\xbf"), ("utf-16", b"")])
def test_encodings(encoding, prefix):
    raw = prefix + KICAD.encode(encoding) if encoding == "utf-8" else KICAD.encode("utf-16")            # "utf-16" writes its own byte order mark
    t = bom.read_bom(raw)
    assert refs(t) == ["C1", "C2", "U1", "TP1"] and t.columns["ref"] == "Reference"          # the mark does not stick to the first header cell
    assert t.encoding.startswith(("UTF-8", "UTF-16"))


def test_utf16_without_a_mark_and_an_xlsx_are_refused_with_a_clear_message():
    with pytest.raises(bom.BomError, match="byte order mark"):
        bom.read_bom(KICAD.encode("utf-16-le"))
    with pytest.raises(bom.BomError, match=r"Excel workbook \(.xlsx, .xls\) is not read"):
        bom.read_bom(b"PK\x03\x04" + b"\x00" * 40, "bom.xlsx")
    assert issubclass(bom.BomError, GerberError)


@pytest.mark.parametrize("cells, expected", [
    ({"dnp": "DNP"}, "dnp"), ({"dnp": "DNI"}, "dnp"), ({"dnp": "NF"}, "dnp"), ({"dnp": "NM"}, "dnp"), ({"dnp": "DNF"}, "dnp"), ({"dnp": "Yes"}, "dnp"), ({"dnp": "x"}, "dnp"),
    ({"dnp": ""}, ""), ({"dnp": "No"}, ""), ({"dnp": "0"}, ""), ({"type": "DNI"}, "type"), ({"type": "SM"}, ""), ({"type": "Do not place"}, "type"),
    ({"note": "NF"}, "note"), ({"note": "not fitted"}, "note"), ({"populate": "No"}, "populate"), ({"populate": "Yes"}, ""), ({"populate": "0"}, "populate"),
    ({"value": "DNP"}, "value"), ({"value": "10k DNP"}, "value"), ({"value": "NF"}, ""), ({"description": "Capacitor 100 nF"}, ""), ({"description": "0402 10k DNI"}, "description"),
    ({"value": "100nF", "description": "NM (nanometre)"}, ""), ({"value": "NC"}, ""),
])
def test_the_explicit_not_fitted_markers(cells, expected):
    assert bom.not_fitted_reason(cells) == expected


def test_ranges_and_limits():
    assert bom.expand_designators("R1-R4 C9") == ["R1", "R2", "R3", "R4", "C9"]
    assert bom.expand_designators("R1-R9999999") == ["R1-R9999999"]
    assert bom.expand_designators("R1-R" + "9" * 5000) == ["R1-R" + "9" * 5000]           # no int() of a huge digit string
    assert len(bom.expand_designators(" ".join(f"R{i}" for i in range(50000)))) == bom.MAX_TOKENS_PER_CELL
    with pytest.raises(bom.BomError):
        bom.read_bom(b"a,b,c\n1,2,3\n")


def test_duplicates_keep_the_first_and_say_so():
    t = bom.read_bom(b"Reference,Value\nR1,1k\nR1,2k\n")
    assert [(r.ref, r.value) for r in t.rows] == [("R1", "1k")] and "appear more than once" in t.warnings[0]
    m = bom.merge([t, bom.read_bom(b"Reference,Value\nR1,3k\nR2,4k\n", "b.csv")])
    assert m.rows["R1"].value == "1k" and m.rows["R2"].value == "4k" and any("more than one BOM file" in w for w in m.warnings)
    assert m.get("r2").ref == "R2"                                                          # matched ignoring the case


def test_the_assembly_variant_is_reported():
    t = bom.read_bom(b"Designator,Comment,Variant\nR1,1k,Fitted-A\nR2,1k,Fitted-A\nR3,1k,Lite\n")
    assert t.variants == ["Fitted-A", "Lite"]
    assert bom.merge([t]).variants == ["Fitted-A", "Lite"]


def test_looks_like_bom_by_columns_not_by_name():
    assert bom.looks_like_bom(KICAD) and bom.looks_like_bom(PREAMBLE) and bom.looks_like_bom(JLC) and bom.looks_like_bom(ALTIUM)
    # A placement table has X and Y columns: not a BOM
    assert not bom.looks_like_bom("Ref,Val,Package,PosX,PosY,Rot,Side\nR1,1k,R_0603,1,2,0,top\n")
    assert not bom.looks_like_bom("Designator,Mid X,Mid Y,Layer,Rotation\nR1,1,2,T,0\n")
    assert not bom.looks_like_bom("a,b,c\n1,2,3\n") and not bom.looks_like_bom("Reference\nR1\n") and not bom.looks_like_bom("%FSLAX46Y46*%\nG04 x*\n")


def test_hostile_cells_are_only_text_and_bounded():
    t = bom.read_bom(("Reference,Value\n=1+1,=cmd|' /C calc'!A0\nR1," + "x" * 100000 + "\n").encode())
    assert t.rows[0].ref == "=1+1" and len(t.rows) == 2 and len(t.rows[1].value) <= 200
    many_cols = ",".join(["Reference", "Value"] + [f"c{i}" for i in range(200)]) + "\n" + ",".join(["R1", "1k"] + ["z"] * 200) + "\n"
    assert refs(bom.read_bom(many_cols.encode())) == ["R1"]


def test_too_many_rows_and_too_many_designators_are_refused(monkeypatch):
    monkeypatch.setattr(bom, "MAX_ROWS", 50)
    with pytest.raises(bom.BomError, match="rows"):
        bom.read_bom(("Reference,Value\n" + "".join(f"R{i},1k\n" for i in range(200))).encode())
    monkeypatch.setattr(bom, "MAX_ROWS", 200000)
    monkeypatch.setattr(bom, "MAX_DESIGNATORS", 100)
    with pytest.raises(bom.BomError, match="designators"):
        bom.read_bom(("Reference,Value\n" + "".join(f"R{i},1k\n" for i in range(200))).encode())


def test_a_file_above_the_size_limit_is_refused(monkeypatch):
    monkeypatch.setattr(bom, "MAX_BYTES", 1000)
    with pytest.raises(bom.BomError, match="limit"):
        bom.read_bom(b"Reference,Value\n" + b"R1,1k\n" * 1000)


def test_fuzz_2000_mutated_tables_end_in_a_table_or_a_bom_error():
    rnd = random.Random(20261106)
    seeds = [KICAD.encode(), JLC.encode(), ALTIUM.encode(), EASYEDA.encode(), PCBWAY.encode(), PREAMBLE.encode(), KICAD.encode("utf-16"), b"\xef\xbb\xbf" + JLC.encode()]
    junk = [b"\x00", b"\xff", b'"', b",", b";", b"\t", b"\r", b"\n", b"R1-R99999999", b"=1+1", b"\xef\xbb\xbf", b"x" * 3000, b'"\n"', b"\xd0\xcf\x11\xe0", b"PK\x03\x04"]
    t0 = time.time()
    for _ in range(2000):
        raw = bytearray(rnd.choice(seeds))
        for _ in range(rnd.randint(1, 6)):
            k = rnd.randrange(len(raw) + 1)
            op = rnd.random()
            if op < 0.4:
                raw[k:k] = rnd.choice(junk)
            elif op < 0.7 and raw:
                del raw[k:k + rnd.randint(1, 12)]
            elif raw:
                raw[min(k, len(raw) - 1)] = rnd.randrange(256)
        try:
            t = bom.read_bom(bytes(raw))
            assert all(isinstance(r.ref, str) and r.ref for r in t.rows)
        except bom.BomError:
            pass
    assert time.time() - t0 < 60


def test_the_reader_is_linear_in_the_size():
    def run(n):
        raw = ("Reference,Value,Footprint\n" + "".join(f"R{i},1k,R_0402\n" for i in range(n))).encode()
        t0 = time.perf_counter()
        bom.read_bom(raw)
        return time.perf_counter() - t0
    run(2000)
    a, b = run(20000), run(80000)
    assert b < a * 4 * 3 + 0.5                                                              # four times the rows in about four times the time (with a margin for noise)


# ------------------------------------------------------------------------------------------------------------------------------------------------ the role rule
@pytest.mark.parametrize("ref,value,package,role", [
    ("R1", "10k", "R_0402_1005Metric", "source"), ("C3", "100n", "C_0402_1005Metric", "none"), ("U1", "RP2040", "QFN-56-1EP_7x7mm", "component"),
    ("Q1", "AO3400", "SOT-23", "component"), ("D1", "SS14", "D_SMA", "component"), ("J1", "USB_C", "USB_C_Receptacle", "none"),
    ("TP1", "TP", "TestPoint_Pad_D1.0mm", "none"), ("L1", "2.2uH", "L_1210_3225Metric", "source"), ("BL_GND1", "MountingHole_Pad", "Molex156Pin", "none"),
    ("X9", "", "", "none"),
])
def test_role_rule(ref, value, package, role):
    assert bom.classify(ref, value, package)["role"] == role


def test_silent_tie_and_ambiguous_words():
    assert bom.classify("ZZ9")["role"] == "unknown" and bom.proposal(bom.classify("ZZ9")) == "unknown"
    c = bom.classify("R5", "", "C_0402_1005Metric")                 # a resistor name on a capacitor footprint: prefix says source, footprint says none
    assert c["role"] == "unknown" and c["conflict"]
    j = bom.classify("J3", "SMA", "")                               # an RF connector whose value is SMA: the word is also a diode package
    assert j["ambiguous"] and bom.proposal(j) == "unknown"
    assert not bom.classify("D1", "SS14", "D_SOD-123")["ambiguous"]


# ------------------------------------------------------------------------------------------------------------------------------------------------ the local library
def _library():
    """!
    @brief The local boards library (PCBT_LIBRARY, or the folder above the env folders of the tests), or None.
    @return Path or None.
    """
    for var in ("PCBT_LIBRARY", "PCBT_REAL_BOARDS", "PCBT_GERBER_SAMPLES"):
        v = os.environ.get(var)
        if not v:
            continue
        p = Path(v).resolve()
        for q in [p] + list(p.parents):
            if (q / "real").is_dir() and (q / "samples").is_dir():
                return q
        env = Path(v)
        if (env.parent.parent / "real").is_dir():
            return env.parent.parent
    return None


BOARDS = [("cmm2", ["real/cmm2/placement/pos.csv"]), ("co60", ["real/co60/placement/pos.csv"]), ("isastm", ["real/isastm/placement/pos.csv"]),
          ("oswlight", ["real/oswlight/placement/pos.csv"]), ("rp2040", ["real/rp2040/placement/pos.csv"]), ("vstcm", ["real/vstcm/placement/pos.csv"]),
          ("librevna", ["samples/heldout/kicad__librevna/VNA-top-pos.csv", "samples/heldout/kicad__librevna/VNA-bottom-pos.csv"]),
          ("paste-board", ["generated/synthetic/paste-board/files/pos.csv"])]


def test_the_study_counts_are_reproduced_on_the_placement_tables_of_the_library():
    lib = _library()
    if lib is None or not all((lib / f).is_file() for _, fs in BOARDS for f in fs):
        pytest.skip("the local boards library is not present")
    from pcbthermal.gerber import parts as P
    results = []
    for _, files in BOARDS:
        for f in files:
            results += [bom.classify(r["ref"], r.get("value", ""), r.get("package", "")) for r in P.read_placement(lib / f)]
    assert len(results) == 1180
    assert collections.Counter(r["role"] for r in results) == {"component": 193, "source": 465, "none": 509, "unknown": 13}
    assert sum(r["conflict"] for r in results) == 15
    pairs = {}
    for a, b in (("prefix", "package"), ("prefix", "value"), ("package", "value")):
        both = [(r["votes"][a], r["votes"][b]) for r in results if r["votes"][a] and r["votes"][b]]
        pairs[f"{a}/{b}"] = (len(both), sum(1 for x, y in both if x == y))
    assert pairs == {"prefix/package": (1115, 1105), "prefix/value": (895, 890), "package/value": (892, 889)}


def test_the_real_pulsonix_bom_has_three_sections_86_designators_and_5_dni():
    lib = _library()
    f = None if lib is None else lib / "samples/pulsonix/rabbit/rabbit watch(Bill of Materials).csv"
    if f is None or not f.is_file():
        pytest.skip("the Pulsonix sample is not present")
    t = bom.read_bom(f.read_bytes(), f.name)
    assert t.sections == 3 and len(t.rows) == 86
    assert sum(1 for r in t.rows if r.not_fitted) == 5 and {r.ref for r in t.rows if r.not_fitted} == {"TP1", "TP2", "TP3", "TP4", "TP5"}
    assert t.columns["value"] == "Part Name" and t.columns["mpn"] == "Part Number" and t.columns["ref"] == "Components" and t.columns["lcsc"] == "Distributor Part Number"
    assert bom.looks_like_bom(f.read_bytes()[:8192].decode("utf-8", "replace"))
