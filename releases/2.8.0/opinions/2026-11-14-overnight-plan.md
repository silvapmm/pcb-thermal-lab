# Overnight plan for 2.8.0: reviewer's opinion

Scope: three questions on `development` e02ba367 and the branch `fix/housekeeping-280`. Read-only review; this file is the only change. Nothing was committed, merged or pushed.

## Verdicts

| Question | Verdict |
| :-- | :-- |
| 1. Wording of G1 in `docs/versions.md` | **Change it**, and change it in the five files that carry the same reference, not only in `docs/versions.md` |
| 2. `fix/housekeeping-280` | **GO** for a `--no-ff` merge after the whole battery; no defect found; a small test of the ignored keyword is advised, not required |
| 3. Wave 2 order | **Changed slightly**: light items first while the machine is shared; first two: the metal-block warning re-measure and the finite-element extensions (A43) |

## 1. The measured board (G1)

**Finding.** The two lines are not a generic idea. Line 363 says 'the third party's board' and names a branch a named research branch for that board; line 429 says the first dataset 'may come from a third party's board' and that the maintainer has none of his own. Both point to a specific board that exists outside the project. The same reference is in four other tracked files:

| File | Line | Text to neutralise |
| :-- | :-- | :-- |
| `docs/versions.md` | 363, 429 | 'the third party's board', a named research branch for that board, 'third party's board (the maintainer has no measured board of his own)' |
| `research/ROADMAP.md` | 19, 133, 179, 180 | 'a third party built one and his data may be the first dataset', row 'The third party's board', row 'Request list for the third party' |
| `research/REVIEW.md` | 86 | '(a third party's board, ...)', 'ask the third party for the data' |
| `CLAUDE.md` | 411 | heading 'and the third party's board for G1' and the sentence 'The maintainer has no measured board yet but a third party built one ...' |
| `releases/2.7.0/final-opinion/fem-reference-opinion.md` | 76 | 'external data (the third party's board)' |

The disclaimer and the Results-summary line ('never compared with a measured copper board') are generic and stay.

**Neutral wording** (G1 is a future physical measurement of a purpose-built board of our own; the request list stays as a generic list for any external dataset):

* `docs/versions.md` line 363, replace the paragraph by:
  > **The physical measurement (G1) does not block the version**: a physical measurement of a purpose-built board (the plan in `research/ROADMAP.md` section 5) runs on its own research branch when the data exists; until then 2.8.0 ships without it and the Results-summary line 'never compared with a measured copper board' stays.
* `docs/versions.md` item 5 (line 429), replace by:
  > 5. **The physical measurement (G1)**: no model has been compared with a measured board. G1 is a physical measurement of a purpose-built board (the plan and the list of data a measurement must record are in `research/ROADMAP.md` section 5: the stack-up, the copper layout, the power per part, the ambient temperature, the orientation, enclosure and mounting, the position of every reading, the measured temperatures, the uncertainties and a photograph); the lead time of the boards is the long pole. It decides the face-up law (board D) and removes the line 'never compared with a measured copper board' of the Results summary.
* `research/ROADMAP.md` line 19, first cell: 'G1: the first measurement dataset: a physical measurement of a purpose-built board (the plan of section 5)'; line 133: 'a measurement on a physical board built for the purpose (section 5)'; row 179 removed; row 180 renamed 'Data a measurement must record' with the same nine points, 'the third party' removed ('how the power was measured' etc. stay).
* `research/REVIEW.md` line 86: 'the first measurement dataset (a purpose-built board, `ROADMAP.md` section 5)' and 'build the boards of the plan'.
* `CLAUDE.md` line 411: heading '... between 2.7.0 and 2.8.0' (drop 'and the third party's board for G1'); replace the sentence by 'G1 is a physical measurement of a purpose-built board; the plan and the data it must record are in `research/ROADMAP.md` section 5.'
* `releases/2.7.0/final-opinion/fem-reference-opinion.md` line 76: 'external data (a measured board)'. It is a signed release record; editing it is acceptable because the change removes a reference and does not change a verdict, but the maintainer may prefer to leave release records untouched: his choice.

These are document edits on a `docs/<topic>` branch (for example `docs/g1-neutral-wording`), maintainer agent, quick tests (`test_docs`, `test_license_header`, `test_third_party_text`). **Git history keeps the old text** (published history is never rewritten); only the tree going forward is neutral. Say so to the maintainer.

**Related finding, same commit area.** Commit c93ec5f2 ('Add six generic items') put numbers in 'Planned: 2.8.0' that no script of the repository produces: 'tens of percent' for the metal block, 'about 45 % low' for the Lumped dense via group, '8 to 13 %' and '2 to 6 %' for the via cluster under a tab block, 'about twice too high' for the bare-metal emissivity, '2.5 to 6.5 K/W' for thick-film resistors. By the review rule a number no script reproduces is a finding, and their origin cannot be checked here. Advice: keep the items, drop the numbers until a study in `research/` prints them on a synthetic case of ours ('a first check suggests a large difference; to be measured'). The 0.75 K/W of the shipped 'D2PAK / TO-263' entry is in `pcbthermal/data/defaults.json` and may stay.

## 2. `fix/housekeeping-280`

Two commits, 11 files. Checked:

* `viawell.build(..., origin, active=None)`: nothing in the body reads `active` (grep); the FVM (`fvm.py:237`) and FDM (`fdm.py:308`) calls drop it; no other caller in `pcbthermal/`.
* The research code that matched the call by text (`research/point-via-convergence/lib/program_patch.py`, regexes `_LOOP_FVM` and `_LOOP_FDM`, used also by `research/via-real-board/lib/edge_patch.py`) matches `viawell\.build\(.*\n`, so the shorter call still matches: `pp.patched("mw_disc")` compiles on the branch.
* The five wrappers (`barrel.py`, `contact.py`, `edge_hook.py`, `viavariants.py`, `order_patch.py`) take `active=None` and pass it on; the program accepts it. `order_patch.py` keeps the default before `*a`, harmless since the program never passes more positionals.
* `factor_reuse` docstring and comment now state the true peak (one LU plus the matrices of the solve under way): correct.
* README: the three images exist in `docs/images/`; CHANGELOG `[Unreleased]` and the 'Planned' rows are consistent.
* Run on the branch (light set): `tests/test_via_well_sheet_order.py`, `test_imported_via_rim.py`, `test_docs.py`, `test_license_header.py`, `test_version.py`, `research/via-well-sheet-order/tests`, `research/via-contact-geometry/tests`: 765 passed.

**Pre-existing failure, not of this branch**: `research/point-via-convergence/tests/test_program_patch.py` fails 3 tests on `development` too (the 'point' copy reads 35.623 K against the frozen 35.611 K of f2d5c03; FDM 35.976 against 35.962). Most likely the barrel length `d + 0.5 t_cu` of 2.6.0 entering the copy through `viawell`; not verified. It is outside `tests/`, so the battery does not see it. To record in `research/REVIEW.md` and fix on that folder's branch (stale frozen values or the copy), not here.

**Deprecation test**: not required for the merge (the research tests that pass `active` positionally already exercise it), but cheap and worth it: one test that `viawell.build` returns identical blocks and `gz_via` with and without `active` (positional and keyword), so that a later change cannot give the keyword a meaning or drop it while research code still passes it. Can be added on the branch before the battery.

**Merge**: GO with `--no-ff` after the whole battery by the tester. The battery is heavy (about 43 minutes, a few GB): start it only when the shared study has released the machine or the load rule of `CLAUDE.md` allows it. `tmp/real-board-study/.heavy_lock` is a directory that belongs to that study: look, do not touch. Check `git ls-files .venv` is empty before the merge.

## 3. Wave 2 order

Proposed order while the machine is shared (light first, enablers early, heavy runs behind the lock):

1. **Metal-block warning re-measure** (S, light, synthetic, runs now).
2. **Finite-element extensions A43** (M; plan and scripts now, small meshes now, large meshes after the lock clears).
3. **Lumped dense via group** (M, light to medium; benefits from A43 for the reference).
4. **Transient reference** (M, heavy time stepping; wait for a quiet machine).
5. **Via cluster under a tab block** (needs A43's barrel and cluster cases).
6. Then E13 (memory-heavy, alone on the machine), 5a, A18, A27, A32/A40, A30, the memory-law refresh, as in the table.

Change from the table: the metal-block item and the dense via group move ahead of the transient reference because they are light and the machine is shared; the transient reference stays before E13.

**First two items and their briefs**

*Metal-block warning re-measure*: branch `research/block-and-fins` (the folder exists, no branch: create it from `development`), researcher with the executor, then reviewer.
- Researcher/executor: on 3 to 6 synthetic boards of ours (a plate joined to the board through one, two and four pads, steady state) compare the Lumped and Analytic block with the FVM at 0.5 and 0.25 mm and the 3D solid; extend `scripts/block_equivalent_study.py`.
- Report the spread against the sentence 'within about 5 % of the FVM in the tests' (`api.py:1053`, `gui/panels.py:917`, user guide) and propose the corrected text with the measured range.
- Reviewer: re-run, check the 3D solid is converged (cell halving) and that both sides model the same contact; then a `fix/` branch for the text only.

*Finite-element extensions A43*: reopen `research/independent-fem-edge` (merge `development` first), researcher plans, executor runs, then reviewer.
- Researcher: write the cases of `ROADMAP.md` A43 (hollow plated barrel against `d + 0.5 t_cu` and the rim rule; stripes and imported masks of validation 40 and 45; the L outline; the FDM via effect) with mesh sizes and declared peak memory per run.
- Executor: run the cases under 2 GB now and queue the rest behind the study's lock; every case with a mesh-halving check and an energy balance against the tool's own tests.
- Reviewer: compare each program column with the finite elements on the same board (copper conductivity, films, edge losses, anisotropy), then update the README, `REVIEW.md` and `ROADMAP.md`.

## Open decisions for the maintainer

1. Apply the neutral G1 wording to all five files (advised), and whether to touch the 2.7.0 release record.
2. Drop the unsourced numbers of the six new 'Planned' items until a study prints them (advised).
3. Add the small `active` test on `fix/housekeeping-280` before the battery (advised, not blocking).
