# Log: via fill

- Question from the maintainer: what do fabricators mean by a "filled" via. Fabricator pages read (JLCPCB, ALLPCB; see the README, section 6); the IPC-4761 standard itself was **not** read, its types come from those pages. Study written and run; the program got the four fills.
- Folder created: the script moved from `examples/` to `research/via-fill/`; figures added (`make_figures.py`). The numbers in the README are those printed by `study_via_fill.py` and match `docs/validation.md` section 18.

Not verified: the quoted conductivities of the fills (fabricator pages only); nothing measured on a physical board.
- Schematic diagram added (`scripts/make_diagrams.py`, figure 4): drawn, not computed; the numbers it quotes are those of this README.
- A second picture added to `scripts/make_diagrams.py` (figure 5): a drawing of the real situation (a section or a top view), not a block diagram; every number in it is quoted from this README.
