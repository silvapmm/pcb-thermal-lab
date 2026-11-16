#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_classify_keys.py
@brief Which publisher class does each key of research/theory/BIBLIOGRAPHY.md belong to, and what may a note keep?

Question: how many of the sources the program rests on are open (CC, public domain), how many are
publisher-copyrighted articles, books, theses, vendor notes, standards? The class is a HEURISTIC read from the
citation text of the entry (journal, publisher words, URL host); it is an estimate to plan the work, not a licence
finding (the licence of an entry is `not checked` until its landing page is read, see README 2). Output: a table
printed to stdout and written to data/key_classes.csv.

Run from the repository root: .venv/bin/python research/paper-notes-policy/scripts/study_classify_keys.py
"""
import csv
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BIB = ROOT / "research/theory/BIBLIOGRAPHY.md"
OUT = Path(__file__).resolve().parents[1] / "data" / "key_classes.csv"

# (class, may keep) in the order the rules are tried; first match wins.
RULES = [
    ("confidential", r"OdbppSpec|ODB\+\+ Format", "nothing beyond the citation"),
    ("US government", r"NISTIR|NACA|NASA|NTRS|DTIC|OSTI|NBS|\bNIST\b", "summary + formulas with refs (public domain in the US only for works of government employees; still our own words)"),
    ("standard", r"JEDEC|JESD|IPC[- ]?\d|ASTM|ASHRAE|ASME V&V|ISO \d|IEC \d|XNC|Ucamco|Gerber (?:spec|Layer|Job)|ODB|IPC-2581|IPC7351", "citation + facts we test against; no tables"),
    ("vendor note", r"Application Note|app(?:lication)? note|datasheet|Texas Instruments|\bTI[- ]|Infineon|ROHM|Nexperia|Microchip|Richtek|Renesas|Isola|Bittele|JLCPCB|Altium|Cadence|Siemens|Alpha Novatech|SuperLU|UMFPACK|MUMPS|KiCad|Icepak|Semiconductor Digest|Gerbonara|Clipper|Shapely|PyAMG|HtLibrary|\bht\b library|github", "summary + facts with refs; vendor terms checked per site"),
    ("thesis", r"thesis|dissertation|Ph\.?D|M\.?A\.?Sc", "summary + formulas with refs"),
    ("arXiv / open preprint", r"arXiv", "summary + formulas; verbatim only if the CC licence allows"),
    ("book / lecture notes", r"ISBN|Hemisphere|Wiley|Oxford|Springer, |Cambridge|SIAM, |McGraw|textbook|book|lecture|PIMS|summer school|Lienhard|Saad|Milton|Carslaw|Incropera|Torquato|Golub|Varga|Young, D|Briggs", "references only (equation, page) + our own account"),
    ("journal / conference article", r"J\. Heat|Journal|J\. |Int\. |Trans\.|IEEE|ASME|AIAA|ITherm|Proc\.|SIAM|Elsevier|Comput\.|Phys\.|Math|Appl\.|\(19\d\d\)|\(20\d\d\)", "summary + formulas with refs"),
]
# Hand classification of keys whose citation text the rules cannot read (checked against the entry by eye).
MANUAL = {'SpringerFVHeat': 'book / lecture notes', 'Positivity9pt': 'journal / conference article', 'MFEMStaticCond': 'vendor note', 'Kron2022': 'journal / conference article', 'PMC11410250': 'journal / conference article', 'FourierMultilayerJCU': 'journal / conference article', 'FDvsFVSpringer': 'book / lecture notes', 'EC1998Spreading': 'journal / conference article', 'YovanovichMuzychkaEllison': 'journal / conference article', 'MartinRaithbyYovanovich1991Pages': 'journal / conference article', 'AvelarGanzarolli2003': 'journal / conference article', 'IIETAIntegral': 'journal / conference article', 'HeatsinkCatalogues': 'vendor note', 'GreaseValues': 'vendor note', 'ECHowToSelectHeatsink': 'journal / conference article', 'Chen-style': 'journal / conference article', 'IITPalakkad': 'book / lecture notes', 'PohankaRaudensky': 'journal / conference article', 'Guenin2015': 'journal / conference article', 'Blackmore2010': 'journal / conference article', 'MHTLArchive': 'journal / conference article', 'Lush2004': 'journal / conference article', 'PowerLawAveraging': 'journal / conference article', 'Wiener1912': 'journal / conference article', 'StructureTensor': 'vendor note', 'GreinerHormann1998': 'journal / conference article', 'MonierVinard2017': 'journal / conference article', 'Lasance': 'journal / conference article', 'AalborgVias': 'thesis', 'MondragonVias': 'journal / conference article', 'LasanceEllison': 'journal / conference article', 'Guenin2004': 'journal / conference article', 'Klausmeier': 'book / lecture notes', 'PythonResource': 'vendor note', 'KarpinskiPeaceman2010': 'journal / conference article', 'Ding1995': 'journal / conference article', 'Mondragon2025': 'journal / conference article', 'YovanovichJafarpur1993': 'journal / conference article', 'Muzychka2003Part2': 'journal / conference article', 'MuzychkaMultilayered1999': 'journal / conference article'}
# Corrections by the review: every key the rules put in the strict classes (standard, US government, confidential) was
# read by hand, and the errors of a random sample of 30 other keys; see README 3.
MANUAL.update({'SchwartzEtAl2006': 'journal / conference article', 'Roache': 'journal / conference article', 'FinChannelSources2': 'journal / conference article', 'ArXiv2307.08354': 'arXiv / open preprint', 'OSTI21026063': 'journal / conference article', 'Li1998': 'journal / conference article', 'SoleymaniKoohbanani2013': 'thesis', 'TI-SPRA953B': 'vendor note', 'EC2007Compact': 'journal / conference article', 'EC2019JEDEC': 'journal / conference article', 'EC1999RJB': 'journal / conference article', 'EC2024JESD5114': 'journal / conference article', 'EC1998Conduction': 'journal / conference article', 'ECD5470RoundRobin': 'journal / conference article', 'ROHM-64AN113E': 'vendor note', 'ROHM-65AN114E': 'vendor note', 'ROHM-2R-not-used': 'vendor note', 'VolumetricGuide': 'vendor note', 'Hollands': 'journal / conference article', 'ViaGuides': 'vendor note', 'CadenceJoule': 'vendor note', 'GerberTools': 'vendor note', 'Lienhard2024': 'book / lecture notes', 'ASHRAE2005Preprint': 'journal / conference article', 'Elenbaas1942': 'journal / conference article', 'UcamcoDownloads': 'vendor note', 'UcamcoLayerFormatTests': 'vendor note', 'UcamcoX3Samples': 'vendor note', 'UcamcoFabricationExamples': 'vendor note', 'OpenBoardsGitHub': 'vendor note', 'OdbppSiemens': 'vendor note', 'OdbppParsers': 'vendor note', 'JLCPCBCpl': 'vendor note', 'LiptonRoseTarjan1979': 'journal / conference article', 'Abuska2024': 'journal / conference article', 'GeorgeLiu1981': 'book / lecture notes', 'ElenbaasBCR': 'journal / conference article', 'EymardGallouetHerbin': 'book / lecture notes'})
OPEN_HINT = re.compile(r"CC[- ]BY|open access|MDPI|Frontiers|PLOS|PMC\d|IIETA|escholarship|Creative Commons", re.I)


def entries():
    """!
    @brief Read the entries of the bibliography.

    @return list[tuple[str, str]] Pairs (key, text of the first lines of the entry).
    """
    L = BIB.read_text().splitlines()
    seen, out = set(), []
    for i, line in enumerate(L):
        m = re.match(r"### \[([^\]]+)\]", line)
        if m and m.group(1) not in seen:
            seen.add(m.group(1))
            out.append((m.group(1), " ".join(L[i + 1:i + 8])))
    return out


def classify(key, text):
    """!
    @brief Heuristic class of one entry.

    @param key   Bibliography key.
    @param text  First lines of the entry.
    @return tuple[str, str, bool] (class, what a note may keep, open-access hint).
    """
    probe = key + " " + text
    if key in MANUAL:
        keep = {r[0]: r[2] for r in RULES}.get(MANUAL[key], "citation only until read")
        return MANUAL[key], keep, bool(OPEN_HINT.search(text))
    for cls, pat, keep in RULES:
        if re.search(pat, probe):
            return cls, keep, bool(OPEN_HINT.search(text))
    return "unclassified", "citation only until read", bool(OPEN_HINT.search(text))


def main():
    """!
    @brief Print the class table and write the CSV.

    @return int Exit status.
    """
    rows = [(k,) + classify(k, t) for k, t in entries()]
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["key", "class", "may_keep", "open_hint"])
        w.writerows(rows)
    cnt = Counter(r[1] for r in rows)
    print(f"{len(rows)} keys")
    for c, n in cnt.most_common():
        print(f"  {c:32s} {n:4d}  open-hint {sum(1 for r in rows if r[1]==c and r[3])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
