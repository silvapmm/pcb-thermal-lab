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
| 28 continuum and sources | `docs/theory.md` 1.1, 1.3 | `figures/fig_20_continuum.png`, `figures/fig_21_coverage.png`, `figures/fig_34_part_cut_cell.png`, `figures/fig_35_part_weight_rules.png`, `figures/fig_36_part_example_t.png`, `figures/fig_37_part_edge_shift.png` |
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


## Figures of the rewrite of `docs/theory.md`

Naming rule in `docs/images/` (one rule, decided here): a figure of this folder keeps its file name `fig_NN_topic.png` (the number is unique, so no clash), and a figure of another research folder is copied under a descriptive name without its number, prefixed by the folder (`models_comparison_lumped_rings.png`), as the via and SOR figures already are (`via_*.png`, `sor_*.png`). Each copy is made in the commit that adopts the text.

| Figure | File | Goes into `docs/theory.md` | Italic caption line (the text under the picture) |
| :-- | :-- | :-- | :-- |
| 38 | `fig_38_document_map.png` | the header (the map) | *Figure 38 (`figures/fig_38_document_map.png`): the board of the Problem is idealised in layers (section 1.2) for the FVM, FDM, Lumped and Analytic models; the 3D solid builds real slabs from the same board. Underneath, the pieces that the models share (metal blocks, vias, the heat transfer coefficients and their loop, parts, profiles, the checks). Schematic, no numbers.* |
| 39 | `fig_39_stackup_slabs.png` | 1.2.1 (advanced stack-up) | *Figure 39 (`figures/fig_39_stackup_slabs.png`): left, three copper layers and two gaps of different thickness (illustrative): the node of a layer represents its copper plus half of each adjacent gap, so the slabs add up to the board thickness; middle, the network the nodes make, with `g_j = k_th,j / d_j` per gap; right, a gap made of several sheets: in series through the gap, side by side along it (`combine_sheets`).* |
| 44 | `fig_44_laminate_nodes.png` | 1.4 (laminate nodes) | *Figure 44 (`figures/fig_44_laminate_nodes.png`): left, a section across a copper edge: the gap between two copper nodes is cut into `n` sub-gaps (here `n = 4`) in the cells where copper is absent plus a margin, and is the single link `k_z A / d` elsewhere; middle, the plan of the cells that are cut; right, `n` against the thickness of the gap and the one-layer board, whose laminate is a gap down to the bottom face. Illustrative proportions.* |
| 41 | `fig_41_block_section.png` | 7 (metal blocks, after 7.1) | *Figure 41 (`figures/fig_41_block_section.png`): left, a metal block on the board in section (illustrative proportions): the heat enters the block through the interface `R''` over copper, and over bare laminate also across half a slab of FR-4; it leaves through the exposed face (fins, `h_exp = h_face r_fin + h_extra`) and the side walls (`h_wall = h_face + h_extra`); the board face under the block loses nothing (factor `1 - c`). Right, the cell network these paths make.* |
| 42 | `fig_42_top_path_split.png` | 9 (top path as a root) | *Figure 42 (`figures/fig_42_top_path_split.png`): left, a part with a top path: the junction joins the ambient through `R_top` and the board through `theta` and `R_b`; middle, the residual `g(P_b) = P_b - P + p_top` of the split, computed with `pcbthermal.analysis.part_split` for a board resistance below (A) and above (B) the top resistance (illustrative values `P` = 2 W, `theta` = 5 K/W, `R_top` = 20 K/W, `R_b` = 8 and 40 K/W): monotone, one root, a kink where the top heat is clipped at `P` (case B); right, the plain fixed point `P_b <- P - p_top(T_max(P_b))` on case B, slope -1.6: it jumps between 0 and 1.6 W and is not used. Computed by `scripts/make_figures.py`.* |

`fig_01` was redrawn (it said that a one-layer board gets two laminate nodes; it now says that the gap is cut into laminate nodes where copper is absent). `fig_32` is not copied to `docs/images`: its numbers were not re-run for this version of the program. `models_comparison_lumped_rings.png` (a before-and-after picture) is not used in `docs/theory.md`; the Lumped rings are drawn by `fig_05`. `fig_36` and `fig_37` are in `docs/validation.md` 23 and `via_array_board_gain.png` in `docs/validation.md` 18. Also copied, with their present captions (see their topic files): fig_01 to fig_11, fig_20 to fig_23, fig_31, fig_33; and from `research/models-comparison/figures`: `fig_06_lumped_rings.png` (as `models_comparison_lumped_rings.png`). Where each goes in the new text: fig_20 to 1.1, fig_01 and fig_39 to 1.2, fig_21 (and the existing fig_34, fig_35) to 1.3, fig_02 and fig_07 to 2, fig_03 to 3, fig_04 to 4, fig_05 and the Lumped rings to 5, fig_06 to 6, fig_11, fig_41, fig_31 and fig_33 to 7, fig_08 and fig_23 to 8, fig_09 and fig_42 to 9, fig_10 to 10, fig_22 to 11, fig_38 to the header.
