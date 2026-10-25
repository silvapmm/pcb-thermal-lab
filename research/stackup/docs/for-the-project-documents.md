# Text for the project documents (review of 2026-10-24)

The review of `research/stackup/` (README section 7) found numbers and statements in the program's documents and data that no longer match what the scripts print on the corrected program (`0ea5f07`). The project documents are not edited on a research branch; this is the text to fold in when the maintainer decides.

## 1. `docs/validation.md`, section 12, table A (Lumped column)

Replace the Lumped column with the values printed by `stackup_outline_study.py` now (the minimum ring width of the Lumped moved it 0.9 to 1.1 points):

| Stack | Lumped |
| :-- | --: |
| simple, equal FR-4 gaps | -3.2 % |
| advanced, the same gaps | -3.3 % |
| thin prepreg 0.1 mm top and bottom, 0.7 mm core | -3.5 % |
| prepreg 0.1 mm, metal-core dielectric 1 mm (2 W/mK) | -3.6 % |
| polyimide flex 0.1 mm gaps (0.15 W/mK) | -6.6 % |
| alumina core 0.6 mm (24 W/mK) | -5.2 % |
| copper 70 / 35 / 35 / 70 µm | -0.9 % |
| copper 17.5 µm on every layer | -5.9 % |

and in the bullet below it: "the Lumped within 6 %" -> "the Lumped 0.9 to 6.6 % low".

## 2. `docs/validation.md`, section 12, table C and the sentence after it

Table C is current. Add after "Without the vias under the part (base rise 93.4 K) ... +3.3 / -2.3 %.":

> This holds on boards with copper on both faces. On a one-layer board with a 20 mm pad the heat crosses the laminate and ±30 % of dielectric conductivity moves the rise by +8.7 / -6.1 % (the laminate thickness ±10 % by 1.4 to 1.6 %); the program and an independent 3D solver agree on every such sensitivity within 0.2 points (`research/stackup/README.md`, section 4.4).

## 3. `docs/validation.md`, section 14

The 6 and 8-layer rows were boards with no bottom copper (defect of the study, fixed). Replace the table and the first two bullets with the table and bullets of `research/stackup/README.md` section 4.3 (two columns: outer copper only and a plane on every inner layer). The numbers that change in the text: "0.1 to 1.7 °C (0.2 to 1.5 % of the rise)" -> "0.1 to 1.5 °C (0.2 to 2.0 % of the rise)"; "6 layers within 0.9 °C, 8 layers within 1.4 °C" -> "6 layers within 1.5 °C, 8 layers within 0.8 °C"; "at 93.65 °C" -> "at 93.64 °C"; the middle-prepreg bullet "the effect on the temperature is 0.1 K" -> "the whole JLCPCB 6-layer table is 0.3 to 0.4 K cooler than the template". New bullet: with inner planes the 0.5 oz inner copper of the templates makes the board 5 to 8 K hotter than the 1 oz inner copper of most tables (JLCPCB 6-layer, same inner copper, within 0.4 K).

## 4. `CLAUDE.md`, Decisions Log of 2026-10-21

"dielectric conductivity and thickness move the temperature by about 1 %, copper weight by 5 %" is the sensitivity of a 4-layer board with vias to ±30 % of dielectric conductivity, ±10 % of dielectric thickness and ±15 % of finished copper. A history entry is not rewritten; if the statement is quoted again, give the scope: 2 to 3 % without vias, 6 to 9 % on a one-layer board with a pad.

## 5. `docs/theory.md`, section 1.2 (the advanced stack-up is not described)

Add after the definitions of the layer equation:

> **Advanced stack-up** (`Board.dielectrics` set, one per gap): gap `j` between layers `j` and `j+1` has its own thickness `d_j`, through-plane conductivity `k_th,j`, in-plane conductivity `k_ip,j` and `ρc_j`; the vertical conductance per area is `g_j = k_th,j / d_j`. The node of layer `l` represents `slab_l = t_cu,l + d_{l−1}/2 + d_l/2` (half of each adjacent gap; the outer layers have one), so the slabs add up to the total thickness; the laminate of the node has the thickness-weighted mean `k_ip` and `ρc` of its two half gaps. The simple mode (`dielectrics = None`) keeps `slab = t_pcb/L` and equal gaps `d = (t_pcb − Σ t_cu)/(L − 1)`; the two agree within 0.1 K when the gaps are equal (`validation.md` section 12).

## 6. `pcbthermal/data/stackups.json`, `sources`

**Adopted**: the program's `sources` text already says 0.2 to 2.0 % of the rise with outer copper only and the inner copper effect with planes; the suggestion below is kept as the record.

The fifth source says the JLCPCB and PCBWay tables give a maximum temperature "under 0.5 %" from the templates. With the corrected comparison it is up to 2.0 % of the rise with outer copper only (the dielectric split) and up to 13 % with a plane on every inner layer (because the templates use 0.5 oz inner copper and most tables 1 oz). Suggested text: "... were compared with these templates: with outer copper only the maximum temperature of the example board moves by 0.2 to 2.0 % of the rise; with inner planes the 0.5 oz inner copper of the templates is 5 to 8 K hotter than 1 oz (research/stackup/README.md section 4.3)". This is program data: a `fix/` branch, not this one.

## 7. `pcbthermal/data/stackups.json`, inner copper of the templates (study of 2026-10-24, README section 4.5)

**Adopted in another form**: both weights are offered, `Board.template_inner_oz` = 0.5 (default, JLCPCB standard, the 4-layer entry stays that table) or 1 (35 µm inner copper, dielectrics unchanged), `docs/validation.md` section 14.1. The edit list below (switching the file to 35 µm, or scaling the dielectrics) was not done; it is kept as the record of the options.

Measured on the example board with a full plane on every inner layer (FVM 2 mm; the 3D solid agrees within 0.06 K on 4 and 6 layers): inner copper of 35 µm instead of 15.2 µm lowers the maximum temperature by 7.1 K (4 layers, 90.40 -> 83.27 °C), 7.9 K (6 layers, 84.80 -> 76.89), 7.8 K (8 layers, 79.72 -> 71.88), 7.6 K (10 layers, 78.76 -> 71.15) and 7.5 K (12 layers, 78.22 -> 70.77), when the dielectrics are thinned to keep the total thickness (11 to 14 % of the rise); with unchanged dielectrics the numbers are 0.2 to 0.7 K smaller. A true 0.5 oz base foil (17.5 µm) changes only 1.1 to 1.3 K. The 2-layer template has no inner copper.

If the maintainer chooses to switch (a `fix/` branch, not this one), edit in `stackups.json`:

* `copper_um`: replace every inner value `15.2` by `35` in the entries "4", "6", "8", "10" and "12" (outer `35` stays); for example "4": `[35, 35, 35, 35]`.
* `dielectrics`: to keep the nominal board thickness, scale every `thickness_um` of the entry by `f = (total - sum(copper)) / sum(dielectrics)`: f = 0.9733 (4 layers: 210.4 -> 204.8, 1065 -> 1036.6), 0.9461 (6 layers), 0.9174 (8 layers), 0.9124 (10 layers), 0.9091 (12 layers) (computed by `variant()` in `research/stackup/scripts/study_inner_copper_1oz.py`); or leave the dielectrics unchanged and let the board be 0.04 to 0.2 mm thicker (the total of the entry name, "1.6 mm", would then be wrong). Leaving them unchanged costs only 0.2 to 0.7 K.
* `name` of each entry: "(35 / 4 x 15.2 / 35 um copper ...)" becomes "(35 / 4 x 35 / 35 um ...)"; the first `notes` line ("finished inner copper of 0.5 oz is about 15 to 17.5 um") and the sentence for layer counts not listed ("inner 15.2 um") change to say 1 oz (about 35 um) is used and 0.5 oz (15.2 um, the JLCPCB standard) is the hotter, conservative alternative.
* The 4-layer entry is a copy of the JLCPCB table JLC04161H-7628 (15.2 µm inner): switching it makes it no longer that table. Option: keep "4" as JLCPCB and add the 1 oz variant as a second named template, which needs a code change (`Board.apply_template` picks by layer count).
* The sentence "differs by under 0.5 %" (section 6 above) must be reworded in either case.

The choice (keep 0.5 oz, switch to 1 oz, or offer both) belongs to the maintainer: 0.5 oz is the conservative (hotter) end and the JLCPCB standard; 1 oz is the figure of most other published tables and agrees with the PCBWay and PCBGOGO 4 and 6-layer tables within 0.1 to 0.6 K.

## 8. `pcbthermal/data/stackups.json`, how the 1 oz variant should treat the dielectrics (README section 4.6)

**Adopted**: the program's 1 oz variant leaves every dielectric thickness unchanged, as recommended here; it uses 35 µm, not JLCPCB's 30 µm (`docs/validation.md` section 14.1).

Real 1 oz builds (JLCPCB's own template data, Bittele, PCBWay, PCBGOGO, AdvancedPCB) do not scale the dielectrics: a fabricator re-picks cores and prepreg for the nominal thickness (JLCPCB 1.6 mm: board total -4 % to +4 % against its 0.5 oz build, dielectric total 0.85 to 1.08 times). The one physical thinning is the resin that fills etched copper (Isola rule, confirmed by PCBWay's numbers exactly): it affects only the prepreg, in proportion to the etched fraction, and is zero against a full plane. Against 15 published 1 oz builds the variant with the dielectrics left unchanged is the closest (mean absolute deviation 0.85 K, against 1.00 K for the scaled variant), and against JLCPCB's real 1 oz build 0.69 K against 1.00 K; the three rules differ among themselves by 0.2 to 0.7 K, less than the spread between real builds.

Recommendation for the change proposed in section 7 (the decision is the maintainer's): replace only the inner `copper_um` values and leave every `thickness_um` unchanged (the scaling factors of section 7 are then not applied; the board becomes 0.04 mm (4 layers) to 0.20 mm (12 layers) thicker than nominal, inside the +-10 % tolerance; the name of each entry should then state the real total). **If the variant is meant to represent JLCPCB, JLCPCB's 1 oz inner copper is 30 um, not 35 um** (it raises the temperature by 1.2 to 1.4 K compared with 35 um), and JLCPCB does sell it (help page: 0.5, 1 and 2 oz inner; availability depends on layers and thickness). The sentence "Whether JLCPCB sells a 1 oz inner option was not checked" of README section 4.5 is answered in section 4.6.
