# 22. The stack-up: simple, advanced, typical templates and fabricator tables

![Stack-up schematics](../../stackup/figures/fig_04_stackup_schematic.png)

*Figure 4 of `research/stackup` (`research/stackup/figures/fig_04_stackup_schematic.png`): the simple mode (equal gaps), the advanced mode (copper per layer, material and thickness per gap; each node is the copper plus half of each adjacent gap) and the vertical chain as a series of half gaps.*

Also `research/stackup/figures/fig_05_stackup_to_scale.png` (the 4-layer stack-up in true proportions and what each number is worth). Investigation: `research/stackup/README.md`. **Status: implemented** (`Board.dielectrics`, `data/stackups.json`).

## 1. What it is

The vertical structure of the board: copper thickness per layer and the material and thickness of every dielectric gap. **Simple mode**: equal gaps, `d = (t_pcb - sum t_cu) / (L - 1)`. **Advanced mode** (`Board.dielectrics`): copper per layer, material and thickness per gap; every model reads it through four helpers. Each layer node is the copper plus half of each adjacent gap; the vertical conductance between nodes is the series of half gaps (several sheets in one gap combine with `combine_sheets`).

## 2. Findings

* Advanced mode with equal gaps reproduces simple mode (0.1 K apart) and an exact series circuit of layer nodes to 1e-6 K in the FVM and FDM.
* The stack-up matters (70 to 102 K of rise on the same board between heavy and half-ounce copper, 71 K with a ceramic core) and the models follow it in the same direction.
* **The one number that matters is the finished outer copper**: a 15 % thinner finish raises the rise by 5.7 %; dielectric conductivity and thickness move it by about 1 %.
* The typical templates (`pcbthermal/data/stackups.json`, 1 to 12 layers) are loaded when the layer count changes; only the 4-layer entry is a published fabricator table (JLCPCB, to the last digit); the others are constructed to add up. Other fabricators' dielectric splits move the maximum temperature by 0.1 to 1.7 C.

## 3. Open ideas

An outer dielectric (solder mask) above the top copper and below the bottom copper, a material per copper layer (alloys, plated copper), a library of fabricator stack-ups (Eurocircuits and Sierra Circuits publish no table that could be read).

## 4. Related topics

01, 04 (slabs), 09, 21.

## 5. Sources

* Fabricator tables: [StackupTables]. The copper and via notes: [TI-AN2020]. Own computation: [L-stackup], [L-validation].

*What was read and what was not verified:* from `research/stackup/README.md` and `docs/validation.md` 14 (read in full); the addresses of some pages were not recorded in the stack-up README, so that list is as read, not a citation list.
