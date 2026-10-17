# Research (open investigations)

This file collects investigations that are **not implemented yet**: what was read, what was simulated, what is still open. It is used until the work is implemented;
then the findings are folded into `docs/models.md`, `docs/validation.md` and `docs/roadmap.md`, the scripts stay in `examples/`, and this file goes back to the empty template below.
Values marked *assumed* are not from a datasheet. Everything is reproducible with the scripts named in each section.

## Open now: the Component element (branch `feature/component-element`)

Reproduce: `examples/component_study.py`, `examples/heatsink_study.py`, `examples/block_contact_study.py`.

### Which resistance goes in (datasheets re-read on 2026-10-17)

Thermal figures found in the PDFs (text extracted from the files):

| Part | Junction-to-bottom/pad ("down") | Junction-to-board | Junction-to-top | Only junction-to-ambient? |
| :-- | :-- | :-- | :-- | :-- |
| MOSFET TI CSD17308Q3 | `RθJC` 4.5 K/W max (case = drain pad; measured on 1 in², 2 oz pad) | not given | not given | `RθJA` 46 typ, 58 max (1 in²), 165 max (minimum pad) |
| Buck TI LMR36510 | `RθJC(bot)` 4.3 | `RθJB` 13.6, `ψJB` 13.8 | `RθJC(top)` 54, `ψJT` 4.3 | `RθJA` 42.9 |
| LDO TI TPS7A47 | `RθJC(bot)` 1.7 | `RθJB` 11.9, `ψJB` 11.9 | `RθJC(top)` 27, `ψJT` 0.3 | `RθJA` 32.5 |
| Schottky SS12 (SMA) | `RθJ-L` 20 (junction to terminal) | not given | not given | not in the extracted text (65 in the earlier reading) |
| Schottky SS54 (SMC) | not given | not given | not given | `RθJA` 15 only |
| Resistor Vishay WSL | not given | not given | not given | none: only the power rating at 70 °C |

**Answer to "do manuals always give a number down?"**: no. Four of six give a downward number (`θJC(bot)` or the MOSFET's `RθJC`, `θJ-L` of the SMA diode); the SS54 and the resistor do not. TI's own text says the LDO "θJCbot can be found in" its thermal table and that θJA is the sum of θJCbot and the PCB.
Rule for the form (one field, "junction-to-pad resistance θ"), in order of preference: (1) a downward number (`θJC(bot)`, `RθJC` of a power MOSFET, `θJ-L`, `Rth j-sp`) used as is; (2) only `θJB`/`ψJB`: `Tj = T_ring + ψJB·P` with the board temperature in a ring 0.5 to 1.5 mm outside the body (least pessimistic), or `θJB` as θ (pessimistic by the datasheet board's spreading, 15 K and 7 K on the two chips); (3) only `θJA` on a stated board: θ from the virtual test (`θJA` minus what our model gives for that board; section below); (4) only a power rating at a temperature (resistors): `(Tmax − T_rating)/P_rating`.
The program should say which route was used and warn when `θ·P` exceeds the board's own rise (the number is then probably not a junction-to-pad value).

**When the manual has no usable junction number (2026-10-17 follow-up).**
* *Typical values by package family* (indicative, from web summaries of vendor notes, **not** datasheets; to be replaced by a datasheet value whenever one exists): QFN 2 to 10 K/W, power QFN 1 to 5, DFN 5 to 15, D2PAK 0.5 to 1, TO-220 1 to 2, SOT-223 about 15 (junction to tab); the SMA diode of our set gives 20 (`θJ-L`). The form can offer these as a starting point for a family with a visible "typical, not from your datasheet" note; for chips whose `θ·P` is a few percent of the rise (section above) the error is of no consequence.
* *θ from `θJA`* (the "virtual test": `θ = θJA − R_board`, where `R_board` is what our model gives for the board the datasheet states): **it does not work when the board is not fully stated.** The SS12 gives `θJA` 65 K/W "on 5 × 5 mm pads"; our model of two 5 × 5 mm pads (heat entering by the terminals, 1.6 mm FR-4, 35 µm, board 30 to 80 mm) gives 112 to 168 K/W, so `θ` comes out negative (−47 to −104 K/W); only with 10 mm pads does it approach zero (−8 K/W). The datasheet board must have had more copper than stated. Rule: if the result is negative or larger than `θJA`, ignore it and use the typical value; `θJA` is never an input (the manufacturers say so themselves).
* *Where the heat enters*: for two-terminal parts (SMA diode) the heat enters the board by the **terminals**, not under the body; the footprint of the source should be the terminal areas (two small rectangles), or the whole part when a body-footprint pad exists.
* *Nothing at all*: `θ = 0` (plain Source); the report shows the board temperature under the part and says the junction is hotter.

### R1. Is the parametrisation worth it? Study on five real parts (2026-10-17)

`python examples/component_study.py`. Five parts of section 1.6 on a 60 × 60 mm, 2-layer board (copper pad under the part on both faces, thermal vias under footprints of 3 mm and more, computed natural convection, FVM at 0.5 mm). Level 0 is today's Source (the answer is the hottest board point under the part); level 1 adds **one** junction-to-pad resistance (`Tj = T_max + P θ`); level 2 adds a top path (junction node, section 1.8).
Sources of the literature used for the plan: the two-resistor model is accepted up to ±30 % on `Tj` and is better the closer the application is to the test conditions, better still when the heat goes mainly into the board or a heatsink [18, ROHM, Electronics Cooling 2007, 2019]; `ΨJT` and `ΨJB` are the recommended way to estimate `Tj` on a functional board; compact models (DELPHI) are for boundary-condition independence and need data the makers do not publish.

**A. What the one resistance adds** (`θ` is `θJC(bot)`, `θJ-L` or the derived value of a resistor):

| Part | P [W] | θ [K/W] | Pad | Board under part (level 0) | Tj (level 1) | P·θ | Share of the rise |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| MOSFET CSD17308Q3 | 2 | 4.5 | 8 mm | 227.4 °C | 236.4 °C | 9.0 K | 4 % |
| MOSFET CSD17308Q3 | 2 | 4.5 | 25 mm | 98.6 °C | 107.6 °C | 9.0 K | 11 % |
| LDO TPS7A47 | 1.5 | 1.7 | 8 mm | 176.7 °C | 179.2 °C | 2.5 K | 2 % |
| LDO TPS7A47 | 1.5 | 1.7 | 25 mm | 84.8 °C | 87.3 °C | 2.5 K | 4 % |
| Buck LMR36510 | 0.8 | 4.3 | 8 mm | 109.9 °C | 113.3 °C | 3.4 K | 4 % |
| Buck LMR36510 | 0.8 | 4.3 | 25 mm | 59.3 °C | 62.8 °C | 3.4 K | 9 % |
| Schottky SS12 (SMA) | 0.5 | 20 | 8 mm | 85.6 °C | 95.6 °C | 10.0 K | 14 % |
| Schottky SS12 (SMA) | 0.5 | 20 | 25 mm | 50.9 °C | 60.9 °C | 10.0 K | 28 % |
| Resistor 0603, 0.1 W | 0.1 | 1000 (derived) | 8 mm | 38.9 °C | 138.9 °C | 100 K | 88 % |
| Resistor 0603, 0.1 W | 0.1 | 1000 (derived) | 25 mm | 31.6 °C | 131.6 °C | 100 K | 94 % |

**B. Sensitivity** (pad 25 mm): `θ` ±30 % moves `Tj` by only ±0.8 K (LDO), ±1.0 K (buck), ±2.7 K (MOSFET), ±3.0 K (diode), but ±30 K for the resistor, where the derived number is the whole answer.
**The number chosen matters more than its accuracy**: entering `θJB` instead of `θJC(bot)` adds 15.3 K to the LDO (87.3 → 102.6 °C, +25 % of the rise) and 7.4 K to the buck (62.8 → 70.2 °C, +20 %) because the board's spreading would be counted twice. The virtual JEDEC board (76.2 × 114.3 mm, 2s2p) cannot settle which is right: the datasheets do not give the via array of their test boards, and the program brackets `RθJA` of the TPS7A47 (32.5 K/W) between 51 K/W with no vias and 22 K/W (with `θJC(bot)`; 32 K/W with `θJB`) with nine vias, and the LMR36510 (42.9) between 54 and 25 (34 with `θJB`). So the virtual test is a plausibility check, not a calibration.

**C. A top path** (junction node joined to the footprint by `1/θ`; bare mould = `θJC(top)` + 15 W/m²K on the body; clip-on = 12 K/W heatsink + 1 K/W paste; pad 25 mm):

| Part | Level 1 Tj | Bare mould (heat through the top) | With the 12 K/W heatsink (heat through the top) | θJC(top) |
| :-- | --: | --: | --: | --: |
| MOSFET CSD17308Q3 | 107.6 °C | 104.6 °C (0.6 %) | 67.4 °C (49 %) | 30 K/W (assumed) |
| LDO TPS7A47 | 87.3 °C | 83.2 °C (1.4 %) | 55.5 °C (51 %) | 27 |
| Buck LMR36510 | 62.8 °C | 60.6 °C (1.3 %) | 46.9 °C (41 %) | 54 |
| Schottky SS12 | 60.9 °C | 59.1 °C (1.1 %) | 42.9 °C (49 %) | 60 K/W (assumed) |

**Conclusions (what is worth parametrising)**
1. **One resistance to the pad: yes.** It is the only way to get `Tj` (the junction is hotter than the board point), it adds 2 to 28 % of the rise for chips and about 90 % for a resistor, it comes straight from the datasheet and ±30 % in it is a few kelvin. With the `Tj,max` limit it is the whole of what a designer asks of a part.
2. **Top path: only with a heatsink.** A bare mould carries about 1 % of the heat and changes `Tj` by 2 to 4 K (conservative to ignore); a clip-on heatsink takes 41 to 51 % and lowers `Tj` by 16 to 40 K, which the single resistance cannot see. So the top path is an **optional second block** (a heatsink resistance in K/W plus `θJC(top)`), invisible unless filled.
3. **Not worth it for now:** `ΨJT`/`ΨJB` estimates, full 2R as two mandatory numbers, DELPHI, the Foster chain (only for fast transients of the package itself), presets by part type (the form asks for one number and says which datasheet value to take).
4. **Which value**: `θJC(bot)`, `θJ-L` or `Rth j-sp` when the datasheet has them (the board's spreading is already in our model); `θJB` only when the pad and vias of the board are not modelled; a resistor: `(Tmax − T_rating)/P_rating`.

### R2. Heatsinks and interface materials: typical values and what they do (2026-10-17)

**Values found** (sources read; the presets of the application are *assumed typical values inside these ranges*, always editable):
* metals (Ferrotec material table, Engineering ToolBox): aluminium 204 W/mK (2.71 g/cm³, 0.90 J/gK), copper 386 (8.96, 0.385), brass 111 (8.49, 0.34), stainless 304 13.8 to 14.4 (8.01, 0.46), carbon steel 54 (heat capacity 0.49 J/gK, textbook value); alloys of aluminium vary (190 for 3003 and 2014);
* thermal grease: bond line of 7 to 20 µm at best and 0.05 to 0.1 K cm²/W in the laboratory (Dow Corning); in assembly 25 to 100 µm and 1 to 5 W/mK; it needs pressure to reach its best value; it can pump out with thermal cycling;
* gap pads: 1 to 6 W/mK and 0.5 to 1.2 mm; thermal adhesives 0.5 to more than 6 W/mK; phase-change pads behave like grease above 55 to 60 °C.
**Confirmed on the web (2026-10-17)**: the resistance of a thermal joint is `R_joint = BLT/(k·A) + (R''c1 + R''c2)/A` (bond line over bulk conductivity plus a contact resistance at each face; ASTM D5470 fits both from measurements at several thicknesses). Measured totals (Electronics Cooling, ASTM D5470 round robin, 2014): Arctic Silver 5 paste **32 mm²K/W = 0.32 K cm²/W** at 300 kPa (30.9 at a 23.5 µm bond line), a ceramic paste 41 mm²K/W = 0.41 K cm²/W, a 1.575 mm gap pad **12.1 K cm²/W** at 690 kPa. So a good paste is 0.3 to 0.4 K cm²/W, not the 0.1 of laboratory greases, and the *apparent* conductivity (thickness over measured resistance) is well below the bulk value of the data sheets.
Presets (resistance per area, with the apparent `k`): good paste 1.5 W/mK × 50 µm = 0.33 K cm²/W (matches the measured pastes); **paste, default when unknown** 2 W/mK × 100 µm = 0.5; soft gap pad 3 × 0.5 mm = 1.7; gap pad 1 × 0.5 mm = 5; hard gap pad 1 × 1 mm = 10. On a package the resistance is `R''/A` (K/W): 0.5 K cm²/W over 3.3 × 3.3 mm is 4.6 K/W.

**Simulated** (`python examples/heatsink_study.py`, parts of section 1.9b, pad 25 mm, 12 K/W clip-on heatsink on top of the package, Tj in °C and heat share through the top):

| Part | no heatsink | good paste 0.33 | default paste 0.5 | soft pad 1.7 | gap pad 5 | hard pad 10 |
| :-- | --: | --: | --: | --: | --: | --: |
| MOSFET 2 W (3.3 × 3.3 mm) | 107.6 | 68.4 (48 %) | 69.0 (47 %) | 73.1 (42 %) | 81.0 (32 %) | 87.5 (23 %) |
| LDO 1.5 W (5 × 5 mm) | 87.3 | 55.6 (51 %) | 55.8 (50 %) | 57.4 (47 %) | 61.2 (41 %) | 65.1 (34 %) |
| Buck 0.8 W (4.9 × 3.9 mm) | 62.8 | 47.0 (41 %) | 47.1 (40 %) | 47.8 (38 %) | 49.5 (33 %) | 51.4 (28 %) |
| Schottky 0.5 W (4.3 × 2.6 mm) | 60.9 | 43.2 (48 %) | 43.3 (48 %) | 44.4 (45 %) | 46.9 (38 %) | 49.4 (30 %) |

* **The interface matters on the top of a small package** (MOSFET: 68 °C with a good paste against 88 °C with a hard pad): 10 K cm²/W over 11 mm² is 92 K/W, far more than the heatsink itself. The default paste costs only 0.6 to 1 K against a good paste, so it is a safe default; a gap pad should be typed.
* **Under the board, a metal block helps by 9 K on the MOSFET** (107.6 → 98 °C, block 30 × 30 × 3 mm, natural convection) **and the metal and the interface hardly matter**: aluminium and copper differ by 0.1 K, stainless steel is 1 K worse, and a hard pad 2 K worse than a good paste. With fins (extra h 60 W/m²K) the whole range of metals spans 71.7 to 72.2 °C at 6 mm. What matters is the **block thickness and area and the cooling of its surface** (1 mm 76.8, 3 mm 74.3, 6 mm 71.7 °C with fins), because the board has already spread the heat before the block sees it. The material choice is useful as a convenience (heat capacity for the time simulation, large thin plates), not as a design lever.

**When the datasheet only gives `θJB` (or `ψJB`)**: three ways, from the least to the most conservative (Tj of the LDO on a 25 mm pad, true value 87.4 °C with `θJC(bot)` 1.7 K/W): (1) **`ψJB` with the program's board temperature** `Tj = T_ring + ψJB·P`, with `T_ring` the mean board temperature in a ring 0.5 to 1.5 mm outside the package body: 93.7 °C (+6 K) for the LDO (`ψJB` 11.9) and 65.1 against 62.8 °C for the buck (`ψJB` 13.8); this is the method the manufacturers recommend for a real board and it needs no `θJC(bot)`;
(2) **`θJB` as the junction-to-pad resistance** with the pad and vias drawn: 102.7 °C (+15 K) and 70.2 °C, pessimistic by the spreading of the datasheet's own board, counted twice; (3) the same with a simple heater and no copper drawn, where `θJB` is the better number. The application should say this next to the field, offer the ring temperature as an output ("board temperature 1 mm from the package") and warn when `θ` is larger than the board's own rise.

**What value is "perfect contact"? (simulated 2026-10-17, MOSFET 2 W; `Tj` change against `R'' = 0`)**

| R'' [K cm²/W] | Top heatsink chain (12 K/W + θJC(top) 30): ΔTj | Block under the board: ΔTj |
| --: | --: | --: |
| 0.001 | +0.00 | +0.00 |
| 0.01 | +0.04 | +0.05 |
| 0.03 | +0.13 | +0.11 |
| 0.1 | +0.43 | +0.22 |
| 0.3 (a good paste) | +1.27 | +0.37 |
| 0.5 (default paste) | +2.07 | +0.47 |
| 1 | +3.93 | +0.67 |
| 5 (gap pad) | +14.0 | +1.57 |

**Perfect contact = `R'' = 0.01 K cm²/W` (1e-6 m²K/W)**: it changes the result by 0.05 K against an ideal zero, it is 30 times better than the best measured paste, and the model's floor (1e-7 m²K/W = 0.001 K cm²/W) stays below it. Below 0.003 nothing changes. In the interface form: "full contact" = this value (or a very high `k`); the program says "perfect contact assumed (optimistic)" when no interface is chosen.

### R3. A heatsink that is larger than its contact (2026-10-17)

**The question**: a big plate or heatsink touches the copper (or a component) only on a small area. Today a Heatsink block conducts to the board over its whole outline: through the interface over copper and, in series with the FR-4, over bare laminate. A real heatsink resting on standoffs, on a pad or on one component touches only there.
**Literature** (spreading resistance, Lee, Song, Au and Moran 1995; Yovanovich and Muzychka; Ellison): a small source on a larger plate has `R = R_0 + R_c` (average sink resistance plus the maximum constriction resistance), accurate to about 5 % when the aspect ratio is below 2.5 and the plate is square-ish
(Electronics Cooling: "Calculating spreading resistance in heat sinks", 1998; "Simple formulas for estimating thermal spreading resistance", 2004, reported errors −2 to +5 %). The numerical example of the 1998 article: aluminium 100 × 100 × 1.3 mm, 200 W/mK, catalogue resistance 1.0 K/W, source 25 × 25 mm, `R_c` = 0.66 K/W.
**Check of our plate model** (`block_contact_study.py`, the lateral `k·t` conductance of the block layer with a uniform film coefficient): `R_c` = 0.69 K/W, total 1.69 against 1.66 K/W, +4.5 %, inside the stated 5 % of the correlation. So the block layer reproduces the published spreading resistance.

**Simulation** (MOSFET 2 W, board 60 × 60 mm, 25 mm pads, Al block 40 × 40 × 3 mm under the board, default interface 5 K cm²/W; prototype where the contact conductance of the block is limited to a centred patch and the rest of the block faces an air gap):

| Contact patch | Tj [°C] |
| :-- | --: |
| whole block (40 × 40), as the program does today | 87.8 |
| 25 × 25 mm (the copper pad) | 96.6 |
| 12 × 12 mm | 97.0 |
| 6 × 6 mm | 99.5 |
| none (block floating over the board) | 124.3 |

What it says: (1) most of the gain comes from the copper pad area; shrinking the patch from 25 to 12 mm costs 0.4 K but to 6 mm costs 3 K; (2) touching the bare laminate around the pad is worth 9 K in the model today (through the FR-4), which is optimistic if the real heatsink only touches the pad; (3) with no contact the board gets **hotter than without the block** (124 against 107.6 °C) because the model hides the board face under the block from the air (a conservative choice; a real gap still convects and radiates a little). That last factor needs a decision.
**Convection (and conduction) outside the interface (researched 2026-10-17).** Under a block that does not touch the board the face is not insulated: across a thin air gap the heat goes by **conduction of still air** (`h = k_air/g`, `k_air` about 0.028 W/mK at 55 °C, so 28 W/m²K for 1 mm) plus **radiation between the parallel faces** (`h_r = 4σT³/(1/ε₁ + 1/ε₂ − 1)`: 6 W/m²K for an anodised block of emissivity 0.8, 0.7 for bare aluminium of 0.1, against the board's 0.9). Natural convection inside the gap only starts when the Rayleigh number of the gap exceeds the critical value of a horizontal layer (1708); below it the Nusselt number is 1 and conduction rules (sources: heat-transfer handbooks, `ht` documentation, Purdue ME 418 notes), which holds for gaps up to about 7 mm at 60 K and about 12 mm at 20 K. Above that the Hollands correlation raises `h = Nu k/g`.
The 2b table below reruns the patch study with this gap instead of an insulated face (MOSFET 2 W, Al block 40 × 40 × 3 mm, bare aluminium, patch = the interface area, `Tj` in °C):

| Gap outside the contact | patch 25 mm | 12 mm | 6 mm | none |
| :-- | --: | --: | --: | --: |
| insulated face (previous table) | 96.6 | 97.0 | 99.5 | 124.3 |
| 0.5 mm (h = 57 W/m²K) | 92.2 | 93.2 | 95.7 | 101.7 |
| 1 mm (29) | 93.7 | 94.5 | 97.3 | 106.1 |
| 2 mm (15) | 94.8 | 95.5 | 98.2 | 110.5 |
| 5 mm (6) | 95.7 | 96.3 | 98.9 | 115.6 |

So the insulated face was too pessimistic: a block 1 mm above the board still takes heat through the air (106 against 124 °C with no contact at all) and a small patch of contact plus a 1 mm gap is within 1 to 2 K of the insulated value for patches of 12 mm and more. With a big gap (5 mm and more) the block mostly hinders (115.6 °C against 107.6 °C for the bare board), because the board face loses its direct convection.
**Rule proposed**: outside the interface the board face is coupled to the block through `h = k_air/g + h_r` (gap `g` a parameter, default 1 mm, emissivities of the board 0.9 and of the block a parameter, default 0.5); if the gap is larger than 7 mm the block is taken as not covering the face (the face keeps its free convection and the block only takes heat through the interface). Under the interface the face is covered, as now.

**Proposal for the model (superseded by R5: the contact area is the interface area)**: the Heatsink gets an optional **contact area** (a rectangle or polygon inside its outline; default: the whole outline, as now). The interface conductance exists only over `contact ∩ block ∩ copper` (and over laminate only if the user says the heatsink touches it); outside it the block faces an air gap. The board face under the block outside the contact keeps a fraction of its coefficient (a parameter, default 0.5, to settle).
For a heatsink **on top of a component** the same machinery applies with the contact patch equal to the component footprint: a plate layer whose contact is the junction node through `θJC(top) + paste`, with no contact to the board. This gives the spreading resistance of the plate for free.

### R5. Many levels in a chain: package, interface, board, interface, metal (2026-10-17)

**Interface as the contact area (the maintainer's proposal, 2026-10-17).** A thermal interface (paste, pad, adhesive) is a layer with its own **area** (a polygon, default the whole contact face), material (`k`) and thickness, hence `R'' = t/k`. Where the interface exists the two sides are joined with `G = A/R''`; where it does not exist there is an air gap (no conduction in the first version).
A surface that is in full contact is an interface with a very high `k` (or a very small `t`); a partial contact is a smaller polygon. This replaces the separate "contact polygon" of R3: one object, one place to type the numbers. It applies to the heatsink under the board (interface between board and metal) and to the top of a component (interface between package and heatsink).
Open: how much of the board's own convection to keep under a block outside the interface (0.5 proposed).

**How the levels combine.** Every level adds one conductance in series and, where heat can leave, one parallel branch; the program solves one sparse matrix, so the number of levels does not make the mathematics harder, only longer to describe:

```
                      heatsink (K/W or plate)  -- ambient
                           |  interface on top (R''/A)
             package top --+  theta_JC(top)
                           |
 junction J ---------------+
      |  theta_down (1/theta per footprint cell)
 board cells (copper layers, vias, FR-4) -- faces (h) -- ambient
      |  interface under the board (G = A/R'' over the interface area)
 metal block layer (k t, exposed surface, sides) -- ambient
```
Heat from `J` splits between the top chain and the board in the inverse ratio of their resistances; the board's share spreads sideways, leaves through its faces and, where the block touches it, through the block.

**Simulation** (`python examples/chain_study.py`; junction node, board faces at constant `h` from the board alone, pad 25 mm, default paste 0.5 K cm²/W, heatsink 12 K/W on top, aluminium block 30 × 30 × 3 mm under the board):

| Part | Case | Tj [°C] | Heat through the top | Heat through the block |
| :-- | :-- | --: | --: | --: |
| MOSFET 2 W | board only | 105.0 | 0 % | 0 % |
| | + block under the board, paste 0.5 | 95.6 | 0 % | 27 % |
| | + block, gap pad 5 K cm²/W | 96.7 | 0 % | 28 % |
| | + top heatsink with paste (chain 46.6 K/W) | 68.1 | 46 % | 0 % |
| | + both | 65.2 | 43 % | 16 % |
| LDO 1.5 W | board only | 84.0 | 0 % | 0 % |
| | + block, paste 0.5 | 72.0 | 0 % | 28 % |
| | + top heatsink with paste (chain 41.0 K/W) | 55.1 | 49 % | 0 % |
| | + both | 51.6 | 43 % | 16 % |

The effects are **not additive**: the block alone lowers the MOSFET by 9 K and the top heatsink by 37 K, both together by only 40 K, because the top heatsink already takes 43 to 46 % of the heat and the block's share falls from 27 to 16 %. A change of the paste under the block (0.5 to 5 K cm²/W) moves `Tj` by 1 to 2 K; the same change on top moves it by 10 to 20 K (section R2).

### R4. What else may be missing (2026-10-17)

1. **Power that depends on temperature (electro-thermal feedback)**: the on-resistance of a power MOSFET rises with temperature (about 1.5 to 2 times its room-temperature value at 175 °C; search summary of vendor notes), so the dissipation grows with `Tj`. With `P = P0 (1 + α (Tj − 25))` and the same board, the MOSFET of the study (2 W at 25 °C, 107.6 °C without feedback) reaches 138.6 °C for α = 0.33 %/K, 165.8 °C for 0.5 %/K and 210 °C for 0.67 %/K (power 2.75, 3.41, 4.48 W): a design that looks fine at nominal power can exceed `Tj,max`. It is the same kind of loop as the computed `h` (cheap, a linear scalar iteration). Proposal: an optional "power temperature coefficient (%/K)" on the heater/component, off by default, with the converged power reported. LED efficiency falling with temperature is the same mechanism with the opposite sign of the benefit.
2. **Maximum power at `Tj,max`** (derating): the model is linear for constant coefficients, so `P_max = P·(Tj,max − T_amb)/(Tj − T_amb)`; one line in the report per component.
3. **Packages with several dies or several heat sources** (dual MOSFETs, modules): two heaters inside one footprint already work (power adds up); a per-die junction would need one θ per die.
4. **Pulsed operation of a package**: the transient impedance `Zth(t)` curves of MOSFET datasheets (a Foster chain) are the later step; with the current time simulation the package has no capacity, so a short pulse sees `θ·P` instantly (conservative).
5. **Ambient inside an enclosure** is the user's ambient; the program does not model the air heating up. A note in the interface.
6. **Solder attach of the pad** is part of the board side (not of `θJC(bot)`, measured on a cold plate with grease): a 25 µm solder layer adds a fraction of a K/W; ignored, to mention in the help text.

### Open questions for the maintainer

1. Thermal interface of a top heatsink optional (agreed): without it the program assumes perfect contact (optimistic); keep a visible note and offer the default paste (0.5 K cm²/W)? 
2. Heatsink contact area = the area of its interface (R5: a polygon with the paste's `k` and thickness, default the whole contact face, full contact `R'' = 0.01 K cm²/W`); outside it the air-gap coupling of R3 (gap parameter, default 1 mm)? (answered by the maintainer's proposal; confirm)
3. Heatsink on a component as a plate layer (spreading in the plate) or only as a K/W number from the datasheet in the first version?
4. Include the power temperature coefficient in the first Component delivery?

## Template (what this file looks like when nothing is pending)

```
# Research (open investigations)

Nothing pending. Add a section per investigation: the question, what was read (with links), what was simulated (script and numbers), the proposal and the open questions.
When it is implemented, fold the findings into models.md, validation.md and roadmap.md and delete the section.
```
