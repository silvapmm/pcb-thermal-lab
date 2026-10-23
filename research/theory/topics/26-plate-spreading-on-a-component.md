# 26. The base of a heatsink on a component: plate or only K/W?

![Plate spreading](../figures/fig_19_plate_spreading.png)

*Figure 19 (`figures/fig_19_plate_spreading.png`): left, the base plate under a small source: the heat spreads sideways in the base before it reaches the film to the air; right, the extra resistance of the base as a share of the whole top chain for five bases and two source sizes (the table of the research notes).*

Investigation: `research/component-heatsink/` (`base_spreading_study.py`, `block_contact_study.py`); text: `docs/research.md` R3 and R8. **Status: decided: K/W only on top of a component; the plate model stays under the board.**

## 1. The question

Is a plate model of the heatsink base (spreading in the metal) needed on top of a component, or is the catalogue `theta_SA` in K/W enough? The catalogue value already contains the spreading of the catalogue's own test source; a small component adds the conduction through the base under it and the spreading in the plate.

## 2. The physics

A small source on a larger plate has `R = R_0 + R_c`: the average sink resistance plus the maximum constriction (spreading) resistance, accurate to about 5 % when the aspect ratio is below 2.5 and the plate is square-ish (topic 18). The plate layer of the program (the lateral `k t` conductance of the block with a uniform film coefficient) reproduces the published example (aluminium 100 x 100 x 1.3 mm, catalogue 1.0 K/W, source 25 x 25 mm, `R_c` = 0.66 K/W): `R_c` = 0.69 K/W, total 1.69 against 1.66 K/W, +4.5 %.

## 3. The simulation (3D finite-volume plate 40 x 40 mm, catalogue 12 K/W)

Extra resistance on the mean temperature of the source, and its share of the whole top chain (`theta_JC(top)` + paste + `theta_SA` = 46.6 K/W for the 3.3 mm MOSFET, 41 K/W for the 5 mm LDO):

| Base | 3.3 mm source | 5 mm source |
| :-- | --: | --: |
| aluminium 1 mm | 1.69 K/W (3.6 %) | 1.32 (3.2 %) |
| aluminium 3 mm | 0.75 (1.6 %) | 0.54 (1.3 %) |
| copper 3 mm | 0.40 (0.9 %) | 0.29 (0.7 %) |
| carbon steel 1 mm | 6.31 (13.5 %) | 4.90 (12.0 %) |
| carbon steel 3 mm | 2.83 (6.1 %) | 2.04 (5.0 %) |

For an aluminium or copper base the spreading is 1 to 4 % of the top chain; it matters (5 to 13 %) only for a thin base of a poor conductor such as steel.

## 4. The decision

First version: **K/W only** (`theta_JC(top)` + interface + `theta_SA`), with a note that a thin steel or stainless base adds more. The plate model stays where it exists (a metal block under the board, where the geometry of contact and copper matters) and comes back for the component top only if a case needs it.

## 5. Limits

The 5 to 30 % of the catalogue literature applies to sources much smaller than the base and a low `theta_JC(top)`; the study covers two sources, two base sizes and uniform film coefficients.

## 6. Related topics

11 (the block layer), 13 (convection scenarios), 18 (spreading), 24, 25.

## 7. Sources

* Spreading resistance of a source on a plate: [Lee1995] (could not be read), [YovanovichMuzychkaEllison], [EC1998Spreading], [ECSimpleSpreading2004] (errors -2 to +5 %); the numerical example of the 1998 article (aluminium 100 x 100 x 1.3 mm, source 25 x 25 mm).
* Own computation: [L-parts].

*What was read and what was not verified:* from `docs/research.md` R3 and R8 (read in full); the correlation sources were summarised by the earlier work, not read here.
