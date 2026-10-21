# Research (open investigations)

This file collects investigations that are **not implemented yet**: what was read, what was simulated, what is still open. It is used until the work is implemented;
then the findings are folded into `docs/models.md`, `docs/validation.md` and `docs/roadmap.md`, the scripts stay in `examples/`, and this file goes back to the empty template below.
Values marked *assumed* are not from a datasheet. Everything is reproducible with the scripts named in each section.

## Open now: the Component element (branch `feature/component-element`)

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
3. Heatsink scenarios (natural scaling, forced factors): later (`docs/roadmap.md` 1.11).

## Template (what this file looks like when nothing is pending)

```
# Research (open investigations)

Nothing pending. Add a section per investigation: the question, what was read (with links), what was simulated (script and numbers), the proposal and the open questions.
When it is implemented, fold the findings into models.md, validation.md and roadmap.md and delete the section.
```
