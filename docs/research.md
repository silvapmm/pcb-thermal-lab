# Research (open investigations)

This file collects investigations that are **not implemented yet**: what was read, what was simulated, what is still open. It is used until the work is implemented;
then the findings are folded into `docs/models.md`, `docs/validation.md` and `docs/roadmap.md`, the scripts stay in `examples/`, and this file goes back to the empty template below.
Values marked *assumed* are not from a datasheet. Everything is reproducible with the scripts named in each section.

## Open now: the Component element (junction node, heatsink scenarios, Foster chain)

**Decided (2026-10-17) and implemented the same day:** θ in the worst case (all the power enters the board; one junction-to-pad number; `θJA` never an input); a top heatsink as a fixed `θsa` in K/W only (scenarios noted in `docs/roadmap.md` 1.11); K/W only for the heatsink on a component (R8). The power temperature coefficient went in with the first delivery. The fixed-`θsa` top path was implemented on 2026-10-21 (`docs/models.md` section 6, `docs/validation.md` section 9, `examples/top_path_study.py`); what is below about scenarios, the plate layer and the interface with its own area is the part still open.

Reproduce: `examples/component_study.py`, `examples/heatsink_study.py`, `examples/block_contact_study.py`.

### Implemented on 2026-10-17 and what stays open from it

The junction-to-pad resistance θ (worst case), the junction limit with its margin and power limit, the `ψJB` ring estimate, the power temperature coefficient and the package-family typical values are implemented and documented in `docs/models.md` section 6 and `docs/validation.md` section 9 (the datasheet table, the study on five parts and the sensitivity are there).
What stays here is the **top path** of the study, behind the top path now implemented (2026-10-21; junction node joined to the footprint by `1/θ` and to the ambient through `θJC(top)` + interface + heatsink; `examples/component_study.py`, level 2):

| Part | Tj without top path | Bare mould (heat through the top) | With a 12 K/W clip-on heatsink (heat through the top) | θJC(top) |
| :-- | --: | --: | --: | --: |
| MOSFET CSD17308Q3 | 107.6 °C | 104.6 °C (0.6 %) | 67.4 °C (49 %) | 30 K/W (assumed) |
| LDO TPS7A47 | 87.3 °C | 83.2 °C (1.4 %) | 55.5 °C (51 %) | 27 |
| Buck LMR36510 | 62.8 °C | 60.6 °C (1.3 %) | 46.9 °C (41 %) | 54 |
| Schottky SS12 | 60.9 °C | 59.1 °C (1.1 %) | 42.9 °C (49 %) | 60 K/W (assumed) |

A bare mould carries about 1 % of the heat (2 to 4 K); a heatsink takes 41 to 51 % and lowers `Tj` by 16 to 40 K, which the single resistance cannot see: this is the case that justifies the junction node.

### R3. Heatsink air flow: catalogue values against a scaling factor (2026-10-22)

**Question.** Should the heatsink on a package have its own forced-air option, computed from the natural-convection θSA, or should it use catalogue values by flow?

**What was done.** The typical heatsinks of the library (`defaults.json`, `heatsinks`) were compiled from catalogues (Wakefield-Vette, Fischer, Aavid, SAME Sky; sources in `docs/models.md`). The ratio θSA(forced) / θSA(natural) of the catalogues was compared with the factors of the volumetric-resistance guide (Electronics Cooling, *How to select a heat sink*: 500 to 800 cm³·K/W natural, 150 to 250 at 1 m/s, 80 to 150 at 2.5 m/s, 50 to 80 at 5 m/s; mid-values give 0.31 at 1 m/s and about 0.22 at 2 m/s):

| Heatsink | Catalogue ratio | Guide factor | Difference |
| :-- | --: | --: | --: |
| BGA 40×40×18 mm, 1 m/s | 0.33 | 0.31 | within 6 % |
| BGA 40×40×18 mm, 2 m/s | 0.20 | about 0.22 | within 15 % |
| TO-220 board-level, 2 m/s | 0.34 | about 0.22 | the guide is about 35 % low (a small heatsink uses the air worse) |
| Pin-fin 10×10 mm, "forced air" (speed not stated) | 0.52 | not comparable | speed unknown |

**Findings.** A scaling factor is a fair estimate for a large heatsink and misses by tens of per cent for a small one; the natural-convection value itself falls as the temperature rise grows (quoted at a 75 K rise by Boyd/Aavid, 10.8 K/W at 1 W against 7.68 at 75 K for the SAME Sky part). The air speed of the board (Environment) acts on the board faces only, so a heatsink with its own fan has a different flow.

**Decision.** Implemented: catalogue values by flow, two lists (heatsink, then air flow, only the flows the catalogue gives). Not implemented, in `docs/roadmap.md`: "other speed (estimated)" by a factor, the default flow linked to the board air speed, heatsinks with a fan (Boyd 40 mm sets about 1.1 K/W), the heatsink defined by its geometry with the fin channel effect, and the scaling of θSA with the temperature rise.

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

### R6. The heatsink and its convection: several scenarios, one number (2026-10-17)

**What the catalogues give**: one resistance `θsa` (K/W, heatsink to ambient) at stated conditions, often a curve against power or air velocity, and little else. The program has to turn it into something that behaves correctly in the scenarios the user runs. Read and confirmed on the web:
* chain: `Rja = Rjc + Rcs + Rsa` (junction-case, case-to-sink interface, sink-to-ambient) and `Rsa = (Ts − Ta)/Q − Rjc − Rcs` for the required heatsink (Electronics Cooling, "How to select a heat sink"); spreading resistance of a source much smaller than the base adds 5 to 30 % (the plate model of R3 covers it);
* **natural convection**: `W = β·ΔT^1.25`, so the resistance `ΔT/W` falls as `ΔT^−0.25`: a heatsink at a 30 K rise is 1.257 times worse than the catalogue value at 75 K (Alpha Novatech and similar catalogues; `(75/30)^0.25 = 1.257` agrees); a low power makes the heatsink worse, a high power better;
* **orientation and finish**: a bad orientation can be about 25 % worse; anodised aluminium radiates more than bare (emissivity about 0.8 against 0.1), which matters in natural convection;
* **forced convection**: the volumetric performance `C = R·V` (cm³ K/W) is 500 to 800 in natural convection, 150 to 250 at 1 m/s, 80 to 150 at 2.5 m/s and 50 to 80 at 5 m/s, i.e. factors of about 0.31, 0.18 and 0.10 on the natural value; natural and forced convection cross at 1 to 2 m/s; the same table gives the **size** of a heatsink from the resistance wanted: 20 cm³ is 25 to 40 K/W in natural convection and 4 to 7.5 K/W at 2.5 m/s;
* altitude lowers the performance of a heatsink in thin air (the source's 0.80 at 3000 m is ambiguous between a resistance and a performance factor; to check before use); a finer fin pitch is better only if the flow can enter.
Interface values of the same article: 0.07 to 0.81 in²°C/W (0.45 to 5.2 K cm²/W), consistent with the presets.

**Approach with only `θsa` (proposal)**: the heatsink is a conductance `1/θsa` from its base to the ambient (a lumped node on a component, spread uniformly over the plate area on a block under the board) with a **scenario** that sets how `θsa` varies:
1. *Fixed* (default; the number is used as given: the simplest and what the datasheet states for its own conditions);
2. *Natural convection*: `θsa = θref·(ΔTref/ΔT)^0.25` (`ΔTref` from the datasheet, default 75 K), with `ΔT` the heatsink's own rise, solved by the same fixed-point loop as the computed `h` (converges in a few iterations);
3. *Forced*: `θsa = θnatural × f(v)` with `f` 1, 0.31, 0.18, 0.10 for 0, 1, 2.5 and 5 m/s, or the points of the datasheet curve.
One environment setting would drive all of it: the air speed already used for the board faces (computed `h`) sets the heatsink scenario too, and the orientation sets the factor (a vertical board and vertical fins are the good case).
**Simulation** (`python examples/heatsink_convection_study.py`; MOSFET with the top chain `θJC(top)` 30 (assumed) + default paste 4.6 + `θsa`, board `h` constant): with a 12 K/W catalogue value at 75 K the natural scaling gives 17.8 K/W at 2 W (a 25 K rise) and `Tj` 70.4 °C against 68.1 °C with the fixed number (+2.3 K, +4 K at 4 W the other way: 113.9 against 111.1); the same heatsink at 1, 2.5 and 5 m/s gives 65.7, 64.5 and 63.6 °C. The **scenarios change `Tj` by 2 to 7 K here because `θJC(top)` (30 K/W) limits the path**: a better heatsink or more air buys little on a plastic package and a lot on a part with a low `θJC(top)` (metal lid, bare die), which is why the scenario is worth a switch but the fixed value is a good default.

### R7. Vertical information and presentation (noted 2026-10-17)

* **Vertical (z) information to carry**: the stack-up (layer thicknesses and dielectrics, roadmap section 8), the height of the component above the board (the air gap `g` under a heatsink or plate, R3, comes from it), the orientation of the board (horizontal or vertical; the computed `h` already has it), and for enclosures the free height above the board. A "vertical layout" panel or a small side view would make the gap, the stack and the interfaces visible; to design with the maintainer.
* **Perfect contact in the interface form**: the value (0.01 K cm²/W) must be presented intuitively, for example as a named choice ("soldered or bonded: perfect contact") next to the pastes and pads, not as a number to remember; to design with the maintainer.

### R8. Heatsink on a component: plate or only K/W? (topic under discussion, 2026-10-17)

**Question**: is a plate model of the heatsink base (spreading in the metal) needed on top of a component, or is the catalogue `θsa` in K/W enough? The catalogue value already contains the spreading of the catalogue's own test source; what a small component adds is the conduction through the base under it and the spreading in the plate.
**Simulation** (`python examples/base_spreading_study.py`; 3D finite-volume plate 40 × 40 mm, uniform film `h = 1/(R0·A)` on the top, source on the bottom, catalogue 12 K/W; extra resistance on the mean temperature of the source, and its share of the whole top chain `θJC(top)` + paste + `θsa` = 46.6 K/W for the 3.3 mm MOSFET, 41 K/W for the 5 mm LDO):

| Base | 3.3 mm source | 5 mm source |
| :-- | --: | --: |
| aluminium 1 mm | 1.69 K/W (3.6 %) | 1.32 (3.2 %) |
| aluminium 3 mm | 0.75 (1.6 %) | 0.54 (1.3 %) |
| copper 3 mm | 0.40 (0.9 %) | 0.29 (0.7 %) |
| carbon steel 1 mm | 6.31 (13.5 %) | 4.90 (12.0 %) |
| carbon steel 3 mm | 2.83 (6.1 %) | 2.04 (5.0 %) |

So for aluminium or copper bases the spreading is 1 to 4 % of the top chain (it is inside the 5 to 30 % of the catalogue literature only for sources much smaller relative to the base *and* a low `θJC(top)`), and it matters (5 to 13 %) only for a thin base of a poor conductor such as steel. **Recommendation**: first version = K/W only (`θJC(top)` + interface + `θsa`), with a note that a thin steel or stainless base adds more; the plate model stays where it already exists (metal block under the board, where the geometry of contact and copper matters) and returns for the component top only if a case needs it.

### R4. What else may be missing (2026-10-17)

1. *(implemented: power temperature coefficient and the power limit at `Tj,max`; see `docs/models.md` section 6)*
2. **Packages with several dies or several heat sources** (dual MOSFETs, modules): two heaters inside one footprint already work (power adds up); a per-die junction would need one θ per die.
3. **Pulsed operation of a package**: the transient impedance `Zth(t)` curves of MOSFET datasheets (a Foster chain) are the later step; with the current time simulation the package has no capacity, so a short pulse sees `θ·P` instantly (conservative).
4. **Ambient inside an enclosure** is the user's ambient; the program does not model the air heating up. A note in the interface.
5. **Solder attach of the pad** is part of the board side (not of `θJC(bot)`, measured on a cold plate with grease): a 25 µm solder layer adds a fraction of a K/W; ignored, to mention in the help text.

### Open questions for the maintainer (all about the future heatsink on the IC and the interfaces)

1. Interface with its own area: default the whole contact face; perfect contact `R'' = 0.01 K cm²/W` shown as a named choice ("soldered or bonded"); outside the interface the air gap of R3 (default 1 mm)?
2. Heatsink on a component: K/W only (R8, spreading is 1 to 4 % of the chain for aluminium and copper)?
3. Heatsink scenarios (natural scaling, forced factors): later (`docs/roadmap.md`, "What we want to implement", Component).

## Open now: the heater as a pure source or as a component (to align, 2026-10-22)

**The situation.** One `Heater` carries two different things. (1) A **heat source**: a power in watts over a footprint on one layer ("5 W and that is it"). (2) A **component**: a part with a junction, a package and a way to the air through its top. All the fields are in the same form today:

| Box in Properties | Fields | What it is | Where the number comes from | When it is used |
| :-- | :-- | :-- | :-- | :-- |
| Part | Power | heat dissipated | you (or the Power calculator) | always |
| Junction | θ junction-pad (K/W) | resistance from the junction to the pad / board under the part | datasheet: RθJC(bottom or exposed pad), θJ-L, Rth j-sp (never θJA); or the family list | to report `Tj = T_board,max + P_board·θ`; without it the report gives the board temperature under the part only |
| Junction | *Typical θ by package family* (list) | fills θ with an indicative value | the library `package_theta` (web summaries, **not** datasheets) | only as a starting value, always replaced by the datasheet number |
| Junction | Tj max, ψJB, Power coefficient | junction limit (margin, power limit), second estimate of Tj from the board ring, power that changes with temperature | datasheet | optional reports and the power loop |
| Heatsink on the package | θSA (K/W) | resistance from a heatsink on top of the package to the air | the heatsink's datasheet at your air flow | **switches the top path on** (needs θ > 0 too) |
| Package top: junction to case | θJC(top), body thickness and material (helper), contact area | resistance through the package top, estimated from the body, area of the lid | datasheet RθJC(top); the helper `t/(k·A)` when it is missing | only when the top path is on |
| Interface: package top to heatsink | paste or pad (material, thickness, conductivity, resistance), divided by the contact area | the paste between package and heatsink | presets or the supplier | only when the top path is on |

**How they connect.** The top path is a chain `junction → θJC(top) → interface/contact area → θSA → ambient` in parallel with the way down through the board (`θ`). The program shares the power between the two: `Tj − Ta = (T_board,max − Ta + P·θ)/(1 + θ/R_top)`, with `R_top = θJC(top) + interface/area + θSA`; the heat that goes up is **not** put into the board (the board receives `P − P_top`), so a heatsink on the package cools the board too. Without θ or without θSA there is no top path and all the power enters the board (the worst case).

**Why it feels like two things.** It is: a pure source has no junction, so θ, Tj max, ψJB, the power coefficient and the whole top path make no sense for it; and a component with a heatsink on top needs the chain above. Today a pure source can show all those boxes (greyed when they cannot apply).

**Decided on 2026-10-22 (maintainer):** option 1 (a Type: heat source / component) is agreed; the family list fills the typical values and those values are settings (the library `package_theta` has now θ, θJC(top), Tj max and a note); the interface of a pure source is the one **under** the heater, between it and the board. The GUI was changed for this; the rest (naming, order of the boxes, the report of a source) is still to be tuned.

**Options to align (to discuss).**
1. A **Type** at the top of the heater: *Heat source* (power only, nothing else shown) or *Component* (junction, package, top path). A source could still carry a cooling on top without a junction (θ = 0: the case is the junction), a paste between a source and a metal block being what the user probably means by "an interface".
2. The **family list** becomes a library of packages (Preferences) with several typical columns (θ junction-pad, θJC(top), ψJT, ψJB, body size) that fill the component's fields at once, with the typical values shown below and editable, like the via fill; each with its note and source, always marked as indicative.
3. Clearer field names that say the datasheet line: *Junction-to-pad θ (RθJC bottom / θJ-L / Rth j-sp)*, *Junction-to-case top θJC(top)*, *Heatsink on the package θSA*.
4. The order of the boxes follows the heat: Part → Junction → Package top → Interface → Heatsink on the package, shown as a chain, with the live Tj and the heat share (top / board) below.
5. The datasheet "Thermal information" table mapped line by line to the fields (TI: RθJC(bot) → θ, RθJC(top) → θJC(top), ψJT → calculator, ψJB → ψJB) in the help.

## Open now: Gerber import and the mapping of copper to the grid (2026-10-22)

Branch `research/gerbers`; everything (scripts, tests, tables, sources) is in [`research/gerbers/README.md`](../research/gerbers/README.md). Summary:

**Question.** A Gerber is vector data, the FVM works on square cells and knows only the copper *fraction* of each cell. Can the vectors be converted exactly, and how should they feed the grid?

**Answers.**
* **Vectors to polygons: exact.** gerbonara (Apache-2.0) gives the primitives, shapely unions them in file order with the polarity (dark adds, clear subtracts); holes and islands are kept (one Uno-clone layer: 103 polygons, 80 holes, 43 285 vertices). The data model has no place for it yet: `Zone` is one polygon with a scalar `fill`, no holes.
* **Raster of the vectors: fine.** Area within 0.2 % at 0.1 mm pixels; a binary raster keeps the area but **interrupts** a trace thinner than about 1.4 pixels (pixel of at most half the thinnest trace: 0.05 mm for 0.1 mm traces).
* **The mapping to the cell is the problem, not the pixel.** On 42 windows of 7 real boards (reference: the copper mask solved pixel by pixel), the fill fraction the FVM uses today is 10 to 11 % too cool on the mean temperature of a heated block with 35 µm copper (up to 18 % at 140 µm, 14 to 15 % with plated holes), because clearances cut the conduction paths that the average assumes:

| Mapping of the cell | Error 0.6 mm cells | 1.0 mm | 2.0 mm | Needs |
| :-- | --: | --: | --: | :-- |
| fill fraction (today) | 9.7 % | 11.3 % | 11.1 % | `f` |
| geometric mean `S_cu^f S_lam^(1-f)` | 2.2 % | 2.4 % | 3.0 % | `f` only |
| directional `sqrt(low*up)` (lambda 0.5) | 1.0 % | 1.3 % | 3.2 % | fine mask, `Sx`, `Sy` per cell |
| flow-based faces | 0.6 % | 0.9 % | 3.6 % | fine mask, local solves |

  (mean absolute error of the mean temperature, `research/gerbers/study_mapping.py`; with two layers and plated holes: 13.6 to 14.9 % today, 2.8 to 4.1 % geometric mean, 0.5 to 1.0 % lambda 0.5, `study_two_layer.py`; the ranking holds from 18 to 140 µm of copper, `study_contrast.py`.)

**Proposal, in steps** (nothing implemented): (1) the geometric mean in the cell conductance, no new data; (2) directional conductances with lambda 0.5 from a fine copper mask stored per layer (`Sx`, `Sy` per cell in `fvm.py` and `fdm.py`, in-plane `kx`, `ky` in the 3D solid; Lumped and Analytic keep the average fill); (3) optionally flow-based faces. The geometric mean was validated on Gerber copper only: a hand-drawn hatch fill is a set of stripes (arithmetic mean along, harmonic across) and is **not** tested.

**Other projects** (read for ideas only; FYPA, padne are AGPL-3.0): FYPA and padne keep shapely polygons with holes and build a triangular mesh (`triangle`, CGAL) for a FEM solve; two KiCad plug-ins rasterise to a binary grid (0.1 mm, or 0.5 to 0.3 mm with adaptive merging). The mesh libraries are a licensing problem for a closed product (Triangle restricts commercial use, the CGAL mesh packages are GPL), which is one more reason to stay on the square grid.

**Open.** Which stage enters the program; validation on hatched zones, a thick-copper multi-layer board of a real design and against a measurement; the layer-assignment dialog and how to tell vias from pads (a Gerber cannot, a `.kicad_pcb` can); what the Lumped and Analytic models do with a rasterised copper. When it is implemented the findings fold into `models.md`, `theory.md` and `validation.md`, and this section is removed.

## Evidence for the junction node and the Foster chain (moved from the roadmap, 2026-10-22)

The part of the Component element that is **not implemented**: a junction node (JESD15-3 two-resistor model), a heat-sink node with capacity and the Foster chain for package transients. The implemented part (junction-to-pad `θ`, the junction limit, `ψJB`, the power coefficient, the top path with `θJC(top)`, the interface and `θSA`) is in `docs/models.md` section 6 and `docs/validation.md` section 9. The numbers `[n]` refer to the references at the end of this file.

### E3 Package: the JEDEC two-resistor model

The 2R compact model (JESD15-3) has three nodes (junction, case, board) and two resistances (junction-to-board, junction-to-case), the die at one temperature, ambient isothermal, power entering the junction; it applies to single-die packages [1], [2].
DELPHI (JESD15-4) adds surface nodes and shunt resistors for higher accuracy; manufacturers rarely publish those resistances, so it stays out of scope until a data source exists [2].

**Which datasheet numbers may be used.** `θJC,top` and `θJB` are resistances: the user enters them. `ΨJT` and `ΨJB` are **not** true resistances (only part of the heat flows between the two measured points; ΨJT is typically 0.5 to 2 K/W against θJC of 4 to 15 K/W; ΨJB is within about 15 % of θJB)
and are never accepted as resistors [3], [4]. The program can *report* `ΨJT = (T_j − T_top)/P` and `ΨJB = (T_j − T_board)/P` from its own solution, to compare with the datasheet as a consistency check, and should find 75 to 95 % of the heat leaving through the board for a plastic package [3].

**Structure** (the same series-parallel network in the three models; only the attachment to the board differs):

```
          P (constant, wave or table)
           |
          [T_j]--- θJC,top ---[T_case]--- R_top ---> ambient    (R_top = 1/(h A_top) with the computed h, or a heat heatsink)
           |
           θJB (spread over the footprint cells with weights w_i)
           |
        board cells under the package
```

* **FVM**: one extra unknown `T_j`; the footprint cells couple to it with `G_i = w_i/θJB` (`w_i` coverage weights, `Σ w_i = 1`: TI's "block of footprint size" practice [3], without an artificial short); `T_j` couples to ambient with `G_top = 1/(θJC,top + R_top)`.
  The augmented matrix stays symmetric positive definite.
* **Lumped**: `T_j` is a node attached to ring 0 of the heater layer and to ambient. **Analytic**: a scalar Woodbury update on the footprint-average modal response: `θ̄_fp = θ̄_0 + g_ff f`, `f = G_b (T_j − θ̄_fp)`, `T_j = (P + G_b θ̄_fp)/(G_b + G_top)`.
* **Top surface cooling** is not part of the standard; TI closes the circuit with an ambient resistance from the convective and radiative loss of the package top [3]: the computed `h` already in the program applied to the package area and temperature, or a heat heatsink.

**Limits to show to the user.** JESD15-3 itself states that the error of a 2R prediction "cannot be known a priori", that it may over- or under-predict, that it grows with the difference between the application and the JEDEC test environment, and that published studies show errors on the junction **temperature rise** "in the neighbourhood of 30 % or less", a guide and not a bound [18];
DELPHI is quoted within about 10 % (typically 5 % against detailed models) [5], [19]. The 2R model works best when the heat goes mostly into the board or a heat heatsink [19]. Single junction temperature (no die hot spots, no multi-die). `θJB` depends on the test board (below). No heat capacity in the standard models: the Package is **quasi-static**,
valid for periods well above the package time constants; dynamic compact models were still being standardised [5] and an RC ladder from measured transient curves is the way to add it [6].

### E4 Heat heatsink on a component

Top cooling of a Package: none (package top with the computed `h` or a fixed resistance), **heat heatsink** (`junction → θJC,top → case → θCS → heatsink node → θSA → ambient`, the usual `θJA = θJC + θCS + θSA` [3], [4]) and later a heat heatsink described by geometry.

* **θSA depends on the temperature rise** (agreed): the natural-convection `h` grows roughly as `ΔT^(1/4)` and radiation faster, so a datasheet value is valid at its own operating point; datasheets give power against temperature rise and the resistance is `ΔT/P`.
  Design: the user enters `θSA` and the `ΔT_ref` at which it was specified; the program scales the convective part with `(ΔT/ΔT_ref)^(−1/4)` in the same iteration that computes `h`; without `ΔT_ref` the number is constant. To check before shipping: the exponent against a real curve, and the convection/radiation split.
* **Heat-heatsink capacity** `C_hs` (J/K, mass × specific heat; aluminium about 0.9 J/(g K)) as an optional node capacity from the first version (agreed): with it fast waves see only `θJC + θCS` in parallel with `θJB` because the heatsink stays near its mean temperature;
  without it the heatsink answers instantly and the junction ripple of fast waves is overestimated (conservative). The package's own capacity (die and mould) comes later from the manufacturer's `Zth,JC(t)` curve as a Foster chain [8].

### E5 Power profiles with a Package

The profile drives `P` as now. The **average-or-resolve decision** keeps measuring the board (that is what costs computing time) but the program also reports `T_j(t)` at every time step: with the board temperature nearly constant, `T_j(t) = T_board,mean + P(t)·R_eff`, `R_eff = θJB ‖ (θJC,top + θCS + …)`, which is a cheap post-processing of the instantaneous power
and is **not averaged away** (on the example, 13.3 W on / 4 W average with `R_eff` ≈ 4.8 K/W gives a junction about 64 K above the board while the board only oscillates 0.4 K; illustrative values). Without package capacity this is an upper bound for fast waves.

### E6 What real datasheets give (read on 2026-10-16)

Parameters found in datasheets of typical parts (all read from the PDF text, except the LED row, taken from a search summary):

| Part | Thermal parameters given | Conditions stated | Source |
| :-- | :-- | :-- | :-- |
| Power MOSFET, TI CSD17308Q3 (SON 3.3 × 3.3) | `RθJC` 4.5 K/W (max); `RθJA` 58 K/W (max, 1 in² pad) and 165 K/W (max, minimum pad); power 2.7 W at 25 °C ambient, 28 W with the case at 25 °C; `Tj` −55 to 150 °C; transient thermal impedance curves | board 1.5 × 1.5 in, 1.52 mm FR-4, **2 oz** (71 µm) copper pad of 1 in² (6.45 cm²); `RθJC` "by design", `RθJA` "determined by the user's board design" | [10] |
| Power MOSFET, Infineon OptiMOS (application note) | `RthJC` (bottom) 1.1 K/W; `Ptot` 136 W at `Tc` 25 °C and 3.0 W at `Ta` 25 °C with `RthJA` 50 K/W; **`ZthJC(tp, D)` curves** and the rule `ΔTj = Zth(tp, D) · Ptot`; "Zth consists of Rth and Cth" | 40 × 40 × 1.5 mm FR-4, **6 cm² of 70 µm copper** on one layer for the drain, board vertical in still air | [11] |
| DC-DC converter, TI LMR36510 (HSOIC-8, exposed pad) | `RθJA` 42.9, `RθJC(top)` 54, `RθJB` 13.6, `ΨJT` 4.3, `ΨJB` 13.8, `RθJC(bot)` 4.3 K/W; a graph of `RθJA` against copper area | JEDEC board; the datasheet says the table "is not valid for design purposes" and that `RθJA` depends on power, airflow, PCB area, copper heat-heatsink area, number of thermal vias and neighbours | [12] |
| LDO, TI TPS7A47 (QFN-20, exposed pad) | `RθJA` 32.5, `RθJC(top)` 27, `RθJB` 11.9, `ΨJT` 0.3, `ΨJB` 11.9, `RθJC(bot)` 1.7 K/W; "`θJA` is the sum of `θJCbot` plus the PCB copper contribution" | JEDEC board; `θJA` "only a relative measure of package thermal performance" | [13] |
| Schottky diode, SMA (SX SS12…SS120) | `RθJ-A` 65 and `RθJ-L` (junction to terminal) 20 K/W; `Tj` −55 to 125 or 150 °C; no `RθJC`, no `Zth` | PCB with 0.2 × 0.2 in (5 × 5 mm) copper pads | [14] |
| Schottky diode, SMC (SS54) | `RθJA` 15 K/W only; `Tj` −55 to 125 °C | "junction to ambient", pad not stated | [15] |
| Power metal-strip resistor, Vishay WSL | **power rating at 70 °C** (0.1 W for 0603, 0.125 W for 0805 …), derating curve to zero at the maximum temperature (170 °C); no thermal resistance | rating at 70 °C, board mounting | [16] |
| LED, high power (Samsung and others; search summary, not read) | `Rth j-sp` junction to solder point: a "real" value (about 5 K/W) and a lower "electrical" one (about 3 K/W); `Tj` max 150 °C | the LED dissipates `Vf·If` minus the light emitted, which the datasheet does not give as a number | [17] |

**What this means for the Component element**

1. **The parameter sets differ by part type**, so the Package form needs optional fields and presets by type, not one fixed set: (a) `θJC,top` + `θJB` (TI converters and LDOs, the full 2R set); (b) **one** resistance to the board or terminal (`θJC(bot)` of a MOSFET, `θJ-L` of a diode, `Rth j-sp` of an LED) and no top path;
   (c) only `θJA` on a stated board (some diodes); (d) only a **power rating at a temperature** (resistors: a thermal resistance can be derived as `(T_max − T_rating)/P_rating`, for example 100 K / 0.1 W = 1000 K/W for the 0603 at its 70 °C rating, an order of magnitude to be checked against the manufacturer's mounting note).
2. **`θJA` must never be an input** of the board model: manufacturers say so themselves ([12], [13]); it is useful only as a plausibility check (our `T_j − T_ambient` on a board like the datasheet's should approach `P·θJA`) and `RθJA` against copper area (the CSD17308Q3 gives 58 and 165 K/W for 6.45 cm² and the minimum pad) is a good **validation case** for the model.
3. **Which resistance goes between the junction and our board.** In the exposed-pad parts above `θJC(bot)` (4.3 and 1.7 K/W) is much smaller than `θJB` (13.6 and 11.9 K/W): `θJB` is measured on the JEDEC board and **includes the spreading of the heat in that board**, while `θJC(bot)` stops at the pad. Our model already spreads the heat in the real board under the footprint, so using `θJB` there would count the board's spreading twice. Proposal: the Package takes the
   **junction-to-pad resistance** (`θJC(bot)`, `θJ-L`, `Rth j-sp`) when the datasheet gives it, and `θJB` otherwise, with a note on which one was used; the `ΨJB` consistency check (E3) will show whether the choice is sensible for a given part. To settle with a real part.
4. **Transient curves** `Zth(tp, D)` (MOSFETs) contain `Rth` and `Cth`: they are the input of the later Foster chain, and the datasheet shortcut `ΔTj = Zth(tp, D)·P` is a good check of our time simulation.
5. **Copper weight matters**: the MOSFET boards are 2 oz (71 µm) or 70 µm, our default is 35 µm; the datasheet `RθJA` values cannot be compared without matching the copper of the board.
6. **LEDs**: the heat is `Vf·If` minus the optical output; the Component needs a "fraction of the electrical power that becomes heat" (or the heat power directly), which is not a datasheet number.
7. The simple **Source** (a heater with a power) stays the default and needs none of this.

### E7 How the datasheet tests convert to our model (researched 2026-10-16)

**What each test measures** (JESD51 family [18], [20], [21], [22]):

| Metric | Test | What it is physically | Transferable to our board model? |
| :-- | :-- | :-- | :-- |
| `θJC(top)`, `θJC(bot)` | cold plate on the top or bottom face, one heat path (JESD51-14 dual interface or the cold-plate method) | resistance **inside the package** from the junction to that face; meaningful for packages with a predominantly 1D path (the `θJB/θJC` ratio above about 10, power packages); an overmolded BGA gave 0.82 against 1.79 K/W by the two methods [22] | **yes**, it is a package property; the solder, thermal paste or heat-heatsink interface on that face is ours |
| `θJB` | double ring cold plate, heat forced through the board (JESD51-8); board temperature 1 mm from the package edge (area-array parts) or on the lead foot (leaded parts) | package resistance **plus part of the test board** for area-array parts, none for leaded parts [18], [23] | **partly**: use it only when `θJC(bot)` is not given, and expect it to over-estimate if the part's heat spreading is already in our board [18] |
| `θJA` | still air, 0.3 m cube, JEDEC board 1s0P (JESD51-3) or 2s2p (JESD51-7), at least 76 × 114 mm with at least 50 µm on the top copper (JESD51-2, -3, -7) [20] | package + test board + convection together | **no as input** (manufacturers say so [12], [13], [23]); **yes as a validation target**, see the virtual test below |
| `ΨJT`, `ΨJB` | same environment as `θJA`, with the real heat partition | `ΔT/P` between the junction and a measured top or board temperature, **not** a resistance [3], [18] | as a **post-processing estimate**, see level A |

**Three levels of approximation, from cheapest to richest**

* **A. Source plus ψ (no new physics).** The heat enters the board under the footprint as today; after the simulation the program estimates `T_j = T_board,ref + ΨJB·P` (or `T_j = T_top + ΨJT·P` when a top temperature exists), where `T_board,ref` is the simulated board temperature on the reference point of the test (a ring 1 mm outside the package body).
  This is the method the manufacturers themselves recommend with a measured temperature on the real board; Richtek measured 79.9 °C with the body-diode method against 79.98 °C from `ΨJB` and the measured board temperature, and 79.9 °C from `θJA(EVB)` [23]; `ΨJT` is the better estimate when the power is uncertain because the top is closer to the junction temperature than the board is [23].
  Valid while the application is close to the test conditions (no heat heatsink, similar board); it needs `ΨJB` (given by IC makers, not by most MOSFET and diode makers) and it does not change the board field.
* **B. Package (JESD15-3, E3).** A junction node with the two resistances, built as the standard's **block-and-plate**: an isothermal block the size of the package, insulated on its sides, between two plates whose resistance equals `θJC,top` and `θJB`; the plate on the board has the footprint area, i.e. a uniform conductance `1/(θ·A)` per unit area,
  which is exactly our `G_i = w_i/θJB`; the heat source sits in the block (a volume or area source, never a point); the block's own resistance must be two orders of magnitude below the plates' [18]. **Exposed-pad parts: the standard allows replacing `θJB` by `θJC(bottom)`** [18] (4.3 against 13.6 K/W and 1.7 against 11.9 K/W for the two TI parts of E6), which settles which number goes between the junction and our board.
  Needed when a heat heatsink or a strong top path exists. Expected error on the rise: 30 % or less in the standard's words [18].
* **C. DELPHI / detailed.** Needs resistances manufacturers do not publish; out of scope until a data source exists.

**The virtual JEDEC test (validation and a way to recover a missing number).** Build the datasheet's own board in the program (JESD51-3 1s0P or JESD51-7 2s2p, 76.2 × 114.3 mm, the copper and the pad area the datasheet states), natural convection (computed `h`, still air), the package with the user's resistances, and compute
`θJA = (T_j − T_amb)/P`, `ΨJT` and `ΨJB`; they should land near the datasheet values (to be checked on the TPS7A47: `θJA` 32.5, `ΨJT` 0.3, `ΨJB` 11.9 K/W with `θJC(bot)` 1.7 K/W; and on the CSD17308Q3: `RθJA` 58 and 165 K/W for 6.45 cm² and the minimum pad of 2 oz copper). The test is the **calibration of the Component**: if it fails by more than the 30 % of the 2R,
the parameters or the board data are wrong. It also converts the parts that only give `θJA` on a stated board (the SMA diode: `θJA` 65 K/W on 5 × 5 mm pads): the package resistance is `θJA` minus the resistance that **our model** gives to the stated board, the same relation TI states (`θJA = θJC(bot)` plus the contribution of the PCB copper [13]).

**What the Component form asks, by case**: (1) the datasheet gives `θJC(top)` and `θJC(bot)` or `θJB` → Package with the top path; (2) one resistance to the pad, lead or solder point (`θJC(bot)`, `θJ-L`, `Rth j-sp`) → Package without a top path; (3) only `θJA` on a stated board → the package resistance from the virtual test; (4) only `ΨJB`/`ΨJT` → level A; (5) only a power rating at a temperature → derived resistance with a warning.
The board reference temperature of a `ΨJB` estimate and the 1 mm ring are outputs of the board field, not inputs.

### E8 Prototype on a real part: is the junction node worth it? (2026-10-16)

`examples/package_prototype.py` (outside the program) simulates the TI CSD17308Q3 power MOSFET (SON 3.3 × 3.3 mm, `RthJC` 4.5 K/W to the drain pad, `Tj` max 150 °C) on the datasheet's own board (38.1 × 38.1 mm, 1.52 mm FR-4, 71 µm copper, a square copper pad on the top, still air with the computed `h`) in two ways:
**offset** = what the program does today (the heat enters the board under the footprint, `Tj = T_max under the footprint + P·θ`) and **node** = a junction node joined to the footprint by a uniform conductance `1/θ` (the block-and-plate of JESD15-3) plus an optional path through the top.

| Test | Datasheet | Offset | Node |
| :-- | --: | --: | --: |
| `RθJA` on 1 in² of 2 oz copper (1 W) | 46 typical, 58 max | **46.7** | **45.1** |
| `RθJA` on a 5 mm pad (assumed size, the datasheet does not give it; 1 W) | 165 max | 164.2 | 162.8 |
| `Tj` at 2 W, 1 in² pad, no top path | | 112.5 °C | 109.4 °C |
| 2 W with a bare mould (30 K/W + convection, assumed) | | | 108.9 °C, 0.7 % of the heat through the top |
| 2 W with a 12 K/W clip-on heat heatsink, `θJC(top)` 40, 20, 5 K/W (assumed) | | cannot represent it | 73.6, 63.4, 51.1 °C; 46, 58, 73 % of the heat through the top |
| 2 W with a 4 K/W heat heatsink, `θJC(top)` 20 K/W (assumed) | | cannot represent it | 57.6 °C, 65 % through the top |

What it shows:
* **The physics and the one-resistance approach already reproduce the datasheet**: `RθJA` within 2 % of the typical value on the 1 in² board with `θJC(bot)` only (the datasheet value is a maximum for the 58 and a typical for the 46), and the minimum-pad figure within 1 % of the maximum (a coincidence of the assumed pad size, to be repeated with the real pad).
* **Without a top path the junction node changes little**: 3 K (3 % of the rise) lower than the offset, which is conservative; for a bare FET the **simple heater with the junction-to-pad resistance is enough**.
* **With a heat heatsink on the top the answer changes by a factor of two** (112 against 51 to 74 °C) and the offset method cannot see it: that is the case that justifies the junction node.
* The result depends strongly on the junction-to-top resistance, which this datasheet does not give: the heat-heatsink case needs `θJC(top)` from the manufacturer or an assumption stated in the report.

**Consequence for the design (to keep it simple).** (1) The Component stays a **Source** with one optional field, the *junction-to-pad resistance* (today's `θJB` field, renamed and documented as `θJC(bottom)` / `θJ-L` / `Rth j-sp`); with it alone the program behaves as today and is within the 3 % above, and it is validated by the virtual JEDEC test (the table above is that test).
(2) A **top path** (heat heatsink or top resistance) is a second optional group of fields; only when it is filled the program adds the junction node (FVM and FDM first; the Lumped and Analytic models warn that they ignore it until they get it). (3) The ψ estimate and the Foster chain come later. Nothing else is asked from the user.


## References of the evidence above

2. J. Stori, K. Brady, T. Thurman, *Representation of a Thermal Resistor Network Model of a Packaged Component in STEP AP210 Edition 2*, NISTIR 7648, 2008, https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir7648.pdf (read: JESD15 family, 2R with three nodes and two resistances, DELPHI with shunt resistors).
3. Texas Instruments, *Semiconductor and IC Package Thermal Metrics*, SPRA953B, 2012, https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/171/4745.TI_5F00_PackageThermalMetrics_5F00_spra953b.pdf (read: definitions of θJC, θJB, ΨJT, ΨJB, the 3-resistor estimate, the θJB redistribution problem, 75 to 95 % of the heat through the PCB).
4. Renesas, *Thermal Characterization of Packaged Semiconductor Devices*, https://www.renesas.com/en/document/whp/thermal-characterization-packaged-semiconductor-devices (read: ΨJB within about 15 % of θJB, ΨJT, mould compound emissivity about 0.95, `θJA = θJC + θCS + θSA`).
5. *Compact Thermal Modeling: Impacting the Industry*, Semiconductor Digest, 2007, https://sst.semiconductor-digest.com/2007/03/compact-thermal-modeling-impacting-the-industry/ (read: DELPHI within 10 %, boundary-condition independence, dynamic models in standardisation).
6. Siemens, *Experiment vs. Simulation, Part 4: Compact Thermal Models*, https://blogs.sw.siemens.com/simulating-the-real-world/2013/04/05/experiment-vs-simulation-part-4-compact-thermal-models/ (read: standard 2R and DELPHI lack thermal capacitance; RC ladders from transient measurements add it).
7. gerbonara, https://pypi.org/project/gerbonara/ (documentation https://gerbolyze.gitlab.io/gerbonara); listed only.
8. Nexperia, AN11261, *Using RC thermal models* (Foster and Cauer networks), https://mouser.com/pdfDocs/AN11261-3.pdf; Texas Instruments SLUAAT8, *Using MOSFET Transient Thermal Impedance Curves in Your Design*, https://www.ti.com/lit/pdf/sluaat8 (repetitive pulses, `D + (1 − D) z(t)`).
9. Not used as a source for the 2R model: ROHM's application note "two-resistor model" (https://fscdn.rohm.com/en/products/databook/applinote/common/two_resistor_model_for_thermal_simulation-e.pdf) defines junction-to-board and board-to-ambient resistances, which is not the JESD15-3 definition.
10. Texas Instruments, CSD17308Q3 datasheet (SLPS262C), https://www.ti.com/lit/ds/symlink/csd17308q3.pdf (read: thermal information, `RθJC`, `RθJA` and the pad area graph).
11. Infineon, *OptiMOS Power MOSFET Datasheet Explanation*, AN 2012-03, https://www.infineon.com/assets/row/public/documents/24/42/infineon-mosfet-optimos-datasheet-explanation-applicationnote-en.pdf (read: `Ptot`, `RthJA` conditions, `ZthJC`).
12. Texas Instruments, LMR36510 datasheet (SNVSBD7B), https://www.ti.com/lit/ds/symlink/lmr36510.pdf (read: thermal information and the application note on `RθJA`).
13. Texas Instruments, TPS7A47 datasheet, https://www.ti.com/lit/ds/symlink/tps7a47.pdf (read: thermal information and the power dissipation section).
14. SX Semiconductor, SS12 to SS120 SMA Schottky rectifiers, https://www.ickey.cn/static-pf/datasheet/22/76/cc08/2276cc08322b3110623485720f87bf21.pdf (read: thermal resistance and its PCB note).
15. SS54 Schottky barrier rectifier (SMC), Farnell/element14 datasheet V1.1, https://components101.com/sites/default/files/component_datasheet/SS54%20Schottky%20Diode.pdf (read).
16. Vishay, WSL power metal strip resistors, https://www.vishay.com/docs/30100/wsl.pdf (read: power rating at 70 °C and the derating curve).
17. Samsung LED, high power LED datasheets (for example https://download.led.samsung.com/led/file/automotive/Samsung_C_Gen3_1W_WH_SPHWH1A1N1A0_DS_Rev.1.6.pdf); the thermal figures come from a search summary and the files were **not read**.
18. JEDEC JESD15-3, *Two-Resistor Compact Thermal Model Guideline* (text read, mirror at http://www.simu-cad.com/userfiles/images/ZaiXianXiaZai/ef8f29116ed54c67a8a8d77502611043.pdf): definitions of `θJB` and `θJCtop`, replacing `θJB` by `θJCbottom` for exposed-pad packages, `ψJB` as a substitute, `ψJT` not allowed, the block-and-plate construction, accuracy "30 % or less".
19. Electronics Cooling, *Compact thermal modeling in electronics design* (2007), https://www.electronics-cooling.com/2007/05/compact-thermal-modeling-in-electronics-design/ (read: 2R about 30 % or less, DELPHI within 10 %, typical errors under 5 % against detailed models, lack of `θJB` data from some manufacturers).
20. Electronics Cooling, *JEDEC Thermal Standards: Developing a Common Understanding* (2019), https://www.electronics-cooling.com/2019/11/jedec-thermal-standards-developing-a-common-understanding/ (read: JESD51-2, -3, -5, -6, -7, -8, -9, -14, JESD15-3 and -4; test boards of at least 76 × 114 mm).
21. Electronics Cooling, *Use of junction-to-board thermal resistance in predictive engineering* (1999), https://www.electronics-cooling.com/1999/01/use-of-junction-to-board-thermal-resistance-in-predictive-engineering/ (read: `RJB` depends on the board, about 10 % scatter, errors under 25 % in a CFD study).
22. Electronics Cooling, *The Applicability of JESD51-14 for the Determination of Junction to Case Thermal Resistance* (2024), https://www.electronics-cooling.com/2024/04/the-applicability-of-jesd51-14-for-the-determination-of-junction-to-case-thermal-resistance/ (read: single-path packages, `Rjb/Rjc` above about 10, an overmolded BGA 0.82 against 1.79 K/W).
23. Richtek, *Application and Definition of Thermal Resistances on Datasheet*, AN061 (2020), https://www.richtek.com/Design%20Support/Technical%20Document/~/media/AN%20PDF/AN061_EN.ashx (read: `θJB` on the lead foot for leaded parts, `θJA/θJC/θJB` not applicable to another board, the `ΨJB` and `ΨJT` estimates and their measured check).
24. Texas Instruments, *AN-2020 Thermal Design by Insight, Not Hindsight*, SNVA419C (2013), https://www.ti.com/lit/an/snva419c/snva419c.pdf (read: `θCu`, `θVIA`, copper weight, board area rule of thumb, heat heatsink on the bottom against the top).
25. Y. Shen, H. Wang, F. Blaabjerg, H. Zhao, T. Long, *Thermal Modeling and Design Optimization of PCB Vias and Pads*, IEEE Trans. Power Electronics (2019), https://tenglong.eng.cam.ac.uk/files/thermalmodelinganddesignoptimizationofpcbviasandpads.pdf (abstract and structure read: analytical via-array and pad models verified by CFD and measurements).

## Template (what this file looks like when nothing is pending)

```
# Research (open investigations)

Nothing pending. Add a section per investigation: the question, what was read (with links), what was simulated (script and numbers), the proposal and the open questions.
When it is implemented, fold the findings into models.md, validation.md and roadmap.md and delete the section.
```
