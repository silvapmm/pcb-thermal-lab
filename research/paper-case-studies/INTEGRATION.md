# What could change in the program or the documents, with the measured outcomes

Nothing in `pcbthermal/`, `tests/`, `examples/`, `ico/` or the project documents is touched by this folder. The studies have run (README sections 10 to 14); each proposal below says what was measured and what it would cost. A change to the program is implemented only after the maintainer decides, on a `fix/` or `feature/` branch with the whole battery; the reviewer has not yet reviewed these results.

## 1. Proposals that touch the program

### 1.1 Laminate sub-gap rule for thin sources on thick boards (S2; decision for the maintainer)

* **Measured** (README 11.3, FVM at 0.25 mm against the extrapolated 3D reference, 33 combinations, bare and pad boards): the default rule (0.4 mm, 4 sub-gaps) is within about 4 % (bare) and 6 % (pad) for sources of 5 mm and above on boards up to 1.6 mm, and **too cool by 16.6 % (bare) and 19.8 % (pad) for a 2 mm source on a 3.2 mm board** (2 mm sources: 4 to 11 % too cool at 0.8 and 1.6 mm). The cell (0.5 against 0.25 mm) is not the cause.
* **Options measured**: (0.2, 8) brings the worst rows to -6.3 % (bare) and -9.0 % (pad) at 1.7 to 1.8 times the node layers of the default; (0.1, 16) brings every row that ran within -2.5 to +1.9 % at 3.0 to 3.4 times the node layers, and the memory guard refuses it on the 40 mm board at 0.25 mm (435 200 unknowns, 10.4 to 11.3 GB estimated against 10.3 GB allowed). The cost in seconds and bytes was **not measured** (node-layer counts only).
* **Proposal**: (a) keep the default and write the limit into `docs/theory.md` 1.4 and `docs/validation.md` 21.2 (error map of README 11.3); (b) if the maintainer wants the error removed for small sources, make `n_max` depend on the source size or the thickness (a rule per cell: the number of sub-gaps under a footprint that is small against the thickness), measured on a copy first; the frozen numbers move for every board with patterned copper and are refrozen in the same branch. No change is recommended on this evidence alone: the options exist in `SolverOptions` and Preferences already, and a user with a thin source on a thick board can choose them.
* **Not affected**: the Lumped, the Analytic (their errors on these boards are far larger and are the known limits of the models) and the solid model (see 1.3).

### 1.2 One mean convection coefficient per face on a poorly conducting plate with concentrated sources (S3; text and a possible warning)

* **Measured** (README 13.3): on the vertical glass plate (k_s 1.03 W/mK, two strips of 3875 W/m2 per face, peak 83 K against a plate mean near 44 K) all five models give the strips 84.6 to 86.0 K against the conjugate solution's 74.9 and 80.2 K: **+10.3 % on the mean of the two strips** and the plate maximum +6.4 %, of which +8.6 points are the uniform coefficient (an FVM run with the total coefficient that the conjugate solution itself implies gives the same excess) and +1.4 the correlation (9.18 against 9.39 W/m2K). On the ceramic plate (28.38 W/mK) the program is within 5 % on each strip (mean of the strips -2.0 %).
* **Proposal**: a sentence in `docs/theory.md` (heat transfer coefficients) and `docs/validation.md`: the coefficient is one per face and computed from the mean face temperature; for a thin board whose in-plane conductance is below a few 10 W/mK times the thickness and with a concentrated source the peaks are read 6 to 14 % too hot, on the safe side. A warning is not recommended: the effect is on the safe side and a threshold would be a guess on two cases. A local coefficient `h(T_local)` iterated in the FVM would remove it, but it is a feature (non-linear matrix at each Picard step), not a fix, and it would need its own investigation.
* **Not found wrong**: the correlation itself (laminar and general natural forms differ by 0.1 to 0.2 point on these plates).

### 1.3 The 3D solid model on thick laminates (S2 L4; open, not a recommendation)

* **Measured**: solid3d at 0.25 mm is too hot by up to +20.0 % (bare, S = 2 mm, 3.2 mm) and +27.4 % (pad); at 0.5 mm on the 40 mm board -0.3 to +2.4 % (bare) and +3.5 to +8.4 % (pad). Not decisive (L4 is reported only). **Not examined** why: the laminate is a small number of slabs in the solid model, which would explain an error that grows with the thickness (a guess, not tested here). Open for the reviewer or a study on the slabs of `solid3d.py`.

### 1.4 The via rule (S1 C): no change

* **Measured**: against an independent axisymmetric unit-cell solver with the same flux condition, the FVM, FDM and 3D solid are within 0.4 to 2.2 % on all nine samples at the cell of pitch / 8 to pitch / 16 (the error does not grow with refinement). The Analytic is 8.2 to 13.1 % too resistive (above its 10 % attention threshold on five of nine samples), the Lumped 4.1 to 9.5 %, both on the safe side. No change; the Analytic figure goes into `docs/validation.md` as measured.
* The measurement itself (Soleymani's Fig. 33) is bracketed by equations 28 and 29 for three of four groups (README 10.2); the program equals those equations to the accuracy of the solver, so the program is "validated against the measurement" only to the extent that the thesis's closed form is (13 % claimed by the thesis); the straight 1.25 mm group (10.0 against 7.0 W/mK, +43 %) is not usable.

## 2. Text for the project documents (nothing adopted; the template is in `docs/validation-rows.md`)

| Where | What |
| :-- | :-- |
| `docs/validation.md` | a row against a measurement (Soleymani, three usable groups) and its limits; a row of equation 50 of Muzychka and others against an extrapolated 3D reference (0.07 to 1.15 %); a row for the vertical plate of Lee and Yovanovich (the independent solver within the plot reading of the paper's curves; the program +10 % on a poor conductor, -2 % on a good one); the laminate error map of README 11.3 |
| `docs/theory.md` 1.4, 2.6 | the published check of the laminate rule (the limit of 1.1 above); one sentence on the via check (S1 C) |
| `research/theory/BIBLIOGRAPHY.md` | statuses updated in this folder (README 15) |
| `docs/versions.md` 'Planned' | nothing is added here; 1.1 and 1.2 are decisions to take first |

## 3. Risks and limits of the evidence

* The extrapolated reference of S2 carries an uncertainty of about 1 % (worst row -1.15 %); the options in 1.1 differ from each other by more than that, the default's error at the worst rows by far more.
* S3's glass case compares the program with an independent numerical solution of the paper's own equations, not with Zinnes' measurements directly (those are plots with 4 to 8 K scatter on the ceramic); the independent fluid side is first-order and slightly high (0.3 to 3.7 % in the local Nusselt number against the similarity solution).
* The runs used one machine (16 GB, about 17 GB reported by the memory guard); the resident sizes (8.2 GB for the one-off S/32 reference, about 3 GB for the program part) are measured here.
* The reviewer's pre-run corrections (README 9) changed how S2 reads the temperature and how S1 part D turns a via contrast into psi_ta; the outcomes refer to the corrected scripts. The S2 criterion L1 was changed after its first result (README 11.2) and says so.
