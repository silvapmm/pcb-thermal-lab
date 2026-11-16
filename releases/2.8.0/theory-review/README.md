# Final theory review of 2.8.0

The reviewer's pass over the whole of `docs/theory.md` against the code before the release (CLAUDE.md sections 11 and 12), on branch `docs/theory-280-review` from `development` 77ed4822. Scope: every chapter against the functions it describes; the items of 2.8.0 that must be in the theory; the sources and their reading status; the history sentences; a picture per section; the agreement of `docs/models.md` where it restates the theory. The user-facing documents (README, guide, images, validation, models usage, CHANGELOG, versions) were reviewed by another reviewer on another branch and were not touched here.

## 1. Verdict

**GO for the theory of 2.8.0.** No formula or constant of the document disagrees with the code. What was wrong was text: a stale status of the finite-element model (it said the checkbox of the window was a later branch, and it hid that the model is steady state only), two figures with the number 50, sources named without a key, history sentences inside the explanation of what is implemented, and two stale lines of the module map. All of it is corrected on this branch. No defect of the program was found.

## 2. Independent checks made in this review

Run on `development` 77ed4822 (the code of this branch is the same), `nice -n 10`, under 0.3 GB.

| Check | Reference | Result |
| :-- | :-- | :-- |
| The film through the half copper (1.2a) | closed form of the series column: a 20 × 20 mm two-layer board, two 1 mm copper plates of 50 W/mK, 7.5 W over the whole top, `h_top` 0, `h_bottom` 400 W/m²K, insulated edges | bottom node 47.06250 K equals the closed form `q/h + q t/(2k)` (FVM and FDM at 2 mm) |
| The omitted half copper towards the laminate (1.2a, 1.2c) | same column | the top node is 0.37500 K below the closed form, exactly `2 × q t/(2k)`, as the theory states |
| The surface read-out (1.2c) | same column | surface minus column = +0.18750 K on the top face and −0.18750 K on the bottom face, exactly `± q t/(2k)` (FVM and FDM) |
| The FEM with the plain film (4a) | same column | both columns and both faces equal the closed form to 1e-5 K (172.4375, 47.0625, 172.6250, 46.8750 K), heat balance −1.9e-12 |
| Maxwell's self term (5) | double integral of the difference density of a unit square | 0.447049155904 against `exp(ln 2/3 + π/3 − 25/12)` = 0.447049155904 |
| Convection laws (8) | `research/theory/scripts/check_correlations.py` | the vertical laminar form +6.6 / −5.2 / −25.0 % of the general one at `Ra` 10⁵ / 10⁷ / 10⁹, as section 8 quotes; the `ht` worked examples reproduced |
| Constants against the code | read in the modules | `face_film_h`, `thickness.offsets` (`t (2 q_top − q_bot)/(6 k)`), `UPPER_RATIO` 0.5, `THICK_PLATE_LIMIT` 0.05, laminate `S_MAX` 0.4 mm and `N_MAX` 4, 3D `slab_rule` 4 to 16, FEM `FEM_DIRECT_MAX` 30 000, CG `rtol` 1e-10 with the restart at `max(1e-8, 100 tol)`, `CU_ONE_MAX` 105 µm, `CU_SLAB` 70 µm up to 8, `GAP_RATIO` 1.4, growth 0.3 per unit distance, `BLOCK_SLABS` 2 to 8, `K_PAD` 1, `PATCH_NSIDE` 4, `AREA_FIX` 1.0143, `FEM_MAX_PATCHES` 200, 145 rod samples, the refusals (2000 outline vertices, 0.02 mm, 10 000 lines, 20 000 nodes, 6 million unknowns), memory 6.7 kB × 1.15 and 15.9 kB direct; Lumped `IMAGE_MAX_CELLS` 3600, `RING1_SOURCES` 900, the floor at a tenth of the half ring, `CORE_R`, `MAX_CORE`, `MACRO_CAP`; Analytic `READOUT_TOLERANCE` 0.25 %, `LOCAL_MODES` 16, `LOCAL_MAX_UNKNOWNS` 3000, bracket 0.05 to 20; blocks `r_c ≥ 1e-7`, `r_b`, `r_cu`, `r_half`, the exact cover limited to the board cover; convection 0.54, 10⁷, 0.14 with the Prandtl factor, 0.475 Ra^(1/5), Churchill-Chu constants, 0.664 and 0.037/871, the radiation coefficient; viawell `e^(−1/4)`, the lattice radius 0.1985 | all as the theory states |

## 3. Per chapter

| Chapter | Verdict | What was corrected | Trust |
| :-- | :-- | :-- | :-- |
| Header, 0 symbols and constants | corrected | units: every difference in K, the rule in `units.py` | high |
| 1.1 to 1.2.1 layered idealisation | matches | | high |
| 1.2a film term | corrected | history removed ('since', 'before', 'now'); the exactness on a column added with this review's check | high (exact, checked) |
| 1.2b bound | matches | | high |
| 1.2c surface read-out | corrected | 'What changed' rewritten as 'No threshold'; the 0.375 K of the half copper explained as `2 × q t/(2k)` and reproduced; the flag uses the equivalent side `√A`, not the side (stated) | high in 1D, medium beyond `t/a` 0.5 (upper estimate) |
| 1.3 sources and geometry | matches | one 'now' removed from a caption | high |
| 1.4 laminate nodes | corrected | the one-layer closed form without the half copper stated as such, not as an older form | medium-high (the `1/n` error and the edge band are measured, not bounded) |
| 1.5 to 1.8 via, Gerber, imported copper, parts | matches (spot check of the via constants) | | medium-high |
| 2 FVM | matches (spot check) | | high |
| 3 FDM | matches (spot check) | | high |
| 4 3D solid | corrected | the face film with no version tag; the block reading described instead of 'the earlier reading' | high |
| 4a FEM | corrected | status: steady state only, the checkbox exists, not a time model; 'later branch' and 'review' history turned into statements and checks; the refinement option named; units µm and °C; plan-mesh figure renumbered 53; sources given keys with status | high for the steady model (exact on a column, scikit-fem 5e-9 K); the comparison campaign (validation 56, 57) is not run |
| 5 Lumped, 5.1, 5.2 | corrected | 'now' sentences of the part read-out and the first link rewritten; Maxwell's self term given a key | medium (constants fitted against the FVM, stated) |
| 6 Analytic, 6.1 | corrected | caption 'the transient now'; the eigenproblem size stated as 1024 for four layers; the per-layer edge paragraph freed of the history of 2.5.x and 2.6.0; 'in 2.6.0' and 'in 2.8.0' removed | medium (fitted tiles, stated) |
| 7 blocks, 7.1 to 7.5 | corrected | 7.5: the film term explained without 'before `fix/face-film-half-slab`' | high for 7.1 to 7.3, the bound of 7.5 is a bound |
| 8 convection and radiation | matches (constants and printed examples) | '(now the code)' | medium (the laws are ±20 to 50 % of the published scatter, stated) |
| 9 parts | matches | | high |
| 10 power profiles | corrected | two history sentences (an earlier form of the admittance, the response cell) rephrased; the second kept as the reason of the rule | medium-high |
| 11 verification summary | corrected | three rows added: the film term, the surface read-out, the FEM | |
| 12 references | corrected | keys added: [ZienkiewiczTaylor2000] M, [Hughes2000] M, [Pyamg] R metadata / N paper, [MaxwellGMD] M | |

Every key cited in the document is defined in section 12 and in `research/theory/BIBLIOGRAPHY.md` (checked by script; the four new keys have entries with licence and status). Every section that explains a model, an equation or a method has a picture (the sections without one, 0, 1.1, 1.3.1, 2.1, 2.2, 2.5, 7.3 and 12, are covered by the figure of their chapter or are tables). Figures 48 to 53 are added to the index `research/theory/docs/theory-figures.md`.

## 4. Changes outside `docs/theory.md`

* `docs/models.md`: the read-out table (the FEM column, no longer 'once its model branch merges'), the module map (`fem.py` added; `femmesh.py`, `femcore.py` no longer 'not selectable yet'; `thickness.py` every thickness, not 'thick outer copper').
* Figure `fig_50_fem_plan_mesh.png` renamed `fig_53_fem_plan_mesh.png` in `docs/images/` and `research/theory/figures/` (the surface figure keeps 50); `make_fig_fem_mesh.py` and `releases/2.8.0/DOC_REVIEW_CHECKLIST.md` follow. The picture itself did not change.
* `research/theory/BIBLIOGRAPHY.md`: the four entries; pyamg 5.4.1 installed (the earlier entry said 5.3.0).

## 5. Defects of the program

None found. Points for the maintainer, not defects:

1. `pcbthermal/thickness.py:116` flags the upper estimate with `t / √A > 0.5`; the study measured square sources. An elongated part (2 × 20 mm on a 2 mm plate) has `√A` 6.3 mm and is not flagged, while its narrow side gives `t/a` = 1. Whether the narrow side is the right measure is not measured; the theory now says what the code does.
2. `pcbthermal/memory.py:61` says the direct figure is `1.1 × 14 402` (15 842 bytes) and `FEM_DIRECT_BYTES` is 15 900: rounded up, conservative, consistent with the theory's 15.9 kB.

## 6. Stale text left for others (not in this scope)

* `CLAUDE.md` sections 1 and 11 say the FEM ships steady **and transient** in 2.8.0; the code is steady state only (`api.TIME_MODELS`, `fem.py` docstring, the tooltip 'Steady state only'). Either the transient is still planned for 2.8.0 or the two sentences are to be corrected.
* `docs/models.md` 2.8 (usage, the other reviewer's scope): 'The time simulation and the compare views are later branches' is to be checked against the window.
* Numbers that do not name their tree: most numbers of the document name a section of `validation.md`, which names the tree; the numbers written directly (for example the costs of 1.4, the 7 ms of 1.3.2, the timings of 4a 'tree of that branch') were not re-run and are left as they are.

## 7. Sources not opened

[ZienkiewiczTaylor2000], [Hughes2000] (the FEM element), [MaxwellGMD] (the self term, value checked by quadrature), the paper of [Pyamg]; and, as already marked in the document, [CarslawJaeger] (M), [IncroperaDeWitt] (M), [Krogh1919] (M), [Peaceman1978] (S), [Young1950] and [Young1971] (N), [Varga1962] (N), [ChurchillChu1975] (N, equations through Lienhard), [LloydMoran1974] (N), [GoldsteinLau1983] (N), [JESD51family] (N), [Davis2006] and [Roache] (M). None of them is the only support of a formula in use: each formula resting on them is either checked numerically in the repository or read in a secondary source that was opened.

## 8. What was read and what was not verified

Read in full: `docs/theory.md` sections 0 to 1.4, 4, 4a, 5 and 5.2 (every line); sections 1.5 to 3, 6 to 10 and 11 by their equations, constants and the passages of 2.8.0 (a spot check, not every sentence); the code of `model.Board.face_film_h`, `thickness.py`, `blocks.block_cover` and `extra_layers`, the constants of `femcore.py`, `femmesh.py`, `memory.py`, `lumped.py`, `analytic.py`, `analytic_local.py`, `viawell.py`, `viaconstriction.py`, `laminate.py`, `convection.py`, `checks.py`. Not re-run: the studies behind the numbers of sections 1.4, 2, 5, 6, 7.5 and 10 (the reproduction pass of the tester covers the research folders); the FEM comparison campaign (not written yet); the transient chapters were checked against their constants only. Tests run on this branch: `tests/test_docs.py`, `test_license_header.py`, `test_version.py`, `test_third_party_text.py`, `test_help.py`, `test_face_film_half_slab.py`, `test_maximum_principle.py`, `test_theta_orders.py`, `test_via_well_sheet_order.py`, `test_published_cases.py`, `research/theory/tests`: 913 passed, 1 skipped, 2 xfailed.
