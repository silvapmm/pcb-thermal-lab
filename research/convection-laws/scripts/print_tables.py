#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file print_tables.py
@brief Print, as Markdown tables, the numbers of the README of this folder from the JSON files that the studies write to out/ (so that the README is a copy of a printout, not of memory).
@details Tables: the cavity benchmark, the strip in cold boxes, the 17 boards (hottest rise and change for each pair of laws, with radiation, convection only, double and half power),
         the summary by pair. Usage: .venv/bin/python research/convection-laws/scripts/print_tables.py
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
LEVELS = ["RH+program-down", "RH+GL", "RH+FI", "Jaffer"]


def load(name):
    """!
    @brief Read a JSON file of out/.
    @param name File name.
    @return Parsed JSON or None when missing.
    """
    p = os.path.join(OUT, name)
    return json.load(open(p)) if os.path.exists(p) else None


def plate_rows():
    """!
    @brief The rows of the strip sweep from every out/plate_mac*.json, without repeats (same faces, Ra, box scale and resolution).
    @return list of dict.
    """
    seen, rows = set(), []
    for name in sorted(f for f in os.listdir(OUT) if f.startswith("plate_mac") and f.endswith(".json")) if os.path.isdir(OUT) else []:
        for r in load(name) or []:
            key = (r.get("faces", "both"), r["ra"], r["s"], r["fine"])
            if key not in seen:
                seen.add(key)
                rows.append(r)
    return rows


def main():
    """!
    @brief Print every table that has its input.
    @return None.
    """
    cav = load("cavity.json")
    if cav:
        print("| Ra | cells | Nu hot wall | Nu cold wall | de Vahl Davis | error | max u on x = 0.5 (ref) | max v on y = 0.5 (ref) |\n| --: | --: | --: | --: | --: | --: | --: | --: |")
        refu, refv = {1e3: 3.649, 1e4: 16.178, 1e5: 34.73}, {1e3: 3.697, 1e4: 19.617, 1e5: 68.59}
        for r in cav:
            print(f"| {r['ra']:.0e} | {r['n']}{'' if r['ratio'] == 1.0 else ' graded ' + str(r['ratio'])} | {r['nu_hot']:.4f} | {r['nu_cold']:.4f} | {r['reference']} | {r['error_pct']:+.2f} % | "
                  f"{r['umid_max']:.2f} ({refu[r['ra']]}) | {r['vmid_max']:.2f} ({refv[r['ra']]}) |")
    pl = plate_rows()
    if pl:
        print("\n| faces hot | Ra | box s | grid | Nu up | Nu down | balance | converged | max u | steps |\n| :-- | --: | --: | :-- | --: | --: | --: | :-- | --: | --: |")
        for r in pl:
            print(f"| {r.get('faces', 'both')} | {r['ra']:.0e} | {r['s']:g} | {r['nx']} x {r['ny']} | {r['nu_up']:.3f} | {r['nu_down']:.3f} | {r['balance']:.3f} | {r['converged']} | {r['umax']:.1f} | {r['steps']} |")
    be = load("board_effect.json")
    if be:
        for tag, title in (("rad", "with radiation"), ("conv", "convection only (emissivity 0)"), ("p2", "double power"), ("p05", "half power")):
            print(f"\nHottest rise of the program (K) and change for each pair, {title}:\n\n| board | program (K) | " + " | ".join(LEVELS) + " |\n| :-- | --: | " + " | ".join("--:" for _ in LEVELS) + " |")
            for r in be:
                a = r[f"{tag}|program"].get("rise")
                cells = []
                for lv in LEVELS:
                    b = r[f"{tag}|{lv}"].get("rise")
                    cells.append("n/a" if not (a and b) else f"{100 * (b / a - 1):+.1f} %")
                print(f"| {r['board']} | {a:.2f} | " + " | ".join(cells) + " |")
            print("| **min / max / mean** | | " + " | ".join(
                "{:+.1f} / {:+.1f} / {:+.2f} %".format(*(lambda v: (min(v), max(v), sum(v) / len(v)))([100 * (r[f'{tag}|{lv}']['rise'] / r[f'{tag}|program']['rise'] - 1) for r in be if r[f'{tag}|{lv}'].get('rise') and r[f'{tag}|program'].get('rise')])) for lv in LEVELS) + " |")


if __name__ == "__main__":
    main()
