# releases/

Release work: the tools and the reports of the release gate (`CLAUDE.md`, "Agents and workflow"). **Not investigations**: `research/` holds one folder per question; the regression harness, the reproduction passes and the final opinions of a release never go there.

| Folder | What it holds |
| :-- | :-- |
| [`regression-harness/`](regression-harness/README.md) | The harness of every release: 17 boards x 5 models x 3 cells run on a tag and on the tree (`scripts/study_baseline_release.py`, `study_run_suite.py`), the classified diff against the table of expected shifts (`study_diff.py --strict`, `reference/expected_shifts_<version>.json`), the freeze of the reference file (`study_freeze_reference.py`), the version comparison (`scripts/regen_version_comparison.sh`). `lib/regress_*.py` is copied byte for byte into `tests/regression/` (`tests/test_harness_copy.py`). |
| [`2.4.5/reproduction/`](2.4.5/reproduction/README.md) | Reproduction pass of 2.4.5. |
| [`2.5.0/reproduction/`](2.5.0/reproduction/README.md) | Reproduction pass of 2.5.0 (parts A to E). |
| [`2.6.0/reproduction/`](2.6.0/reproduction/README.md) | Reproduction pass of 2.6.0 (research tests on the combined tree). |
| [`2.6.0/final-opinion/`](2.6.0/final-opinion/README.md) | The reviewer's final opinion on 2.6.0 (release gate step 5). |
| [`2.7.0/research-audit/`](2.7.0/research-audit/README.md) | The directed audit 'README against code, folder by folder' of every research folder on the 2.7.0 tree (branch `release/2.6.1-research-audit`, named when the next version was still planned as 2.6.1; it is now 2.7.0, and the branch keeps its name as the record), with the folder renames by topic. |
| [`2.7.0/doc-review/`](2.7.0/doc-review/README.md) | The documentation review of 2.7.0 (step 6b of the release gate): the checklist of what was checked, changed and left stale on purpose. |

## Layout rule

`releases/<version>/{reproduction,final-opinion,...}/` for the reports of one version (each with its `README.md`, and `scripts/`, `tests/` when it has code); `releases/regression-harness/` for the shared tooling. Python files follow the Doxygen and licence-header rules (`tests/test_docs.py` covers `releases/**/scripts` and the harness `lib/`). A new version adds `releases/<version>/`; a `releases/<version>/README.md` is written only if the folder needs an index.

## How a release uses them

1. After the version bump, run the harness on the previous tag and on the tree and freeze the numbers (`CLAUDE.md`, "Branches and Versions", frozen numbers).
2. The `tester` writes the reproduction pass into `releases/<version>/reproduction/` (branch `release/<version>-reproduction`, e.g. `release/2.7.0-reproduction`).
3. The `reviewer` writes the final opinion into `releases/<version>/final-opinion/`.

Branches made before this folder existed (`research/reproduction-245`, `research/reproduction-250`, `research/reproduction-260`, `research/release-regression-245`, `docs/final-opinion-260`) keep their names as the record.

## Branch history

Release work was first done on `research/` and `docs/` branches. The commits are duplicated under the `release/` names (the same commits); the maintainer deletes the old names by hand. The rule: release work (reproduction passes, regression harness, final opinion, refreeze) lives in `releases/` and on branches named `release/<version>-<topic>` (`release/regression-harness` for the harness); `research/` and `research/<topic>` branches are only for investigations; a branch is never named `research/` for release work.

| Old branch | New branch | Folder now |
| :-- | :-- | :-- |
| `research/release-regression-245` | `release/regression-harness` | `regression-harness/` |
| `research/reproduction-245` | `release/2.4.5-reproduction` | `2.4.5/reproduction/` |
| `research/reproduction-250` | `release/2.5.0-reproduction` | `2.5.0/reproduction/` |
| `research/reproduction-260` | `release/2.6.0-reproduction` | `2.6.0/reproduction/` |
| `docs/final-opinion-260` | `release/2.6.0-final-opinion` | `2.6.0/final-opinion/` |

The integration branch was called `develop` until 2.7.0 (renamed `development` after the release of 2.7.0); older entries keep the old name.

The rename is done: the branch is `development` locally and on `origin` (`origin/develop` was deleted by the maintainer); see `2.7.0/rename/README.md`.
