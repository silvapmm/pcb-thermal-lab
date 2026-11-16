# Research tests that mirrored the program: decisions of 2.8.0

The question came from the maintainer: why keep tests that only reproduce the Lumped text of 2.7.1? He follows the reviewer's answer. The reproduction pass found research tests that failed on 2.8.0, or were skipped there, because they mirrored program source: a copy of a function, a patch of its text, or numbers frozen from an old commit.

Each test group falls into one of three cases:
* **Deleted.** The test only certifies that a copy equals the old source, or it is pinned to a commit and already failed on v2.7.1. The study README stays the record of its run.
* **Redone.** The claim of the investigation still means something for 2.8.0. The test is rewritten against the program as it ships, with numbers measured now.
* **Kept version-aware.** The folder's studies need the switch to reproduce their record.

Tree: `development` 232ba648 (the 2.8.0 candidate). Runs were light, one test file at a time, peak 1.8 GB.

| Folder | Test group | Decision | Reason and evidence |
| :-- | :-- | :-- | :-- |
| `lumped-via-groups` | copy equals the earlier patch; zone model without vias is the program; energy balance and restore of the patch; core-internal resistance; micro peak (5) | **deleted** | They certify the copies `lumped_groups.py` and `lumped_zones.py` against the 2.7.1 Lumped text, which the 2.8.0 first link rewrote (anchors not found). The zones were adopted in 2.5.0; the program's network is tested in `tests/`. |
| `lumped-via-groups` | zone model against the fine-grid reference; vias that conduct nothing (2) | **redone** | The claims hold for the program. The 3 x 3 array effect is -4.28 % of the 1/16 mm reference (18.914 K), bound 6 %. Dead vias give -0.88 % against the board without vias, bound 1.5 %. |
| `lumped-analytic-vias` | patched Lumped and Analytic "off" equal the values frozen from `f2d5c03` (2) | **deleted** | Pinned. They failed on v2.7.1 already (the program moved since: laminate, slabs, face laws). |
| `lumped-analytic-vias` | the patches restore the program (1) | **deleted** | Source-text patch of the 2.7.1 Lumped; it no longer applies. |
| `lumped-analytic-vias` | unit-cell error; the row of five vias; copper-fill gain of the example board (3) | **redone** | Adopted in 2.4.5 (`fix/via-constriction`). Unit cell: Lumped +0.89 %, Analytic -0.64 % of the 1/16 mm reference, bound 2 %. Row: Lumped +5.96 % (bound 8 %), Analytic -0.81 % (bound 2 %). Example-board gain: FVM 4.245 K, Lumped 4.666 K, Analytic 4.324 K, bound 0.5 K. |
| `lumped-near-edge` | the variants apply to the program text; the large-footprint regression of the variant (2) | **deleted** | The variants were ported by `research/lumped-edge-link` and became `fix/lumped-edge-first-link`, so the text they edit is gone. The program's own `tests/test_lumped_edge_first_link.py` covers the images and the footprint limit. |
| `lumped-near-edge` | heat balance and centre (parametrised by variant); corner deficit of the candidate (2) | **redone** | On the program: power out 1.000000 W, centred part +1.9 % of the FVM rise (bound 6 %). The corner part read -22 % on 2.7.1 and **-2.13 %** now (FVM 47.359 K, Lumped 46.349 K), bound 8 %. |
| `lumped-ring-uniform-deficit` | the copy is the program bit for bit at its defaults (1) | **deleted** | It certified the copy of the 2.5.1 Lumped text with the program's switches; the 2.8.0 first link ends that. The other 5 tests check the proposal on its own copy and pass. |
| `point-via-convergence` | the 'point' copy equals the values frozen from `f2d5c03` (2, FVM and FDM) | **deleted** | Pinned. They failed on v2.7.1 already. |
| `point-via-convergence` | copper-fill gain converges to the resolved reference (1) | **redone** | The roadmap regression, now on the program in the FVM and the FDM. At 1, 0.5, 0.25 and 0.125 mm it lies within 0.05 K of the reference (-4.513 K), bound 0.3 K. The frozen point-via half was removed. |
| `young-omega-tiles` | prototype patch installed and removed; bit for bit when switched off; modes hook (3) | **deleted** | Skipped since `fix/via-constriction` (2.4.5): the tile rule and the via self-term are in the program, so the patch has nothing to rewrite. |
| `lumped-zones-adoption` | zones off or without vias equal the program; group outside the footprint; fallback decision (3) | **kept, version-aware** | Its studies compare the zoned copy with the program and need the switch to reproduce their record. `lib/zoned_lumped.py` sets the program's plain-link fallback (`lumped.IMAGE_MAX_CELLS = 0`); `PCBT_ZONES_FIRST_LINK=2.8.0` runs the program as it ships (README 11). |
| `block-and-fins` | (no tests) `study_finned_block_all_models` | **study repaired** | Its wrapper of `blocks.extra_layers` now passes `board_cover` on. The premise of `study_why_coefficients_fail` is stale since M1; this is written in its README. |

**Totals.** 16 tests deleted (and the `potlinks` case of a parametrised test), 8 redone, 3 kept version-aware. The switches `PCBT_LUMPED_FIRST_LINK`, `PCBT_PROGRAM_TREE` and `PCBT_RUN_PINNED` of the first follow-up are removed again, with their conftests (no kept test needs them). Tests now, each folder on its own:

| Folder | Result |
| :-- | :-- |
| `lumped-via-groups` | 11 passed |
| `lumped-analytic-vias` | 10 passed |
| `lumped-near-edge` | 4 passed |
| `lumped-ring-uniform-deficit` | 5 passed |
| `point-via-convergence` | 17 passed |
| `young-omega-tiles` | 23 passed |
| `lumped-zones-adoption` | 20 passed |

No folder has a skipped test left.

**Rule for the future** (written in `research/README.md`): a research test that mirrors program source (a copy of a function, a patch of its text, or numbers frozen from an old commit) must either be version-aware or be removed when the program source changes. Version-aware means a switch that restores the program it copies, stated in the README. A claim worth keeping is re-tested on the program as it ships. The study README stays the record of its run.
