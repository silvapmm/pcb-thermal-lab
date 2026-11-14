# Integration of the finite-element extensions

**What enters the program: nothing.** `git diff development --stat -- pcbthermal tests examples ico` stays empty; new code lives in `lib/` of this folder
(additions that import `independent-fem-edge/lib`, never edit it) and its `scripts/`.

## Recommendation
1. Build the tool additions in this order: hollow-barrel case (no tool change), block, solder and plate slabs (`lib/stack_ext.py`), mask sampling, L case, then the
   capacity matrix and Crank-Nicolson (`lib/transient.py`) with its own small tests (exact RC, 1D slab, energy balance, `dt` halving) before any program comparison.
2. Run what fits under 2 GB (README 3), queue the rest behind the machine lock; every case with a mesh-halving check and the energy balance.
3. The reviewer compares each program column on the same board (conductivity, films, edge losses, anisotropy), then updates the README, `research/REVIEW.md`
   and `research/ROADMAP.md` (A43). Results that find the program wrong become proposals here, never edits.
4. This planning pass enables: the via cluster under a tab block, the Lumped dense via group reference, E13, 5a, A30 and B5 (`docs/versions.md`), and the transient reference.

## Risks
* Memory: levels finer than 0.1 mm for the cluster are 1.4 to 5.8 million unknowns (estimates) and need the quiet machine.
* The program's representation of a tab and a solder layer may not exist as an input; study 2 first states the mapping.
* The brief's Crank-Nicolson is the program's own, not the tool's: the transient costs a new integrator, not a small addition.
