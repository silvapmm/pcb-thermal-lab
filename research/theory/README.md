# Theory: what each model, equation and method is

This folder explains, one topic per file, every model, equation and planned method of the program: a picture of the idea, the formulation, the limits, how the program does it, where it is tested and the sources with their reading status. It adds no new results and changes nothing in the program. The text of topics 01 to 11, 28 and 29 is already folded into `docs/theory.md`; the folder stays as the longer explanation and the record.

![Map of the theory](figures/fig_38_document_map.png)

*Figure 38 (`figures/fig_38_document_map.png`): the map of the theory: the board is idealised in layers for the FVM, FDM, Lumped and Analytic models, the 3D solid builds real slabs from the same board, and underneath are the pieces the models share. Schematic, no numbers.*

## How to read it

Pick a topic in the table and open its file in `topics/`. Every topic file has the same order: picture, what it is, formulation, assumptions and limits, how the program does it, where it is tested, related topics, sources, and a closing line on what was read. Planned topics say **Status: planned** at the top and claim no results. Sources are cited by key; [`BIBLIOGRAPHY.md`](BIBLIOGRAPHY.md) gives each one with its address and whether it was read (R), seen as a summary (S), known from memory (M) or not obtained (N).

## The topics

Code is the module in `pcbthermal/`; the research folder holds the evidence.

| # | Topic | Status | Code | Research folder |
| --: | :-- | :-- | :-- | :-- |
| 01 | [Layered idealisation](topics/01-layered-idealisation.md) | in program | `model.py`, `laminate.py` | [stackup](../stackup/README.md), [solid3d-verification](../solid3d-verification/README.md), [effective-conductivity](../effective-conductivity/README.md) |
| 02 | [Finite volumes (FVM)](topics/02-finite-volume.md) | in program | `fvm.py` | [models-comparison](../models-comparison/README.md) |
| 03 | [Finite differences (FDM)](topics/03-finite-difference.md) | in program | `fdm.py` | [models-comparison](../models-comparison/README.md) |
| 04 | [3D solid](topics/04-solid-3d.md) | in program | `solid3d.py` | [solid3d-verification](../solid3d-verification/README.md) |
| 05 | [Lumped rings (LPTN)](topics/05-lumped-rings.md) | in program | `lumped.py` | [models-comparison](../models-comparison/README.md), [outline](../outline/README.md) |
| 06 | [Analytic series](topics/06-analytic-series.md) | in program | `analytic.py` | [models-comparison](../models-comparison/README.md), [block-and-fins](../block-and-fins/README.md) |
| 07 | [Time stepping](topics/07-time-stepping.md) | in program | `fvm.py` | - |
| 08 | [Heat transfer coefficients](topics/08-heat-transfer-coefficients.md) | in program | `convection.py`, `api.py` | [effective-conductivity](../effective-conductivity/README.md) |
| 09 | [Parts and the junction](topics/09-parts-junction.md) | in program | `analysis.py`, `api.py` | [component-heatsink](../component-heatsink/README.md) |
| 10 | [Power profiles](topics/10-power-profiles.md) | in program | `profiles.py` | - |
| 11 | [Metal blocks and fins](topics/11-metal-blocks-fins.md) | in program | `blocks.py` | [block-and-fins](../block-and-fins/README.md), [fin-channel](../fin-channel/README.md) |
| 12 | [Foster chain](topics/12-foster-chain-planned.md) | **planned** | - | - |
| 13 | [Heatsink scenarios](topics/13-heatsink-scenarios-planned.md) | **planned** | - | [component-heatsink](../component-heatsink/README.md) |
| 14 | [Virtual JEDEC test, known-power reference](topics/14-virtual-jedec-and-known-power-planned.md) | partly planned | `inverse.py` | [power-calculator](../power-calculator/README.md) |
| 15 | [Import and power list](topics/15-import-and-power-list-planned.md) | **planned** | - | [gerber-import](../gerber-import/README.md) |
| 16 | [Multigrid](topics/16-multigrid-planned.md) | **planned** (optional) | - | [models-comparison](../models-comparison/README.md) |
| 17 | [Copper to cells, the tensor](topics/17-copper-mapping-and-tensor.md) | researched | - | [gerber-models](../gerber-models/README.md) |
| 18 | [Spreading resistance](topics/18-spreading-resistance.md) | verification | `solid3d.py` | [solid3d-verification](../solid3d-verification/README.md) |
| 19 | [Nets, current, Joule heat](topics/19-nets-current-and-joule-heat.md) | researched | - | [gerber-nets](../gerber-nets/README.md) |
| 20 | [Board outline](topics/20-board-outline.md) | in program; Gerber reader researched | `model.py`, `geometry.py` | [outline](../outline/README.md), [gerber-import](../gerber-import/README.md) |
| 21 | [Vias and fills](topics/21-vias-and-fills.md) | in program | `model.py` | [via-fill](../via-fill/README.md) |
| 22 | [Stack-up](topics/22-stack-up.md) | in program | `model.py`, `data/stackups.json` | [stackup](../stackup/README.md) |
| 23 | [Power calculator](topics/23-power-calculator.md) | in program | `inverse.py` | [power-calculator](../power-calculator/README.md) |
| 24 | [Thermal interfaces and metals](topics/24-thermal-interfaces-and-metals.md) | in program | `model.py` | [component-heatsink](../component-heatsink/README.md) |
| 25 | [Contact area, air gap, chain of levels](topics/25-contact-area-gap-and-chain.md) | contact area in program; gap and chain researched | `blocks.py` | [component-heatsink](../component-heatsink/README.md) |
| 26 | [Plate spreading on a component](topics/26-plate-spreading-on-a-component.md) | decided (K/W only) | - | [component-heatsink](../component-heatsink/README.md) |
| 27 | [Datasheet numbers and compact models](topics/27-datasheet-numbers-and-compact-models.md) | `theta` and top path in program; junction node not | `analysis.py` | [component-heatsink](../component-heatsink/README.md) |
| 28 | [Continuum problem and sources](topics/28-continuum-and-sources.md) | in program | `model.py`, `geometry.py` | [rotated-square-3d](../rotated-square-3d/README.md) |
| 29 | [Verification ladder](topics/29-verification-ladder.md) | in program | `tests/` | [models-comparison](../models-comparison/README.md), [solid3d-verification](../solid3d-verification/README.md) |
| 30 | [Board orientation](topics/30-board-orientation.md) | in program | `convection.py` | [horizontal-plate-h](../horizontal-plate-h/README.md) |
| 31 | [Program architecture and API](topics/31-program-architecture-and-api.md) | in program | `api.py`, `cli.py`, `jobs.py` | - |
| 32 | [The removed program against the current one](topics/32-legacy-program-against-current.md) | history | tag `legacy-wxpython-1.0.0` | [models-comparison](../models-comparison/README.md) |
| 33 | [Time-dependent results](topics/33-time-dependent-results.md) | in program | `fvm.py`, `profiles.py` | - |
| 34 | [Input checks](topics/34-input-checks.md) | in program | `checks.py` | [effective-conductivity](../effective-conductivity/README.md) |
| 35 | [Curved boards](topics/35-curved-boards.md) | in program | `geometry.py` | - |
| 36 | [Prepreg and sheets in a gap](topics/36-prepreg-and-sheets-in-a-gap.md) | in program | `model.py` | [stackup](../stackup/README.md) |
| 37 | [Why the FVM and the Analytic model agree](topics/37-why-fvm-and-analytic-agree.md) | explanation | - | [models-comparison](../models-comparison/README.md) |

## Figures and scripts

The pictures are in `figures/` (`fig_01` to `fig_44`; 40 and 43 unused), each embedded with its caption in the topic it explains; [`docs/theory-figures.md`](docs/theory-figures.md) says where each one goes in the project documents. Topics 17 to 24 and 27 link the pictures of their investigations instead of copying them. `scripts/make_diagrams.py` draws the diagrams, `scripts/make_figures.py` the data figures (about 3 minutes) and `scripts/make_fig_part_outline.py` figures 34 to 37 (about 6 minutes); the other scripts are numerical checks named in the topics. Illustrative curves say so in their caption; they are not results.

```sh
.venv/bin/python research/theory/scripts/make_diagrams.py
.venv/bin/python -m pytest -q research/theory/tests              # links, figures, bibliography keys, topic sections
```

## Adoption

A topic is adopted when the maintainer decides: its text goes into `docs/theory.md` (or `docs/versions.md` "Planned" for planned work), its picture into `docs/images/`, its sources into the bibliography of that document. Corrections for the project documents found here are in [`docs/for-the-project-documents.md`](docs/for-the-project-documents.md); `docs/` also holds the plan of the `docs/theory.md` rewrite, the maintainer's reference compilation and the list of sources to obtain.

## What was read and what was not verified

* **Read in full**: `docs/theory.md`, the sections of `docs/models.md`, `docs/versions.md` "Planned", `docs/calculators.md` and `docs/validation.md` named in the topics, and the READMEs of the investigations they cite. The topics restate them; the numbers in a topic come from those documents and are marked with their source.
* **Sources**: the reading status of each is in `BIBLIOGRAPHY.md`; statements from sources marked M or N are marked "(memory)" there. The Python `ht` package (1.2.0) was read: its documentation and its code differ in the Hollands formula. The maintainer's compilation (`docs/reference-compilation.md`) is second-hand; only its numbers were checked.
* **Checked numerically here**: the Bruggeman and Hashin-Shtrikman properties (`scripts/check_mapping_formulas.py`), the correlations (`scripts/check_correlations.py`), the area loss of a polygon corner (topic 35), the coverage sum against the polygon area (topic 28) and the explanation of topic 37 (`scripts/study_fvm_analytic_edges.py`: the first explanation was wrong).
* **Not verified**: the residual -0.1 to -0.3 % of the Analytic with insulated edges; the multigrid timings (quoted from `docs/versions.md`, printed by no script); the formulas of the planned topics 12 and 16 (textbook knowledge, no source opened).

## Review

* **Status**: topics reviewed against `develop` `3e90a7f` and the READMEs of the investigations they cite; the figures were read one by one. Status in [`../REVIEW.md`](../REVIEW.md).
* **Independent checks**: the Lumped factors `f_R` and `f_P` re-derived from the disc solution (topic 05); the top-path closure and its root (topic 09); the fixed point of the power coefficient (figure 9); the theta-method factor and the explicit-Euler limit (figure 7); the laminate construction (topic 01); the explanation of topic 37 (the 0.3 to 1.0 % between the Analytic and the FVM is the edge loss the cosine series leaves out, not mesh error).
* **Limits**: the numbers of the Gerber topics (15, 17, 19, 20) are those of their folders, reviewed there; the pictures explain, they are not tests.
* **Program defects**: none open. The one found here (`Heater.top_resistance()` with `theta` against `junction_theta()` in `analysis.part_split`) is closed: since 2.4.3 the top path exists only on a component (`Heater.has_top_path()`), where the two are the same value (`tests/test_top_path_role.py`).
