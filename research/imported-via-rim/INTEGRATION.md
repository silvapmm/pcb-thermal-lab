# Integration: rim test of the vias from the imported masks (proposal, not implemented)

1. `pcbthermal/viawell.py` `rim_copper_shares`: for an imported layer with a mask use the ray test (`research/imported-via-rim/lib/rimmask.py`, reach 0.5 mm, threshold 0.5, 48 rays, one-pixel steps);
   a drawn layer keeps its rule; heaters count as contact. Not the drill circle alone: it reads 1.0 on every via of the six library boards (the pad is on every layer).
2. Effect: FVM parts 0 to 4.4 % hotter on five real boards at 1 and 0.5 mm; at most 1.2 % on the synthetic boards (reference agreement kept or moved to the safe side). Frozen numbers: none move (no imported board in the harness).
3. Moves the numbers of every imported board with vias: a `fix/` branch with `docs/validation.md`, `docs/theory.md` 2.6 (the sentence that imported copper counts as full contact), tests from `tests/test_rimmask.py`, and the whole battery.
4. Decisions for the maintainer: the reach (a rule from drill and pad radius is better than the fixed 0.5 mm); whether to ship the warning of README 6 meanwhile. Risk: a via reached by a single track on an outer layer reads a small share.
