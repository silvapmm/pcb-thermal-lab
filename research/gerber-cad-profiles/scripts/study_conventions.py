#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_conventions.py
@brief Measure the writing conventions of every tool from its sample files: units, number format, zero omission, X2 attributes, drill dialect.
@details Question answered (README 3.4): what does each program write, so that the profile table can say it?  For every set (grouped
         by the tool that wrote it) it counts, over the Gerber files: units, the `%FS` format, X2 file functions, `TF.GenerationSoftware`,
         `TO.C` (reference designators in the paste file), `TA.AperFunction`, the G54/G55/G70/G71/G75/G36 codes and the end of file; and
         over the drill files: units, zero suppression, FMAT, how plating is told, and the comment style.  Output is a table per item.
         Run: .venv/bin/python -I research/gerber-cad-profiles/scripts/study_conventions.py
"""
import collections
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import cadprofiles as cp  # noqa: E402
import study_markers as sm  # noqa: E402


def sets():
    """!
    @brief All sets with their truth tool (marker-study roots and held-out sets).
    @return list Tuples (key, truth, folder).
    """
    out = [(rel, truth, os.path.join(sm.DATA, rel)) for rel, truth, _ in sm.ROOTS if os.path.isdir(os.path.join(sm.DATA, rel))]
    hb = os.path.join(sm.DATA, "heldout")
    out += [("heldout/" + d, d.split("__")[0], os.path.join(hb, d)) for d in sorted(os.listdir(hb))]
    return out


def gerber_facts(text):
    """!
    @brief What a Gerber file's header says.
    @param text  Whole file text (LF line ends).
    @return dict Feature -> value.
    """
    f = {}
    m = re.search(r"MO(MM|IN)\*", text)
    f["unit"] = m.group(1) if m else ("G70/71" if re.search(r"G7[01]\*", text) else "none")
    m = re.search(r"FS([LT])A?X(\d)(\d)Y(\d)(\d)\*", text)
    f["fs"] = "%s %s.%s" % ("L" if m and m.group(1) == "L" else "T", m.group(2), m.group(3)) if m else "none"
    f["x2_ff"] = bool(re.search(r"TF\.FileFunction", text))
    f["x2_gen"] = bool(re.search(r"TF\.GenerationSoftware", text))
    f["to_c"] = bool(re.search(r"TO\.C,", text))
    f["to_n"] = bool(re.search(r"TO\.N,", text))
    f["aperfn"] = bool(re.search(r"TA\.AperFunction", text))
    f["g54"] = bool(re.search(r"G54D\d", text))
    f["g36"] = bool(re.search(r"G36\*", text))
    f["g75"] = "G75" in text
    f["g74"] = "G74" in text
    f["eof"] = "M02" if re.search(r"M02\*", text) else ("M00" if re.search(r"M00\*", text) else "none")
    f["lp_clear"] = bool(re.search(r"%LPC\*%", text))
    f["ab_lm"] = bool(re.search(r"%(AB|LM|LR|LS)", text))
    return f


def drill_facts(text):
    """!
    @brief What an Excellon header says.
    @param text  File text (LF line ends).
    @return dict Feature -> value.
    """
    f = {}
    m = re.search(r"(?m)^(METRIC|INCH)(?:,(LZ|TZ))?(?:,([0.]+))?", text)
    f["unit"] = m.group(1) if m else ("M71" if re.search(r"(?m)^M71", text) else ("M72" if re.search(r"(?m)^M72", text) else "none"))
    f["zeros"] = m.group(2) if m and m.group(2) else ("TZ(M71,TZ)" if "M71,TZ" in text else "none")
    f["fmat"] = (re.search(r"(?m)^FMAT,(\d)", text) or [None, "none"])[1]
    plated = []
    if re.search(r"TF\.FileFunction,(Plated|NonPlated|MixedPlating)", text):
        plated.append("x2 comment")
    if re.search(r"(?m)^;TYPE=(PLATED|NON_PLATED)", text):
        plated.append(";TYPE=")
    if re.search(r"PLATED MILS|PLATED MM", text):
        plated.append("per-tool comment")
    f["plated"] = "+".join(plated) or "file name only"
    f["tools"] = "T codes" if re.search(r"(?m)^T\d+[CF]", text) else "no tool codes"
    f["abs"] = "G90" if "G90" in text else ("ICI" if "ICI,ON" in text else "default")
    f["g93"] = bool(re.search(r"G93", text))
    f["g05"] = bool(re.search(r"G05|G81", text))
    return f


def main():
    """!
    @brief Count the conventions per tool and print the tables.
    @return int Exit code.
    """
    g = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    d = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    nfiles = collections.Counter()
    for key, truth, folder in sets():
        for dp, _, fs in os.walk(folder):
            for fn in fs:
                p = os.path.join(dp, fn)
                if os.path.splitext(fn)[1].lower() in sm.SKIP_EXT or os.path.getsize(p) == 0 or fn in ("LICENSE", "README", "SOURCE", "_SOURCE.txt"):
                    continue
                raw = open(p, "rb").read(200000)
                text = cp.normalise(raw) if len(raw) < 8192 else raw.decode("latin-1").replace("\r\n", "\n").replace("\r", "\n")
                scope = cp.file_scope(fn, text[:cp.HEAD_BYTES])
                if scope == "gerber":
                    for k, v in gerber_facts(text).items():
                        g[truth][k][v] += 1
                    nfiles[(truth, "gerber")] += 1
                elif scope == "drill":
                    for k, v in drill_facts(text).items():
                        d[truth][k][v] += 1
                    nfiles[(truth, "drill")] += 1
    print("### Gerber files (count of files with each value)\n")
    keys = ["unit", "fs", "x2_ff", "x2_gen", "to_c", "aperfn", "g54", "g36", "g75", "eof", "lp_clear", "ab_lm"]
    print("| tool | files | " + " | ".join(keys) + " |")
    print("| :-- | --: | " + " | ".join(":--" for _ in keys) + " |")
    for t in sorted(g):
        cells = []
        for k in keys:
            c = g[t][k]
            if k in ("x2_ff", "x2_gen", "to_c", "aperfn", "g54", "g36", "g75", "lp_clear", "ab_lm"):
                cells.append("%d" % c.get(True, 0))
            else:
                cells.append(", ".join("%s %d" % (a, b) for a, b in c.most_common(3)))
        print("| %s | %d | %s |" % (t, nfiles[(t, "gerber")], " | ".join(cells)))
    print("\n### Drill files\n")
    dk = ["unit", "zeros", "fmat", "plated", "tools", "abs", "g93"]
    print("| tool | files | " + " | ".join(dk) + " |")
    print("| :-- | --: | " + " | ".join(":--" for _ in dk) + " |")
    for t in sorted(d):
        cells = []
        for k in dk:
            c = d[t][k]
            cells.append(("%d" % c.get(True, 0)) if k == "g93" else ", ".join("%s %d" % (a, b) for a, b in c.most_common(3)))
        print("| %s | %d | %s |" % (t, nfiles[(t, "drill")], " | ".join(cells)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
