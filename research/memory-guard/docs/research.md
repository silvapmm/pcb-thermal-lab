# Text for `docs/research.md` (when the work is adopted)

## Memory limit and guard

**Question.** How much memory does a solve of each model take as the unknowns grow, and can the program refuse, before it allocates, a run that the machine cannot hold?

**State.** A prototype estimator, a measurement ladder and a design are in `research/memory-guard/`; the ladder was run (145 measured points on a 16 GB Mac). Measured: the peak follows the nodes per plan cell t = unknowns / cells; exponent 1.08 to 1.10 for t up to 4.5 and 1.36 above, 1.41 for the FDM with laminate nodes, 1.23 to 1.28 for the 3D solid; 2.4 to 18.6 KB per unknown at 500 000 unknowns; a six-layer plain board takes 8.8 GB per million unknowns, a two-layer board 2.9 to 4.5; the block SOR takes up to 75 n^2 bytes; the review replaced the classes by one law per model in t_eff = min(t, cells / t) after four of six boards of 8 and 12 copper layers came out above the class estimate (README 14.2), and measured the animation transient at 3.5 times the steady peak (ten factors kept); the cell-major numbering gives the same answer to 1.2e-12 K and a conditional gain.

**Open.** The laws on a second machine; the power-profile and FDM transient factors; the Analytic's dependence on the via tiles (0.5 GB at 640 000 unknowns, so not limiting); the 3D solid above 400 000 unknowns (extrapolated); the stripes cell-major point at 0.25 mm on a quiet machine; the reviewer's cell-major board; Windows and container detection of the physical memory; installed against available memory (the 70 % of 16 GB equals the usable memory at rest).
