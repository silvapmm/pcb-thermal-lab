# Phase 3: sources, sinks and links in the application (design, prototype in `lib/pdn.py`)

*Phase 3 of three of the Gerber research (`research/gerber-import`, `research/gerber-models`, `research/gerber-nets`); the section numbers of the README (4.x) are those of the original single study.*

Questions from the maintainer: *how could the sinks and resistances be implemented in the application, and has anyone done it?* What the research found is in README 4.36 and 4.40; this document is the design.

* **What is added**: `Problem.electrical` with named terminals (position and size of a pad, net) and the elements `vsource` (volts), `isink` (amps) and `link` (ohms between two terminals); the part (`Heater`) may carry a `current` and a `net`. Absent = nothing changes, bit for bit.
* **Where it plugs in**: after the copper mask exists (the same pixels that give the face conductances), `pdn.solve` gives the potential, the Joule heat per pixel and the power of every link; `joule.to_cells` adds it to the source term of the thermal grid; the existing fixed-point loop of `api._solve_with_tc` adds the resistivity of copper rising 0.39 %/K. The thermal models do not change: the heat enters as one more source.
* **Why the links matter**: in the prototype scenario a 0.1 ohm link carries 18 times the heat of all the copper of a 1.5 A rail; pieces of one net that are not joined by copper are normally joined by such a part, so the part list (value of the 0 ohm, ferrite, shunt or fuse) is what the electrical side needs from the design.
* **Inputs, to be decided later** (maintainer): the electrical data may be passed as an extra argument of the import (a sidecar file next to the project, or a KiCad netlist plus part fields) or typed in a pads table; the research leaves the form open.
* **Open**: vias in the network; the return current in the ground net (the prototype grounds the sinks ideally, while the same current heats the ground copper); regulators (load as constant power); time dependence; ratings (IPC-2152).
* **Nothing of this exists in the program**: `Problem.electrical` is a design; `docs/versions.md` "Planned" lists the electro-thermal coupling as future work.
* **The loop with the temperature** (review, README 4.41): with a constant current the Joule heat of a track at one temperature is `P = I² R20 (1 + α (T − 20))`, the form of the power coefficient of `api._solve_with_tc`, and the plain fixed point converges whenever a solution exists (ratio `α Rth I² R20` < 1; runaway at 1). Three things to change when it is used: the program refers `tc` to 25 °C (use `α / (1 + 5 α)` = 0.386 %/K or a 20 °C reference), it evaluates the power at the hottest point under the part (an upper bound for a track: use the resistance of the solved field, `rho(T)` per pixel), and it gives up after 80 iterations (the lumped loop needs 124 at a ratio of 0.8).
* **The cells**: `joule.to_cells` sums from the first pixel and keeps the rows of the mask (from the top); the pixel lattice must be anchored on the program's cells and the rows flipped to the program's y upwards.

The network is drawn in Figure 5 of `README.md` (`figures/fig_05_network_diagram.png`): pieces and link, equivalent circuit, resistor mesh and energy balance.

## Order of work (proposal)

1. The Joule heat of a net with given terminals on one layer (`joule.solve_net`, README 4.20), added to the source term of the thermal grid (`joule.to_cells`).
2. Pieces joined by links, sources and sinks (`pdn.solve`): the pads table or a netlist as the source of the currents.
3. Vias between layers in the network; regulators (a load that depends on its input voltage); the loop with the resistivity of copper.
4. Ratings (IPC-2152) and the report.

Each step has its own validation (a hand count on strips and series, the energy balance, then a measurement if one becomes available) and the documentation rules of `CLAUDE.md`.
