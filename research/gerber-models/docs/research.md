# Research summary, phase 2: the copper in the simulation models

Ready to paste into the project `docs/research.md` as a section when the maintainer adopts the work (updated 2026-10-23). Everything is reproducible from `research/gerber-models/` (README sections, `CONCLUSIONS.md`, `LOG.md`); nothing in `pcbthermal/` was changed.

## Open now: the copper in the simulation models (2026-10-23)

**Answers** (numbers in the README of the folder):

* **The fill fraction is biased cool**: 10 to 23 % on real copper (up to 49 % across stripes). Flow-based face conductances (Sampson 2005/2017, prior art) are within 0.3 to 3.6 % in every case tested (README 4.4 to 4.13); lambda 0.5 within 1.0 to 3.2 %; coverage masks cut the error of the flow-based faces from 6.5 to 4.1 % (4.26).
* **`Zone.fill` keeps its formula; imported copper needs its own element**; zones are combined per cell with a maximum, which loses copper in abutting zones; the fix is the maximum per sample point, not an additive rule (4.27, 4.39).
* **Every model** (4.16, 4.27, 4.34, 4.35, 4.37): FVM 11.9 to 2.6 %, FDM 15.9 to 7.1 %, Lumped 13.0 to 4.8 %, Analytic 18.6 to 12.2 % (5.9 % with one effective conductance); on rectangles the Lumped is 16 % and the Analytic 26 % below the FVM, the 3D solid 7 to 9 % above (two layers); the 3D solid has no laminate under a single copper layer (346 to 174 K once corrected).
* **Import end to end** (4.31): -15.1 % today against -2.1 / -5.3 % (Stormduino) and -5.0 % against +4.0 / +2.1 % (own board); another reader changes it by 0.01 to 0.04 %.
* **Mappings as an option** (4.38): flow-based faces, lambda 0.5 and the cell problem 1.7 to 2.5 % against 6.5 % for the fill fraction; `SolverOptions.copper_mapping` with `fill` as default.
* **Literature** (`docs/literature.md`): the flow-based faces are Sampson's method, the tile bound is Blackmore's, Guenin suggests two tests not yet done.

**Not validated**: any measurement of a physical board; the 2D Bruggeman and Hashin-Shtrikman closed forms and the Keller-Dykhne duality are from memory (checked by limits); Sampson's board could not be rebuilt (an analogue gives a factor of 5 to 10 against his 26); the corrections of 4.39 were not run through the whole battery.

**Open decisions for the maintainer**: which stage enters the program (`INTEGRATION.md`); the zone `pattern` for hatched zones; the union of zones by sample point and the 3D laminate fix (a `fix/<topic>` branch); the option `copper_mapping`.

Pictures (`../figures/`): `fig_01_copper_mapping_to_cells.png`, `fig_02_ic_board_thermal.png`, `fig_03_import_end_to_end.png`, `fig_04_import_setup.png`, `fig_05_models_our_board.png`, `fig_06_rect_board_models.png`.

* **Thin tracks and angles** (README 4.42): a 0.05 mm track already cools a 6 mm heater by 3 %; the mask recognises a track if the pixel is at most half its width; the 1 mm cells reproduce 96 to 98 % of an axis-aligned track's effect but 38 to 53 % (flow-based faces) of a 45-degree one: isolated diagonal copper is the largest residual error. **Eleven boards** (4.43): lambda 0.5, cell problem and flow-based faces 1.3 to 1.5 % against 6.2 % for the fill fraction. Guide: `REPORT.md`.
