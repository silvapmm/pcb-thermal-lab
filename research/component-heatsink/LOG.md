# Log: the part, its top path and its heatsinks

- Package basis researched (NISTIR 7648, TI SPRA953B, Renesas white paper, Semiconductor Digest, Siemens); `package_prototype.py` showed the offset reproduces the TI CSD17308Q3 datasheet RθJA within 2 %.
- `component_study.py`, `heatsink_study.py`, `block_contact_study.py`, `chain_study.py`, `heatsink_convection_study.py` and `base_spreading_study.py` written while discussing the junction node, the heatsink on the package and the interfaces with the maintainer. Decision: worst case first.
- The top path implemented (fixed-point loop) and checked against the junction-node prototype by `top_path_study.py` (0.4 to 0.8 K).
- Heater type (source or component), package family list, typical heatsink list (catalogues of Wakefield-Vette, Fischer, Aavid and SAME Sky; several values from distributor listings, not manufacturer datasheets) and the flow study (`docs/research.md` R3, now in `NOTES.md`).
- Folder created: the eight scripts moved from `examples/`; all eight were run again and reproduce the numbers of `NOTES.md` and `docs/validation.md` section 9 (MOSFET 107.6 → 104.6 → 67.4 °C; program 69.8 against prototype 69.0 °C; fixed 12 K/W against natural scaling 68.1 → 70.4 °C). The README table of the offset was re-read from the output: an earlier line in a draft said "1 to 3 K" and was corrected to 2.5 to 10 K.

Read in full, from summaries, or from memory: see `NOTES.md` section by section. The factors for forced air come from a guide (Electronics Cooling, 1995) and were compared with a few catalogue values only. θJC(top) of the MOSFET and the Schottky are assumed. Not verified: no measurement of a physical part; the junction node was only prototyped.
- Schematic diagram added (`scripts/make_diagrams.py`, figure 5): drawn, not computed; the numbers it quotes are those of this README.
