# Opinion on four leftover branches with commits not on `development`

Reviewer's opinion for the maintainer, who follows it. Nothing was deleted, merged or renamed by this review. Tree read: `development` at `af6bc80f`. Branches read with `git log development..<branch>`, `git diff development...<branch> --stat`, `git show` of every unique commit; none of the four exists on `origin` (`git branch -r` lists none of them), and every worktree (`.claude/worktrees/merge-280d`, `article-1319202`, `paper-notes`, `readout-selector`) is clean (`git status --short` empty).

Rules applied: work branches (`fix/`, `feature/`, `docs/`, `research/`) are never deleted; a throwaway `tmp/` branch is deleted without asking once its work is on a real branch or on `development`, and a `tmp/` branch with unique work is reported, never deleted (decisions log, `docs/tmp-branch-rule`). Since none of these refs was pushed, a "promotion" is: the maintainer agent creates the new branch at the same commit (`git branch <new> <tmp>`), checks `git rev-parse <new>` equals `git rev-parse <tmp>`, moves or removes the worktree, then deletes the `tmp/` name.

## Summary

| Branch | Unique commits | What it holds | Unique value | Third-party or confidential content | Recommendation |
| :-- | --: | :-- | :-- | :-- | :-- |
| `tmp/merge-280d` | 3 | a trial merge of `fix/profiles-cut-overlay-flake` and `fix/drawn-copper-faces` with conflict markers resolved by hand | none: both branches were merged into `development` by their own merges | none | **(a) delete** |
| `tmp/article-1319202` | 1 | a literature note (metadata and abstract, status N) on Muzychka's influence-coefficient paper, ITherm 2004, DOI 10.1109/ITHERM.2004.1319202 | small but unique: a lead and a plan; not on `development` in any form | none (bibliographic data and our paraphrase of the abstract; no text of the paper) | **(b) promote** to `research/muzychka-influence-coefficients`, not merged |
| `tmp/paper-notes-policy` | 1 | the copyright study behind ROADMAP F10: legal and publisher evidence, key classes, a note template, three pilot notes, a similarity checker with tests | real and unique: `development` holds only its conclusions (ROADMAP F10 quotes "the policy study of the copyright question" without a path) | no copied text found; the pilot notes are own-words notes about copyrighted sources and were never reviewed for "own words" | **(b) promote** to `research/paper-notes-policy`; merge only after review |
| `docs/readout-selector` | 1 | `releases/2.8.0/fem-model/READOUT_SELECTOR.md`, the design answer "a view, not a mode" for the surface read-out | historical only: the decision is on `development` (CLAUDE.md 11, `SURFACE_DECISIONS.md` row 1), later superseded in its details | none | **(c) keep as is**, never merge |

## 1. `tmp/merge-280d`: delete

Commits (2026-11-14): `6142968d` Merge fix/profiles-cut-overlay-flake, `5ffb6466` Merge fix/drawn-copper-faces, `dabec363` Resolve merge markers (keep both sides, `CHANGELOG.md` and `docs/validation.md` only). The `--stat` against `development` (39 files, 2100 lines) is misleading: `git` finds several merge bases and counts the content of the merged branches.

Evidence that nothing is lost:
* All parents of the three commits are ancestors of `development`: `ec5f991f`, `2d8aa9e2` (the tip of `fix/profiles-cut-overlay-flake`), `e90bd670` (the tip of `fix/drawn-copper-faces`). `development` merged both branches itself (`c8d718bd` Merge fix/profiles-cut-overlay-flake, `ed6d9c99` Merge fix/drawn-copper-faces) and later closed `research/drawn-copper-faces` (`0fa4beef`).
* Of the 731 files whose content differs between the tip and `development`, only 7 hold a blob that never existed on `development` (`CHANGELOG.md`, `docs/models.md`, `docs/theory.md`, `docs/validation.md`, `docs/versions.md`, `pcbthermal/help/index.html`, `tests/test_help.py`); these are this trial's own resolution of the conflicts, which `development` resolved differently and has since moved past. The rest are older versions of files `development` has updated. `research/transient-reference-boards/` and `tests/test_element_tree_filter.py` are identical on both.

Action: remove the clean worktree `.claude/worktrees/merge-280d` (`git worktree remove`, no `--force`) and delete `tmp/merge-280d`. It cannot pass the check `git rev-list --count development..tmp/merge-280d` = 0 (it gives 3, merge commits of its own), so the deletion rests on the evidence above, not on that count.

## 2. `tmp/article-1319202`: promote to `research/muzychka-influence-coefficients`, no merge yet

Commit `4d5df757` (2026-11-14): `research/article-1319202/README.md` (40 lines) and `INTEGRATION.md` (9 lines). The paper (Y. S. Muzychka, *Influence coefficient method for calculating discrete heat source temperature on finite convectively cooled substrates*, ITherm 2004, pp. 394-402; journal version IEEE Trans. CPT 29 (3) 2006) is **status N**: the note rests on Crossref, OpenAlex and Semantic Scholar metadata and the abstract. It is not on `development`: `research/theory/BIBLIOGRAPHY.md` has `[Muzychka2003]` and `[Muzychka2004Orthotropic]` but no influence-coefficient entry, and the ROADMAP has no line for it.

Value: a plan to read the paper and reproduce one published multi-source case as an independent check of the Lumped superposition of neighbours and of the Analytic edge. Small, but it is work a deletion would lose.

Privacy and licence: bibliographic data, a paraphrase of the abstract and the names of papers held in the local library (no content of them). Nothing third-party is stored; fine for a tracked branch.

Problems for a merge: the folder is named by a document number, not by topic (CLAUDE.md 9.2); there is no study, no figure, no section 'What was read' beyond the note, and the paper itself must first be obtained (IEEE, closed). So: create `research/muzychka-influence-coefficients` at `4d5df757`, verify equality, delete the `tmp/` name, and leave it unmerged. When the maintainer obtains the PDF and opens the investigation, the first commit on that branch renames the folder to `research/muzychka-influence-coefficients/` and adds the ROADMAP line; it is merged only when closed and reviewed. If the maintainer does not want to open it, the alternative that keeps the value is one ROADMAP line (an investigation item pointing at the DOI and the plan of `INTEGRATION.md`) on a `docs/` branch, after which the `tmp/` branch can be deleted.

## 3. `tmp/paper-notes-policy`: promote to `research/paper-notes-policy`, merge after review

Commit `553e6160` (2026-11-14): `README.md` (the answer: own-words notes possible for every non-confidential class, expression never), `INTEGRATION.md` (rules by class, a template, guard changes for `tests/test_third_party_text.py`, who writes and signs, seven decisions for the maintainer), `figures/fig_01_paper_to_note_line.png`, `notes_pilot/` (three notes: Jaffer 2023, Lienhard 2024, Yovanovich and Jafarpur 1993), `scripts/check_note_similarity.py`, `scripts/study_classify_keys.py`, `scripts/make_diagrams.py`, `tests/test_similarity.py`, `.gitignore`.

On `development` in another form: only the conclusions, inside ROADMAP F10 (Thermal Sources Atlas: 'Rules from the copyright policy study: notes in our own words are possible ... no quotation over 25 words ...'). CLAUDE.md 7 does not carry a notes policy, and the evidence (the statutes and publisher terms read, with statuses), the class counts, the template, the checker and its tests exist only on this branch. F10 depends on them and today cites a study no tracked branch holds. The decisions log of the tmp-branch rule already says this branch holds unique work.

Licence and privacy, checked file by file: every script and test carries the licence header; the tests use synthetic text only ("no third-party text is used"); the checker reads `papers/` at run time and stores nothing; `.gitignore` keeps `data/` and `out/` out. The three pilot notes are summaries of copyrighted works in our words with equations as facts and page references, which is what `BIBLIOGRAPHY.md` already does; but by the folder's own README they 'were not reviewed by the reviewer agent', so the "own words" rule they illustrate has not been applied to them. A note that drifted into close paraphrase is the one risk named by the study itself, and published history is never rewritten.

Conditions for a merge into `development` (in order): (1) the reviewer reads each pilot note against the page images and the similarity tool is run against the local text (or the pilot notes are removed and kept local); (2) the README and INTEGRATION lose the 'TEMPORARY, never merged, tmp branch' wording and the layout follows CLAUDE.md 9.6 (`notes_pilot/` is not a standard folder: under `docs/` or dropped); (3) `research/paper-notes-policy/tests` and `tests/test_docs.py` and `tests/test_license_header.py` pass; (4) `research/REVIEW.md`, `research/README.md` and ROADMAP F10 (with the path of the study) are updated in the commit of the review. The decisions of its INTEGRATION 7 (adopt the principle in CLAUDE.md 5 and 7, the pilot of 20 notes, who signs, the quotation limit) remain the maintainer's.

## 4. `docs/readout-selector`: keep as is, do not merge

Commit `ac1b9151` (2026-11-15): `releases/2.8.0/fem-model/READOUT_SELECTOR.md` (109 lines), the answer to 'should a selector choose between the column mean and the surface?': a view selector, never a calculation mode, because `heater_stats` is read inside the solve (top-path split, power-coefficient loop, Power Calculator). The branch is 195 commits behind `development`.

On `development` in another form: the principle is CLAUDE.md 11 ('the surface read-out is a VIEW, never a mode') and `releases/2.8.0/fem-model/SURFACE_DECISIONS.md` row 1, with the same reason. Several details of the note were later reversed by `feature/surface-always-both` (the surface always computed and its Layer entries always listed, not only above 105 um copper; one merged surface column; surface files on request with `--surface-files`), so merging the note now would put a document into `development` that contradicts the shipped behaviour.

It is a `docs/` work branch, so it is never deleted; it stays as the record of the reasoning, unmerged. If the maintainer prefers the record on `development`, the only acceptable form is a one-line pointer in `SURFACE_DECISIONS.md` to the branch and commit, not the file.

Stale text found on `development` while checking (a separate item, not fixed here): `releases/2.8.0/fem-model/DESIGN.md` item 7 still lists '`SolverOptions` `readout`, CLI `--readout`' in the shared vocabulary; neither exists (`pcbthermal/api.py` has only the `readout` label of a table column; `pcbthermal/cli.py` has `--surface-files`). A note under that item pointing to `SURFACE_DECISIONS.md` would close it.

## 5. What was checked and what was not

Checked: the commit lists, the stat, every file of the four unique non-merge commits read (the merge trial through its resolution diff, its parents and a blob search on `development` history), remote presence, worktree states, the corresponding content on `development` (decisions log, ROADMAP F10, `BIBLIOGRAPHY.md`, `SURFACE_DECISIONS.md`, `DESIGN.md`, `api.py`, `cli.py`). Not checked: the pilot notes against the papers (the papers library was not opened, by instruction); the legal statements of the paper-notes study (not re-read; it is research, not legal advice); nothing was run.
