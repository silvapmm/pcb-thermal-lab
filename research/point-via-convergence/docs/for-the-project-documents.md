# Text for the project documents (the via on the grid)

`docs/` of the research branch equals `develop` and is not edited here. These texts are folded in when `fix/point-via` is implemented (`INTEGRATION.md`); the theory text is in `theory-text.md`. Every number is printed by a script of `research/point-via-convergence/scripts/`.

## `docs/versions.md` (chapter Planned: the item 'Point via')

Replace the item by: "**Point via** (`fix/point-via`; evidence `research/point-via-convergence/README.md`). The via is one conductor reached through the weighted mean temperature of a footprint of cells in each plane and a Peaceman well (`ln(r_eff / r_t)/(2π S)`), `r_t = 0.78 r_v`; the barrel nodes are reduced to couplings added to the matrix. Converges with the cell (worst error of the via effect against the fine-grid layered reference 0.7 % at 1 mm, 0.5 % at 0.5 mm, 0.4 % at 0.25 mm and finer, program 7, 10 and 20 %; the layered model of a via is itself -2 to +4 % from an axisymmetric 3D barrel over 2 to 6 planes, README 3.3); example board at 1 mm: FVM 85.81 -> 85.22 °C, FDM 84.38 -> 85.12 °C. Also: the 3D solid gets one footprint rule for every via (its open and filled boards were different models at some cells). The SOR solver needs the via couplings or a refusal. Test: gain of the 3 x 3 board within 0.3 K of the reference from 1 to 0.125 mm."

## `docs/validation.md` section 2.1 (Against the grid)

The sentence "It has no limit to converge to ..." is replaced, when the item is implemented, by: "The via is an equivalent hole of radius `0.1985 Δx` on a point sink; the program reaches the real constriction at 0.76 mm for a 0.3 mm via. With the footprint and well treatment the gain of the 3 x 3 board is -4.42 to -4.51 K from 1 to 0.0625 mm against -4.51 K resolved." The example-board rows are re-run (85.22, 85.17, 85.15 °C at 1, 0.5, 0.25 mm in the FVM).

Until then, add after the sentence: "(the constant is `exp(-(γ + 1.5 ln 2)) = 0.19851`, computed from the lattice kernel; Peaceman's radial argument gives 0.2079 and his rounded value is 0.2; `research/point-via-convergence/README.md` 2)".

## `docs/models.md` (via model)

"A via is a vertical conductor between the planes. In the FVM and FDM it is reached from each plane through the mean temperature of a few cells around its centre and a well resistance; on coarse cells it is a point with a well, on fine cells a disc. Result: the temperature changes by less than 1 % of the via effect between 1 mm and 0.0625 mm cells; the radius `0.78 r_v` is a single constant that keeps the via within a few percent of a 3D barrel on common stack-ups."

## `docs/research.md`

Entry: "A5, the point via: studied; the treatment, its impact and the limits are in `research/point-via-convergence/`; waits for `fix/point-via`."

## `CHANGELOG.md` (Unreleased, when implemented)

"- **Vias converge with the cell** (FVM, FDM): the barrel is reached through a footprint of cells and a well instead of a point in one cell; the copper-fill gain no longer drifts when the cell is refined (example board: FVM 85.81 -> 85.22 °C and FDM 84.38 -> 85.12 °C at 1 mm; boards without vias do not change). **3D solid**: one footprint rule for every via."

## `CLAUDE.md` Decisions Log entry (when implemented)

"**The via on the grid** (`fix/point-via`, investigation A5): a source in one cell of a five-point stencil has the radius `0.19851 Δx` (computed; Peaceman 0.2, 0.2079 by his radial argument), so the point via over-constricted below 0.76 mm for a 0.3 mm drill. The via is now one conductor reached through the mean temperature of a footprint (centred disc, enlarged until its lattice effective radius is `0.78 r_v`) and a Peaceman well; couplings in the matrix, no new unknown. Measured: ..."

## `docs/research.md` / literature status

[Peaceman1978] S, [Peaceman1983] N, [Ibraguimov2022] R (sections 1 and 5.1), [Gjerde2019] S, [WolfsteinerDurlofskyAziz2003] S, [ShenWang2019Vias] R in part (`research/theory/BIBLIOGRAPHY.md`, section 1).
