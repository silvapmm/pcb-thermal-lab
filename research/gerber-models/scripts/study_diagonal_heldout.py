"""!
@file study_diagonal_heldout.py
@brief A held-out test of the gate that decides which cells get diagonal faces (README 4.48): the thresholds and the gate were chosen on the 42 windows and the 0 and 45 degree tracks, so here they are tested, unchanged, on data they never saw.
@details Four kinds of held-out data, decided before the run (the gates are those of study_diagonal_gate.GATES, none is retuned): (1) new random windows of the same seven boards with another seed (101), disjoint in position from the 42 but from the same boards; (2) windows of layers of a board that was never used, the Allegro board (layers B, L2 and L3); (3) the cell size: the same windows with 0.5 mm and 2.0 mm cells (the gate was chosen at 1.0 mm); (4) tracks at 15, 30, 60 and 75 degrees (the gate was chosen on 0 and 45 degrees). Errors are against the nine-point pixel reference of study_diagonal.py, as in 4.48. Writes out/diagonal_heldout.json.
         Run: PYTHONPATH=. .venv/bin/python research/gerber-models/scripts/study_diagonal_heldout.py (from the repository root; about 30 minutes).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-models in order)

import json

import numpy as np

import conduction as cd
import diagonal as dg
import readers
import scenarios as sc
import study_diagonal_gate as sg
import study_track_width_angle as st
import windows
from paths import OUT

SEED = 101                    # not the seed (7) of the 42 windows
CELLS = (5, 10, 20)           # pixels per cell side: 0.5, 1.0 and 2.0 mm (the gate was chosen at 10)
ANGLES = (15, 30, 60, 75)     # degrees: the gate was chosen on 0 and 45


def new_windows(per_board=6):
    """!
    @brief Windows with a new seed on the seven boards of the 42, and on three layers of the Allegro board that was never used.
    @param per_board Windows per board or layer.
    @return list of (name, mask) pairs.
    """
    rng = np.random.default_rng(SEED)
    out = []
    n = int(round(windows.WIN / windows.PIX))
    h0, h1 = int(windows.HEATER[0] / windows.PIX), int(windows.HEATER[1] / windows.PIX)
    cases = [(b, "F") for b in windows.BOARDS] + [("alleg", k) for k in ("B", "L2", "L3")]
    for b, layer in cases:
        files = readers.board_files(b)
        x0, y0, x1, y1 = readers.box(files.get("edge"), files[layer])
        got = tries = 0
        while got < per_board and tries < 400:
            tries += 1
            ox, oy = rng.uniform(x0, x1 - windows.WIN), rng.uniform(y0, y1 - windows.WIN)
            m = readers.render(files[layer], ox, oy + windows.WIN, windows.WIN, windows.WIN, windows.PIX)
            if 0.15 <= m[h0:h1, h0:h1].mean() <= 0.9 and m.mean() >= 0.15:
                out.append((f"{b}:{layer}", m))
                got += 1
        print(f"{b} {layer}: {got} windows", flush=True)
    return out


def windows_part(items):
    """!
    @brief Error of the mean heater rise of every gate, on every window and every cell size, against the nine-point pixel reference.
    @param items list of (name, mask).
    @return dict cell size -> gate -> list of (window name, error %).
    """
    res = {n: {} for n in CELLS}
    for i, (name, mask) in enumerate(items):
        S, power, fixed, heater = sc.window_scenario(mask)
        y0, y1, x0, x1 = heater
        ref9 = dg.pixel_reference9(S, windows.PIX, power, 10.0, fixed)[y0:y1, x0:x1].mean()   # one reference serves every cell size
        for n in CELLS:
            for g, v in sg.gated_runs(S, windows.PIX, n, power, fixed, heater).items():
                res[n].setdefault(g, []).append((name, 100 * (v / ref9 - 1)))
        if i % 6 == 5:
            print(f"window {i + 1} of {len(items)}", flush=True)
    return res


def tracks_part():
    """!
    @brief The share of a track's cooling that every gate reproduces for tracks at angles the gate was not chosen on.
    @return dict "width/angle" -> gate -> share (%).
    """
    res = {}
    St0 = np.full((int(st.SIZE / st.PIX_TRUTH),) * 2, cd.S_LAM)
    p_t, f_t, _ = sc.box_scenario(St0.shape, st.PIX_TRUTH, 6.0)
    ref_none = st.heater_mean(dg.pixel_reference9(St0, st.PIX_TRUTH, p_t, 10.0, f_t))
    S0 = np.full((int(st.SIZE / 0.1),) * 2, cd.S_LAM)
    p0, f0, h0 = sc.box_scenario(S0.shape, 0.1, 6.0)
    none = sg.gated_runs(S0, 0.1, 10, p0, f0, h0)
    for w in st.WIDTHS:
        for th in ANGLES:
            layer = st.ng.Layer(st.track_text(w, th))
            _, ct = st.masks(layer, st.PIX_TRUTH)
            ref = st.heater_mean(dg.pixel_reference9(st.sheet(ct), st.PIX_TRUTH, p_t, 10.0, f_t))
            _, c01 = st.masks(layer, 0.1)
            runs = sg.gated_runs(st.sheet(c01), 0.1, 10, p0, f0, h0)
            res[f"{w}/{th}"] = {m: 100 * (1 - runs[m] / none[m]) / (1 - ref / ref_none) for m in runs}
        print(f"track width {w} mm done", flush=True)
    return res


def main():
    """!
    @brief Run the held-out windows and tracks, print the tables and write the results.
    @return None.
    """
    items = new_windows()
    w = windows_part(items)
    for n in CELLS:
        print(f"\nHeld-out windows ({len(items)}), cells of {n * windows.PIX:.1f} mm: mean absolute error (bias), worst")
        for g, v in w[n].items():
            e = np.array([x[1] for x in v])
            print(f"  {g:40s} {np.mean(np.abs(e)):5.2f} ({np.mean(e):+5.2f})   worst {np.max(np.abs(e)):5.1f}")
    print("\nOnly the Allegro layers (never used), cells of 1.0 mm")
    for g, v in w[10].items():
        e = np.array([x[1] for x in v if x[0].startswith("alleg")])
        print(f"  {g:40s} {np.mean(np.abs(e)):5.2f} ({np.mean(e):+5.2f})")
    t = tracks_part()
    print("\nShare of the track's cooling reproduced (%), angles " + str(ANGLES) + ", mean over the widths 0.15 to 0.3 mm")
    for g in next(iter(t.values())):
        print(f"  {g:40s} " + "  ".join(f"{np.mean([t[f'{wd}/{a}'][g] for wd in (0.15, 0.2, 0.3)]):5.0f}" for a in ANGLES))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "diagonal_heldout.json").write_text(json.dumps({"windows": {str(n): w[n] for n in CELLS}, "tracks": t}, indent=1))


if __name__ == "__main__":
    main()
