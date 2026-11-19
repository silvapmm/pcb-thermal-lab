# Audit leftovers (items e9 text part and e14 of the 2.9.0 plan)

Source: `releases/2.8.0/audit/FINAL.md` 4.4, `releases/2.8.0/plan-resume/PLAN.md` row 'Warning and label wording', `releases/2.8.0/final-review/PART_2B.md`. Each row was filled by reading the tree of `development` b49ed14d. Branch `fix/audit-leftover-texts`.

| item | state on b49ed14d | what this branch did |
| :-- | :-- | :-- |
| `tests/test_analytic_perlayer.py` quotes -4.07 to +0.06 % | done in 2.8.0 (docstring gives -4.91 to -0.01 %) | nothing |
| `tests/test_maximum_principle.py` cold spot '8 to 14 K' | done in 2.8.0 (5.5 to 12.8 K) | nothing |
| `memory.VIA_CELLS_REF` comment against theory 2.7 | done: comment, constant and theory 2.7 agree (63 % at 500 cells, 25 vias = 80 to 100 cells) | nothing |
| `gerber/parts.py` '0402 to 1206' | done (reads 0201 to 1206, as the table) | nothing |
| validation 4.1 note with the -4.91 % of the 48 boards | done in 2.8.0 (note of the final review, line of 4.1) | nothing |
| `docs/models.md` 2.3 'thin heaters +9.5 %' | done (+8.4 %) | nothing |
| guide copper-fill gain sentence (via item of `help/index.html`) | open: '4.3 to 4.7 K (FVM 4.2 K)' against validation 18.1 (FVM 4.07 to 4.25, Analytic 4.23 to 4.32, Lumped 4.46 to 4.72 K at 0.5 to 1 mm) | fixed: '4.2 to 4.7 K (FVM 4.1 to 4.3 K)' |
| validation 12 A and B prose | open: the prose quoted the earlier tables (FDM 4 % low, L 6.5 % low, rise grows 34 %, 102.5 / 69.8 K) | fixed: rewritten to the numbers of tables A and B, re-run for this check (`stackup_outline_study.py`, 18 s, the tables print the same digits) |
| validation 29.2 body columns | open: still 5fc91430 values, before section 51; needs the 4.6 min `study_jedec_board_readings.py` run | not done (a measurement, not a text) |
| split of the 3D columns of `validation_study.py` from the program columns | open (code of a study) | not done: not text |
| bottom-face Rayleigh warning says 'turned down' also for a board colder than the air | open (`api.py`) | fixed: wording names the bottom face and says a colder board uses the face-up law |
| calculator point label '1 mm around the part' | open (label, `help/calculator.html`, `help/index.html`, `docs/calculators.md`) while the band is 0.5 to 1.5 mm | fixed: 'Board temperature 0.5 to 1.5 mm around the part (ring)' everywhere |
| coarse-cell time to 63 % in the 'only N cells wide' warning | open | fixed: one sentence (+26 % for a 6 mm part at a 2 mm cell with the edges at mid-cell, -10 % with the edges on cell lines, both against the same board at 0.5 mm; `research/transient-reference-boards` 4.4, `study_review_checks.py align`, re-run by the review: +25.74 / -10.10 %; the first text set the +28 % of the finite-element reference beside the -10 % of the 0.5 mm cell) in the two coarse-cell texts that give the cell advice |
| e14: Power profile message with only the 3D solid or only the FEM ticked | open (`api.py`: 'the 3D solid is steady state only') | fixed: 'the 3D solid and the FEM are steady state only, so they have no time simulation' (the phrase 'steady state only' is kept, two tests assert it) |
| convection under the source (decision 2 of the plan) | open | fixed: one sentence in the thick-plate warning and in theory 1.2c, with the limit and the margin below |
| `research/fdm-inset-edge`, `research/analytic-edge-and-transient` scripts | on their own research branches | left open: not this branch |
| laminate in the edge film of the reduced models; Analytic mode cap; via at a copper corner and via-board scripts | studies | left open: investigations |

## The margin for the convection sentence

The effect (`docs/theory.md` 1.2a to 1.2c): where a part and a face film share a face, the film of 1.2a is driven from the plate mean, not from the hotter face under the part, so it takes a fraction `h t / (2k)` of the part's flux too little and the part reads hot by about that fraction of its rise. Limit: a stated limit while that is under 0.5 % of the rise, `h t / (2k)` = 5·10⁻³, about 9.6 mm of copper at 400 W/m²K.

Checked by the review over the 23 parts on an outer layer of the regression set (the example boards included; `h` the typed coefficient or at least 20 W/m²K, plus a plain heatsink over the part centre on that face): the largest value is 9.1·10⁻⁷ (35 µm copper), about 5500 times under the limit. Any PCB copper up to 0.4 mm at 1000 W/m²K stays under 5.2·10⁻⁴ (closed form; the real boards of `pcb-library` were not loaded). A metal block does not carry the part on its film face, so the term does not apply to it.

Corrected by the review: the first text of this branch described the effect as 'the face film under the source stays in the models (the part is not taken out of it)', which is a different effect (the part covering the face), used the scale `h t / k` (1.8·10⁻⁶ for the copper, 2.9·10⁻⁴ for the 3 mm aluminium block of `finned_block`) and put the limit at about 4 mm of copper. The 4 mm came from the earlier reviewer's answer (`releases/2.8.0/fem-model/DECISIONS_REVIEWER.md`, decision 2), which wrote 'more than 4 mm' for `h t / (2k)` > 5·10⁻³; that is 9.6 mm. The sentence 'under 0.5 % up to about 4 mm' was true but not the limit.
