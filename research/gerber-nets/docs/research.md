# Research summary, phase 3: nets with voltage and current

Ready to paste into the project `docs/research.md` as a section when the maintainer adopts the work. Everything is reproducible from `research/gerber-nets/` (README sections, `CONCLUSIONS.md`); nothing in `pcbthermal/` was changed.

## Open now: nets with voltage and current

**Answers** (numbers in the README of the folder):

* **Nets and Joule heat** (4.20): the current of a net between two terminals gives the heat per cell, exactly I²R (`lib/joule.py`).
* **Tracks at any angle** (4.23): area exact except at 45 degrees on the lattice; the five-point stencil is too resistive on a thin tilted track.
* **Separate pieces of one net** (4.36): joined outside the copper by parts; the current per pad is an input, the voltage carries no current; a piece with no source or load has no heat.
* **Sources, sinks and links** (4.40, `lib/pdn.py`): a 0.1 ohm link makes 225 mW at 1.5 A against 12 mW for all the copper of the rail; the energy balance closes to 0.0004 mW in 7.5 W; checked against closed forms (strip, L bend, ring sector), an exact series network and a current split (README 4.41). Design: `Problem.electrical`, `vsource`, `isink`, `link`; the heat added to the thermal grid.

**Not validated**: a measurement; vias between layers, the return current in the ground net, regulators and ratings are not in the prototype; rho(T) is checked only on a lumped track; the heat was not added to a thermal run.

**Open decisions for the maintainer**: the form of the electrical inputs (left open by the maintainer); whether it enters the program before phases 1 and 2.

Pictures (`../figures/`): `fig_01_angles_pixel_grid.png`, `fig_02_nets_and_joule.png`, `fig_03_ic_board_nets_and_joule.png`, `fig_04_pdn_links.png`, `fig_05_network_diagram.png` and the diagrams `fig_06` to `fig_09`.
