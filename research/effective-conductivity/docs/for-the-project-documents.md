# Text for the project documents when this work is adopted

Nothing in the project documents was edited from the research branch. This file holds the corrections and the text to add.

## Corrections (with the measured effect of each)

| Where | What to change | Effect |
| :-- | :-- | :-- |
| `docs/research.md` lines 86 to 88 (and the copy in `research/component-heatsink/NOTES.md`), `docs/theory.md` sections 7 (the plate model: "reproduces the published spreading resistance") and the validation table ("Plate (block) model, published spreading resistance (Lee et al.), +4.5 %"), `docs/theory.md` references ("Lee, Song, Au and Moran (1995)") | Attribute the numerical example to the Electronics Cooling article of **Seri Lee** (1998); say that the 1995 paper was not located. Replace "+4.5 %" by "+0.6 %, -0.8 % and -4.6 % at the centre, the edge midpoint and the corner of the article (0.66, 1.29, 2.38 K/W) when the source edges coincide with cell edges (0.5 mm cells); at 1 mm cells the check reads +4 % at the centre because the 25 mm source falls half a cell off the grid" | None on any result of the program; the model is better than the documents say at the centre and edge and as good as the article's own 5 % at the corner |
| `docs/validation.md` section 15 and 17, `docs/models.md` where the plate model is described | The same attribution | None |
| `docs/theory.md` section on natural convection | Add that the laminar form of Churchill and Chu (Ra below 1e9) exists and what it would change (-0.7 to +0.2 % of the rise of a vertical board) | None |

No document of the project states that an averaged conductivity of the stack is adequate, so no correction is needed there; the statement of Culham and Yovanovich (the means can be 70 % to 300 % off) can be added where the one-node-per-layer idea is explained.

* `docs/validation.md` section 15 (and 17), `docs/theory.md` section 7 and `research/block-and-fins/`, `research/component-heatsink/`: the numerical example of the spreading resistance of a plate (aluminium 100 x 100 x 1.3 mm, source 25 x 25 mm, `R0` 1.0 K/W: centre 0.66 K/W) is in the Electronics Cooling article *Calculating Spreading Resistance in Heat Sinks* by **Seri Lee** (January 1998), not in a paper of "Lee, Song, Au and Moran (1995)", which has not been located. The article also gives the edge-midpoint value (1.29 K/W) and the corner value (2.38 K/W), now reproduced (`research/effective-conductivity/`).
* Where the documents say that the effective conductivity of a board can be taken as the geometric mean of the series and parallel conductivities, or that the harmonic mean is adequate (Lemczyk and others), add that Culham and Yovanovich (1998) show errors up to 70 % to 300 % for any such mean because of the spreading resistance and the layer order.

## Text for `docs/validation.md` (a new section)

**Published cases reproduced with an independent 3D solver.** `research/effective-conductivity/` (README, ten figures counting the diagrams). An independent finite-volume solver of a laminated block (`lib/layered3d.py`) reproduces: the centre, edge-midpoint and corner constriction resistance of Seri Lee's plate (0.668, 1.284 and 2.275 K/W against 0.66, 1.29 and 2.38); the cross of five sources of Muzychka, Culham and Yovanovich (maximum 80.62 C against 80.61, area-weighted mean source temperature 78.90 against 78.87) and their first case within 1 % of the rise; the effective conductivity of the five layer orders of Culham and Yovanovich within 2 to 6 %. The five models of the program agree with it within 0.3 % (FDM 1.2 % for a 5 mm source on 50 mm) on the Cu / FR4 / Cu version of that coupon for source areas of 1 % to 100 % of the board. One temperature node through the thickness falls short at the surface under a source by `q'' t / (2 k)`: 2.3 % for a 10 mm plate of `k` 50 and 13 % for `k` 10 (`research/effective-conductivity/` 4.6), negligible for copper layers.

## Text for `docs/roadmap.md`

* Input check for a thick, poorly conducting plate under a source (`research/effective-conductivity/INTEGRATION.md` 1).
* Natural convection of a vertical board: decide between the general and the laminar form of Churchill and Chu after reading the paper (`INTEGRATION.md` 2).
* Papers of the Waterloo archive still to read as images: the Elenbaas limit for a parallel-plate channel (mhtl91-11), the general laminar plate expression of Yovanovich (mhtl93-4), packaging density and effective conductivity (mhtl95-4).
