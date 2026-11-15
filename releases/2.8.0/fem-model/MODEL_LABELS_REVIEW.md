# Model labels: the word "comparison"

Review of the maintainer's question: *does it make sense to have the word "comparison" in the names of the models? If they are models, they are models, full stop.* Tree: `development` at `6c225276`. Nothing in the program was changed; the before/after pictures were rendered offscreen from a throwaway branch (labels patched at run time, not in the source).

## 1. Verdict

**Replace.** Drop the suffix ", comparison" from the three checkboxes, keep ", reference" on the FVM, and show the grouping with a **thin separator line** between the three main models and the other three (option L3 below). The role (off by default, cross-checks the main models) moves to the first sentence of each tooltip, the user guide and `docs/models.md`.

New labels of the Models box, top to bottom:

| Key | Today | New |
| :-- | :-- | :-- |
| `fvm` | Finite volume (FVM), reference | Finite volume (FVM), reference (unchanged) |
| `lumped` | Thermal network (LPTN) | Thermal network (LPTN) (unchanged) |
| `analytic` | Analytical (Fourier series) | Analytical (Fourier series) (unchanged) |
| (separator) | none | thin horizontal line, `muted` theme tone |
| `fdm` | Finite difference (FDM), comparison | Finite difference (FDM) |
| `solid3d` | 3D solid (finite volumes), comparison | 3D solid (finite volumes) |
| `fem` | Finite elements (FEM), comparison | Finite elements (FEM) |

## 2. What the word means today, and whether it is accurate

- In the code, `api.COMPARISON_MODELS = ("fdm", "solid3d", "fem")` (`pcbthermal/api.py:43`): models outside the three main ones, off by default, used to cross-check them. `--model compare` runs all six (`cli.py:57`, `100`, `362`).
- The reference of the table ("Error vs FVM") is the FVM when it runs (`Simulation.reference`, `api.py:238`); otherwise it is the **first result**, so a run with the FEM alone uses the FEM as its own reference, and the coefficients of later stages are taken from the first ticked model of `MODEL_NAMES + COMPARISON_MODELS` (`api.py:1188`). The comment "never the reference of the decisions" (`api.py:43`) is therefore true only when a main model is also ticked.
- Accuracy of the label: the word describes a **role**, not the **kind** of the model. The FDM is a full layered model (steady, animation, profiles), the 3D solid and the FEM are full 3D models; each can be run alone and gives a complete answer. The suffix suggests they are partial or auxiliary, which they are not; and on the FEM it reads as a lesser model while it is the most detailed one (resolved surface of thick copper). The suffix ", reference" on the FVM is different: it names a function the program really gives it (the column "Error vs FVM", the coefficients of the time stages), so it stays.
- The same word is used elsewhere with another meaning (SOR "for comparison", the copper mappings "Lambda" and "Fill" of the import window "comparison"): those are options kept to show a known error, not models; they are out of scope and stay.

## 3. Options rendered (Models box, real dock width 322 px, light and dark)

Contact sheet `model_labels.png` (scratchpad of the review session, not committed): rows L1 to L4, columns light and dark.

| Option | Description | Assessment |
| :-- | :-- | :-- |
| L1 | Today: ", comparison" on FDM, 3D solid, FEM | Longest label 37 characters; reads as "lesser models"; the maintainer's objection holds |
| L2 | Suffix dropped, no other mark | Cleanest; but the six look equal and nothing says why three are off by default until the tooltip |
| **L3** | Suffix dropped + thin separator after the Analytic | **Recommended.** Keeps the grouping (main / others) without a word that judges the model; one widget; no new text to translate or test; same in both themes |
| L4 | Suffix dropped + small headings "Main models" / "More models (off by default)" | Explicit, but two more lines in a crowded dock and the heading reintroduces a classification in words; acceptable second choice |

A short tag at the right (for example a grey "3D") was considered and not rendered: at 322 px it competes with the label text and repeats what the name already says.

## 4. Inventory: where the word is attached to a model

"Change" = what the recommendation does. Records of past versions (`docs/version-comparison.md` 2629, 2770; older entries of `docs/versions.md` and `docs/decisions-log.md`) quote the label as it was then and stay as they are.

| File:line | Text today | Change |
| :-- | :-- | :-- |
| `pcbthermal/gui/panels.py:1561-1563` | `Finite difference (FDM), comparison`, `3D solid (finite volumes), comparison`, `Finite elements (FEM), comparison` | Labels as in section 1; insert a `QFrame.HLine` after the Analytic checkbox (theme tone `muted`) |
| `pcbthermal/gui/panels.py:1568-1571` | tooltips of `solid3d`, `fdm` ("for comparison"), `fem` | First sentence: "Off by default; a cross-check of the three models above." then the present text (FDM: drop "for comparison") |
| `pcbthermal/gui/panels.py:1599`, `1623`; `gui/tips.py:65` | SOR "for comparison" | none (a solver option, not a model) |
| `pcbthermal/gui/fieldscale.py:167` `MODEL_SHORT`; `results.py:14` `MODEL_LABELS`; `memory.py:83`; `panels.py:1744` | FVM, FDM, 3D solid, FEM (no suffix) | none: the results cards, combos, tables and the memory line already carry no suffix |
| `pcbthermal/gui/results_view.py:587` | tab "Models" (`kind="compare"`) | none (the tab compares the models; the word is correct there) |
| Preferences | no model label | none |
| `pcbthermal/cli.py:38`, `362-363` | `--model compare`; help "those three plus the comparison models fdm, solid3d and fem" | keep the choice `compare` (a verb: compare the six; changing it breaks scripts); help text: "those three plus fdm, solid3d and fem" |
| `pcbthermal/api.py:43`, `128-157` | `COMPARISON_MODELS`; project keys `comparison_models`, `comparison_only` | keep (section 5); correct the comment of line 43 ("never the reference" is untrue when it runs alone) |
| `pcbthermal/gui/help.py:149` (About) | "the finite-element comparison model uses it" | "the finite-element model uses it" |
| `pcbthermal/help/index.html:251` (twice) | heading and tick text `Finite elements (FEM), comparison` | `Finite elements (FEM)`; the paragraph keeps "a sixth model, off by default" and says what it cross-checks |
| `pcbthermal/help/index.html:298` | "FEM (comparison model, steady state, off by default)" | "FEM (steady state, off by default)" |
| `pcbthermal/help/index.html` (Models box text, if the guide lists the six) | | add one sentence: "the line separates the three main models from three slower models that are off by default and cross-check them" |
| `README.md:11`, `91`, `194` | "as a comparison, finite elements"; "(finite elements, comparison, `--model fem`)"; "finite-element comparison model" | drop "comparison" (say "off by default" where it matters) |
| `docs/models.md:152`, `157`, `565` | "a comparison model like the FDM and the 3D solid"; checkbox `Finite elements (FEM), comparison` | new label; the role sentence once, in the section that lists the six models: "the FDM, the 3D solid and the FEM are off by default and cross-check the main three" |
| `docs/theory.md:562`, `608`, `614`, `666` | "a comparison model", heading "Finite elements (comparison model, key `fem` ...)" | heading "Finite elements (key `fem` ...)"; prose may keep "cross-checks the FVM" (a statement of role, true) |
| `docs/validation.md:64`, `2386` | "the program's own comparison model" (3D solid) | none needed (a statement of role in a validation text); optional rewording |
| `docs/versions.md:23`, `410` (2.8.0, unreleased) | checkbox `Finite elements (FEM), comparison` | new label |
| `CLAUDE.md:10`, `149`, `202` | "plus comparison models", "a comparison model like the FDM and the 3D solid (checkbox `Finite elements (FEM), comparison`, off by default)", "saved under `comparison_models`" | new checkbox label; "plus three models off by default"; keep the key name |
| `tests/test_fem_gui.py:63` | `assert box.text() == "Finite elements (FEM), comparison"` | new label |
| `tests/test_help.py:33` | word `"Finite elements (FEM), comparison"` | `"Finite elements (FEM)"` |
| `tests/test_tooltips.py`, `tests/test_model_lists.py` | no label text checked (grep) | none; a separator `QFrame` needs no tooltip (not a control) |

## 5. The project-file key `comparison_models`

Keep it. It exists because the reader of v2.7.1 refuses unknown names in `solver.models`, so the FEM is saved in a key older readers drop (`api.py:128-157`, `comparison_only` when it is the only model). The key is internal (never shown), it matches the code's constant `COMPARISON_MODELS`, and the behaviour is pinned by `tests/test_fem_gui.py` (save/open) and the format tests. Renaming is still possible because 2.8.0 is not released, but it buys nothing for the user and touches the reader, the writer, the schema checks and the tests. If renamed, the neutral name would be `extra_models` (with `extra_only`); this review does not recommend it.

## 6. What the change touches, and the effort

- Code: `panels.py` (three labels, three tooltip sentences, one separator), `cli.py` help string, `help.py` About sentence, one comment in `api.py`. No model, no number, no file format changes: no pending file, frozen numbers unaffected.
- Tests: `tests/test_fem_gui.py:63`, `tests/test_help.py:33`; optionally a check that the separator sits after the Analytic. GUI stress test unaffected.
- Documents: user guide (3 places), README (3), About, `docs/models.md`, `docs/theory.md` (heading and 3 sentences), `docs/versions.md` (2.8.0 entry), `CLAUDE.md` (sections 1 and 11), `CHANGELOG.md` (Unreleased), a Decisions Log entry.
- Screenshots: `docs/images/simulation_fem.png` and its copy `pcbthermal/help/simulation_fem.png` (`examples/make_screenshots.py --fem`); the window shots that show the Models box (`editor.png`, `editor_imported*.png`, `editor_warnings*.png`; `editor.png` is already stale: it shows five models, no FEM) at the next full screenshot run.
- Effort: about one hour of work on a `fix/` branch (or folded into the FEM interface work), plus the whole battery before the merge.

## 7. Open decision for the maintainer

1. L3 (separator, recommended) or L4 (headings) or L2 (no mark).
2. Keep the key `comparison_models` (recommended) or rename it before 2.8.0 is released.
