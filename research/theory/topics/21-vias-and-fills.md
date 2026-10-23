# 21. Vias: the barrel, the fill and arrays under a part

![Via fills](../../via-fill/figures/fig_04_via_fills_schematic.png)

*Figure 4 of `research/via-fill` (`research/via-fill/figures/fig_04_via_fills_schematic.png`): the via fills as cross-sections: an open barrel, a resin plug (0.3 W/mK), conductive paste (8 W/mK) and an electroplated copper fill, with the heat path down the barrel and the thermal area it gives.*

Also `research/via-fill/figures/fig_05_via_array_under_a_part.png` (nine vias in parallel under a part). Investigation: `research/via-fill/README.md`. **Status: implemented** (the via fill, `Via.fill_k`, library `VIA_FILLS`).

## 1. What it is

A via connects the layers of the board through a copper-plated barrel. In the layered models (topic 01) it is a conductance in parallel with the dielectric gap; in the 3D solid (topic 04) it is a rod of the same copper area.

## 2. The thermal area

Along the axis `R = L / (k_cu A_eq)` with

    A_eq = A_plating + min(k_fill / k_cu, 1) pi r_in^2           (open barrel: k_fill = 0)

and `A_plating = pi [(D/2)^2 - (D/2 - t_plating)^2]`. An electroplated copper fill is the whole disc, `pi (D/2)^2`. The via is assigned to the cell that contains its centre; in the Analytic model it is a tile conductance `c_via = k_cu A_via / d` (topic 06).

## 3. What the fill does

The usual fabricator "filled via" is an **epoxy resin plug** (IPC-4761 types V to VII of its seven types I to VII: tenting, plugging, filling, capping): it keeps the hole closed and the surface flat, and conducts like FR-4 (192.1 against 192.4 K/W, no gain). A conductive paste helps a little (about -5 %). Only an **electroplated copper fill** is a real heat path: the resistance of one 0.3 mm via falls by 69 %, and on the example board the maximum temperature falls by 3.9 K. Guides give roughly 4 thermal vias about 40 K/W and 16 vias about 10 K/W.

## 4. Limits

The barrel is a lumped area, the lateral effect of the wall is neglected, vias are point features (about 0.5 % against 3D rods; the FDM puts a via on the nearest node and is 2 to 3 % low at 1 mm). The 185 K/W an article gives for an epoxy-filled via is not a model of the fill.

## 5. Related topics

01, 04, 06, 09 (vias under a package), 23 (the copper dominates the calculator's error).

## 6. Sources

* Fill types and materials: [ViaGuides] (JLCPCB, ALLPCB, Atlas PCB; the standard IPC-4761 not read: [IPC4761]). Copper, via thermal resistances and board area: [TI-AN2020]. Via arrays and pads, analytical models checked by CFD and measurements: [Shen2019] (abstract and structure).
* Own computation: [L-via].

*What was read and what was not verified:* from `research/via-fill/README.md` (read in full); the fabricator pages as recorded; IPC-4761 itself was not read.
