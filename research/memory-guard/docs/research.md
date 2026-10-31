# Text for `docs/research.md` (when the work is adopted)

## Memory limit and guard

**Question.** How much memory does a solve of each model take as the unknowns grow, and can the program refuse, before it allocates, a run that the machine cannot hold?

**State.** A prototype estimator, a measurement ladder and a design are in `research/memory-guard/`; the ladder is not yet run. Known from earlier measurements: layered FVM on a plain board is linear in the unknowns (2.7 KB each); the laminate-rule boards take 7 to 11 KB each at 0.25 mm; the 3D solid takes 6.6 KB (plain board) to 14 to 19 KB (example board) each and grows faster than linearly.

**Open.** The fitted coefficients and their margin; the laws of the Analytic (quadratic in the tiles with vias), the Lumped and the transient; the cell-major numbering as a program change; Windows and container detection of the physical memory; installed against free memory.
