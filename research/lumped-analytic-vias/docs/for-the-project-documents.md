# Text for the project documents (when the work is adopted)

Not applied to `README.md`, `CHANGELOG.md`, `docs/` or `CLAUDE.md` from the research branch; to be copied on the `fix/via-constriction` branch. **Review note**: the texts below describe both proposals as the researcher wrote them; the reviewer recommends the Analytic proposal and, for the Lumped model, the micro well alone or nothing (README 10, `INTEGRATION.md` 6): if so, drop the cluster term and the legacy option from these texts and quote the Lumped numbers of `L_ring`.

## `docs/research.md` (while the decision is open)

**Lumped and Analytic models overstate vias (A6, `research/lumped-analytic-vias/`).** Read: Fish (2017) on the microspreading resistance of via cells (in part), the flux-tube spreading review of Yovanovich and others (text only). Simulated: the program's Lumped and Analytic models against a fine-grid layered solver (1/16 mm, barrels drawn) and a 3D solver on about 150 board configurations (unit cell of a lattice, a lone via, a row, 3 x 3 arrays at 3.5 to 1 mm on 2, 4 and 6 layers, thermal pads) and on the example board with denser arrays. Found: both models join the planes through the barrel conductance alone and leave out the constriction of the heat converging on the barrel, `(ln(R/r_t) - 3/4) / (2 pi S)` per plane; the Lumped model of the program equals the closed form without it to the digit on a lattice cell (error 1.8 to 60.6 %), and the Analytic model carries an accidental, tile-dependent constriction (+36 to +173 % with the tile) plus a position error. Fixes measured on copies: a Krogh well per plane with a cluster term (Lumped; the copper-fill gain of the example board 6.79 to 4.47 K against 4.20 K for the corrected FVM) and a self-term, a bilinear spread and 1 mm tiles around vias (Analytic: 4.27 K, mean error 0.3 to 2.3 % on every kind of simple board). Still open: the lone via and the dense arrays of open barrels in the Lumped model, Gerber boards with many vias.

## `CHANGELOG.md` (Unreleased, under Fixed)

* Lumped and Analytic models: the heat converging on the barrel of a via (the constriction resistance of each plane) is now part of the model; the effect of copper-filled vias was overstated by 35 to 60 % (the example board: copper-fill gain 6.8 and 6.3 K, now 4.5 and 4.3 K; the FVM gives 4.2 K). Boards with vias change by 0.5 to 2 K in these two models. `SolverOptions.via_model = "legacy"` keeps the old numbers for one release and warns.

## `CLAUDE.md` Decisions Log (the maintainer's entry, to write on adoption)

*Via constriction in the Lumped and Analytic models* (`research/lumped-analytic-vias/`, reviewed): the cause of roadmap item A6 is the missing constriction resistance of the planes at the barrel; Lumped gets a Krogh well per plane with a Kron reduction of the barrel and a cluster term (groups of vias as one disc inside the rings), Analytic a self-term in the tile response, a bilinear spread of the via over four tiles and tiles of 1 mm around vias. The legacy behaviour stays selectable for one release. Constants assumed (not derived): macro radius from the touched rings, isolation 0.7 tile, guard half a tile, 1200 active tiles.

## `docs/versions.md`, chapter 'Planned' (as an item)

*Fix: the constriction of the vias in the Lumped and Analytic models* (after the investigation `lumped-analytic-vias`; branch `fix/via-constriction`): the two proposals of `INTEGRATION.md`, the option `via_model`, the warnings, the tests of `INTEGRATION.md` 3 and the update of the via scenarios of `docs/validation.md`. Open after it: the lone via and the dense open arrays in the Lumped model; a Gerber board with many vias.

## `research/ROADMAP.md` (A6, as done in this folder)

*A6. Why Lumped and Analytic overstate vias.* Studied (`lumped-analytic-vias`): the missing constriction; fixes measured; left open: the Lumped macro term on dense arrays (a better model of a sink at the centre of the footprint ring), the Lumped lone via (ring-dependent), Gerber boards with many vias, a reproduction of a published via-array constriction case (none found openly readable).
