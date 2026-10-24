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

The fifth source says the JLCPCB and PCBWay tables give a maximum temperature "under 0.5 %" from the templates. With the corrected comparison it is up to 2.0 % of the rise with outer copper only (the dielectric split) and up to 13 % with a plane on every inner layer (because the templates use 0.5 oz inner copper and most tables 1 oz). Suggested text: "... were compared with these templates: with outer copper only the maximum temperature of the example board moves by 0.2 to 2.0 % of the rise; with inner planes the 0.5 oz inner copper of the templates is 5 to 8 K hotter than 1 oz (research/stackup/README.md section 4.3)". This is program data: a `fix/` branch, not this one.
