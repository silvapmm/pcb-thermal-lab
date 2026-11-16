# Final code-against-theory review of 2.8.0, part 2a: `docs/theory.md` chapters 9 to 12 and `docs/models.md`

Scope: the parts and the junction temperature (9, 9.1), the power profiles and the fast waves (10, 10.5), the verification summary (11), the references (12) of `docs/theory.md`, and the whole of `docs/models.md`, read against `pcbthermal/analysis.py` (`heater_stats`, `part_split`, `_ring_mean`), `api.py` (`SolverOptions`, `_solve_with_tc`, `_top_path_split`, `_part_warnings`, `_run_profiles`, `response_cell_mm`, `suggest_cell_mm`, `_solve_computed_h`), `model.py` (`Heater.junction_theta`, `top_resistance`, `has_top_path`, `interface_kcm2`, `combine_sheets`), `profiles.py`, `stackimpedance.py`, `blocks.py` (what models.md 2.6 states), `inverse.py`, `jobs.py`, `gui/compute.py`, `checks.py` (the warnings the two documents quote), `fileschema.py`, `package.py`, `cli.py`, `gerber/parts.py`, `data/defaults.json`, `data/stackups.json`. Tree: `development` da16d80f. Branch `docs/final-review-2a`; documents only, nothing in `pcbthermal/` or `tests/` was edited. The audit files of `releases/2.8.0/audit/` (REVIEW_A1, A4, A5, L1L5, DECISIONS) were the list of superseded values to look for; `papers/notes/SOURCE_MAP_AUDIT.md` (local library) was read for the source statuses.

## Method

Each statement was compared with the function that implements it; one numeric example per section was recomputed with a light script (scratch, private `PCBTHERMAL_CONFIG`, no solve above one second, no heavy lock taken):

* (9.2): `P₀` 2 W, `R` 40 K/W, `α` 0.5 %/K gives 133.3 K (now written in the text).
* (9.3)/(9.4): the illustrative values of figure 42, case A, give `P_b = P R_top/(R_top + Θ + R_b)` = 1.212 W, `Tj − T_amb` 15.76 K, `P_top` 0.788 W (now written).
* (10.2) to (10.5): the headline case (60 × 40 mm, two layers, 10 mm part, 20 Hz, 30 %, 10 W) gives 6.3545 K from `column_for_heater(...).swing(0.05, 0.3)`, equal to the 6.355 K of `validation.md` 37.2; the Lanczos factor of `_from_coefficients` is `np.sinc(k/(N/2))` = `sinc(2k/N)` (0.63662 at `k = N/4`).
* models.md 2.4.1: `laminate.n_for_gap(1.6 mm, 0.2 mm, 8)` = 8 and `(1.6 mm, 0.1 mm, 16)` = 16, so the stated bounds were wrong.
* models.md 2: the four models through `simulate` on the example board at 1 mm (0.26 / 0.24 / 0.03 / 0.80 s, one machine).

Then every number was compared with `docs/validation.md` and the audit reviews, every cross-reference and figure was checked to exist, and the stale values of the audit were searched for.

## Verdicts

| Section | Verdict | Evidence |
| :-- | :-- | :-- |
| theory 9 (9.1, 9.2) | matches; **made explicit** | (9.1) = `part_split`; ring = `RING_INNER` 0.5 / `RING_OUTER` 1.5 mm on the bounding box, cell centres on the board, absent on a coarse grid; tolerance 10⁻⁵, 80 iterations, runaway at 1500 °C or 50 times (`_solve_with_tc`). **Added**: the Lumped `heater_peak`, the ψJB and junction with the board power under a top path, the source case (`junction_theta` = interface over the footprint), the power clipped at zero, the device temperature of the coefficient, the 80-iteration warning, the after-run warnings of `_part_warnings`, a worked example |
| theory 9.1 top path | matches; **made explicit** | `R_top` = `top_resistance` with `contact_area` and the sheet `t/k` of `interface_kcm2`; only a component with `Θ > 0` and `θSA > 0`; Illinois on `[0, P]`, Broyden "good" update from all power in the board, six halvings, 40 steps, `10⁻⁵`, best iterate, warning above `10⁻⁴` (`err <= 10 tol`); a worked example; solve counts from `validation.md` 9 and the docstring |
| theory 9 limits | **corrected** | the gap to the junction-node prototype is 0.6 to 1.4 K on the tables of `validation.md` 9 (the 0.4 to 0.8 K of the older text predates the laminate nodes, which the prototype lacks); the θJC(bot)-to-hottest-point convention of audit A5 F-086 added |
| theory 10 (10.1, decision, run) | matches; **made explicit** | `M` = 3000 (≥ 50) terms (`wave_response`); the reference model FVM, Lumped, Analytic, then FDM (`TIME_MODELS`, `_run_profiles`); one-shot tables outside the budget; at least 20 steps per window; the common period from fractions (denominator 10⁵) and the 50-times cap (`_common_period`); the 200 000-step refusal estimated on 12 windows; theta 1 or 0.5; one-shot start at its first power and its last power held |
| theory 10.5 closed form | matches; **made explicit** | `column_for_heater`, `half_admittance` (tanh form), `impedance` (`kv(1, ma)`), `_from_coefficients` (`sinc(2k/N)`, corrected by A5), `N_SAMPLES` 16384, `MIN_FILL` 0.9, `FILL_LATTICE` 16, `EXACT_COEFFICIENT_LIMIT` 4·10⁶ (about 490 rows), the raw `h_top`/`h_bottom` without the half-slab term (5·10⁻⁷), the headline swing re-computed (6.3545 K) |
| theory 10.5 items 1 to 4, limits table | matches; one number **corrected** | `FAST_STRETCH_S` 4, `FAST_STRETCH_MANY_LAYERS_S` 2, `RIPPLE_WINDOW_SAMPLES` 600, `FAST_BARE_HZ` 1, `EDGE_WAVE_PERIOD_S` 1, `RESPONSE_CELL_FLOOR_MM` 0.25 and `RESPONSE_CELL_MM` 2 now named. Near a side: 0.60 at 0.1 Hz (`validation.md` 37.2; the theory said 0.61, the number of the warning text); the half-copper row added. Four-layer node error 3.6 to 5 times and 0.13 to 0.23 at 10 Hz equal `validation.md` 37.1 and 37.3 |
| theory 11 | **corrected (five stale rows)** | solvers 7·10⁻⁹ → 4·10⁻⁹ K (`validation.md` 5, 3.9·10⁻⁹ on the example board); layered idealisation 0.1 to 0.7 % → 0.1 to 0.5 % on the four boards and the cold finite-element column of 3.1 (audit A2 2.3: FVM within about 1 % on the one-sided pad, not +2.9 %); 3D solid +8 % → +4.9 % at 1 mm against the converged reference, 'within 0.2 %' → 0.3 % (the example board −0.3 %); energy-balance row had no section (now 1, 12, 23.1); the plate row pointed at theory 7.5 only (now validation 20 and 22.1); the convection row said validation 8 for numbers that are in theory 8 (fixed). **Added** rows: fast waves (37) and the independent transient reference (7), merged with the time-stepping row |
| theory 12 | **corrected** | [Lienhard2024] lacked page 234 / PDF 248 (eq. 5.62, used in 10.5); [CarslawJaeger] lacked 10.5; [JESD51family] now says which documents are not in the library and where they matter (validation 19, 29.2); the pointer to 'section 20' of the bibliography is ambiguous (two sections numbered 20) and now names the right one and says this table wins where it is newer. `research/theory/BIBLIOGRAPHY.md` section 20: [EC1998Spreading] 'R (equations and numbers, as images)' corrected to S (numbers R, equations N, as the audit A1 RA-346 decided and the theory already said); [Lienhard2024] given the pages of the audits |
| models 1 | matches | the sheet, the via area, the via fills (`libraries.via_fills`: 0.3 / 8 / 385 W/mK) |
| models 2 (table) | **corrected** | the Analytic transient was 'vias calibrated per heater', replaced in 2.6.0 by the coupled block of modes; a row of re-measured times added (the 0.13 / 0.12 s / 10 ms / 0.4 s are kept as the earlier solve-only figures) |
| models 2.1 | matches | harmonic face, `lu_factor`, Auto = a quarter of the smallest heater (`suggest_cell_mm`, 0.25 to 2 mm, 1 mm cap with imported copper) |
| models 2.2 | **corrected** | the copper edge across a heater: FDM −1.3 % at 1 mm in `validation.md` 2 (2.7.1), not 1.9 %; 'about 0.1 %' bounded by 0.5 % |
| models 2.3 | **corrected** | thin heater +9.6 % (not +9.5), the copper edge −29.8 % added (`validation.md` 2) |
| models 2.4 | **corrected** | the Analytic with an edge across the heater is −27.9 % (`validation.md` 2), not 25 % |
| models 2.4.1 laminate options | **corrected** | the sub-gap bounds (`n_for_gap`: 8 needs `S_MAX` below `d/7` = 0.229 mm, 16 below `d/15` = 0.107 mm; the old '0.19 / 0.09 mm or less' were sufficient values); the same error corrected in theory 1.4 by part 1a. Ranges 0.05 to 5 mm and 1 to 16 = `SolverOptions.__post_init__` |
| models 2.5 | matches | guidance only |
| models 2.6 metal block | **corrected** | the contact and exposed-face formulas lacked the half-slab terms of `fix/face-film-half-slab` (`blocks.extra_layers`: `R'' + t/(2k) + t_cu/(2k_cu)` over copper, `+ d/k_gap` over laminate, exposed `h_exp/(1 + h_exp t/(2k))`); 'FR-4' replaced by the gap next to the face; the table said 'compared with the 3D solid within 1.8 %' for the finite-element solid |
| models 2.7 | matches | part 1a verified the slab rule and the memory figures |
| models 3, 4b, 4c | matches | `check_problem`, `check_model_limits`, `check_thick_plates`, `memory.check` (part 1a) |
| models 4 | **corrected** | reference model includes the FDM; the response cell is 0.25 mm up to `max(cell, 2 mm)`, coarser for the memory |
| models 5, 18 | matches | `convection.py` laws, `UP_LIMIT` 1e7, eq. 8.35, Re 5e5, 0.01 W/m²K and at most 30 Picard steps; the ratio 0.88 Ra^(−1/20) (0.62 at 1e3, 0.49 at 1e5) recomputed |
| models 6 | **corrected** | the interface of the top path is divided by `contact_area` or the footprint (the table said the footprint); the prototype gap 0.6 to 1.4 K; the 'Not in this version' list aligned with `versions.md` Planned (an interface of its own area exists only as `contact_area`) |
| models 7 | **corrected** | `transient` takes `--model fvm|fdm|analytic`; the other options exist in `cli.py` |
| models 8.1, 8.2 | matches; one detail **added** | the loading bounds `MAX_COORD_MM` 1e6 mm and `MAX_NUMBER` 1e100 (`fileschema.py`); package limits = `package.py` constants |
| models 8b | **corrected** | the simple stack-up row 'slab thickness/N' was stale since 2.7.0 (the same table said the opposite two lines below); the dielectric presets: the library notes mark all of them 'no source' except the FR-4 0.3 through-thickness (second hand), so 'agree with vendor data' was reworded |
| models 9 | matches | outline treatment (part 1a) |
| models 10 | **corrected** | `junction` was listed twice; 'top' refused with a top path (`power_from_temperature`) |
| models 11 | matches | `spawn`, terminate then kill after 5 s (`gui/compute.py`) |
| models 12, 17 | matches | `stackups.json` templates, `combine_sheets` formulas; films 10 / 15 / 10 W/m²K of `defaults.json` `new_board` documented as program defaults without a source |
| models 13, 15, 16 | matches | `INTERFACES` presets (0.33 / 0.5 / 1.67 / 5 / 10 K·cm²/W from thickness over conductivity), `heatsinks` θSA list, fin ratio 4.7 / 8.3 and the block table of `validation.md` 12 D |
| models 19 to 19.4 | **corrected** | 19.1 still said 'This version has no import dialog'; 19.2 envelope list (`parts.envelope`: 0201 to 1206, SOT-23, the SOP family, a body grown by 0.8 / 1.6 mm) and the 0.3 mm tolerance sentence (it read '0.5 mm is not exceeded'); the JEDEC numbers of the exposed pad brought to `validation.md` 29.2 (32.2 / 42.4 / 48.5 K/W at 1 mm; 27.6 to 36.4 K/W) |
| validation 9 (evidence of theory 9) | **corrected** | CSD17308Q3 RθJA 47.1 K/W at 0.5 mm after `fix/drawn-copper-faces` (`docs/calculators.md` 2.1 −2.4 %; the −1.4 % of the audit was the tree before that branch) |

Every figure the two documents link exists; every `validation.md` section they cite exists.

## Items (program, tests, research scripts; not edited here)

1. **Fast-wave warning texts** (`checks.check_fast_wave`, `checks.py` around lines 386 to 440): near a side '0.61 at 0.1 Hz' against 0.60 in `validation.md` 37.2; bare laminate 'about 0.75 at 1 Hz' against 0.73, and '2.4 times too large at 1 kHz' while the bare-laminate range reaches 4.1. Text only, no frozen number moves.
2. **Figure 22 is stale** (`research/theory/scripts/make_diagrams.py`, `ladder`, around line 761): '2e-8 K', 'convection correlations 1 to 3 %' (the audit T-166 called that misleading), 'FVM 0.4 to 2.2 %', '±4 %' on a heater-sized pad. The caption now says so; regenerate with the numbers of the table of theory 11 and look at it. No number of the program moves.
3. **`gerber/parts.py` module docstring** (line 13) says '0402 to 1206'; `_PASSIVE` starts at 0201. Docstring only.
4. **`stackimpedance.column_for_heater` uses the typed `h_top`, `h_bottom`** and not `Board.face_film_h`: a 5·10⁻⁷ difference for 35 µm; recorded in the theory as a stated simplification; aligning it would move no frozen number (the frozen boards have no fast wave) but changes the closed form in the last digits.
5. **`validation.md` order**: section 49 is placed after 51; the bibliography has two sections numbered 20. Documents of other owners; renumbering moves every citation, so left as a question.
6. **The plate check by `blocks.py`** lives in `validation.md` 20 as one sentence; the audit A1 proposal of a regression test (T1, Seri Lee through `blocks.py`) is not in `tests/` yet.

No item moves a frozen number; no mismatch of physics between the code and the theory was found in chapters 9 and 10.

## Trust level per chapter

* **9 parts: high.** The equations, constants and the root finding are the code's; the closed form and the exact root are tested; the convention (hottest point plus `Θ`) is on the safe side and now stated with its size.
* **10 profiles: high** for the decision, the run and the closed form (re-computed to the digit); **medium** for the fast-wave limits near sides, with vias and on bare laminate, which rest on the reviewer's 3D references of the research folder (not re-run here) and on no measurement.
* **11 verification summary: medium-high** after the corrections; the finite-element rows rest on the audit's converged references; the figure is stale (item 2).
* **12 references: high** for the statuses (aligned with the audits and the local source map); the bibliography's own section 20 had two stale rows, now corrected.
* **models.md: medium-high.** Fourteen sections had stale numbers or stale statements, all corrected against the code and `validation.md`; the timing row is of one machine.

## What was not verified

* The 3D and finite-element references behind 10.5 and 11 were not re-run (their numbers are those of `validation.md` 3, 3.1, 37 and the audit A2); the decision table of 3168 cases was not re-run.
* `models.md` 2.4.1 one-layer numbers, 2.7 timing and 4b block-flux figures were checked for consistency with `validation.md`, not re-run (part 1a covered the code).
* The GUI statements of `models.md` 8 and 19.4 (window behaviour) were read against the code names only, not driven.
* The heatsink catalogue values (`heatsinks` θSA) were compared with `defaults.json`, not with the vendor pages.
