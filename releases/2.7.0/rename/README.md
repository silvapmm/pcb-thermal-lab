# Rename of the integration branch: develop to development

The maintainer renames the git branch by hand; this folder records the text rename done by pattern (the word `develop` is also an English verb, so nothing was replaced blindly).

## Changed (word `develop` as the branch name, 44 occurrences in 8 files)

| Class | Files | Occurrences |
| :-- | :-- | --: |
| Project agents (`from develop`, `against develop`, `origin/develop`) | `.claude/agents/{executor,maintainer,researcher,reviewer}.md` | 7 |
| Rules of `CLAUDE.md` (Git Workflow, Branches and Versions, Git Policy, Research branches, Claude Code Settings, Agents and workflow, flow diagram), lines 102-120, 223-224, 241-243, 270-283, 312, 329, 337-338, 350-351 | `CLAUDE.md` | 36 |
| Rule text of the harness integration note (`off develop`) | `releases/regression-harness/INTEGRATION.md` | 1 |

Also edited: one note in `CLAUDE.md` (Git Workflow) and one in `releases/README.md` saying the branch was called `develop` until 2.7.0; `docs/versions.md` line 11 'Release state' now says 2.7.0 is released (it still said prepared on `develop`).

## Left on purpose (about 599 lines in 181 files)

* Decisions Log, 'Where to continue', test-count history and 'Branches and Versions' history sentences of `CLAUDE.md`: records of what happened.
* `docs/versions.md`, `docs/validation.md`, `CHANGELOG.md`, `research/**` (READMEs, REVIEW.md, ROADMAP.md, scripts and their comments), `releases/**` reports: history; `develop` there means the branch now called `development`.
* Test and source comments and docstrings (`pcbthermal/checks.py`, `tests/test_*.py`): "values of develop before the change", history of a number; no test reads the branch name.
* `releases/regression-harness/scripts`: `--label develop`, `develop-tip` are free labels of output files, not git refs.
* Commit messages and tags (untouched); the verbs "develop", "developed", "developer", "development" (the word).

## Lines of the git-ignored `.claude/settings.local.json` the maintainer must change (not edited here)

* line 28: `"Bash(git branch -D develop*)"` -> `"Bash(git branch -D development*)"`
* line 29: `"Bash(git branch -d develop*)"` -> `"Bash(git branch -d development*)"`
* line 48 (text of the `autoMode.allow` rule): `... zero commits outside develop.` -> `... outside development.`
* `worktree.baseRef` (line 42) is `"head"`: no change. No other line names `develop`.
