# Text for the project documents ((from the review of the via fill))

`docs/` of this branch equals `develop` and is not edited here. When the next documents branch off `develop` is made, fold these corrections in. Every number is printed by `research/via-fill/scripts/study_via_model_checks.py` or `study_via_fill.py` (README sections 4 and 7).

## `docs/validation.md` section 18 (What fills a via barrel)

* Replace the second bullet by: "On the example board (3 × 3 vias of 0.3 mm under U1, FVM at 0.5 mm): open 85.87 °C, resin 85.87 (−0.01 K), conductive paste 85.70 (−0.18 K), copper fill 81.98 (−3.89 K). All five models order the fills the same way (`test_via_fill.py`) but not with the same size: the copper-fill gain is −3.9 to −4.6 K in the FVM, FDM and 3D solid (0.5 and 1 mm cells) and −6.3 to −7.0 K in the Lumped and Analytic models. On a via-array board solved independently with the barrels drawn at their real size (`research/via-fill` README 7.3) the gain is −4.45 K: FVM, FDM and 3D solid within 0.1 to 0.3 K at 0.5 to 1 mm, Lumped and Analytic 35 to 52 % too large. Below 0.5 mm the FVM gain shrinks by 0.3 to 0.4 K at every halving of the cell (the via is a point in one cell)."
* First bullet: "the textbook figure for this barrel" → "the closed form for this barrel (0.3 mm drill, 25 µm plating, 1.6 mm, 385 W/mK), as stated by the thermal-via article (192 °C/W per via, 12 K/W for 16)". Inside the program the barrel crosses only the dielectric gaps (1.46 mm on the example board, 175.6 K/W): the copper layers are plane copper.
* Third bullet: "the 0.5 to 1 mm via-in-pad resistance of the solder" has no meaning; write "the solder of a via-in-pad (and solder wicking into an open via)".
* First paragraph: "another source quotes up to 16, silver-filled epoxy 3 to 15" is in none of the three cited pages (checked 2026-10-25); remove it or mark it "source not recorded". ALLPCB quotes 1 to 3 W/mK for "epoxy" without saying which; JLCPCB quotes "approaching 400" for electroplated copper.

## `docs/validation.md` section 2.1 (Against the grid)

"The FVM rises monotonically to its limit (within 0.2 % from 1 mm; ...)" → "The FVM rises monotonically (0.06 K from 1 to 0.5 mm, 0.08 K from 0.5 to 0.25 mm). It has no limit: without the vias the board settles (94.67, 94.71, 94.72 °C at 1, 0.5, 0.25 mm), with them a via in one cell adds a constriction that grows as the cell shrinks (a point source acts like a hole of radius 0.198 Δx; for a 0.3 mm via the right cell is about 0.5 to 0.8 mm). See `research/via-fill` README 7.3."

## `docs/theory.md` sections 2 (FVM), 3 (FDM) and 4 (3D solid)

* Section 2, "A via is assigned to the cell that contains its centre (it is a point feature; this costs about 0.5 % against the 3D rods on the example board)": add "On cells finer than about 0.5 mm the point via over-constricts: the copper-fill gain of a via array falls from −4.4 K at 0.5 mm to −3.3 K at 0.0625 mm against −4.45 K for resolved barrels (`research/via-fill` README 7.3)." The "0.5 %" was measured at one cell size only. Section 3 (FDM, via on the nearest node): the same remark.
* Section 4, `a_via`: add "clipped at 1 per cell, so a via whose copper-equivalent area exceeds the cell (a 0.3 mm copper fill below 0.27 mm cells, a 0.5 mm copper fill below 0.44 mm) loses the excess".
* The `A_via` formula of section 1.2 is right; add that `D` is the **drill** diameter (plating inside it).

## `docs/models.md` section 1 (vias) and the user guide

* `d_v` in the `A_via` formula is the drill diameter (the plating is inside it).
* The tooltip of the via diameter (`gui/tips.py`) and the docstring of `Via.diameter` say "finished hole": see `research/via-fill/INTEGRATION.md` 3 (a finished hole of 0.3 mm is a 0.35 mm drill: 15 % less resistance open, 27 % copper-filled).

## `docs/roadmap.md`, "What we want to implement"

* "Via as a disc, not a point: Peaceman well index or spreading over the cells of the disc in the FVM and FDM, and no per-cell clip in the 3D solid, so that boards with vias converge with the cell (`research/via-fill/INTEGRATION.md` 1 and 2)."
* "Lumped and Analytic: vias 35 to 52 % too effective on a via array under a part (the copper-fill gain), measured against an independent solver (`research/via-fill` README 7.3)."
