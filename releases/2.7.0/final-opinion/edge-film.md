# Review: the edge film of imported copper on an outline, from the centroid

Branches: `research/imported-copper-edge-film` (d3cd9097) and `fix/imported-copper-edge-film-centroid` (a61f7381, from `develop` 24882dfb). Reviewer's verdict: **GO for both, with the two fixes below applied on the fix branch** (not committed by the reviewer).

## Verdict in short

* The claims reproduce on the program of the fix branch to the printed digit (ten turned and shifted 20 mm boards, imported copper 1.2 mm inside the outline, 1 mm, mean error against the 3D truth): `h_side` 10 -0.43 to -0.39 %, 200 -3.00 to -0.94 %, 500 -4.90 to -1.13 %, 1000 -6.36 to -1.26 %.
* The 3D truth of the investigation (`lib/truth3d.py`) agrees with the program's independent solver `tests/helpers/layered3d.py` to 5e-7 on the same board (isotropic laminate, insulated edge, copper inside the outline and to it).
* **The risk left open (copper reaching the outline) is not a defect.** Against the truth, copper to the wall, 20 mm board: 200 W/m2K 1 mm -1.32 % (before) to +0.34 % (after), 0.5 mm -1.16 to -0.33 %; 1000 W/m2K 1 mm -3.90 to -0.53 %; a 12 mm square with a 2 mm heater -1.36 to +0.70 % at 1 mm, -1.39 to -0.38 % at 0.5 mm, -1.22 to -0.72 % at 0.25 mm. The only worse figure is the worst board of the 12 mm square at 1 mm (+2.43 against -2.01 %). No exception, blend or inset-only rule is justified, so none was implemented. The 92.93 K of the 12 mm quadrilateral of the tests at 1 mm is the cell error of a cell half the heater (90.20 K at 0.125 mm); the drawn board's 91.77 K is not a reference.

## Findings

| # | Kind | Finding | Evidence | Action |
| :-- | :-- | :-- | :-- | :-- |
| 1 | defect in the program (minor) | On a board with some imported and some drawn layers, the laminate nodes of the rule took the centroid distance also between two drawn layers, against the stated rule 'drawn layers keep the centre'. | 4-layer turned board, outer layers imported, inner drawn, 1 mm: 85.72 K, 85.49 K after the fix | Fixed: `Network.laminate_neighbours` (the copper layers next to every node added by the rule); a laminate node takes the centroid only next to an imported layer. Test `test_a_laminate_node_takes_the_centroid_only_next_to_an_imported_layer`. |
| 2 | memory (minor) | `geometry.cover_centroids` refined 64 cell rows at a time: 173 MB on a 200 x 150 mm outline at 0.25 mm, 369 MB at 0.125 mm, outside the memory guard. | tracemalloc | Fixed: 16 rows (54 / 131 MB, same time 0.42 / 1.9 s, centroids equal to 4e-13 m). |
| 3 | stale document | `docs/validation.md` 39.3, `CHANGELOG.md` and `docs/versions.md` 'Planned' 21 said that copper reaching the outline was not compared with a truth and that the centroid film was 1.3 % hotter than the drawn film. | this review | Rewritten with the truth table (validation 39.3; the limits move to 39.4). |
| 4 | limit to record | The film from the centroid converges from above, the film on the node from below; at 1 mm on T and L outlines the change moves the hottest point +2.9 to +3.8 % of the rise (no truth for these shapes). | `study_edge_film_review.py shapes` | Recorded in validation 39.3. |
| 5 | study layout (not changed) | `lib/study_outline_mask.py` of the investigation is a study kept in `lib/` because `lib/cases.py` imports its board builder. | | Noted in the research README 8.6. |

## Other checks (all pass)

Symmetric matrix, no positive off-diagonal entry, constant field to 2e-17 and heat balance to 1e-12 on T, L, four-layer, striped, mixed and real boards; time simulation of the 12 mm board ends at 118.33 K against 118.35 K steady; real imported outlines of the local library: oswlight (round, 4 layers) +0.63 / +0.31 / +0.17 % and rp2040 +0.36 / +0.21 / +0.10 % of the rise at 1 / 0.5 / 0.25 mm and 200 W/m2K, within 0.01 % at 10 W/m2K, run time unchanged. A drawn board does not call the centroid (test). Tests on the fix branch: `test_imported_edge_film_centroid.py` (14), `test_cut_cell_links.py`, `test_imported_copper.py`, `test_laminate_rule.py`, `test_laminate_edge_band.py`, `test_maximum_principle.py`, `test_docs.py`, `test_license_header.py`, `tests/regression` at 2 mm: 995 passed, 4 skipped, 2 xfailed (before the strip change; after it the four files most concerned, 771 passed). Research tests of the folder: 6 passed; the program is untouched on the research branch.

## Reproduce

`.venv/bin/python releases/2.7.0/final-opinion/scripts/study_edge_film_review.py wall 200,1000 1,0.5` (the truth is computed, about 5 minutes per coefficient; needs `research/imported-copper-edge-film/lib`, or `PCBT_EDGE_FILM_LIB`), `small 200 1,0.5,0.25`, `shapes`, `real` (the local library, `eval "$(pcb-library/scripts/link_env.sh)"`).

## Not verified

The whole battery (the maintainer's, before the merge); a four-layer truth, a disc truth and a truth for T, L, striped and real boards (only the move of the change was measured); the drawn-layer centroid film with copper to the wall; the FDM (unchanged).

## Open decisions for the maintainer

1. The centroid film for the DRAWN layers (`docs/versions.md` 'Planned' 21, research ROADMAP A33): moves frozen numbers of three outline boards; before deciding, repeat the copper-to-the-wall check with drawn zones.
2. Whether the -2 % of four sub-gaps below the resolved laminate at a bare edge band is accepted as the known 1/n limit (n = 16 halves it at 2.3 times the unknowns).
