# Review L12: numerics, memory guard and the default data

Assignment L12 of the literature-to-code track (`ASSIGNMENTS.md`; formulas F-072 to F-078 and F-095 to F-100 of `formulas.csv`) and the claims of the numerics and data chapters (`docs/theory.md` 0, 2.2 to 2.5, 2.7, the sources table; `docs/validation.md` 5, 7, 26; the rows T-052 to T-061, T-077, T-078, VA-049, VA-051, VB-042 of `claims.csv`, which the register gave to A2 and which A2 did not settle). Program: `development` 35eeb773 (2.7.1 plus documents). Branch `docs/audit-l12`; nothing in `pcbthermal/` or `tests/` was edited: the program and test changes are the items of section 5. Every number below is printed by `releases/2.8.0/audit/scripts/study_numerics_data.py` (parts named in brackets) or by the command quoted.

## 1. What was re-run and what it printed

| run | where | printed |
| :-- | :-- | :-- |
| direct, CG, SOR on five boards | `research/models-comparison/scripts/solver_equivalence.py` (3 s) | SOR (residual 1e-9) within 3.9e-9 K of the direct solve; original step rule 2.7 to 16 K off; sweeps 282 / 673 / 726 / 779 / 636 (validation 5 table replaced) |
| the same on the example board at 1 and 2 mm | `python -m pcbthermal solvers examples/example_board.pcbt.json --cell-mm 1|2` | 726 and 356 sweeps, 3.93e-9 and 2.66e-9 K |
| SOR sweeps against omega (`omega`) | example board | Rayleigh omega 1.93885 (2 mm), 1.96716 (1 mm); sweeps at delta −0.03 / −0.015 / 0 / +0.015 / +0.03: 758 / 571 / 356 / 480 / 711 (2 mm), 2278 / 1634 / 726 / 1281 / 7916 (1 mm) |
| theta method (`theta`) | uniform one-layer board, set-up of `tests/test_fvm.py` | implicit Euler 3.0626 / 1.6688 / 0.8746 / 0.4482 K (orders 0.88 / 0.93 / 0.96), Crank-Nicolson 0.3152 / 0.0772 / 0.0192 / 0.0048 K (2.03 / 2.01 / 2.00); energy −1.4e-4 |
| step responses (`steps`) | example board, 1 mm | monotone (smallest increment 2.6e-5 K/W), Z(end)/R 0.999999; 4 against 16 steps per stage 1.2e-3 / 1.5e-3 of R; against implicit Euler with 16 steps 4.8e-3 / 5.3e-3 |
| SuperLU modes (`lu`) | example board, FVM and FDM at 1 mm | nnz(L+U) equal in both modes (6 546 998 and 6 938 988), default mode `perm_r == perm_c`, all pivots positive, solutions differ 6e-15 |
| observed order (`order`) | 48 mm two-layer board, insulated edges, 2 / 1 / 0.5 / 0.25 mm | smooth (full copper, heater on grid lines): peak orders 1.94 / 1.99, heater mean 1.96 / 1.99; feature (copper edge at 24.3 mm under a 6 mm heater off the grid): peak rise 105.8 / 136.0 / 145.4 / 144.1 K, not monotone |
| memory law (`memory`, one process per point) | example board, `api.simulate` | FVM 0.5 / 0.35 / 0.25 mm peak 0.669 / 1.440 / 3.058 GB against 0.880 / 2.020 / 4.461 GB; FDM 0.5 / 0.35 mm 0.692 / 1.559 against 0.859 / 2.096 GB: peak / estimate 0.69 to 0.80, peak / law without safety 0.91 to 1.03 |
| maximum principle | `pytest -s tests/test_maximum_principle.py` (2.7.1), and the same test on `git archive v2.5.2` and `v2.6.0` | 2.7.1: example 16 / 64 positive entries (largest 0.0178 of the diagonal), dense array 432 / 432 at 0.5 mm, 1872 / 2448 at 0.25 mm (largest 0.018 / 0.015 / 0.023 / 0.022); v2.5.2: 832 / 864, 0.74 / 1.31; v2.6.0: 432 / 432, 0.018 / 0.015; cold spot of the copper-edge board −5.491 / −12.801 K at 0.5 / 0.25 mm (xfail, as written) |
| tests of the group | `tests/test_maximum_principle.py`, `test_sor_omega.py`, `test_memory.py`, `test_symmetric_lu.py`, `test_robustness_and_balance.py` | 116 passed, 2 xfailed (32 s) |
| copper constants (`copper`) | example board, 1 mm | 385 → 398 W/mK (Lienhard Table A.1): rise −1.52 % FVM, −1.57 % Lumped, −1.52 % Analytic |
| unsourced defaults (`sens`) | example board; bare 60 × 40 mm two-layer board, 6 mm 1 W part | FR-4 in-plane 0.3 / 0.6 / 1.2: example +0.6 / +0.3 / −0.3 %, bare +81 / +25 / −15 %; through 0.25 / 0.35: +1.6 / −1.3 % and +3.6 / −2.7 %; emissivity 0.6 / 0.3 (computed h): +6.5 / +15.3 % and +3.9 / +8.5 % |
| self distance of a square (`gmd`) | quadrature and closed form | 0.4470491559 both |

Pages read on the image (papers library, read only, rendered to the scratchpad): [Lienhard2024] Table A.1, book page 739 (PDF 753, rotated table; the 20 °C columns and the copper rows); [Saad2003] printed pages 122, 126, 127 (PDF 142, 146, 147: Theorem 4.10, Theorem 4.16 with eq. 4.46, eq. 4.47); [LiptonRoseTarjan1979] page 356 (PDF 11, Remarks: `O(n^{3/2})` time, `O(n log n)` space); [SoleymaniKoohbanani2013] (the 2016 thesis) printed page 52 (PDF 69: Azar and Graebner's 0.29 W/mK through the plane). Text layer only: Lienhard PDF 753 to 754 for the metals (aluminium, brass, steels), SuperLU guide PDF 25 (SymmetricMode, DiagPivotThresh; the pages 2.5.2 and 2.6 were image-read earlier and not repeated). Not in the library: [George1973] (the local file named after George is another paper), [Patankar1980], [Young1950], [Young1971], [Varga1962], [Davis2006].

## 2. Findings, ranked

1. **Wrong document (fixed): the numbers of the via couplings of theory 2.2 were those of 2.5.x.** 832 / 864 and 3104 / 3872 positive entries and a largest entry 0.74 / 1.31 (up to 2.2) times the diagonal are printed by the test on the tag v2.5.2; since the rim rule of 2.6.0 (the via no longer couples the bare third layer of that board) the test prints 432 / 432 and 1872 / 2448 with a largest entry 0.015 to 0.023 of the diagonal. The qualitative statement (positive entries exist, `K` is no M-matrix, no cold spot on full copper) holds; the size quoted was 40 to 100 times too large. Corrected, with the history said.
2. **Wrong attribution (fixed in the documents; data marks are an item): the program's copper is not Lienhard's.** The sources table and theory 8 cited [Lienhard2024] 'Table A.1 (copper)' as if it held the program's constants. Table A.1 (book page 739, PDF 753, image) prints pure copper at 20 °C 398 W/mK, 8954 kg/m³, 384 J/kgK; the program uses 385 / 8960 / 385, with no recorded source (a common handbook value for commercial copper). 385 reads the example board 1.5 % hotter than 398 (all three models), the safe side. Theory 0 now has a table of every default constant with its basis and status.
3. **Unsourced and sensitive (limit recorded): FR-4 in the plane, 0.9 W/mK.** No source anywhere in the repository (the library note says 'about 0.9'). It hardly matters with copper (±0.3 % on the example) but sets a part on bare laminate: +25 % / −15 % of the rise for 0.6 / 1.2 W/mK on a two-layer board without copper. The through-thickness 0.3 has second-hand support (0.29 measured by Azar and Graebner, quoted by the Soleymani thesis, image; 'typical 0.3' in [Rodero2025]). The emissivity 0.9 has no source (+6.5 / +15 % at 0.6 / 0.3 on the example with computed coefficients). Theory 0 says so; the user-facing marks are item I1 (decision 5 of `DECISIONS.md`).
4. **Misleading (fixed): 'below the optimum the sweeps grow slowly, above it steeply'** (theory 2.3). Young's theory gives the opposite near the optimum (an infinite slope of the SOR radius just below `ω_opt`, slope 1 above), and the program agrees: on the example board −0.015 / +0.015 around the Rayleigh omega costs 1634 / 1281 sweeps at 1 mm (571 / 480 at 2 mm); only within about 0.03 of 2 does an overestimate blow up. The Rayleigh bound is right for another reason: it can never reach 2 (where an SPD SOR stops converging), and it lands at the measured minimum on the example board. The derivation of the bound (symmetrised Jacobi matrix, any trial vector) is now written.
5. **Misleading (fixed): the safety factor of the memory law 'is the largest measured/fitted ratio rounded up'.** It is that ratio times 1.1 (1.27, 1.12, 1.18 × 1.1 = 1.40, 1.24, 1.30; `research/memory-guard` README 14.2), and it bounds only the ladder points (the via cases fall under it 7 times in 85). Five fresh points on 2.7.1 (the example board, 151 000 to 598 000 unknowns) peak at 0.69 to 0.80 of the estimate and 0.91 to 1.03 of the law without the factor: the law holds on the current program.
6. **Stale (fixed): validation 5.** The table was of 2.6.x (the multilayer temperatures moved with the physical slabs of 2.7.0, the 2-layer SOR 306 → 282 sweeps, the example's largest SOR difference 6.3e-9 → 3.9e-9 K). Replaced by the 2.7.1 output; the substance (agreement to 4e-9 K, the step rule 2.7 to 16 K off) holds.
7. **Narrower (fixed): 'second order for smooth fields, first order at features'** (theory 2.5). The smooth case re-measures 1.94 / 1.99. At a feature (a heater across a copper edge, both off the grid lines) the peak is not monotone with the cell (105.8 / 136.0 / 145.4 / 144.1 K), so no order can be read; the sentence now says that the change with the cell is the measure.
8. **Cannot be checked (marked): '50 random via layouts … 3 of 100 runs below ambient by at most 0.2 %'** (theory 2.2). No script of the repository prints it (a scratch file of the review of 2.4.5) and it predates the rim rule. Marked as a claim to re-measure (item I5).
9. **Stale code comment (item I3):** `memory.SOR_BLOCK_SHARE` says 'Share of the limit one dense SOR block may take'; the rule is on the sum over all the blocks (`sor_block_fits`, theory 2.3).
10. **Small data inconsistencies (item I6):** the copper of a metal block is 386 W/mK (`libraries.metals`, Ferrotec) and of the board 385; the aluminium 204 W/mK is neither Lienhard's pure aluminium (237) nor 6061-T6 (167); brass `ρ c_p` is 2.91e6 against 8490 × 340 = 2.89e6 from its own note.

## 3. Formulas (F-072 to F-078, F-095 to F-100)

| fid | as coded against the source | range, warning | case | verdict | action |
| :-- | :-- | :-- | :-- | :-- | :-- |
| F-072 FV, harmonic faces, theta method | `fvm.transient_from_network` and `step_responses_from_network` build `(C/Δt + ϑK) x₁ = (C/Δt − (1−ϑ)K) x₀ + Q`, as (2.5); stages as written (10 doubling stages; 18 stages of 4, ratio 3, `t_end` = 10 τ without the pins). [Patankar1980] not in the library (M); the stability factor is a two-line derivation | all | the exact exponential: orders 0.88 to 0.96 and 2.00 to 2.03, energy −1.4e-4 | **holds** | none (test I4 optional) |
| F-073 Young omega, Rayleigh bound | `sor_omega` = theory (2.3), (2.4); [Saad2003] eq. 4.47 p 127 and Theorem 4.16 p 126 by image (consistently ordered) | not consistently ordered with via blocks or laminate columns: said | example board: minimum of the sweeps at the Rayleigh omega | **holds**; the sentence on the side was misleading | theory 2.3 corrected |
| F-074 SuperLU symmetric mode, guard | `lu_factor` = theory 2.3 (diagonal > 0, symmetry 1e-12 of the largest entry, probe residual 1e-8, fallback logged) | fallback logged | equal fill, `perm_r == perm_c`, 6e-15 | **holds** | none |
| F-075 memory law | `estimate_bytes` = (2.8) term by term (`t_eff = max(1, min(t, cells/t))`); LRT p 356 by image; George not in the library | refuse / slow / warn as written | 5 fresh points 0.91 to 1.03 of the law | **holds**; safety-factor sentence misleading | theory 2.7, validation 26 |
| F-076 via gain | `via_gain` = (2.8b) | symmetric mode only, said | not re-measured (a via-dense ladder is heavy) | **holds as an own fit**, not re-verified | none |
| F-077 block SOR | `solve_sor` relaxes `ω K_BB⁻¹(Q_B − K_B θ)` per colour group; fallback when the sum of `75 n²` exceeds 25 % of the limit; Theorem 4.10 p 122 by image (point case), block case through Varga (S) | fallback visible | example board 3.9e-9 K | **holds** | comment of `SOR_BLOCK_SHARE` (I3) |
| F-078 board time constant | `ΣC / (Σg_amb − Σg_pin)` | — | step response ends at 0.999999 R | **holds** | none |
| F-095 metals | library values = notes (Ferrotec, ToolBox; addresses not recorded) | — | Lienhard text layer: Al 237 / 6061 167 against 204; brass 109 / 111; AISI 304 13.8 / 14.4 | **narrower** | I6; theory 0 table |
| F-096 board materials | copper 385 / 8960 / 385 **not** in Lienhard Table A.1 (398 / 8954 / 384, image); FR-4 0.3 second hand; 0.9, 1850, 900 no source | — | sensitivities measured (section 1) | **misleading attribution; unsourced** | theory 0, 8, sources table, models 17 corrected; I1, decision D1 |
| F-097 interfaces | two presets with empty notes, the 'typical default' with no source | — | — | **unsourced in part** | I1 |
| F-098 via fills | copper 385 = the board copper; epoxy 0.3, paste 8 rest on fabricator pages (A3) | — | — | **holds as recorded** (not re-checked here) | none |
| F-099 emissivity 0.9 | no source | computed h only | +6.5 / +15 % at 0.6 / 0.3 | **unsourced** | theory 0; I1 |
| F-100 stack-up templates | not re-checked in this pass | — | — | **not verified here** | none |
| (decision 5) self distance 0.447 | Maxwell's geometric mean distance of a square, `exp(ln 2/3 + π/3 − 25/12)` = 0.447049 (from memory), quadrature 0.4470491559 | — | — | **holds** (rounding 1e-4 in the potential) | theory 5 sentence extended |
| (decision 5) air fits | done by L1/L5 against Table A.6 (image) | — | — | settled there | none |

## 4. Claims

| id | claim (short) | verdict | action |
| :-- | :-- | :-- | :-- |
| T-052 | via couplings 832 / 864, 3104 / 3872, up to 2.2 times the diagonal | **false on the current program** (2.5.x numbers; 2.7.1: 432 / 432, 1872 / 2448, at most 0.023) | theory 2.2 replaced |
| T-053 | cold spot 7.94 / 14.43 K (5.49 / 12.80 on 2.7.0) | **holds** (−5.491 / −12.801 K on 2.7.1) | none |
| T-056 | 50 random via layouts, 3 of 100 below ambient | **cannot be checked** (no script; before 2.6.0) | marked in theory 2.2; I5 |
| T-057 | direct, CG, SOR agree; same fill; 1e-11 K | **holds** | none |
| T-058 | sweeps 2197 → 676, 1054 → 364; 726 on 2.7.0 | **stale, holds in substance** (726 and 356 on 2.7.1) | theory 2.3 |
| T-059 | Young's relation, Saad Theorem 4.16, eq. 4.47 | **holds** (image) | page numbers added in the bibliography |
| T-060 | theta method orders, unconditional stability | **holds** (measured orders) | none |
| T-061 | second order smooth, first at features | **narrower** | theory 2.5 sentence added (the cut-cell numbers are A2's) |
| T-077 | memory law on 67 points, via term on 59, 7 of 85 under by 1.27 | **holds** (not re-fitted; 5 fresh points inside the spread) | validation 26 audit paragraph |
| T-078 | FDM exponent 1.34 at the 4/3 bound; George R in part | **holds** for LRT (image p 356); George **cannot be checked** here (not in the library) | none |
| (theory 2.3) | 'below the optimum slowly, above steeply' | **misleading** | rewritten |
| (theory 2.7) | safety factor 'rounded up', 'does not fall below the measurement' | **misleading** | rewritten |
| (theory 8, sources) | copper 'in Table A.1' | **misleading** | rewritten, page and values added |
| (models 17) | FR-4 'measure 0.29 to 0.34' | **narrower** (0.29 second hand, 0.34 no source) | sentence sourced |
| VA-049 | agreement 7e-9 K, step rule 2.7 to 16 K | **holds** (3.9e-9); table stale | validation 5 table and text replaced |
| VA-051 | implicit Euler 3.06 / … / 0.45, CN 0.315 / … / 0.005, energy 0.2 % | **holds** to the digit | none (the test checks two step sizes only: I4) |
| VB-042 | memory law ratios and safety factors | **holds** (quoted from the README; fresh points agree) | none |

Not settled here and left to their assignments: VB-027 and VB-028 (validation 25 history rows, A6), RCC-061 to RCC-075 (SOR with vias, A3), VA-023 and RA-309 (orders of the 3D solid references, A1 and A2).

## 5. Items for the program and the tests (not edited)

| # | item | branch | moves numbers |
| :-- | :-- | :-- | :-- |
| I1 | the marks of decision 5: in the Preferences tooltips and the library notes, copper 385 'typical, no recorded source; pure copper is 398 W/mK at 20 °C (Lienhard Table A.1)', FR-4 in-plane 0.9 and its density and heat capacity, the emissivity 0.9 ('depends on the solder mask and finish'), the six dielectric presets and the two interface presets with empty notes and the 'typical default' paste; the FR-4 note to cite the 0.29 of Azar and Graebner | `fix/typical-values-marks` | no |
| I2 | **decision D1 for the maintainer**: keep copper 385 (recommended: on the hot side by 1.5 % on the example board, a value for commercial or deposited copper, now marked) or take 398 from Table A.1 (every frozen record moves by about 1.5 % of the rise, a pending file) | maintainer | only if 398 |
| I3 | `memory.SOR_BLOCK_SHARE` comment: the share is of the sum over the blocks | any `fix/` | no |
| I4 | tests: hold the counts of `test_maximum_principle.py` in a band (positive entries, largest ratio below 0.05 on the dense array) so that theory 2.2 is pinned; the theta-method test at four step sizes with the orders (validation 7) | `fix/` | no |
| I5 | the random via layouts of theory 2.2: commit a study that prints them on the current program, or withdraw the sentence | A2 / A6 | no |
| I6 | library consistency: block copper 386 → 385 (or say why they differ), aluminium 204 named as an alloy, brass `ρ c_p` from its note | `fix/typical-values-marks` | blocks of copper and brass by under 0.5 % |
| I7 | the user guide and the bare-laminate warning: say that a part on bare laminate depends on the in-plane FR-4 conductivity (+25 / −15 % for 0.6 / 1.2 W/mK), which has no source | A6 | no |

## 6. What was not verified

* [George1973], [Patankar1980], [Young1950], [Young1971], [Varga1962] and [Davis2006] are not in the library: the statements resting on them are checked as derivations (the theta factor, the Rayleigh bound) or by the program, not on the page.
* The via gain of the memory law (2.8b) and the `75 n²` bytes of an SOR block were not re-measured (heavy, via-dense ladders); the time laws of the 'slow' mark were not re-measured; Windows and containers were not measured (as the theory says).
* `data/stackups.json` (F-100) was not re-checked against the fabricator pages in this pass.
* The SuperLU guide sections 2.5.2 and 2.6 were not re-imaged (image-read by an earlier pass; the text layer of PDF 25 agrees).
* Lienhard PDF 754 (stainless steels) was read on the text layer only.

## 7. Verdict

**GO for trust in the numerics chapters** (theory 2.2 to 2.5, 2.7; validation 5, 7, 26) with the corrections of this branch: the solvers, the relaxation factor, the symmetric LU and its guard, the theta method and the memory law do what the theory says and the measured numbers hold on 2.7.1; what was wrong was text (stale via-coupling numbers, the side of the omega error, the definition of the safety factor), not the program.

**GO with conditions for the data**: the attribution of the copper constants was wrong and is corrected in the documents; the user-facing marks of decision 5 (item I1) and the maintainer's decision on 385 against 398 (I2) are open. No number moves in this branch.
