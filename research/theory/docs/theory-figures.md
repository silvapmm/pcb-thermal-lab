# Where each topic goes when it is adopted

| Topic | Goes into | Picture to copy to `docs/images/` |
| :-- | :-- | :-- |
| 01 layered idealisation | `docs/theory.md` 1.2 | `figures/fig_01_layered_idealisation.png` |
| 02 finite volumes | `docs/theory.md` 2 (and 1.3 for the coverage) | `figures/fig_02_fvm_cell.png` |
| 03 finite differences | `docs/theory.md` 3 | `figures/fig_03_fdm_nodes.png` |
| 04 3D solid | `docs/theory.md` 4 | `figures/fig_04_solid3d_slabs.png` |
| 05 Lumped rings | `docs/theory.md` 5 | `figures/fig_05_lumped_rings.png` |
| 06 Analytic series | `docs/theory.md` 6 | `figures/fig_06_analytic_modes.png` |
| 07 time stepping | `docs/theory.md` 2 ("Transient") | `figures/fig_07_theta_method.png` |
| 08 heat transfer coefficients | `docs/theory.md` 8 | `figures/fig_08_heat_transfer.png` |
| 09 parts and the junction | `docs/theory.md` 9 | `figures/fig_09_part_runaway.png` |
| 10 power profiles | `docs/theory.md` 10 | `figures/fig_10_profile_decision.png` |
| 11 metal blocks and fins | `docs/theory.md` 7 | `figures/fig_11_metal_block.png` |
| 12 Foster chain (planned) | `docs/versions.md` "Planned" ("Component element (the part of the plan not done)") | `figures/fig_12_foster_chain_planned.png` |
| 13 heatsink scenarios (planned) | `docs/versions.md` "Planned" (heatsink air flow) and `docs/research.md` R3, R6 | `figures/fig_13_heatsink_scaling_planned.png` |
| 14 virtual JEDEC, known power | `docs/calculators.md` 2.1 and 2.4, `docs/versions.md` "Planned" | `figures/fig_14_virtual_jedec_planned.png` |
| 15 import and power list (planned) | `docs/versions.md` "Planned" (import) | `figures/fig_15_import_to_power_planned.png` |
| 16 multigrid (planned) | `docs/versions.md` "Planned" (solvers) | `figures/fig_16_multigrid_planned.png` |
| 24 thermal interfaces and metals | `docs/research.md` R2, `docs/models.md` 15, 16 | `research/component-heatsink/figures/fig_04_block_metal_and_interface.png` |
| 25 contact area, gap, chain | `docs/research.md` R3, R5 | `figures/fig_17_air_gap.png`, `figures/fig_18_level_chain.png` |
| 26 plate spreading | `docs/research.md` R3, R8 | `figures/fig_19_plate_spreading.png` |
| 27 datasheet numbers and compact models | `docs/research.md` E3 to E8 | `research/component-heatsink/figures/fig_06_package_sections.png` |
| 28 continuum and sources | `docs/theory.md` 1.1, 1.3 | `figures/fig_20_continuum.png`, `figures/fig_21_coverage.png` |
| 29 verification ladder | `docs/theory.md` 11 | `figures/fig_22_verification_ladder.png` |
| 30 board orientation | `docs/models.md` 18 (and theory 8) | `figures/fig_23_orientation.png` |
| 31 program architecture and API | `docs/models.md` 7, 8 | `figures/fig_24_architecture.png` |
| 32 removed program against the current | `docs/validation.md` 6 | `figures/fig_25_legacy_vs_current.png` |
| 33 time-dependent results | `docs/validation.md` 7 | `figures/fig_26_time_results.png` |
| 34 input checks | `docs/models.md` 3 | `figures/fig_27_input_checks.png` |
| 35 curved boards | `docs/models.md` 14 | `figures/fig_28_curved_boards.png` |
| 36 prepreg and sheets in a gap | `docs/models.md` 17 | `figures/fig_29_prepreg.png` |
| 37 why the FVM and the Analytic model agree | `docs/validation.md` 4 | `figures/fig_30_why_fvm_analytic_agree.png` |
| 17 to 23 | their own investigations; the text goes into `docs/theory.md` as new sections when the work is adopted | the figures named in each topic (they already live in the investigation) |

The figures are copied (with an italic caption line) in the commit that adopts the text, together with the text of the section they explain. The sources of a topic go into the bibliography of the document that receives it.
