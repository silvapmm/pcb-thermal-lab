# Review A5: imported copper, the Power Calculator and fast waves (with L10 and L8)

Assignment A5 of the 2.8.0 fine-comb audit (`releases/2.8.0/audit/ASSIGNMENTS.md` on `docs/audit-claims-register`: the 23 claims of risk 3), joined with the literature-to-code groups L10 (package and calculator: F-086 to F-094) and L8 (transient, profiles and the stack impedance: F-079 to F-085). Program: `development` 5fc91430. Branch `docs/audit-a5`; nothing in `pcbthermal/` or `tests/` is edited: program and test items are listed in section 5. This file is written as the work goes (a cut-off loses nothing); sections marked *(pending)* are not done yet.

## 1. What was re-run and what it printed

*(filled as the runs finish)*

## 2. Findings, ranked

*(pending)*

## 3. Claims: verdict and action

*(pending)*

## 4. Formulas L10 and L8: printed against coded

Pages read on the image in this review (papers library, read only, rendered with pypdfium2 to the scratchpad; text layer as cross-check): ROHM 64AN113E PDF page 3 (table 2 and NOTE1, figure 4), TI SPRA953 (local copy revision D) PDF pages 10 and 11 (sections 4, 4.1, 5, 5.1, eq. 9). Lienhard 2024 eq. 5.62 was read on the image by S1 and not repeated.

| fid | formula as printed (source, page) | as coded | verdict | note, action |
| :-- | :-- | :-- | :-- | :-- |
| F-079 | own: periodic response by superposition of delayed steps | `profiles.wave_response` (exact sums over the stretches of `_cumulative_response`, extremes at breakpoints and stretch middles) | MATCHES (own, exact for a linear board) | held by `tests/test_profiles.py`; not re-derived term by term |
| F-080 | own: average-or-resolve with a shared budget | `profiles.decide` | MATCHES the text of theory 10 | rule, no source needed |
| F-081 | slab quadrupole `Y = kγ (Y_L + kγ tanh γd)/(kγ + Y_L tanh γd)`, `γ = sqrt(jωc/k)` (own, from the transfer-matrix method; [CarslawJaeger] M) | `stackimpedance.half_admittance`: the same, slab by slab from the convective face (`Y_L = h`) inwards | MATCHES (derivation checked: the input admittance of a uniform line terminated by `Y_L`) | the source stays M; the independent check is the two reference solvers of `research/fast-wave-oscillation`, of which the program-side tables were re-run here (section 1) |
| F-082 | disc on a leaking sheet, centre: `Z = (1 − m a K₁(m a))/(π a² Y)`, `m² = Y/S` | `HeaterColumn.impedance`: the same | MATCHES (re-derived: inside `θ = q/Y [1 − m a K₁(ma) I₀(mr)]`, continuity at `r = a` holds by the Wronskian `I₀K₁ + I₁K₀ = 1/x`) | the equal-area disc is the program's choice; near a side 0.61 at 0.1 Hz (warned, `checks.check_fast_wave` (b)) |
| F-083 | `θ(t) = 2 Re Σ σ_k Z(kω₀) c_k e^(jkω₀t)`, `k = 1 .. N/2 − 1`, `N = 16384` | `_from_coefficients`: `σ_k = np.sinc(k / (N/2))` | **TEXT WRONG** in theory 10.5 (`σ_k = sinc(k/N)`) | corrected on this branch to `sinc(2k/N)`; the code is the standard Lanczos factor over the `N/2` harmonics |
| F-084 | own: 4 s (2 s with three or more layers), `MIN_FILL` 0.9 | `profiles.FAST_STRETCH_S`, `FAST_STRETCH_MANY_LAYERS_S`, `stackimpedance.MIN_FILL` | MATCHES theory 10.5 | the four-layer node error moved with 2.7.0 (section 2.3): the threshold of 2 s for three or more layers was measured on the old node and is now more conservative than needed (the node is closer to the truth), not less |
| F-085 | own: response cell a quarter of the narrow side of the smallest part | `api.response_cell_mm` | MATCHES | - |
| F-086 | `Tj = T_board + θ P` (two-resistor idea of JESD15-3; worst case: hottest board point under the footprint) | `analysis.part_split`, `heater_stats` | MATCHES theory 9 | quantity: a datasheet θJC(bot) is defined to the pad held by a cold plate (nearly isothermal); the program adds it to the hottest point under the footprint, which is the safe side. On the JEDEC board the hottest point and the pad mean differ by the amount in section 1 (study `study_jedec_board_readings.py`) |
| F-087 | ψJB: "the difference between the junction temperature and the **center package pin temperature**, divided by the power" (TI SPRA953 PDF p 11, section 5; measurement per JESD51-6, not read); `Tj = T_PCB + ψJB P` (eq. 9) | `analysis._ring_mean`: the mean of the cell centres in a band 0.5 to 1.5 mm outside the bounding box of the footprint, on the part's layer, all four sides | **DEFINITION SECOND HAND** in the documents | the documents said the ring is "the point where the datasheet's ψJB takes the board temperature" (1 mm from the package: vendor summaries, S); corrected in `docs/calculators.md` 1.1 and 3 to say what the read page prints; the help (`pcbthermal/help/calculator.html` line 85) and the tooltip keep "the board 1 mm from the package": item P4 |
| F-088 | `Ttop = Tj − ψJT P` (ROHM 65AN114E, TI SPRA953 eq. 4 to 7; R) | `inverse._temperature` (`row["t_junction"] − psi_jt × power`) | MATCHES | with a top path on the part (θSA set) `t_junction` already carries the split while `ψJT × P` uses the whole power: the calculator documents say not to use this route with a heatsink (calculators.md 3); item P5 (refuse or warn) |
| F-089 | own: `P = P_run (T_meas − T(0))/(T(P_run) − T(0))`, secant for computed h | `inverse.power_from_temperature` | MATCHES; affine check re-run (section 1: manual h 0.00 K off the line, computed h +1.35 / −5.67 / −13.73 K at 0.5 / 2 / 3 W, the secant finishes it) | the result field `resistance_k_per_w` is `(T_meas − T_amb)/P`, which includes the rise of the other heaters (`T(0) − T_amb`); calculators.md 1.1 defines `R = (T(P_run) − T(0))/P_run`. They are equal only with one heater. Item P6 (text of the result window or the code) |
| F-090 | own: one-at-a-time effects, root sum of squares; design amplitudes assumed | `inverse.power_band`, `defaults.json` `calculator` | MATCHES calculators.md 1.1b and 1.1c | re-run: the example band reproduces (ring 1.62 to 2.31 W none, 1.56 to 2.34 W hand), the four drawn boards moved by 0.001 to 0.012 W (section 1) |
| F-091 | own: `P = P0 [1 + α (Tj − 25)]`, runaway guard | `api._solve_with_tc` | MATCHES | not re-run (A1 and the battery hold it) |
| F-092 | `R_top = θJC(top) + R''/A + θSA`; root of the split (Illinois, Broyden) | `analysis.part_split`, `api._top_path_split` | MATCHES theory 9 | `tests/test_top_path.py` holds the exact root |
| F-093 | package θ library (QFN 5, Power QFN 3, DFN 10, D2PAK 0.75, TO-220 1.5, SOT-223 15, SMA 20, 0603 1000 K/W) | `defaults.json` `package_theta`, with notes | MATCHES its notes (S: web summaries; θJC(top) assumed except the 27 K/W of the TPS7A47, which S1 read in its datasheet; SMA 20 to 28 K/W from two datasheets; 0603 derived from a rating) | already labelled 'indicative, not from a datasheet' in the note of the first entry only; decision 5 of `DECISIONS.md` (mark every unsourced entry 'typical, no source') applies; no number to correct |
| F-094 | heatsink θSA library (11 catalogue entries) | `defaults.json` `heatsinks` | MATCHES its notes (catalogue and distributor listings, S) | **limit with a sign**: 'BGA 40×40×18, natural' carries 7.68 K/W, the catalogue value at a 75 K rise; the same note gives 10.8 K/W at 1 W. For a part with a small rise the library value reads the heatsink 40 % better than the catalogue (the unsafe side). Item P7: take 10.8 K/W or add the rise to the name; the program has no scaling of θSA with the rise or the flow (stated) |

## 5. Program and test items (not edited here)

*(pending)*

## 6. Trust verdict per chapter

*(pending)*

## 7. What was not verified, sources to obtain

*(pending)*
