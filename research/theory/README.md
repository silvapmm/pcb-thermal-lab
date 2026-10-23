# Theory: what each model, equation and method is, with pictures and sources

## 1. The question

`docs/theory.md` states every equation the program solves, but as a dense text; the planned work lives in `docs/roadmap.md` and `docs/research.md`; the evidence is spread over a dozen investigations. A reader needs one place that explains **what each method is, what its symbols mean, how the program does it, where it fails, where it is tested and what it is based on**, with a picture of the idea. This folder is that place: one file per topic in `topics/`, one bibliography for all of them, and the pictures drawn here or reached by a path into the investigation that made them. It changes nothing in the program and in the project documents.

## 2. How to read it

| Start with | If you want |
| :-- | :-- |
| the table in section 3 | the list of topics, what each is based on, the code and the document section behind it |
| `topics/NN-*.md` | one topic: picture, formulation, limits, tests, related topics, sources |
| `BIBLIOGRAPHY.md` | the citation of every source, its address, **whether it was read**, and which topics use it |

Every topic file has the same layout: the picture with an italic line saying what it shows; what it is; the formulation (symbols, equations); what it assumes and where it fails; how the program does it (modules and document sections); where it is tested (paths into `docs/validation.md` and the investigations); related topics; sources by key; and a closing line "What was read and what was not verified". Topics for planned work say **Status: planned** at the top, give the idea and the tests that would accept it, and make no claim of results.

## 3. The topics

Code and documents are those of `develop`; "inv." is the investigation that holds the evidence (paths from `research/`).

| # | Topic | Status | Picture | Code | `docs/` | Evidence |
| --: | :-- | :-- | :-- | :-- | :-- | :-- |
| 01 | [Layered idealisation](topics/01-layered-idealisation.md) | in program | fig. 1 | `model.py` | theory 1.2 | inv. `solid3d-verification`, `stackup` |
| 02 | [Finite volumes (FVM)](topics/02-finite-volume.md) | in program | fig. 2 | `fvm.py` | theory 2 | inv. `models-comparison` |
| 03 | [Finite differences (FDM)](topics/03-finite-difference.md) | in program | fig. 3 | `fdm.py` | theory 3 | inv. `models-comparison` |
| 04 | [3D solid](topics/04-solid-3d.md) | in program | fig. 4 | `solid3d.py` | theory 4 | inv. `solid3d-verification` |
| 05 | [Lumped rings (LPTN)](topics/05-lumped-rings.md) | in program | fig. 5 | `lumped.py` | theory 5 | inv. `models-comparison`, `outline` |
| 06 | [Analytic series](topics/06-analytic-series.md) | in program | fig. 6 | `analytic.py` | theory 6 | inv. `models-comparison`, `block-and-fins` |
| 07 | [Time stepping](topics/07-time-stepping.md) | in program | fig. 7 | `fvm.py` | theory 2 | `validation.md` 7 |
| 08 | [Heat transfer coefficients](topics/08-heat-transfer-coefficients.md) | in program | fig. 8 | `convection.py`, `api.py` | theory 8 | `validation.md` |
| 09 | [Parts and the junction](topics/09-parts-junction.md) | in program | fig. 9 | `analysis.py`, `api.py` | theory 9 | inv. `component-heatsink` |
| 10 | [Power profiles](topics/10-power-profiles.md) | in program | fig. 10 | `profiles.py` | theory 10 | `validation.md` 7 |
| 11 | [Metal blocks and fins](topics/11-metal-blocks-fins.md) | in program | fig. 11 | `blocks.py` | theory 7 | inv. `block-and-fins` |
| 12 | [Foster chain](topics/12-foster-chain-planned.md) | **planned** | fig. 12 | - | roadmap 1.11 | - |
| 13 | [Heatsink scenarios](topics/13-heatsink-scenarios-planned.md) | **planned** | fig. 13 | - | roadmap, research R3 R6 | inv. `component-heatsink` |
| 14 | [Virtual JEDEC test, known-power reference](topics/14-virtual-jedec-and-known-power-planned.md) | partly planned | fig. 14 | `inverse.py` | calculators 2.1, 2.4 | inv. `power-calculator` |
| 15 | [Import and power list](topics/15-import-and-power-list-planned.md) | **planned** | fig. 15 | - | roadmap, import | inv. `gerber-import` |
| 16 | [Multigrid](topics/16-multigrid-planned.md) | **planned** (optional) | fig. 16 | - | roadmap, solvers | `models-comparison` solver study |
| 17 | [Copper to cells, the tensor](topics/17-copper-mapping-and-tensor.md) | researched | `gerber-models` figs 22, 23 | research `lib/conduction.py`, `diagonal.py` | roadmap, import | inv. `gerber-models` |
| 18 | [Spreading resistance](topics/18-spreading-resistance.md) | verification | `solid3d-verification` fig. 6 | `solid3d.py` | validation 16 | inv. `solid3d-verification` |
| 19 | [Nets, current, Joule heat](topics/19-nets-current-and-joule-heat.md) | researched | `gerber-nets` figs 8, 6, 5 | research `lib/joule.py`, `pdn.py` | roadmap idea 1 | inv. `gerber-nets` |
| 20 | [Board outline](topics/20-board-outline.md) | rectangle rule in program; reader researched | `outline` fig. 4, `gerber-import` fig. 16 | `model.py` | validation 13 | inv. `outline`, `gerber-import` |
| 21 | [Vias and fills](topics/21-vias-and-fills.md) | in program | `via-fill` fig. 4 | `model.py` | validation 18 | inv. `via-fill` |
| 22 | [Stack-up](topics/22-stack-up.md) | in program | `stackup` fig. 4 | `model.py`, `data/stackups.json` | validation 12, 14 | inv. `stackup` |
| 23 | [Power calculator](topics/23-power-calculator.md) | in program | `power-calculator` fig. 4 | `inverse.py` | calculators | inv. `power-calculator` |

### 3.1 Diagrams and illustrations

The 16 pictures drawn in this folder (figures 1 to 16 in `figures/`, one script, shared shapes in `research/diagram_kit.py`) are embedded in topics 01 to 16. Topics 17 to 23 embed the pictures of the investigations that made them, by relative path, so a picture exists once and is not copied.

| File | Drawn in | Topic |
| :-- | :-- | :-- |
| `figures/fig_01_layered_idealisation.png` | this folder | 01 |
| `figures/fig_02_fvm_cell.png` | this folder | 02 |
| `figures/fig_03_fdm_nodes.png` | this folder | 03 |
| `figures/fig_04_solid3d_slabs.png` | this folder | 04 |
| `figures/fig_05_lumped_rings.png` | this folder | 05 |
| `figures/fig_06_analytic_modes.png` | this folder | 06 |
| `figures/fig_07_theta_method.png` | this folder | 07 |
| `figures/fig_08_heat_transfer.png` | this folder | 08 |
| `figures/fig_09_part_runaway.png` | this folder | 09 |
| `figures/fig_10_profile_decision.png` | this folder | 10 |
| `figures/fig_11_metal_block.png` | this folder | 11 |
| `figures/fig_12_foster_chain_planned.png` | this folder | 12 |
| `figures/fig_13_heatsink_scaling_planned.png` | this folder | 13 |
| `figures/fig_14_virtual_jedec_planned.png` | this folder | 14 |
| `figures/fig_15_import_to_power_planned.png` | this folder | 15 |
| `figures/fig_16_multigrid_planned.png` | this folder | 16 |

Curves that are only illustrative (the shape of a series, a fixed point with arbitrary numbers, a pulse train) say so in their italic line; no number of these pictures is a result. The numbers quoted in the topics come from the project documents and the READMEs of the investigations and are marked with the source.

## 4. Folder layout

| Path | What it is |
| :-- | :-- |
| `README.md` | this index |
| `BIBLIOGRAPHY.md` | every source: key, citation, address, reading status, topics that use it; the list of what to read next |
| `topics/` | the 23 topic files |
| `figures/` | `fig_01` to `fig_16` |
| `scripts/make_diagrams.py` | draws the 16 figures (no data, no program) |
| `docs/theory-figures.md` | where each topic goes in the project documents when it is adopted |
| `tests/test_theory.py` | the checks of this folder: every figure and link exists, every bibliography key used in a topic is defined, every topic has the sections |

```sh
.venv/bin/python research/theory/scripts/make_diagrams.py        # the figures
.venv/bin/python -m pytest -q research/theory/tests              # the checks
```

## 5. Still to write

* Theory sections without a topic file: `docs/theory.md` 1.1 (the continuum problem), 1.3 (sources and geometry: sub-sampled coverage, exact power), 11 (verification summary). The coverage of 1.3 is described in topic 02.
* Items of `docs/research.md` (R2 to R8, E3 to E8: heatsink larger than its contact, chains of many levels, the datasheet conversions) are drawn in `research/component-heatsink/`; they get a topic when they are decided.
* The topics of the planned work (12 to 16) say what would be built; they become formulation and results when the work is done, and their text moves into `docs/theory.md` with the picture.

## 6. Adoption

A topic is adopted when the maintainer decides: its text is folded into `docs/theory.md` (or `docs/roadmap.md` for planned work), its picture copied to `docs/images/`, its sources into the bibliography of the document that uses them. The folder stays as the record. Until then the project documents are not edited from a research branch (`CLAUDE.md`, "Research branches").

## What was read and what was not verified

* **Read in full**: `docs/theory.md` (all sections), the parts of `docs/models.md`, `docs/roadmap.md`, `docs/calculators.md` and `docs/validation.md` named in the topics, and the READMEs and literature notes of the investigations named in topics 17 to 23. The topic files restate them; they add structure, the pictures, the paths and the bibliography, not new results.
* **Not opened in this work**: every textbook and standard of `BIBLIOGRAPHY.md` marked M or N; the statements taken from them are marked "(memory)" or "(from the project documents)" there. Sources marked S were seen as search summaries by the earlier work that cites them.
* **Not verified**: the planned topics (12 to 16) describe intended behaviour; the formulas of topic 12 and 16 are general textbook knowledge written without a source; the pictures are explanations, not tests.
