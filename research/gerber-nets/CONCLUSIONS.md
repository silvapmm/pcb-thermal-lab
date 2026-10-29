# Conclusions, phase 3: nets with voltage and current

Maturity: early (a prototype and a design, not yet joined to a thermal run); the direction is good. Written on branch `research/gerbers` (phase 3 of three of the Gerber research, split from one study: `research/gerber-import`, `research/gerber-models`, `research/gerber-nets`; the section numbers 4.1 to 4.50 are those of the original study; the sections of this folder are listed in `README.md`, the map of all of them in `gerber-import/README.md`, chapter "Where the sections are"). Everything quoted here has a section of `README.md` (numbers, tables, limits), a script (`scripts/`) and, where it is a claim that can break, a test (`tests/`, 18 tests in about 1 s; `cd research/gerber-nets && python -m pytest -q tests`). Nothing in `pcbthermal/` was changed, and no code of the electrical side exists there. The independent review is README section 7.

**Scope**: this file concludes on nets with a voltage and a current (Joule heat, tracks at any angle, separate pieces, sources, sinks and links). Where the net of a piece of copper comes from is concluded in [`../gerber-import/CONCLUSIONS.md`](../gerber-import/CONCLUSIONS.md), the copper in the thermal models in [`../gerber-models/CONCLUSIONS.md`](../gerber-models/CONCLUSIONS.md).

## 1. Where we stand

![A track as squares of copper](figures/fig_08_track_in_squares.png)

*Figure 8: a track as a row of squares of sheet resistance, and what the electrical side must be given.*

![Where the power goes](figures/fig_09_where_the_power_goes.png)

*Figure 9: a source, a link and a load; the link carries the whole current.*

1. **Nets and Joule heat are feasible**: the net comes from the file (pads and tracks; zone fills may carry none, so use connectivity; `gerber-import` README 4.29), and `joule.py` turns a current into a heat map that sums exactly to I²R (README 4.20); the solver meets the closed forms of a strip, an L bend (0.559 squares at the corner) and a ring sector, converging at first order with the pixel (README 4.41).
2. **Tracks at any angle on the pixel grid**: area exact except at 45 degrees on the lattice (±6 %) and where the edges fall on the pixel centres; a track as narrow as the pixel breaks into pieces with 4-connectivity (not with 8); the five-point stencil is up to 2 times too resistive on a tilted 1.5 to 2 pixel track and 6 % at 12 pixels across, the nine-point 4 % (4.23); on a thin curved track both stencils are equally high (README 4.41).
3. **Separate pieces of one net** (4.36): on the Stormduino `+5V` and `+3V3` are two pieces each and the USB shield four, in the CAD file as well as in the Gerbers; pieces of one net are joined outside the copper (a header, a jumper, a bead, a fuse, a shunt, or a route left unfinished). The Joule heat of a piece is the I²R of the current that flows in its copper; the **voltage of a net carries no current**, so the input is a **current per pad** (or a power and a voltage), and a piece with no source or load pad has no current and no heat.
4. **Links matter more than copper** (4.40): in the prototype a 0.1 ohm link between two pieces of a 1.5 A rail makes 225 mW, 18 times the 12 mW of all the copper; the energy balance closes to 0.0004 mW in 7.5 W and the load voltage equals the series circuit of the pieces to 0.3 µV (the load, V at its pad times the current, is the power of the IC). The return current in the ground copper is not modelled.
5. **How it could enter the application** (`INTEGRATION.md`): a `Problem.electrical` with terminals, `vsource`, `isink` and `link` and a current and net on the part; the heat added to the thermal grid as a source; vias, regulators and ratings are open.

## 2. The validated numbers

| Claim | Number | Where | Test |
| :-- | :-- | :-- | :-- |
| Track at any angle: area within 0.5 % except 45° on the lattice (±6 %); 4-connectivity breaks a track as narrow as the pixel, 8-connectivity does not | | 4.23 | `test_thin_track_at_an_angle_connectivity_area_and_resistance`; `research/gerber-import/tests/test_reader_claims.py::test_a_track_as_wide_as_the_pixel_can_vanish_on_the_lattice` |
| Resistance of a tilted track, five-point stencil: +97 % at 1.5 px, +10 % at 8 px, +6 % at 12 px across | | 4.23 | same, `study_angles.py` |
| Joule heat of a net: strip, series, parallel, conservation (also into cells of any size) | exact to 1e-9 | 4.20 | `tests/test_joule.py` |
| Closed forms: L bend (0.559 squares at the corner), ring sector `Rs θ / ln(ro/ri)`; nets VIN and S1 against their hand counts | +0.06 % at 20 px; 2.1 % at 80 px, first order; 32.3 against 32.2 mΩ; S1 extrapolates to 109.8 mΩ | README 4.41 | `study_references.py`, `tests/test_references.py` |
| Prototype with a source, a sink and a link: energy balance | source 7499.999 mW = copper 12.3 + link 225.0 + load 7262.7 mW (difference −0.0004 mW) | 4.40 | `study_pdn_links.py`, `tests/test_pdn.py` |
| Strip resistance equals its squares (four-point stencil), floating copper carries nothing, link carries the whole current, a sink with no source is refused | within 2 % / exact / exact | 4.40 | `tests/test_pdn.py` |
| Network: series circuit of the pieces, current split of two strips | 0.3 µV; 1.000000 and 2.000000 A | README 4.41 | `tests/test_references.py` |
| Electro-thermal loop on a lumped track, constant current | fixed point = closed form; converges with ratio `α Rth I² R20`, runaway when it reaches 1 | README 4.41 | `tests/test_references.py` |
| Our IC board: arc net resistance within +15 % of the hand count, heat equal to I²R | 119 mohm against 110 mohm of 229 squares | 4.30 | `tests/test_our_board_nets.py` |

## 3. What is not validated, and the limits

* **No comparison with a physical measurement** (a current, a temperature or a voltage drop of a real board).
* One layer at a time; vias between layers, the return current in the ground net, regulators, time dependence and ratings are not in the prototype; the resistivity rising with temperature is checked only on a lumped track (README 4.41).
* Copper resistivity 1.68e-8 Ω m (pure copper; the annealed standard to which 0.393 %/K belongs is about 2.6 % higher; plated outer copper is thicker than 35 µm): from memory, not checked against a source.
* The heat of the copper was not added to a thermal run here (the way is `joule.to_cells` and the source term of phase 2's network).
* The conduction stencil: four-point (exact for axis-aligned copper) or nine-point (better for wide tilted tracks, 20 % too resistive on a 2 pixel strip).
* How other tools do it was learned from search excerpts only; nothing was read in full (4.40).

## 4. Recommendations and decisions left to the maintainer

1. **Do not infer currents from voltages**: take a current per pad from a power budget, a datasheet or a netlist; take the resistance of the links (0 ohm, bead, shunt, fuse) from part fields or a library.
2. **Order of work**: first the Joule heat of a net with given terminals (4.20) on one layer, then pieces joined by links, then vias, then the coupling with the temperature of the thermal run.
3. **Inputs**: the form of the data (an extra argument of the import, a sidecar file, a KiCad netlist plus part fields, a pads table) is left open by the maintainer to decide later.
4. **Open decisions**: whether the electrical side enters the program at all before phases 1 and 2; whether IPC-2152 checks are wanted.

## 5. How to reproduce

```
cd research/gerber-nets && python -m pytest -q tests                  # 18 tests, 1 s
.venv/bin/python research/gerber-nets/scripts/study_pdn_links.py       # section 4.40, seconds
.venv/bin/python research/gerber-nets/scripts/study_references.py      # README 4.41, seconds
.venv/bin/python research/gerber-nets/scripts/study_net_joule.py       # section 4.20 (needs data/conformance from gerber-import, gerbonara and shapely)
.venv/bin/python research/gerber-nets/scripts/study_angles.py          # section 4.23 (gerbonara and shapely)
.venv/bin/python research/gerber-nets/scripts/make_figures.py          # figures 1 to 5 (figure 1 needs gerbonara)
.venv/bin/python research/gerber-nets/scripts/make_diagrams.py         # figures 6 to 9
```
