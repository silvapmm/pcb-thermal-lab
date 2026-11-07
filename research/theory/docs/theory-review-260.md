# Review of `docs/theory.md` for the 2.6.0 release gate (step 3)

Reviewed against the code of the integration tree `feature/integration-260` at `e68da036`; corrections on the branch `docs/theory-review-260`, made from that tree (the 2.6.0 changes exist only there), documents only, nothing in `pcbthermal/`. The fast-wave item (`fix/fast-wave-ripple`, theory 10.5, validation 37) is under review elsewhere and was not reviewed here.

## Verdict

**GO for the theory of the 2.6.0 changes**, after the corrections below (all made on this branch). Every formula of the merged model changes was read against its code (constants, signs, units, conditions) and agrees; what was wrong were stale sentences that the new models contradicted, one sampling statement introduced by the exact-cover change, a few numbers that differed from the tables of `validation.md`, and the missing description of the hostile-outline bounds. No defect of the physics was found in the code.

## How it was checked

* Read against the code, section by section: Lumped first ring (`lumped.ring_edges`, `_equivalent_radius`: eq. 5.1 is the code), exact board cover and part weights (`geometry.exact_coverage`, `part_weights`, `_EXACT_SNAP`, `_EAR_MAX_VERTICES`), cut-cell apertures and the edge film (`fvm.Network._lateral_links`, `_cut_edge_film`, `EDGE_FILM_FLOOR` 0.25; the exclusion of imported copper; `solid3d` apertures and eq. 4.2 with `k_x`), 3D slabs (`solid3d.slab_rule`: `clip(ceil(d / 0.2 mm), 4, 16)`, the counts 8 / 6 / 4 / 10 / 18 of the text) and the face term (`laminate.face_terms`), Analytic per-layer edge (`analytic.py`: `h_eff`, `beta`, `beta_l`, `EDGE_MISMATCH_MIN`, GMRES restart 30 and 1e-6) and local transient (`LOCAL_MODES` 16, `LOCAL_MAX_UNKNOWNS` 3000, `analytic_local.FACTOR_BRACKET` 0.05 to 20), face-down convection (`convection.DOWN_COEFFICIENT` 0.475, `DOWN_EXPONENT` 0.2; the Ra 1e2 to 1e9 warning of `api`; figure 23 ratio `0.88 Ra^(-1/20)` recomputed), via barrel (`viawell.barrel_length`, `BARREL_COPPER_FRACTION` 0.5, used by the FVM, FDM, Lumped `gz_via`, `ViaSet.g_gap`, Analytic `d_barrel`) and the rim rule (`rim_copper_shares`, 48 samples, footprint-mean sheet when a share is below 1), laminate edge band (`laminate.edge_band`, `plan_gaps`: `h_side > 0`, two or more layers, a cut gap; the half-cell film `g/(1 + h_side dx / (2 k_ip))` follows from `_cut_edge_film`), Lumped near-edge warning (`NEAR_EDGE_SIDES` 1, `NEAR_EDGE_FLOOR_MM` 5) and small-part raster (`SMALL_PART_*`), the warnings `check_edge_laminate` (200 W/m2K) and `check_reduced_edge_laminate` (150 W/m2K mm), the outline bounds (`OUTLINE_MAX_*`, `POLYGON_MAX_PAIRS`, `Board.validate`), and the package format of `models.md` 8.2 (`package.py` constants).
* Cross references: every `validation.md` section number quoted by `theory.md` and `models.md` exists and the headings of `validation.md` and `theory.md` are unique (script); every key cited in the theory is in its table of sources.
* Numbers: the theory's numbers of the new items were compared with the tables of `validation.md` 31 to 36; the barrel shift was recomputed from `tests/regression/data/pending/via-barrel-and-rim-uncoupling.json` against `v2.5.0.json` (0.0163 to 0.1585 K). No study was re-run.
* Tests, once: `tests/test_docs.py`, `tests/test_license_header.py`, `tests/test_version.py`, `tests/test_help.py`, `research/theory/tests`: 680 passed.

## Defects found and corrected

| # | Kind | Where | What was wrong | Correction |
| :-- | :-- | :-- | :-- | :-- |
| 1 | wrong statement | theory 1.3.1, 1.3.2 | a heater on a rectangular board "sampled 4 x 4" and "s = 8 only when it cannot be clipped": `part_weights` with no outline is `coverage_fraction(..., BOARD_SAMPLES)`, 8 x 8 (the ring of `psi_JB` uses 4) | both sentences give the code's sampling |
| 2 | stale | theory 2.1.1 | "the FDM and the 3D solid keep the cover-scaled links (the 3D solid has the sliver defect ...: its own branch)"; the 3D solid has the apertures and eq. 4.2 | the 3D solid's treatment stated, pointer to section 4 and `validation.md` 33 |
| 3 | stale | theory 4 | "the same as the layered FVM will take"; sources by name, not by key | "as the FVM of 2.1.1"; [JohansenColella1998], [BarrettEtAl2022] cited and added to the sources line |
| 4 | stale | theory 6, Limits | "the FVM itself reads up to 17 % below the 3D solver at 200 W/m2K ... (A16)": the laminate edge band brought the FVM to -0.6 % / -2.3 % | the Analytic's own edge deficit (-5.2 % / -15.2 %) and its warning, `validation.md` 36.3 |
| 5 | stale | theory 10 | "the Analytic model smears vias and heatsinks in time" | the local modal transient of section 6 |
| 6 | stale | theory 5, first-ring limits; `validation.md` 31.6 | "a source near a board edge stays 4 to 15 % cool"; section 35 measures up to -22 % | pointer to the near-edge paragraph and section 35 |
| 7 | wrong number | theory 1.4, `models.md` 2.4.1 | band "at most -2.4 % (FVM)"; table 36.1 gives -2.3 % | -2.3 % |
| 8 | wrong number | theory 2.6, `versions.md`, `CHANGELOG.md` | barrel shift "0.016 to 0.159 K"; table 34.1 and the pending file give 0.158 K | 0.158 K |
| 9 | wrong number | theory 4 | sliver jump 15.9 K; `validation.md` 33.1 prints 15.8 K | 15.8 K with the pointer |
| 10 | missing | theory 1.3.2 | the hostile-outline bounds (100 000 vertices, 500 m of edges, 10 million crossings, 20 million box pairs, 2 million distance pieces, non-finite coordinates) were in `versions.md` only | a paragraph *Limits of a hostile outline* |
| 11 | stale | `models.md` 9 (3D solid on an outline) | "lateral conductivities scale with the cover; the edge loss goes through half a cell" | the apertures, eq. 4.2 and the block slabs |
| 12 | incomplete | `models.md` 2.2 (via) | the rim rule counted zones only; the code counts zones and heaters | "(or heaters)" |
| 13 | source table | theory 12 | [BochkovGibou2019] had no title; [SchwartzEtAl2006] listed for 2.1.1, cited only in 2.5; the "where used" of the cut-cell keys lacked section 4 | title, journal and pages from `BIBLIOGRAPHY.md`; the uses corrected |
| 14 | history in the theory | theory 1.2, 1.3.2 | "before 2.6.0 the length was d", "since fix/exact-board-cover", "the lattices of 2.5.1" | removed (the history is in `versions.md`) |
| 15 | stale | `validation.md` 34, 35, 36 | notes on why a section number was taken ("this tree ends at 33", "36 is reserved ... comes later") | removed |
| 16 | ambiguous reference | `versions.md` 'Planned' | "`validation.md` 31.7 of the star branch" (31.7 here is not that) | names the branch `feature/via-star-coupling` |
| 17 | incomplete | theory 4 caption, 11 | "slabs of at most 0.2 mm" (not above a 3.2 mm gap); the 3D-against-FEM row is a 4-slab measurement | caption states the rule; the row says it was not re-run with the slabs by thickness |

## Defects in the code (not fixed here, for a `fix/` branch)

* `pcbthermal/laminate.py:256`, docstring of `edge_band`: cites "docs/theory.md 3.2" for the cold edge; the section is 1.4 (text only).
* No defect of the physics or of the constants was found against the theory.

## Open items (for the maintainer)

1. `research/theory/BIBLIOGRAPHY.md` has two sections numbered 20 (`research/via-real-board/` and the table of `docs/theory.md`; already so on `develop`); the theory points to "section 20". Renumbering moves references in other documents; left as it is.
2. The display view modes and the package format are not physics and have no theory section; the package is described in `models.md` 8.2 (checked against `package.py`) and the view modes in the user guide.
3. The 3D-solid comparisons of `validation.md` 3 and 3.1 (and the row of theory 11) were measured with 4 slabs per gap; a re-run with the slabs by thickness would refresh them.

## What was not verified

No study was re-run: the numbers of the new items were checked for agreement between `theory.md`, `models.md` and the tables of `validation.md` 31 to 36, and one pending frozen file; whether the tables themselves reproduce is the tester's reproduction pass. The fast-wave item (theory 10.5, validation 37) was excluded by the task. The pictures were checked to exist and to show the item (the test of the figures passed); they were not regenerated.
