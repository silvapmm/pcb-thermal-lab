# 22. The stack-up: simple, advanced, typical templates and fabricator tables

![Stack-up schematics](../../stackup/figures/fig_04_stackup_schematic.png)

*Figure 4 of `research/stackup` (`research/stackup/figures/fig_04_stackup_schematic.png`): the simple mode (equal gaps), the advanced mode (copper per layer, material and thickness per gap; each node is the copper plus half of each adjacent gap) and the vertical chain as a series of half gaps.*

Also `research/stackup/figures/fig_05_stackup_to_scale.png` (the 4-layer stack-up in true proportions and what each number is worth). Investigation: `research/stackup/README.md`. **Status: implemented** (`Board.dielectrics`, `data/stackups.json`).

## 1. What it is

The vertical structure of the board: copper thickness per layer and the material and thickness of every dielectric gap. **Simple mode**: equal gaps, `d = (t_pcb - sum t_cu) / (L - 1)`. **Advanced mode** (`Board.dielectrics`): copper per layer, material and thickness per gap; every model reads it through four helpers. Each layer node is the copper plus half of each adjacent gap; the vertical conductance between nodes is the series of half gaps (several sheets in one gap combine with `combine_sheets`).

## 2. Findings

* Advanced mode with equal gaps reproduces simple mode (0.1 K apart) and an exact series circuit of layer nodes to 1e-6 K in the FVM and FDM.
* The stack-up matters (70 to 102 K of rise on the same board between heavy and half-ounce copper, 71 K with a ceramic core) and the models follow it in the same direction.
* **On a board with copper on both faces the number that matters is the finished copper**: a 15 % thinner finish raises the rise by 5.7 %; the dielectric conductivity (+-30 %) and thickness (+-10 %) move it by about 1 % with vias under the part and 2 to 3 % without. **Not on a one-layer board with a pad**: there the heat crosses the laminate and +-30 % of dielectric conductivity moves the rise by +8.7 / -6.1 % (`research/stackup/README.md` 4.4; the independent 3D solver agrees within 0.2 points).
* The typical templates (`pcbthermal/data/stackups.json`, 1 to 12 layers) are loaded when the layer count changes; only the 4-layer entry is a published fabricator table (JLCPCB JLC04161H-7628 as recorded; its core of 1065 um and inner copper of 15.2 um were confirmed again by the review, the 210.4 um prepreg was not); the others are constructed to add up. Other fabricators' dielectric splits move the maximum temperature by 0.1 to 1.5 C (an earlier check dropped the bottom plane of the 6 and 8 layer boards and read up to 1.7 C).
* **Inner copper, 0.5 oz or 1 oz** (`Board.template_inner_oz`): the templates use 15.2 um inner copper by default; the 1 oz option makes every inner layer 35 um with every dielectric unchanged (the board grows by 19.8 um per inner layer). With a plane on every inner layer the example board is 6.9 to 7.5 K cooler with 1 oz (4 to 12 layers); with copper only on the outer layers under 0.3 K (`docs/validation.md` 14.1, `research/stackup/README.md` 4.5 and 4.6).

* **The effective conductivity of a laminate is not a property of the stack**: for the same copper and FR4 it goes from 15 to 5 W/mK with the order of the layers, falls to 0.4 W/mK when the source covers the whole board and has a maximum near 8 W/mK for a source of a quarter of the board; none of the series, parallel, arithmetic, geometric or harmonic means is a good estimate (up to 70 % off) ([CulhamYovanovich1998], reproduced within 2 to 6 % by `research/effective-conductivity/`). The program does not homogenise: a node per copper layer and a resistor per gap represent the order.

## 3. Open ideas

An outer dielectric (solder mask) above the top copper and below the bottom copper, a material per copper layer (alloys, plated copper), a library of fabricator stack-ups (Eurocircuits and Sierra Circuits publish no table that could be read).

## 4. Related topics

01, 04 (slabs), 09, 21.

## 5. Sources

* Effective conductivity and the order of the layers: [CulhamYovanovich1998], [Lemczyk1992] (the method of its first pages). Fabricator tables: [StackupTables]. The copper and via notes: [TI-AN2020]. Own computation: [L-stackup], [L-validation].

*What was read and what was not verified:* from `research/stackup/README.md` and `docs/validation.md` 14 (read in full); the addresses of some pages were not recorded in the stack-up README, so that list is as read, not a citation list.
