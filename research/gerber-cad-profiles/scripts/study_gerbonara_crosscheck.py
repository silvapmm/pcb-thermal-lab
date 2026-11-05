#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_gerbonara_crosscheck.py
@brief Review: does an independent tool (gerbonara's own generator guess) name the same program as our detector, set by set?
@details gerbonara (Apache-2.0, installed in `.venv-research`) guesses the generator of a set from the file names and a few header
         regular expressions (`layer_rules.MATCH_RULES`, `layers._best_match`). It was written by another author for another purpose
         and shares none of the rules of `lib/cad_markers.json`, so it is an independent reference for the tools both know (KiCad,
         Altium, gEDA, DipTrace, Target 3001, Allegro/OrCAD, EAGLE, Siemens, PADS, Zuken). It is name based, so where it disagrees the
         question is which one is right; the truth column is the source of the set (as in `study_markers.py` and `study_heldout.py`).
         Run from the repository root: `.venv-research/bin/python research/gerber-cad-profiles/scripts/study_gerbonara_crosscheck.py`.
"""
import copy
import os
import pathlib
import sys
import warnings

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import cadprofiles as cp  # noqa: E402
import study_markers as sm  # noqa: E402

# gerbonara generator key -> our profile key (tools gerbonara does not know are not compared)
GB_TO_OURS = {"altium": "altium", "kicad": "kicad", "geda": "geda", "diptrace": "diptrace", "target": "target3001", "orcad": "allegro",
              "allegro": "allegro", "eagle": "eagle", "siemens": "xpedition", "pads": "pads", "zuken": "zuken"}
KNOWN = set(GB_TO_OURS.values())


def gerbonara_guess(paths):
    """!
    @brief gerbonara's generator guess for a list of files (names and header regular expressions only, no parsing).
    @param paths  List of absolute file paths.
    @return tuple (generator key or "none", certain flag as a string).
    """
    from gerbonara import layer_rules, layers
    rules_backup = copy.deepcopy(layer_rules.MATCH_RULES)
    try:
        files = [pathlib.Path(p) for p in paths]
        # apply_rules pops "header regex" from the dict it is given: work on a fresh copy every time
        layers.MATCH_RULES = copy.deepcopy(rules_backup)
        certain_any = None
        for gen, rules in layers.MATCH_RULES.items():
            try:
                certain, cand = layers.apply_rules(files, rules)
            except (UnicodeDecodeError, OSError):
                certain, cand = False, {}
            if certain:
                certain_any = gen
                break
        layers.MATCH_RULES = copy.deepcopy(rules_backup)
        if certain_any:
            return certain_any, "certain"
        try:
            gen, cand = layers._best_match(files)
        except (UnicodeDecodeError, OSError, IndexError):
            return "none", "error"
        return (gen if cand else "none"), "by names"
    finally:
        layer_rules.MATCH_RULES = rules_backup
        layers.MATCH_RULES = copy.deepcopy(rules_backup)


def set_files(root):
    """!
    @brief Gerber, drill and support files of a set (the same walk as the marker study, archives and pictures left out).
    @param root  Folder (absolute).
    @return list Paths.
    """
    out = []
    for dp, _, fs in sm.walk(root):
        for f in fs:
            if os.path.splitext(f)[1].lower() in sm.SKIP_EXT or f.startswith("_SOURCE"):
                continue
            out.append(os.path.join(dp, f))
    return out


def main():
    """!
    @brief Print one row per set: truth, our detection, gerbonara's guess, agreement.
    @return int Exit code.
    """
    warnings.simplefilter("ignore")
    rows = [(rel, truth) for rel, truth, _ in sm.ROOTS]
    held = os.path.join(sm.DATA, "heldout")
    if os.path.isdir(held):
        rows += [("heldout/" + d, d.split("__")[0]) for d in sorted(os.listdir(held)) if os.path.isdir(os.path.join(held, d))]
    table = cp.load_table()
    print("| set | truth | ours | gerbonara | gerbonara basis | gerbonara right | ours right |")
    print("| :-- | :-- | :-- | :-- | :-- | :-- | :-- |")
    n_cmp = n_gb = n_ours = 0
    for rel, truth in rows:
        root = os.path.join(sm.DATA, rel)
        if not os.path.isdir(root):
            continue
        paths = set_files(root)
        det = cp.detect_set(cp.read_heads(paths, root), table)
        gb, basis = gerbonara_guess(paths)
        gb_ours = GB_TO_OURS.get(gb, gb)
        if truth in KNOWN:
            n_cmp += 1
            n_gb += gb_ours == truth
            n_ours += det.profile == truth
            print("| %s | %s | %s (%s) | %s | %s | %s | %s |" % (rel, truth, det.profile, det.confidence, gb, basis,
                                                               "yes" if gb_ours == truth else "NO", "yes" if det.profile == truth else "NO"))
        else:
            print("| %s | %s | %s (%s) | %s | %s | (tool unknown to gerbonara) | %s |" % (
                rel, truth, det.profile, det.confidence, gb, basis, "yes" if det.profile == truth else "NO"))
    print("\nsets of tools gerbonara knows: %d; gerbonara right %d, ours right %d" % (n_cmp, n_gb, n_ours))
    return 0


if __name__ == "__main__":
    sys.exit(main())
