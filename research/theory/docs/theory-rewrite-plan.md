# Plan for the rewrite of `docs/theory.md`

This file is the working plan of the rewrite (steps 1 and 2 of the plan: decisions, move list, sources). The text of `docs/theory.md` is not touched yet: it waits for the merge of `fix/laminate-nodes`, which changes section 1.4. The plan holds the accepted contents, the structure of each model section, the notation, the **move list** (every number or history statement that leaves `docs/theory.md`, with its target, so that nothing is lost) and the reading status of the sources the theory cites.

## 1. What the rewrite is for

`docs/theory.md` should describe the models **as implemented**: the idea in one picture, the unknowns, the equations, the assembly, the solution, the limits in words, where the model is checked and the sources with their reading status. Numbers of tests, timings, sweep counts and the history of what the program used to do belong in `docs/validation.md` and `docs/versions.md`. Each model section is about 1.5 pages.

Problems of the present text (the audit):

* A. history mixed with the model ("before 2.4.5 the weight was...", "the old factor needed 2.8 to 19 times more sweeps");
* B. validation numbers inside the theory (timings, error tables, case counts);
* C. levels of detail mixed (section 2 holds the solvers, the theta method and the via theory; sections 7 and 9 are single blocks);
* D. order: 1.4 (one-layer board) cited from 1.2 before its place; the via theory sits in section 2 and is cited from 3, 4, 5, 6.1;
* E. pictures missing for most sections; the figures have three numbering schemes (fig_NN, V1 to V7, S1);
* F. sources named, not cited by key; section 12 is out of date (no Culham and Yovanovich, Bar-Cohen and Rohsenow, Saad, Peaceman, Krogh, Celik, Muzychka);
* G. duplication with `docs/models.md` and with `research/theory/topics/`.

## 2. Accepted table of contents

The headings that `tests/test_docs.py` checks stay character for character (marked T); `pcbthermal/help/index.html` says "theory section 6.1" (kept).

| Section | Contents | Figures (existing unless marked new) |
| :-- | :-- | :-- |
| header | what the document is, the **map** (board, layered idealisation, five models and the shared pieces), the table section / module / research folder / `models.md` section | **fig_38 new** (document map) |
| 0. Symbols | notation grouped by use (board, layers, heat, matrices, reduced models, convection), renamed clashes (section 4 below) | |
| 1. The physical description (T: "1." in the module table) | 1.1 continuum problem; 1.2 layered idealisation (equation (1), advanced stack-up as 1.2.1); 1.3 sources and geometry (1.3.1 rasterisation, 1.3.2 a part across the outline); 1.4 a one-layer board: the laminate nodes (**waits for `fix/laminate-nodes`**) | fig_20 (continuum), fig_01 (layers), **fig_39 new** (stack-up with slabs, half a gap on each side, gaps of different thickness), fig_21, fig_34 and fig_35 (8 x 8 cover), fig_44 new after the laminate merge |
| 2. FVM (T: `## 2. FVM`) | 2.1 unknowns and faces; 2.2 system; 2.3 solvers (direct, CG, SOR with Young's omega and block SOR); 2.4 time (theta method, stages); 2.5 accuracy; 2.6 the via on the grid | fig_02, fig_07 (theta), SOR figure S1, V1 to V4 |
| 3. FDM (T: `## 3. FDM`) | node-centred layout, a two-column table FVM / FDM (where the data live), vias on node footprints | fig_03; fig_40 new only if fig_03 lacks the data-location comparison |
| 4. 3D solid (T: `## 4. 3D solid`) | slabs, cell materials (via footprint rule), conductances, size limit as a statement (`MAX_CELLS = 250 000`), what it measures | fig_04 |
| 5. Lumped (T: `## 5. Lumped`) | rings, resistances, footprint interior with Bessel factors, superposition, 5.1 via constriction in rings (Krogh cell, groups) | fig_05, models-comparison fig_06, V5, V6 |
| 6. Analytic (T: `## 6. Analytic`) | cosine series, source, influence-weighted copper, tile Green-function (Woodbury) correction, time, **6.1 constriction in tiles** (kept number) | fig_06, fig_32, V5 (shared Krogh cell), V7 |
| 7. Metal blocks (T: `## 7. Metal blocks`) | 7.1 plate in the layered models, 7.2 fins, 7.3 Lumped and Analytic (ring layer, Schur complement), 7.4 close-fin warning, 7.5 thick-plate bound | fig_11, fig_31, **fig_41 new** (block section: sides, exposed face, R''), fig_33 |
| 8. Heat transfer coefficients (T: `## 8. Heat transfer coefficients`) | air, Ra, natural, forced, mixed, radiation, the Picard loop, calibration | fig_08, fig_23; an h-against-dT curve only if fig_08 lacks it |
| 9. Parts (T: `## 9. Parts`) | junction temperature, derived quantities, power coefficient, top path as a root | fig_09, **fig_42 new** (top-path network and the curve of `g(P_b)`) |
| 10. Power profiles (T: `## 10. Power profiles`) | superposition, decision, run | fig_10 |
| 11. Verification summary (T: `## 11. Verification summary`) | five-line table and fig_22, pointer to `validation.md` | fig_22 |
| 12. References | table key / citation / status / where used, from `BIBLIOGRAPHY.md` | |

Figure numbers continue at fig_38 in `research/theory/scripts/make_diagrams.py` (diagrams) and `make_figures.py` (data); sketches are labelled "illustrative"; a figure quotes only numbers the text holds. The figures fig_01 to fig_11, fig_20 to fig_23, fig_31 and fig_33 of `research/theory/figures` are copied to `docs/images` when the text is adopted (fig_34 to fig_37 and the via and SOR figures are there already).

## 3. Structure of every model section

1. the idea in one picture; 2. the unknowns; 3. the equations (numbered); 4. the assembly; 5. the solution; 6. the limits in words (no number tables); 7. where it is checked (`validation.md` section, research folder); 8. the sources (bibliography keys with the reading status, a source not opened marked).

The equation strings that tests look for stay unchanged: `G_x = (2 S₁ S₂`, `(C/Δt + ϑK)`, `(I + G C) y = y₀`, `A_mn a_mn = q_mn`, `ΔT = P₀ R/(1 − α P₀ R)`, `Nu = 0.54 Ra`. **If the symbols `G` and `C` are renamed (section 4), `tests/test_docs.py::test_theory_document_covers_every_model_and_formula_family` must change in the same commit.**

## 4. Notation

The present text uses one letter for several things. Proposed names (the reviewer decides; the cost is the test strings above and the pointers in `models.md`).

| Clash | Uses today | Proposal |
| :-- | :-- | :-- |
| `G` | face conductance (FVM/FDM); modal response of the board between tiles (Analytic `(I + G C) y = y₀`) | face conductance stays `G`; modal response becomes `G_mod` |
| `C` | heat capacity vector (J/K); local conductance matrix of the Analytic correction | capacity stays `C`; the local conductance matrix becomes `C_loc` |
| `R` | resistance; number of rings; radius of the Krogh cell | resistance stays `R`; rings `N_ring`; the cell radius `R_c` |
| `K` | conductance matrix; Bessel function `K₀`; block lateral matrix `K_b` | matrix `K`; Bessel `K₀` always with its index; `K_b` stays (index) |
| `g` | conductance per area between layers; forcing vector of the modal transient | per area stays `g`; forcing becomes `s` |
| `k` | conductivity; wavenumber `k_mn`, `k` in `I_x` | conductivity stays `k`; wavenumber becomes `κ` (and `κ_mn`) |
| `c` | coverage; heat capacity per area `c_l`; via conductance `c_via` | coverage `c`; capacity per area `c_l` stays with its index; `c_via` becomes `G_via` |
| `θ` | temperature rise; junction-to-pad resistance `θ_part`; `ϑ` of the theta method | rise `θ`; the part resistance `Θ_part` or `θ_jp`; method parameter stays `ϑ` |
| `φ` | log potential of the footprint; channel fraction; block temperatures | log potential `φ`; channel fraction `ϕ_ch`; block temperatures `θ_blk` |
| `λ` | fin length of a layer; mode eigenvalue `λ` | fin length `λ_l` with its index; eigenvalues `μ_mn` |
| `ρ` | ring edge `ρ₁`, `ρ_max`; Jacobi spectral radius `ρ`; `ρc` heat capacity | ring edges `E₁`, `E_max`; the spectral radius `ρ_J`; `ρc` stays |
| `H`, `L`, `b` | board height / fin height; layers / length; fin gap / modal vector / `b = R/a` | board height `H_b`, fin height `H_f`; layer count `N_L`, length `ℓ`; fin gap `b_f`, modal vector `β`, ratio `ξ = R/a` |
| `S` | sheet conductance | stays |
| `A` | area; matrix `A_mn`; adjacency matrix | area `A`; modal matrix `A_mn` stays (always with its index); adjacency `N` |
| `f` | copper fill; heat `f = −C y` extracted by local elements | fill `f`; extracted heat `φ_loc` |
| `h` | heat transfer coefficient | stays |
| `T`, `P`, `Q`, `q` | temperature, power, source vector, density | stay |

## 5. The move list

Every number or history sentence that leaves `docs/theory.md`. The target section says where it must be (checked against the present headings of `validation.md` and `versions.md`). When the rewrite is done, tick each line and grep the new theory for the numbers to prove none is left.

| # | Statement now in `theory.md` (section) | Target |
| :-- | :-- | :-- |
| M1 | 1.2: advanced stack-up agrees within 0.1 K with equal gaps (validation section 12); 1 oz inner copper lowers the maximum by 6.9 to 7.5 K (14.1) | `validation.md` 12 and 14.1 (already there); theory keeps the rule (`d_j` unchanged, total thickness grows by Σ Δt_cu) without the numbers |
| M2 | 1.2 limits: 0.4 to 2 % against the 3D solid and the attribution to the idealisation "not measured separately" | `validation.md` 3 (a one-line statement that the attribution is not measured); theory says "the layered idealisation is the model error, measured by the 3D solid" |
| M3 | 1.2: Culham and Yovanovich: any mean 70 % to 300 % off, geometric mean of the coupon 2.7 W/mK 70 % off | stays as a **published number** with its key [CulhamYovanovich1998] (R); our reproduction numbers go to `validation.md` 22.1 |
| M4 | 1.3: history of the weight (before 2.4.5 coverage of the part alone; 4 x 4 cover; 1.5 times the density; +1.3 K; 2.2 K and 3.8 K too hot at 1 and 0.5 mm; "mean bias of +1.4 K at 1 mm remains") | `validation.md` 23 (the numbers) and `versions.md` 2.4.5 (the history); theory keeps the rule `c_i = n_pb / 64` and the two wrong rules with their reasons |
| M5 | 1.3 remaining limit: cut cell conducts with its cover, 0.5 to 0.7 K (about 1 % of the rise) at 1 to 0.5 mm; remedy in Planned | `versions.md` Planned (treat the cut cell by its real shape); theory states the limit in words |
| M6 | figures 36 and 37 captions with numbers (T board, scatter 15.7 to 3 K) | `validation.md` 23; theory keeps fig_34 and fig_35 (the rule), points to 23 for the others |
| M7 | 1.4: against an independent solver the FVM was 0.9 to 4.4 % low (full copper), 10 % low (20 mm pad); number of nodes −4.1, −2.5, −1.8, −1.5 %; under 0.3 % with full copper | `validation.md` 21 (**after the laminate merge**, whose rule may differ) |
| M8 | 2: sparse ordering "half the fill, about 40 % less time"; residual about 1e-13 | `validation.md` 5 (performance), theory keeps "symmetric minimum-degree ordering" |
| M9 | 2 SOR: "0.79 to 1.00 times the sweeps of the board without vias", "2.8 to 19 times", "810 sweeps at 1 mm (2244 before), 404 at 2 mm (1145 before)", "1 x 1 cell where the old factor diverged", "1.1 to 2 times the sweeps of the true optimum", "3 to 16 K" | `validation.md` 5 and `research/young-omega-tiles`, `research/sor-with-via-couplings`; theory keeps the formula, the lower-bound argument, the mask and figure S1 |
| M10 | 2 theta method stages: ten stages / `r = 3`, 18 stages | stays (it is the algorithm, not a result) |
| M11 | 2.6 via: convergence (7, 10, 20 % of the point via; 0.7, 0.5, 0.4 % of the footprint), gain of the 3 x 3 board (−4.50, −4.47, −4.49 K and −4.78 to −3.34 K), "12 to 15 % too large" at the edge, "0.79 times"; the "before, as before" history | `validation.md` 18 (via) and `research/point-via-convergence`; theory keeps the construction, the target radius, the Kron reduction, the limits in words (edge, coarse cell) and figures V1 to V3; V4 (gain against cell) moves to validation |
| M12 | 2.6: "within 1 % on a four-plane 1.6 mm board and −2.1 to +3.9 %" for `0.78 r_v` | `validation.md` 18; theory says the constant is one value that is close on average, not the radius of a real barrel |
| M13 | 3: FDM agrees with the FVM about 0.1 %, via array under 1 % from 1 mm | `validation.md` 2 and 2.1 |
| M14 | 4: timings and memory (2.0 s and 0.75 GB; 7.2 s and 2.15 GB; 15.3 s and 3.5 GB; 57.7 s and 9.9 GB), "it was 2e6, which let a run go on for hours", convergence 4 slabs within 1 % of 8, ±4 % bracket, "a 0.3 mm copper fill below 0.27 mm cells ... (roadmap, section 1)" | `validation.md` 16 (timings, convergence), `versions.md` Planned (clipping of `a_via`, memory guard); theory keeps `MAX_CELLS` as a statement and the clipping at 1 as a limit |
| M15 | 5: "+3 to +13 % with 40 rings" (merging rings); "27 % low, −8.7 %, +9.5 %" | `validation.md` 21 and 3; theory says the merge rule and that a copper edge across the footprint, a corner and a thin heater are where it fails (checks warn) |
| M16 | 6 preamble: the outline paragraph with the bounding box and "10 to 20 %" | `validation.md` 13; theory keeps `s = sqrt(A_outline/(W H))` and the stretching back |
| M17 | 6: "24 % low with a 20 mm pad", "25 %", "0.3 to 1 %"; "a single global factor cooled the distant heater by 18 %" | `validation.md` 3, 4 and 7; the 18 % is a design history: `versions.md` 2.1.0 |
| M18 | 6.1 cause: "copper-fill gain 6.3 to 6.8 K against 4.2 K" and the whole **Limits** paragraph (22 % too small, 65 % too large, 80 %, 16 to 21 % cool, 2 to 3 s and 0.9 GB) | `validation.md` 18 and 18.1; theory keeps a limit in words (lone via, array across a footprint edge, round boards) |
| M19 | 7: "5.5 to 6.4 % too low" (side walls), end faces "40 to 55 %" and "0.7 to 0.9 %" | `validation.md` 12 D; theory keeps "the fins stand on the exposed face; not modelled: end faces, fin heat capacity, lateral conduction along the fins" |
| M20 | 7: "aluminium or copper 1 to 10 mm within 0.6 % of the 3D solid"; Seri Lee +0.6, −0.8, −4.6 % and the `round()` remark; "8 to 31 % off" of the equivalent coefficient | `validation.md` 15 to 17 and 22.1; theory keeps the published values 0.66, 1.29, 2.38 K/W with [EC1998Spreading] and a pointer |
| M21 | 7.4: the evidence (1080-case grid, 667, missed 1 and 367) and "below Ra_b 14 the loss is an upper bound" | `validation.md` 24 (warnings) and `research/fin-channel`; theory keeps `Ra_b`, `φ`, the 90 threshold and the limits in words |
| M22 | 7.5: the 5 % threshold and the auxiliary run (cell of at least 2 mm) | stays in `models.md` 4b; theory keeps the bound and the flux definition |
| M23 | 8: "+7 % to −25 %" and "−0.7 to +0.2 % of the rise" (laminar form), "0.21 %" | `validation.md` 22; theory keeps both forms and [LeFevre1956] (M) for the check |
| M24 | 9: "1.3 to 3.4 K lower on the chips, 0.2 K on a 0603"; the MOSFET example (33 °C against 90.9 °C), solve counts (3, 6, 6 to 7, about 20, median 8 to 9, 90 % within 25, 57, 70) | `validation.md` 9 and 19; theory keeps the equations, why a fixed point fails (slope `−R_b/(R_top+θ)`) and the algorithm in words |
| M25 | 11: the whole table is a summary; numbers 10⁻¹² to 10⁻⁹, 2·10⁻⁸ K, 0.4 to 2.2 %, ±4 %, 1 to 3 %, 0.05 K | stays as a five-line table with pointers to `validation.md`; the numbers remain in `validation.md` |
| M26 | 12 references (textbooks and sources used) | replaced by the generated table of section 6 below |

Two sentences are **kept in the theory** although they carry a number, because they state a limit of what the theory claims: "the models have not been compared with measurements of a physical board" (section 11) and the energy balance identity (section 1.2).

## 6. Sources the theory cites, with the reading status

The full records are in `research/theory/BIBLIOGRAPHY.md` (section 20 holds the table below with the entries). **Nothing was upgraded without a recorded reading.**

| Source | Key | Status | Note for the text |
| :-- | :-- | :-- | :-- |
| Peaceman (1978) | [Peaceman1978] | S | well radius of the point sink; the constant 0.1985 is computed (exp(−(γ + 1.5 ln 2))), the paper's 0.14 sqrt(dx² + dy²) is from memory |
| Krogh (1919) | [Krogh1919] | M (new key) | the closed form (6.1) is own derivation (L), checked against a cell solver; the same mathematics as [Dietz1965] (S) |
| Saad (2003) | [Saad2003] | R for sections 3.3, 4.1, 4.2, 10.2 | Theorem 4.16 and equation 4.47 (pages 126 and 127), Theorem 4.10 (page 122) |
| Young (1950, 1971) | [Young1950] (new), [Young1971] | N, N | cite Saad's Theorem 4.16 for the statement |
| Bar-Cohen and Rohsenow (1984) | [BarCohenRohsenow1984] (new), [ElenbaasBCR] | N for the paper; forms R as printed in [TeertstraReview] equations 8, 20, 21, 22 and in Bar-Cohen, Iyengar, Kraus (2003) pages 1 to 6 (R in part) | `phi` is own algebra on the composite |
| Seri Lee (1998) | [EC1998Spreading] | R (equations 1 and 2 as images, the worked example reproduced 0.657) | the 1995 paper [Lee1995] is N; do not cite it |
| LeFevre (1956) | [LeFevre1956] (new) | M | check of the laminar form only |
| Churchill and Chu (1975) | [ChurchillChu1975] | paper N; equations R through [Lienhard2024] 8.13a, 8.13b (pages 419 to 421) | |
| Culham and Yovanovich (1998) | [CulhamYovanovich1998] | R pages 460 to 466 | no homogenised conductivity |
| JEDEC JESD15-3 | [JESD15-3] | R (mirror) | JESD51 family [JESD51family] N |
| Incropera and DeWitt | [IncroperaDeWitt] | M content | name the edition when quoting an equation number |
| Carslaw and Jaeger | [CarslawJaeger] | M content | the algebra of every use is derived in the code or the studies |
| Patankar (1980) | [Patankar1980] | M content, S citation | the harmonic mean and the theta method are derived in the text |
| Celik and others (2008) | [Celik2008] | R pages 4 to 9 | GCI procedure and Table 1 reproduced |
| Roache | [Roache] | M (summaries S) | cite [Celik2008] for the procedure |
| Muzychka, Culham, Yovanovich (2003) | [Muzychka2003] | R | cross of five sources reproduced |

## 7. Stale topics found and corrected (step 2)

Compared with the current code and `docs/theory.md`:

* **02 finite volume**: the via of the cell of its centre (replaced by the mean-potential footprint, new section 6), the SOR factor `2/(1 + sin(π/n_max))` (replaced by the Rayleigh-quotient estimate of Young's optimum and the block SOR), the sources (Saad, Peaceman, Young), the board cover sampled 8 x 8.
* **03 finite difference**: the via "at the nearest node" and the tables of the FDM error with the point via (replaced by the footprint of nodes and the present agreement).
* **05 Lumped**: the constriction of the heat on a via (new section 6, Krogh cell, groups), sources.
* **06 Analytic**: the tile with vias and the self-term (new section 4.1), source.
* **11 metal blocks**: the close-fin warning on `Ra_b` (replaced "the input checks warn when the gap is smaller than still air allows"), the thick-plate bound (new section 4.1).
* Also found and corrected: topic 04 (the via footprint rule of the 3D solid), topic 21 (the via assigned to the cell of its centre), topic 28 (the board cover sampled 4 x 4). **Topic 01** (one-layer board) is left until the laminate rule is merged; **topic 09** was checked and agrees with section 9 of the theory (the top-path root, the clip at `P`).

## 8. Questions for the reviewer

1. **Renaming** (section 4): is the cost of changing `G` and `C` in the strings of `tests/test_docs.py` worth it? An alternative is to keep `G` and `C` for the Analytic correction and rename the face conductance (`G_f`) and the heat capacity (`C_th`) instead; the Analytic section is then untouched, but the FVM equations change.
2. **The Krogh closed form (6.1)** rests on an own derivation checked numerically and on a source not opened ([Krogh1919], M; [Dietz1965], S for the equation). Is "derived and checked in the repository" enough for the theory, or does it need a published case reproduced (the Fish case of [Fish2017] chapter 6 is reproduced to −2.0 % but tests the microspreading correlation, not the closed form itself)?
3. **`phi` of the close-fin warning** is own algebra on a composite read as printed in a review ([TeertstraReview]); the original paper was not obtained. State it as "own algebra on the composite as printed by the review", or drop the 0.9 line from the theory and keep it in `models.md`?
4. **The laminar natural-convection form** is checked against LeFevre's `g(Pr)` (M). A published numerical case (Lienhard Example 8.1 reproduces the general form, Nu 47.33) exists for the general form only; is the laminar check "own computation against a remembered formula" acceptable?
5. **Section 1.2, "not measured separately"**: the attribution of the 0.4 to 2 % against the 3D solid to the idealisation and to one node per copper layer was not measured. The new text says only that the 3D solid measures the model error. Agree?
6. **Statement of the SOR bound**: the Rayleigh quotient is a lower bound of the Jacobi radius by the min-max principle for the trial vector; Saad Theorem 4.16 needs a consistently ordered matrix (the two-colour parity). Is the mask argument (cells off an outline are `mu = 0` eigenvectors) stated rigorously enough, or should the text say "a heuristic safe side" and cite the measurement?

## 9. Status of the rewrite (step 4: the text is written)

`docs/theory.md` was rewritten section by section in the order of section 2 (header and map, 0 symbols, 1 with 1.1 to 1.4, 2 with 2.1 to 2.6, 3 to 11, 12 as a table). Decisions taken while writing:

* **Notation**: the clashes were renamed as proposed (`G_mod`, `C_loc`, `N_ring`, `κ`, `R_c`, `G_via`, `ϕ_ch`, `Θ_part`, `H_b`, `H_f`, `N_L`, `b_f`, `ξ`, `E_k`, `ρ_J`, `μ_p`, `s`, `φ_blk`, `D_self`, `κ_a`, `E_w`, `μ_air`, `G_p` for the periodic response of section 10). The test string of the Analytic correction became `(I + G_mod C_loc) y = y₀` in `tests/test_docs.py` and in `docs/models.md` 2.4. **The docstring of `pcbthermal/analytic.py` (lines 32 and 388) still writes `(I + G C)`**: not changed (the branch does not touch `pcbthermal/`); it is a one-line change for a fix branch.
* **Section 11**: the five-line table keeps its numbers (a summary, with the section of `validation.md` that holds the evidence), and `fig_22` stays as it is (it carries the same numbers).
* **Figures**: copied to `docs/images`: `fig_44_laminate_nodes.png` (new, drawn by `make_diagrams.py`) and `fig_01` (redrawn: the line about two laminate nodes is gone). `fig_32` (numbers not re-run) and `models_comparison_lumped_rings.png` (a before-and-after picture) are **not used** in the theory; `models_comparison_lumped_rings.png` stays in `docs/images` unreferenced by the theory. `fig_36`, `fig_37` and `via_array_board_gain.png` moved to `docs/validation.md` 23 and 2.1.
* **Move list**: every item M1 to M26 is done: the numbers are in `docs/validation.md` 25 (a table; the numbers were carried over from the earlier text of the theory and **not re-run**, the table says so), the history is in `docs/versions.md` 2.4.5, the statements that stay are in the theory without the numbers. Proof: `grep` of the numbers of the list in `docs/theory.md` finds none (checked: 0.5 to 0.7, 2244, 810, 2.8 to 19, 0.79, 40 %, 18 %, 27 %, 6.9 to 7.5, 5.5 to 6.4, 1.3 to 3.4, 90.9, 1080, 667, timings, 0.21 %, 12 to 15, 22 / 65 / 80 %, 1.4 K, 2.2 K). Numbers that stay on purpose: the published values (Culham and Yovanovich 70 % to 300 %, 2.7 W/mK; Seri Lee 0.66, 1.29, 2.38 K/W; the 0.9, 0.75, 0.5 values of `ϕ_ch`; the thresholds 5 %, 90, 1500 degC, 50 times; Lienhard Example 8.1 Nu 47.33) and the table of section 11.
* **Test constraints** kept: the headings `## 2. FVM` to `## 11. Verification summary`, the module names, and the equation strings (`G_x = (2 S₁ S₂`, `(C/Δt + ϑK)`, `A_mn a_mn = q_mn`, `ΔT = P₀ R/(1 − α P₀ R)`, `Nu = 0.54 Ra`); the help text says "theory section 6.1" (kept).
* **Checks run**: `tests/test_docs.py tests/test_help.py tests/test_license_header.py research/theory/tests` pass. `research/check_figures.py research/theory` reports "no data figure / no diagram" **also on the commit before this step** (the check does not see the figure names that the scripts build with an f-string): a defect of the check, not of this change.

### Questions for the reviewer (new, from the writing)

7. **Section 1.4, the Lumped model keeps two laminate nodes and a board with a metal block keeps them too**, as the docstring of `laminate.py` says; the text states it as the current treatment. Is it intended to stay (the `versions.md` Planned list has no item for it)?
8. **Section 2.3, the `ω` of a network with laminate columns or via blocks**: the statement is "a heuristic on the safe side, not a proved optimum" (the two-colour argument does not hold there). Agree?
9. **Section 6.1, the formula (6.1) and `a = e^(−1/4) r_via`** rest on an own derivation; the text says so (L). The sentence "a published numerical case that tests the closed form itself was not reproduced" is there on purpose.
10. **Section 7.4, `ϕ_ch` (7.5)**: stated as own algebra on the composite as printed (question 3 answered that way in the text; change if the reviewer prefers to drop it).
11. **Section 3, the FDM limit** "not monotonic on coarse cells" was in the old text; its evidence is `validation.md` 2.1 (the FDM column is not monotonic from 4 mm to 1 mm).
12. **`docs/validation.md` 25** carries numbers that were not re-run; a reviewer who re-runs the studies may correct them there.
