"""!
@file component_study.py
@brief What does a Component (package) parametrisation add to a plain heater? Real parts, real datasheet numbers, three levels of detail.

@details Levels compared on the same boards (computed natural convection, FVM at 0.5 mm):
         * level 0: the **Source** (today): the power enters the board under the footprint; the answer is the hottest board point under the part;
         * level 1: Source + **one junction-to-pad resistance** (theta_JC(bottom), theta_J-L, Rth j-sp): Tj = hottest point + P theta;
         * level 2: + a **top path** (junction node joined to the footprint by 1/theta and to the air or a heatsink through the top resistance);
         * level 3 (not computed): full DELPHI / Foster chain (needs data that manufacturers do not publish).
         Datasheet numbers: NOTES.md, E6 (table of the datasheets read) and docs/models.md section 6. Values marked "assumed" are not in the datasheet.

Usage: python research/component-heatsink/scripts/component_study.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, HERE)

import package_prototype as proto                                     # noqa: E402
from pcbthermal import Problem, SolverOptions, simulate               # noqa: E402

# name: footprint (mm), power (W), theta to the pad, theta_JB (if different), psi_JB, theta_JC(top), copper um, Tj max (degC), note
# Tj max: CSD17308Q3 -55 to 150 (SLPS262C); TPS7A47 operating -40 to 125 (SBVS204G, recommended conditions); LMR36510 -40 to 150 (SNVSBD7);
# SS12 125 (SX Semiconductor sheet of NOTES.md [14]; the Vishay SS12 says 150); 0603 resistor 170, the end of its derating curve (not a junction)
PARTS = {
    "MOSFET CSD17308Q3 (SON 3.3x3.3)": dict(w=3.3, h=3.3, p=2.0, th=4.5, thjb=None, thtop=30.0, cu=71, tjmax=150, top_assumed=True),
    "LDO TPS7A47 (QFN-20 5x5)": dict(w=5.0, h=5.0, p=1.5, th=1.7, thjb=11.9, psijb=11.9, thtop=27.0, cu=35, tjmax=125, top_assumed=False),
    "Buck LMR36510 (HSOIC-8)": dict(w=4.9, h=3.9, p=0.8, th=4.3, thjb=13.6, psijb=13.8, thtop=54.0, cu=35, tjmax=150, top_assumed=False),
    "Schottky SS12 (SMA)": dict(w=4.3, h=2.6, p=0.5, th=20.0, thjb=None, thtop=60.0, cu=35, tjmax=125, top_assumed=True),
    "Resistor 0603, 0.1 W": dict(w=1.6, h=0.8, p=0.1, th=1000.0, thjb=None, thtop=2000.0, cu=35, tjmax=170, top_assumed=True),
}


def part_board(part, pad_mm, size=60.0):
    """!
    @brief A 60 x 60 mm, 2-layer, 1.6 mm board with a square copper pad under the part on both faces and thermal vias under the footprint.
    @param part Entry of PARTS.
    @param pad_mm Side of the copper pads in mm (never smaller than the footprint).
    @param size Board side in mm.
    @return Problem with the heater at the centre (power only used to build the footprint weights).
    """
    pad = max(pad_mm, part["w"] + 1.0, part["h"] + 1.0)
    p = Problem.new(size, size, 2)
    p.board.copper_thickness = [part["cu"] * 1e-6] * 2
    p.board.h_mode = "computed"
    c = size / 2
    for layer in (1, 2):
        p.add_zone(layer, rect=(c - pad / 2, c - pad / 2, c + pad / 2, c + pad / 2))
    p.add_heater(1, part["p"], rect=(c - part["w"] / 2, c - part["h"] / 2, c + part["w"] / 2, c + part["h"] / 2), name="U1")
    nx, ny = max(int(part["w"] // 1.2), 1), max(int(part["h"] // 1.2), 1)       # Thermal vias, 0.3 mm, pitch 1.2 mm, only under a big enough pad
    if min(part["w"], part["h"]) >= 3.0:
        for i in range(nx):
            for j in range(ny):
                p.add_via(c + (i - (nx - 1) / 2) * 1.2, c + (j - (ny - 1) / 2) * 1.2, 0.3)
    return p


def run(part, pad_mm, theta=None, top=None):
    """!
    @brief Tj of a part on a board at levels 0, 1 and (when a top resistance is given) 2.
    @param part Entry of PARTS.
    @param pad_mm Pad side in mm.
    @param theta Junction-to-pad resistance to use (default: the part's own).
    @param top Resistance junction to ambient through the top in K/W (None for no top path).
    @return Dict with t0 (level 0), t1 (level 1), t2 (level 2 or None), top share and the board heat transfer coefficients.
    """
    theta = part["th"] if theta is None else theta
    p = part_board(part, pad_mm)
    a = proto.solve(p, part["p"], theta, "offset", cell_mm=0.5)
    out = {"t0": a["foot_max"], "t1": a["tj"], "h": a["h"]}
    out["t2"], out["share"] = (None, 0.0)
    if top is not None:
        b = proto.solve(p, part["p"], theta, "node", top=top, cell_mm=0.5)
        out["t2"], out["share"] = b["tj"], b["top_share"]
    return out


def main():
    """!
    @brief Print the tables.
    """
    amb = 25.0
    print("A. What the junction-to-pad resistance adds (level 1 against level 0), natural convection, 60 x 60 mm board")
    print("| Part | P [W] | theta [K/W] | Pad | Level 0: board under part [degC] | Level 1: Tj [degC] | P*theta [K] | Share of the rise | Tj max |")
    print("| :-- | --: | --: | --: | --: | --: | --: | --: | --: |")
    for name, part in PARTS.items():
        for pad in (8.0, 25.0):
            r = run(part, pad)
            rise = r["t1"] - amb
            print(f"| {name} | {part['p']:g} | {part['th']:g} | {max(pad, part['w'] + 1, part['h'] + 1):g} mm | {r['t0']:.1f} | {r['t1']:.1f} | "
                  f"{part['p'] * part['th']:.1f} | {100 * part['p'] * part['th'] / rise:.0f} % | {part['tjmax']:g}{' (derating end)' if name.startswith('Res') else ''} |", flush=True)
    print("\nB. Wrong number from the datasheet: theta_JB instead of theta_JC(bottom) (pad 25 mm)")
    print("| Part | theta_JC(bot) [K/W] | Tj | theta_JB [K/W] | Tj with theta_JB | Difference |")
    print("| :-- | --: | --: | --: | --: | --: |")
    for name, part in PARTS.items():
        if part["thjb"] is None:
            continue
        a, b = run(part, 25.0), run(part, 25.0, theta=part["thjb"])
        print(f"| {name} | {part['th']:g} | {a['t1']:.1f} | {part['thjb']:g} | {b['t1']:.1f} | {b['t1'] - a['t1']:+.1f} K ({100 * (b['t1'] - a['t1']) / (a['t1'] - amb):+.0f} % of the rise) |", flush=True)
    print("\nC. Sensitivity to the theta entered (+-30 %, pad 25 mm)")
    print("| Part | Tj nominal | Tj at -30 % | Tj at +30 % |")
    print("| :-- | --: | --: | --: |")
    for name, part in PARTS.items():
        n, lo, hi = run(part, 25.0), run(part, 25.0, theta=0.7 * part["th"]), run(part, 25.0, theta=1.3 * part["th"])
        print(f"| {name} | {n['t1']:.1f} | {lo['t1']:.1f} ({lo['t1'] - n['t1']:+.1f} K) | {hi['t1']:.1f} ({hi['t1'] - n['t1']:+.1f} K) |", flush=True)
    print("\nD. A top path (level 2): bare mould (theta_JC(top) + convection on the body) and with a 12 K/W clip-on heatsink + 1 K/W paste (pad 25 mm)")
    print("   Level 2 is a junction node joined to the footprint by a uniform conductance; the node column without a top path is the same network")
    print("   with no path up, so the bare-mould and heatsink columns are compared with it (the level 1 offset is 1.4 to 3.4 K hotter by convention on these pads).")
    print("| Part | Level 1 Tj (offset) | Junction node, no top path | Bare mould Tj (heat through top) | With heatsink Tj (heat through top) | theta_JC(top) [K/W] |")
    print("| :-- | --: | --: | --: | --: | --: |")
    for name, part in PARTS.items():
        if name.startswith("Res"):
            continue
        area = part["w"] * part["h"] * 1e-6
        bare = part["thtop"] + 1.0 / (15.0 * area)
        sink = part["thtop"] + 1.0 + 12.0
        a, b, c = run(part, 25.0), run(part, 25.0, top=bare), run(part, 25.0, top=sink)
        node = proto.solve(part_board(part, 25.0), part["p"], part["th"], "node", cell_mm=0.5)["tj"]     # Same network as level 2, no path up
        tag = " (assumed)" if part["top_assumed"] else ""
        print(f"| {name} | {a['t1']:.1f} | {node:.1f} | {b['t2']:.1f} ({100 * b['share']:.1f} %) | {c['t2']:.1f} ({100 * c['share']:.0f} %) | {part['thtop']:g}{tag} |", flush=True)
    print("\nE. The psi_JB route of the program (Tj = mean board temperature in the ring 0.5 to 1.5 mm outside the body + psi_JB P), FVM at 0.5 mm, pad 25 mm")
    print("| Part | psi_JB [K/W] | T_ring [degC] | Tj psi_JB route | Tj with theta_JC(bot) | Tj with theta_JB as theta |")
    print("| :-- | --: | --: | --: | --: | --: |")
    for name, part in PARTS.items():
        if part.get("psijb") is None:
            continue
        p = part_board(part, 25.0)
        h = p.heaters[0]
        h.power, h.theta, h.psi_jb = part["p"], part["th"], part["psijb"]
        row = simulate(p, SolverOptions(models=("fvm",), cell_mm=0.5)).heater_rows()[0]
        h.theta = part["thjb"]                                      # The wrong datasheet number used as theta
        wrong = simulate(p, SolverOptions(models=("fvm",), cell_mm=0.5)).heater_rows()[0]
        print(f"| {name} | {part['psijb']:g} | {row['t_ring']:.1f} | {row['t_junction_psi']:.1f} | {row['t_junction']:.1f} | {wrong['t_junction']:.1f} |", flush=True)

if __name__ == "__main__":
    main()
