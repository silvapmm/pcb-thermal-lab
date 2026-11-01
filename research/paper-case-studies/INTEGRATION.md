# What could change in the program or the documents, with the measured outcomes

Nothing in `pcbthermal/`, `tests/`, `examples/`, `ico/` or the project documents is touched by this folder. The studies have run (README sections 10 to 14); each proposal below says what was measured and what it would cost. A change to the program is implemented only after the maintainer decides, on a `fix/` or `feature/` branch with the whole battery. **Reviewed** (README 16): each proposal carries the reviewer's recommendation, and section 1.6 sorts them into 2.5.0 and 2.6.0.

## 1. Proposals that touch the program

### 1.1 Laminate sub-gap rule for thin sources on thick boards (S2; decision for the maintainer)

* **Measured** (README 11.3, FVM at 0.25 mm against the extrapolated 3D reference, 33 combinations, bare and pad boards): the default rule (0.4 mm, 4 sub-gaps) is within about 4 % (bare) and 6 % (pad) for sources of 5 mm and above on boards up to 1.6 mm, and **too cool by 16.6 % (bare) and 19.8 % (pad) for a 2 mm source on a 3.2 mm board** (2 mm sources: 4 to 11 % too cool at 0.8 and 1.6 mm). The cell (0.5 against 0.25 mm) is not the cause.
* **Options measured**: (0.2, 8) brings the worst rows to -6.3 % (bare) and -9.0 % (pad) at 1.7 to 1.8 times the node layers of the default; (0.1, 16) brings every row that ran within -2.5 to +1.9 % at 3.0 to 3.4 times the node layers. The memory guard refused it on the 40 mm board at 0.25 mm inside the long study process (10.4 to 11.3 GB estimated against 10.3 GB allowed); in a fresh process the estimate is 8.26 GB, so the refusal was the base of the study process (README 11.3, review).
* **Cost in seconds and bytes, measured by the review** (README 16.3, each run alone, FVM, direct solver): against the default, (0.2, 8) costs 1.4 to 4.6 times the time and 1.2 to 3.0 times the memory on the example board, the harness board `two_layer_partial`, a CO60-like 30 mm window and the 20 mm S2 board; (0.1, 16) costs 2.5 to 40 times the time and 1.7 to 14 times the memory (`two_layer_partial` at 0.5 mm: 0.7 s and 0.43 GB to 28 s and 5.8 GB). Where the part is large the answer moves by 0.2 % or less; on the window with a 2 x 2 mm part the part mean moves +5.1 / +8.6 % at 0.5 mm.
* **The error follows the sub-gap over the part's side** (README 16.3): s / S of 0.07 to 0.10 gives -5 to -1 % (bare) and -9 to -1 % (pad), 0.15 to 0.20 gives -9 to -4 % and -14 to -6 %, 0.31 to 0.39 gives -20 to -12 % and -24 to -14 %, always too cool.
* **Decision of the review** (the request gave it to the reviewer; the maintainer may overrule): **the defaults stay** (0.4 mm, 4). A global finer pair buys nothing where parts are large and costs up to 4.6 times (0.2, 8) or 40 times (0.1, 16) the time; the error is local to small parts over cut gaps.
  * **2.5.0, `fix/thin-part-laminate-warning`, text only** (no number moves, no refreeze): `checks` warns, for the FVM and FDM, about a part on an outer layer whose footprint covers cut cells (the rule's mask) of the adjacent gap when `s = d / n > 0.15 min(part side)`: "the part may read 5 to 25 % too cool (a thick laminate under a small part); `laminate_s_max_mm` near 0.1 of the part's side reduces it at a cost". With the defaults it fires for parts under about 2.5 mm on a 1.6 mm two-layer board without a plane under them and under about 5.2 mm on 3.2 mm. The limit and the table of README 16.3 go into `docs/theory.md` 1.4 and `docs/validation.md` 21.2, with the correction of the 3.2 mm row of 21.2 (README 16.5).
  * **2.6.0, a feature after a study on a copy**: a source-aware rule that cuts the gap under and around a small part (margin about d) into sub-gaps of at most 0.1 S (capped at 16) and keeps the default elsewhere; measured on the 33 combinations and the harness boards before adoption; it moves the frozen numbers only of boards with small parts over cut gaps.
* **Not affected**: the Lumped, the Analytic (their errors on these boards are far larger and are the known limits of the models) and the solid model (see 1.3).

### 1.2 One mean convection coefficient per face on a poorly conducting plate with concentrated sources (S3; text and a possible warning)

* **Measured** (README 13.3): on the vertical glass plate (k_s 1.03 W/mK, two strips of 3875 W/m2 per face, peak 83 K against a plate mean near 44 K) all five models give the strips 84.6 to 86.0 K against the conjugate solution's 74.9 and 80.2 K: **+10.3 % on the mean of the two strips** and the plate maximum +6.4 %, of which +8.6 points are the uniform coefficient (an FVM run with the total coefficient that the conjugate solution itself implies gives the same excess) and +1.4 the correlation (9.18 against 9.39 W/m2K). On the ceramic plate (28.38 W/mK) the program is within 5 % on each strip (mean of the strips -2.0 %).
* **Proposal** (the review agrees: document only): a sentence in `docs/theory.md` (heat transfer coefficients) and `docs/validation.md`: the coefficient is one per face and computed from the mean face temperature; for a thin board whose in-plane conductance is below a few 10 W/mK times the thickness and with a concentrated source the peaks are read 6 to 14 % too hot, on the safe side. A warning is not recommended: the effect is on the safe side and a threshold would be a guess on two cases. A local coefficient `h(T_local)` iterated in the FVM would remove it, but it is a feature (non-linear matrix at each Picard step), not a fix, and it would need its own investigation.
* **Not found wrong**: the correlation itself (laminar and general natural forms differ by 0.1 to 0.2 point on these plates).

### 1.3 The 3D solid model on thick laminates (S2 L4; cause found by the review, a program defect of a comparison model)

* **Measured**: solid3d at 0.25 mm is too hot by up to +20.0 % (bare, S = 2 mm, 3.2 mm) and +27.4 % (pad); at 0.5 mm on the 40 mm board -0.3 to +2.4 % (bare) and +3.5 to +8.4 % (pad).
* **Cause (review, README 16.4)**: the four equal slabs per gap (`n_diel = 4`, fixed by the API). With the same slabs and pixel the solid equals the independent reference to 0.01 K (pad) and differs by exactly the face term (bare); 8 slabs give +5.4 / +13.3 %, 16 give +0.4 / +7.9 % (3.2 mm), the rest being the plan pixel, the slab residual and, on bare laminate, the face term the solid does not add (-3.5 %, which cancels the pixel at 16 slabs). Cost on the 20 mm board: 0.3 s and 0.20 GB (4), 1.4 s and 0.36 GB (8), 5 s and 1.58 GB (16).
* **Wrong statements in the program and the documents**: the docstring of `solid3d.solve_steady` ("8 changes the answer by under 0.6 % even on a heater-sized pad") and `docs/validation.md` 25, row of the 3D solid ("4 slabs per gap is within 1 % of 8 even on a heater-sized pad"): 4 against 8 slabs differ by 5 % at 1.6 mm and 14 % at 3.2 mm under a 2 mm source.
* **Recommendation**: 2.5.0, text only (a `fix/` branch): correct the two statements, and say in `docs/theory.md` 4 that the solid's error grows as (gap / 4 / source side)^2 and that it reads the centre of the top slab without a face term. 2.6.0: slabs by thickness, `n_diel = clip(ceil(d / 0.2 mm), 4, 16)` per gap, and the face term over bare laminate as the FVM has it (the memory guard counts the slabs already); measured on the 33 combinations and the harness before adoption; it moves the frozen 3D numbers of every board with a gap above 0.8 mm, so it is refrozen with the 2.6.0 release.

### 1.4 The via rule (S1 C): no change

* **Measured**: against an independent axisymmetric unit-cell solver with the same flux condition, the FVM, FDM and 3D solid are within 0.4 to 2.2 % on all nine samples at the cell of pitch / 8 to pitch / 16 (the error does not grow with refinement). The Analytic is 8.2 to 13.1 % too resistive (above the study's 10 % attention threshold on five of nine samples), the Lumped 4.1 to 9.5 %, both on the safe side. No change; the Analytic figure goes into `docs/validation.md` as measured, and not beside its 1.8 / 2.9 % on the via effect without saying that the metric differs (a board-wide array resistance, review).
* The measurement itself (Soleymani's Fig. 33) is bracketed by equations 28 and 29 for three of four groups (README 10.2); the program equals those equations to the accuracy of the solver, so the program is "validated against the measurement" only to the extent that the thesis's closed form is (13 % claimed by the thesis); the straight 1.25 mm group (10.0 against 7.0 W/mK, +43 %) is not usable.

### 1.5 Corrections to the project documents found by the review (text, any time)

* `docs/validation.md` 21.2: the 3.2 mm window row (-34.19 -> -9.13 %) was measured against a reference 1.6 % high in its sub-slabs (README 16.5): about -33 -> -7 % against a converged one; a footnote, not a re-run.
* `docs/validation.md` 25 and the docstring of `solid3d.solve_steady`: see 1.3.

### 1.6 What belongs to 2.5.0 and what to 2.6.0 (review)

| Item | Version | Kind | Moves numbers |
| :-- | :-- | :-- | :-- |
| Warning for a small part over a thick cut gap (1.1) | 2.5.0 | `fix/`, text | no |
| Limit of the laminate rule in `theory.md` 1.4 / `validation.md` 21.2, footnote of the 3.2 mm row (1.1, 1.5) | 2.5.0 | documents | no |
| Wrong slab statements of the 3D solid, limit in `theory.md` 4 (1.3) | 2.5.0 | `fix/`, text | no |
| One coefficient per face on a poor conductor, a sentence (1.2) | 2.5.0 | documents | no |
| Validation rows of `docs/validation-rows.md` (measurement, equation 50, plate) | 2.5.0 | documents | no |
| Source-aware laminate rule (1.1) | 2.6.0 | `feature/` after a study | yes, small parts over cut gaps |
| Slabs by thickness and the face term in the 3D solid (1.3) | 2.6.0 | `fix/` after a measurement | yes, 3D records with gaps above 0.8 mm |
| A local convection coefficient (1.2) | later, investigation first | `feature/` | yes |

## 2. Text for the project documents (nothing adopted; the template is in `docs/validation-rows.md`)

| Where | What |
| :-- | :-- |
| `docs/validation.md` | a row against a measurement (Soleymani, three usable groups) and its limits; a row of equation 50 of Muzychka and others against an extrapolated 3D reference (0.07 to 1.15 %); a row for the vertical plate of Lee and Yovanovich (the independent solver within the plot reading of the paper's curves; the program +10 % on a poor conductor, -2 % on a good one); the laminate error map of README 11.3 |
| `docs/theory.md` 1.4, 2.6 | the published check of the laminate rule (the limit of 1.1 above); one sentence on the via check (S1 C) |
| `research/theory/BIBLIOGRAPHY.md` | statuses updated in this folder (README 15) |
| `docs/versions.md` 'Planned' | nothing is added here; 1.1 and 1.2 are decisions to take first |

## 3. Risks and limits of the evidence

* The extrapolated reference of S2 carries an uncertainty of about 0.3 % from its error model (four models, README 16.2) and agrees with equation 50 within -1.15 to -0.07 %; under a pad it is the only reference (about 0.5 % more uncertain). It was adopted after the single-grid check L1 had failed: a post-hoc check, worded so in the README. The options in 1.1 differ from each other by more than that, the default's error at the worst rows by far more.
* S3's glass case compares the program with an independent numerical solution of the paper's own equations, not with Zinnes' measurements directly (those are plots with 4 to 8 K scatter on the ceramic); the independent fluid side is first-order and slightly high (0.3 to 3.7 % in the local Nusselt number against the similarity solution).
* The runs used one machine (16 GB, about 17 GB reported by the memory guard); the resident sizes (8.2 GB for the one-off S/32 reference, about 3 GB for the program part) are measured here.
* The reviewer's pre-run corrections (README 9) changed how S2 reads the temperature and how S1 part D turns a via contrast into psi_ta; the outcomes refer to the corrected scripts. The S2 criterion L1 was changed after its first result (README 11.2) and says so.
