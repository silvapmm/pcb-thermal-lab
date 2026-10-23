# Literature status for nets with voltage and current (phase 3)

Web searches only, excerpts, nothing read in full:

* Commercial power-integrity tools (Cadence Allegro IR drop, Altium PDN Analyzer, Altair PollEx) model supply pins as voltage sources, loads as current sinks per pad or device, series elements as resistances and the copper as a resistor network; the results are the voltage drop, the current density and the power loss per shape and via.
* The OpenROAD PDNSim documentation describes the same for chips: supply pins as voltage sources, switching logic as current sources, the metal as resistances, the capacitances shorted in the static case.
* `docs/roadmap.md` on `develop` lists FYPA (Tomachie fork) and padne (atx): text directives on `DESIGNATOR.PAD` endpoints, a sidecar file, regulator model, the current solution as the heat source (AGPL-3.0: ideas only, no code copied).
* Not found: islands of one net bridged by components, or an inference of current from the voltage alone.
* Not fetched: the repositories of kicad-electrothermal-sim and padne (404), the Altium page (host not resolved).
