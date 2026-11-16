# CLAUDE.md moves: check against `e7dfb609ed6b`

Old CLAUDE.md: 859 lines, 355113 bytes. New CLAUDE.md: 262 lines, 47641 bytes. docs/decisions-log.md: 272264 bytes.

## 1. Sections of the old file and where they are now

| Old section | Now in | Found |
| :-- | :-- | :-- |
| Project Overview | `CLAUDE.md`: ## 1. Project Overview | yes |
| Technology Stack | `CLAUDE.md`: ## 2. Technology Stack | yes |
| Language and Documentation Rules | `CLAUDE.md`: ## 3. Language and Documentation Rules | yes |
| Conventions | `CLAUDE.md`: ## 4. Conventions | yes |
| Licences | `CLAUDE.md`: ## 5. Licences | yes |
| Git Workflow | `CLAUDE.md`: ### Git Workflow | yes |
| Git Language and Naming | `CLAUDE.md`: ### Git Language and Naming | yes |
| Project Structure | `CLAUDE.md`: ## 13. Project Structure | yes |
| Project Structure | `docs/models.md`: ## Appendix: module map (detailed) | yes |
| Why the legacy solvers were replaced | `CLAUDE.md`: why its solvers were replaced: `docs/validation.md` 6 | yes |
| Why the legacy solvers were replaced | `docs/validation.md`: ## 6. | yes |
| Commands | `CLAUDE.md`: ## 14. Commands | yes |
| Branches and Versions | `CLAUDE.md`: ### Branches and Versions | yes |
| Git Policy | `CLAUDE.md`: ### Git Policy | yes |
| Papers library and OCR | `CLAUDE.md`: ## 7. Papers library and OCR | yes |
| Local boards library | `CLAUDE.md`: ## 8. Local boards library | yes |
| Research branches | `CLAUDE.md`: ## 9. Research branches | yes |
| Before every commit: update the documentation (mandatory) | `CLAUDE.md`: ## 10. Before every commit: update the documentation (mandatory) | yes |
| Maintaining This File | `CLAUDE.md`: ## 16. Maintaining This File | yes |
| Claude Code Settings | `CLAUDE.md`: ### Claude Code Settings | yes |
| Agents and workflow | `CLAUDE.md`: ## 12. Agents and workflow | yes |
| Where to continue (2.8.0) | `CLAUDE.md`: ## 15. Where to continue (2.8.0) | yes |
| Decisions Log | `docs/decisions-log.md`: # Decisions Log | yes |

## 2. Decisions Log entries

281 entries in the old log (bullets with their continuation lines, and the instruction line); 281 found byte-identical in `docs/decisions-log.md`; 0 missing.
Order of the entries kept: yes.

## 3. Project structure and the test-count history

65 lines of the old structure block (text and code block); 65 found verbatim in `docs/models.md` (appendix); test-count history (7176 characters) verbatim in `docs/versions.md` 'How each version was tested': yes.

## 4. Commands

11 commands in the old file; 11 still in CLAUDE.md.

## 5. Rules kept verbatim and new standing rules

| Text | In CLAUDE.md |
| :-- | :-- |
| something that must exist and be a RULE is putting that header, the one that mentions me and the licence, in ALL files | yes |
| #  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved. | yes |
| #  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution. | yes |
| Work branches are never deleted, locally or on the remote: they stay as the record of the work. | yes |
| The key is never printed, logged, put in a command line or a URL, or written in an exception, a report or a test output | yes |
| A transcription counts as READ only after the reviewer compares it with the page image | yes |
| no commit without updating, in the same commit, every file the change touches. | yes |
| Literature check (the sources are opened and the published cases are reproduced) | yes |
| When an investigation is closed (or a closed one is reopened and corrected) the reviewer must review it and update it | yes |
| Reports to the maintainer are short and in plain Portuguese | yes |
| QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests --timeout=900 --timeout-method=thread | yes |
| Pages go online to Google (Gemini) by the maintainer's decision | yes |
| The FEM is a program model | yes |
| The surface read-out is a VIEW, never a mode | yes |
| The theory is explicit and self-contained | yes |
| Numbers name their tree and their reference | yes |
| every number the user sees carries the name of its read-out | yes |
| A model correction moves numbers only through pending files | yes |
| The whole battery runs with the real-board environment PROVEN loaded | yes |
| A tester that cannot wait inside its session is resumed | yes |

## 6. Result

Nothing is missing.

## 7. Statements tightened, updated or dropped as stale (by hand, not by the script)

The script proves the sections, the log, the structure, the commands and the dictated rules. These are the statements whose wording changed on purpose; the old text is in the Decisions Log or in git (`git show e7dfb609:CLAUDE.md`).

- **Whole battery time**: "about 8 minutes" was stale; now "about 45 to 50 minutes" (the record in `docs/versions.md`).
- **Exhaustive test passes**: the pass branch was written `research/reproduction-<version>`, which contradicts the rule that release work is never on a `research/` branch; it is now `release/<version>-reproduction` (the example the old text gave: `release/2.7.0-reproduction`).
- **"Series for heavy work, parallel for writing"**: the old bullet said it was "superseded in part" by the load rule; merged into one bullet (series is the default when the PC is busy).
- **Dropped stale notes**: "the notes about agents and workflow go to `docs/agents-workflow`, the theory to `docs/theory-rewrite`" (branches of 2.4.x); "(on the branch `research/gerbers` until it is merged)" (merged long ago); the release-history sentences of "Current release" (in `docs/versions.md` and the log); the renamed folders `analytic-2-6`, `laminate-2-6` (in the log and `docs/versions.md`); the old `research/` release-branch names (in `releases/README.md` and the log); "Keep solver logic ... without wxPython" now says "without a GUI".
- **Test gate statement**: `tests/test_docs.py` is stated to cover `tools/`, `research/*/scripts` and `releases/**/scripts` too (the old file said so in the structure and research sections, not in rule 5).
- **Licence header scope**: `releases/` added to the list of folders (it was stated in the old structure line of `releases/`).
- **Kept as pointers**: "Why the legacy solvers were replaced" is one clause of the overview pointing to `docs/validation.md` 6; "Two roadmaps" and the review register moved to section 11.
- **Size**: the target was about 350 lines and 40 KB; the new file is 262 lines and about 47.6 KB. The rest is rules in force (the licence-header rule verbatim, the research rules, the release gate, the orchestration rules); cutting further would drop rule text, so it is left to the maintainer.
