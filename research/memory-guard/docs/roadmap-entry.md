# Text for `docs/versions.md` (chapter 'Planned') and `research/ROADMAP.md`

**Planned (program), item 1 'Memory limit and guard'**, evidence: `research/memory-guard/` (README 4 to 10, INTEGRATION.md). Keep the item as written; add that the coefficients come from the ladder `study_memory_ladder.py`, that the SOR block guard and the cell-major numbering are part of it (the latter conditional on the ladder), and that the count of unknowns shown in the panel is the one of `fvm.unknowns`.

**Research roadmap**: run the ladder on a quiet machine after the 2.4.5 release; repeat it on a second machine (other RAM, other operating system) to see whether the coefficients move; measure the Analytic tile law, the Lumped and the transient; test the cell-major numbering on the FDM and the 3D solid; decide installed or available memory.
