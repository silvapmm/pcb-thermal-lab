# Measurement plan: one afternoon, four board designs, a logger

What this protocol is for, what it cannot tell, and how to follow it. Numbers marked (study) were printed by
`research/convection-laws/scripts/study_measurement_prediction.py`; numbers marked (estimate) are my own engineering estimates, not measured or
reproduced, and they are the first thing to check once the first run exists.

## 0. The result of the design study, before the plan

* **The hottest point of a board with a local heater is almost blind to the convection law** (study): for a 100 x 80 mm, 2-layer, full-copper board with an 8 x 8 mm
  source at 1.5 W (rise 35 K) the rise changes by at most 0.5 % between the program's laws, Raithby-Hollands with Goldstein-Lau, Raithby-Hollands with Fujii-Imura and Jaffer,
  and by 1.2 % between horizontal and vertical. Almost all the 35 K is the spreading resistance of the copper round the source and not the film on the faces (the mean board
  rise is about 5 K). On the 17 boards of the regression harness the difference is 0.2 to 1.7 % (README section 6). **A test with a local heater validates the model of the
  board (copper spreading, edge, vias, radiation, a multiplier on h) and cannot choose a law.**
* **A uniform plate with one bright face discriminates** (study, `--faces`): the ratio of the rise with the exposed face up to the rise with it down, at the same power,
  is 0.62 (program), 0.69 (Raithby-Hollands up, Goldstein-Lau down), 0.66 (Raithby-Hollands, Fujii-Imura) and 0.52 (Jaffer), at 4 W, with a back loss of 1 W/m2K and an
  emissivity of 0.07 (the model of that table is a 1D balance with the program's own convection functions, no board solver). The spread between laws (up to 0.17 in the
  ratio) is 5 times the 3 % one can reach in a ratio; the back loss and the emissivity move all four ratios together by 0.02 to 0.03 (study), so they do not hide the order.
  That is board D below and it is the test that matters for the horizontal laws.
* **A uniform plate with both faces open tests the coupling of the faces** (study, `--faces`): the 2D numerical plate of README section 5 says that a thin plate with both faces hot has its upper face about 45 % lower than the isolated face
  (a result of a steady, symmetric, two-dimensional model, not shown to hold for a board). With a film heater under board A and nothing else, the rise at 6 W is 30.2 K for the program, 30.9 K for Raithby-Hollands with Goldstein-Lau,
  31.3 K and 30.8 K for the others (a spread of 3.5 %), and 34.1 K (+13 %) if the upper face were 40 % lower: the test E below separates a coupling of that size from every law (study).

## 1. The four board designs

All 100 x 80 mm, 1.6 mm FR-4, 35 um copper, two layers, order five of each from any fabricator that offers the finish (about 20 to 40 EUR per design, estimate).

| board | copper | purpose |
| :-- | :-- | :-- |
| A | both layers full copper, 1 mm clear of the edge, green solder mask | the reference for the multiplier on h |
| B | a 20 x 20 mm pad on both layers at the centre, mask | local heating with little spreading |
| C | as B plus a 3 x 3 array of 0.3 mm vias, 1.3 mm pitch, under the heater | the via effect; the program predicts +6 % of the power for the same rise (study; 5 x 5: +9 %, 6 x 6: +10 %: if the 3 x 3 array is too small to see, order 6 x 6) |
| D | both layers full copper, **no solder mask on the top face, ENIG finish** (bright, emissivity about 0.05 to 0.1: check by the method of section 5) | the up / down test; a film heater is glued to the bottom face and covered with 30 mm of foam |
| E | board A itself with the film heater glued on the bottom face and **no foam**, thermocouples on both faces | both faces open and hot: the coupling of the faces (no extra board) |

Heater of A, B and C: two 2512 resistors (for example 4.7 ohm, 2 W) side by side soldered on the top face at the centre (6.4 x 6.4 mm together), connected in series;
the power is the voltage across the pair times the current, V*I, with V sensed by two separate fine wires at the resistor pads (four-wire) so that the wires of the supply do not enter V.
Power for a rise of 35 K (study): A 1.5 W, B 0.6 W, C 0.66 W; use three powers per board: 0.5, 1 and 1.5 times those values.
Heater of D: a 90 x 70 mm silicone-rubber or polyimide film heater (12 V, 10 W class, about 10 EUR) with its own adhesive, **2 and 4 W only** (study: 2 W gives 26 K up and 41 K down, 4 W 46 K up and 74 K down; 8 W would give 132 to 155 K down, above the glass transition of FR-4, so 8 W is a model point of the study and not a run). **Review correction:** the first version of this plan ran board D at 2, 4 and 8 W on XPS foam; XPS softens at about 75 degC (manufacturers' service limit, estimate, not read here), which the heater side passes at 4 W face down (22 + 74 = 96 degC). Use a mineral-wool or calcium-silicate board (about 0.035 to 0.07 W/mK, rated well above 150 degC; textbook values, estimate) behind the heater; with XPS keep to 2 W.

## 2. Bill of materials (prices are rough, estimate)

| item | quantity | note |
| :-- | :-- | :-- |
| boards A, B, C, D | 5 of each | fabricator, about 100 to 150 EUR in all |
| 2512 resistors 4.7 ohm 1 %, 2 W | 10 | |
| film heater 90 x 70 mm, 12 V | 2 | board D |
| laboratory supply with current limit, 0.1 % voltmeter, 0.2 % ammeter (or two bench multimeters) | 1 | |
| data logger with 6 type K inputs (0.1 K resolution) or six thermocouple modules | 1 | |
| type K thermocouple wire, 36 AWG, bead-welded or twisted and soldered | 3 m | |
| Kapton tape, thermal epoxy (a drop per bead), matt black paint (emissivity about 0.95, any flat black spray, only for the optional run of section 5) | | |
| mineral-wool (or calcium-silicate) board 30 mm, 150 x 150 mm, rated above 150 degC (XPS only if board D stays at 2 W) | 1 | board D back |
| four needle-tip supports (pins in a block of foam), 20 mm high | 4 | |
| a cardboard box (no lid) 0.7 m wide, or a foam screen, as draught shield | 1 | |
| a small anemometer or smoke source to prove the air is still | 1 | see the risk list |

## 3. Method

1. **Isothermal offset of the thermocouples.** With the board unpowered and the shield in place for 30 minutes, read all six thermocouples; subtract each from the mean, keep the offsets (a type K channel is good to 1 K as bought, to 0.1 to 0.2 K after this).
2. Attach T1 to the **bottom** face directly under the heater centre, T2 and T3 on the top face 14 mm and 26 mm from the centre along the short axis (the radial profile), T4 and T5 on the top face 24 mm and 42 mm from the centre along the long axis, with Kapton tape over 20 mm of lead flat on the board and a drop of epoxy on the bead; T6 is the room air thermocouple, shielded from the board by a foil cup, 150 mm from the board edge at the board height.
   The model gives the field of every layer, so compare each reading with the layer it is glued to (T1 with layer 2).
3. Place the board on the four needle supports, horizontal, layer 1 up, inside the shield, a table and nothing else within 0.3 m. Wait 10 minutes for the air to settle.
4. Apply power in steps of 30 minutes (the board's time constant is about 3 minutes (estimate: C about 28 J/K, hA about 0.16 W/K), so 30 minutes is ten constants), read the last 5 minutes mean; the point is accepted when dT/dt of T1 is below 0.02 K/min. Record V, I, T1 to T6.
5. Repeat with the board turned over (layer 1 down), and standing vertical on its long edge (shield kept; two thin wires hold it).
6. Board D: heater side down on the foam (foam under and around the edges), bright face up; 2 and 4 W; then turn the whole sandwich over, bright face down, same powers. Record V, I, T on the bright face at the centre and at 30 mm from it (two thermocouples), room air.
7. Board E: board A with the film heater on the bottom face, no foam, 3, 6 and 12 W, face up and turned over; mean of three thermocouples on the top face (centre and two at 30 mm) and one on the heater side.
8. Compare with the program (section 6).

## 4. Uncertainty budget (estimate; k = 1, rise 35 K, board A)

| source | value | effect on the rise |
| :-- | :-- | :-- |
| power V*I (0.1 % and 0.2 %, wires sensed) | 0.3 % | 0.3 % |
| thermocouple offset after step 1 and drift | 0.15 K | 0.4 % |
| room temperature drift during the point | 0.2 K | 0.6 % |
| bead on the surface (leads along the board, epoxy) | 0.1 to 0.2 K | 0.5 % |
| emissivity of the mask (0.90 +- 0.03; about 45 % of the loss is radiation) | | 1.0 % |
| conduction along the supply wires (30 AWG, about 100 mm, taped; the heat they carry is taken from the board) | up to 1.5 % of the power | 1.0 % |

| residual air movement: the program's own blend of forced and natural convection (cubic) adds 0.3 % to the convection coefficient of the upper face at 0.02 m/s (forced 1.75 against natural 8.7 W/m2K), 1.1 % at 0.05 m/s and 3 % at 0.1 m/s (computed with `convection.h_forced`); a real draught also disturbs the plume and can do more than the blend says (not quantified) | | 1 % assumed, more if the shield is poor |
| total, root sum of squares | | **about 2 % to 3 %** of the rise (board A) |

**Review note on the supply wires (estimate, not measured).** A bare 30 AWG copper wire leaving the heater pads acts as a long fin: `sqrt(h P k A)` is 0.4 to 0.6 mW/K for h = 10 to 20 W/m2K, so two wires leaving at the 35 K of the heater carry 28 to 40 mW, 1.9 to 2.7 % of the 1.5 W of board A and **4.5 to 6.5 % of the 0.62 W of board B** (the two sense wires of the four-wire measurement add about 0.2 mW/K each if they are 36 AWG copper). The 1.5 % of the row above holds only if the wires are taped flat along the board for 30 mm or more, so that they leave it where the board is much cooler; for B and C do that, use the thinnest wire that carries the current, and correct the power by the fin estimate. The budget above is for board A; for B and C the wire term may dominate.

Dominant risk: **draught.** The film of a still board is 6 to 9 W/m2K and is carried by a thin plume; a door, a person walking, a window or a computer fan can break it, and the correlations of the program say nothing about it.
Prove the air still (smoke from a joss stick, or a thread, or an anemometer at 0.02 m/s resolution) with the board powered; discard a point if the smoke is not vertical over the board.
The board D test is less sensitive than the others because the ratio of two runs with the same draught cancels part of it (not quantified).

## 5. Emissivity (optional but it pays)

The mask is 0.9 by the books; board D is bright (about 0.05 to 0.1 by the books). To check a face, run board A once with a strip of matt black paint (0.95) on the bottom face: the shift of the rise gives the radiation share within about 20 %. For board D, the ratio of the rises changes by 0.015 for an emissivity change of 0.05 (study), and by 0.03 for a 1 W/m2K change of the back loss, so both only need to be known to about +-0.05 and +-0.5 W/m2K; take c as the conductivity of the insulation (0.034 W/mK for XPS, about 0.04 for mineral wool) over 30 mm plus a 0.3 W/m2K for the edges, read from the same table.

## 6. What to compare, and what is expected

* **Fit the multiplier on board A, predict the others.** With the program's FVM (1 mm cell, computed h, the measured ambient, the measured V*I), find the multiplier m (`Board.h_calibration`) that makes T5 (the far-field reading, the one that depends on the film) of board A equal the measurement, then predict T1 to T5 of B and C, the turned-over and the vertical runs, with that m. Success: every reading within 5 % of the rise (that is k = 2 of the total of the 3 % budget and the 3 to 5 % model error to be expected: the program's FVM is within 1 to 3 % of a 3D solver on boards like these in `docs/validation.md`; not re-run here).
* **Study of what the fit can absorb** (study): if the "true" film were Raithby-Hollands and Goldstein-Lau, the program with its own laws and a multiplier of 0.977 fitted on A would predict B and C within 0.4 to 0.8 % (up, turned over, vertical); without the multiplier within 0.0 to 0.4 %. The multiplier hides the law, which is why board D exists.
* **Board D** (the decision): the ratio of the rise (up / down) at 2 and 4 W against the table of section 0: program 0.63, Raithby-Hollands with Goldstein-Lau 0.69 to 0.70, Raithby-Hollands with Fujii-Imura 0.66, Jaffer 0.52 to 0.53 (study, 1 W/m2K back loss, 0.07 emissivity). A measured ratio within +-0.03 of a value picks that law; between two, the law is not decided. **Neighbouring laws are only one resolution apart** (program 0.625 against Raithby-Hollands with Fujii-Imura 0.659, and that against Raithby-Hollands with Goldstein-Lau 0.693 at 4 W): the test separates Jaffer from the rest and the program from Raithby-Hollands with Goldstein-Lau, not every pair; and the back loss shifts every ratio by 0.045 from 0.5 to 2 W/m2K (study), so it must be known to +-0.5 W/m2K for the 0.03 to hold. The trend with the power (program 0.629 to 0.624 from 2 to 8 W) is below the resolution.
* **Board E** (the coupling): rise at 3, 6, 12 W with both faces open against the table of section 0 (program 16.8, 30.2, 53.4 K; Raithby-Hollands with Goldstein-Lau 17.0, 30.9, 54.9 K; if the upper face were 40 % lower 18.9, 34.1, 60.0 K, study, emissivity 0.9, edges ignored); a measured excess over the program of 10 % or more says that the faces are coupled; below 4 % nothing is said (the budget).
* **Which of our models to run:** FVM (the reference), FDM, the 3D solid and the Lumped and Analytic models for A (rectangle, they accept it), for B and C the same; the via effect of C against B (study, FVM: +6 % of the power for the same rise) against the Lumped, the Analytic and the 3D solid (not run here). Boards D and E are not model runs: they are the plate balance of the section 0 (and, if a model is wanted, the FVM board with a computed h on one face and a manual small h on the other, which the program cannot mix yet; recorded in INTEGRATION.md as a limit).
* **What a failure means:** a deviation above 5 % on a local-heater board that the multiplier does not fix points to the copper (thickness, spreading), the vias, the heater contact or the supply wires, not to the horizontal law (that difference is 0.2 to 1.7 %, README section 6); only board D separates the law.

## 6.1 One page, to print

1. Offsets, isothermal, 30 min. 2. Glue thermocouples (T1 bottom under the heater; T2, T3 short axis 14 and 26 mm; T4, T5 long axis 24 and 42 mm; T6 air). 3. Boards A, B, C: horizontal up, turned over, vertical, three powers each (A 0.75, 1.5, 2.25 W; B 0.3, 0.6, 0.9 W; C 0.33, 0.66, 1.0 W), 30 min each, smoke test every point. 4. Board D: up and down at 2 and 4 W (mineral wool; 2 W only on XPS). Board E: up and down at 3, 6, 12 W. 5. Write V, I, T1 to T6, the time and the room, every point. 6. Fit and compare as in section 6.

## 7. Limits of the plan

* The predictions are from the program's own functions: the "true" film is a model, not a measurement. The expected accuracy (2 to 3 % of the rise, the model error 3 to 5 %) is an estimate, not demonstrated.
* The edges (1.6 mm) and the corners are 4 % of the area of the faces and are ignored in the board D balance (an edge coefficient of the program's default would move both ratios in the same direction).
* ENIG and mask emissivities are textbook values (0.05 to 0.1 and 0.9), not measured by me.
