# 19. Nets, current and Joule heat: the electrical side

![Track in squares](../../gerber-nets/figures/fig_08_track_in_squares.png)

*Figure 8 of `research/gerber-nets` (`research/gerber-nets/figures/fig_08_track_in_squares.png`): a track as a row of squares of sheet resistance, the section with the heat leaving through the board and the air, and what the electrical side must be given (current, terminals, links).*

More pictures: `research/gerber-nets/figures/fig_06_joule_chain_schematic.png` (from the mask of a net to its heat in the cells), `fig_07_electro_thermal_loop_schematic.png` (the electro-thermal loop, a proposal), `fig_05_network_diagram.png` (pieces of one net, the equivalent circuit, the resistor mesh, the energy balance), `fig_09_where_the_power_goes.png`, `fig_04_pdn_links.png`, `fig_02_nets_and_joule.png`. Nets from the files: `research/gerber-import/figures/fig_17_nets_from_files.png`. Investigation: `research/gerber-nets/README.md` (4.20, 4.23, 4.30, 4.36, 4.40). **Status: researched and prototyped on the research branch; not in the program.**

## 1. What it is

A copper track that carries a current is itself a heater: `P = I^2 R`. The **heat of a net** comes from solving the current in the copper of that net and summing the dissipated power into the cells of the thermal grid. The same solve gives the voltage drop and the hot spots (current crowding at a neck).

## 2. Formulation

* **Sheet resistance**: `R_s = rho / t` (copper 1.68e-8 ohm m at 20 C, +0.393 %/K): 0.48 mohm per square for 35 um copper. A track is `R = R_s * squares` (a 0.2 mm x 20 mm track is 100 squares, 48 mohm).
* **Laplace problem** on the pixels of the net mask (4-connected, face conductance `1 / R_s`, harmonic mean when `R_s` varies): `div(grad V / R_s) = 0`, with terminals as named sets of pixels (the copper under a pad). The Joule power of each pixel sums exactly to `I^2 R`; `joule.to_cells` conserves the total when it sums into cells.
* **Sources, sinks and links**: a supply pin is a voltage source, a load is a current sink, a bead or a shunt is a `link` resistance between two terminals; a piece of copper with no source or load floats and carries no current and no heat, whatever its voltage. Currents per pad are **inputs** (a power budget, a datasheet, a netlist): the copper cannot infer them. Energy balance: source = copper + links + loads.
* **Coupling with temperature**: `rho(T)` makes the heat depend on the temperature; a fixed-point loop between the electrical and the thermal solve, like the one the program already has for the power coefficient (topic 09).

## 3. Where the nets come from

The Gerber X2 attribute `TO.N` names the net of an object (`TD` ends it); the reader keeps the net of every operation. Limits found: pads and tracks carry a net, zone fills may not; one net is often several separate pieces on a layer (12 for `Board_0-/X9` on the top layer of the four-layer `charliewatch-v2` board), most likely joined by vias and the inner layers (an earlier text said the net names of a panel repeat on every board; the review of `gerber-nets`, its README section 7, found one board, not a panel). Working rule: the net of a piece of **connected copper** is the net of the labelled objects it contains (149 of 176 pieces on the top layer have exactly one net, none has two). Plated holes join the pieces of two layers (109 of 109 join, 0 of 66 groups hold two nets). Checked against a KiCad project pixel by pixel: 99.998 % of 2.25 million pixels lie on Gerber copper. (Sources: `research/gerber-import/README.md` 4.29, 4.33 and 4.46, where the reading of the nets now lives.)

## 4. Numbers of the prototype

A synthetic board: 1 A through a track of 70 squares gives 32 mohm and 32 mW (32.27 to 32.34 mohm for pixels of 0.05 to 0.0125 mm on a lattice with no edge on a pixel centre; by hand 34 mohm). In the scenario of figure 9 of `gerber-nets` (5 V source, a 0.1 ohm link, a 1.5 A sink), 225 mW is dissipated in the link, 18 times the 12 mW of all the copper of the rail; the balance closes to 0.0004 mW in 7.5 W. A tilted track on the pixel grid: the five-point stencil is up to 2 times too resistive on a track of 1.5 to 2 pixels across, 6 % at 12 pixels.

## 5. Related topics

09 (the loop), 15 (import), 17 (copper to cells).

## 6. Sources

* Power-integrity practice (supply pins as sources, loads as current sinks, copper as a resistor network): [PDNSim], [AltiumPDN], [CadenceJoule] (search summaries). Trace current and temperature rise: [IPC2152] (named, not read).
* The KiCad file and the X2 attributes: [KiCadFormat], [UcamcoGerber] (revision 2024.05 read in part: the `.N` attribute, its syntax and reserved names, by the review of the separation of the Gerber folders, `research/gerber-import/docs/literature.md`).
* Similar tools (ideas only, AGPL where marked): [OpenToolsIdeas].
* Own computation: [L-gerber].

*What was read and what was not verified:* from `research/gerber-nets/README.md` (read in full); the power-integrity sources are search excerpts.
