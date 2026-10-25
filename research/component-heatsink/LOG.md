# Log of the investigation

Dated entries: what was read (in full, from a summary, from memory), what was run and reproduced, what was not. Older work is recorded section by section in `NOTES.md`.

## 2026-10-25: review by the reviewer agent

* **Run** on the program of `develop` `1674d52` (physics code identical on `research/gerbers`): `package_prototype.py`, `component_study.py`, `top_path_study.py`, `chain_study.py`, `heatsink_study.py`, `heatsink_convection_study.py`, `base_spreading_study.py`, `block_contact_study.py`, `make_figures.py`, `make_diagrams.py`; new `study_top_path_convergence.py`. Every table of the README before the review reproduced to the last digit, except what the corrections below changed.
* **Read in full** (pypdf text of the PDF, downloaded to the session scratch directory, not committed): TI CSD17308Q3 SLPS262C (thermal information, Tj range), TI TPS7A47 SBVS204G (thermal information, recommended Tj −40 to 125 °C), TI LMR36510 (thermal information, Tj −40 to 150 °C), Vishay SS12 document 88746 (RθJA 88, RθJL 28 K/W, Tj −65 to 150 °C). onsemi's SS14 page returned HTML, not the PDF; the SX Semiconductor SS12 sheet of `NOTES.md` [14] was not re-opened.
* **From memory** (not re-opened): Seri Lee and others' spreading formula (Electronics Cooling 1998), used as a closed-form check of the heatsink base; the Electronics Cooling volumetric factors of forced air; the heatsink catalogue values of the library.
* **Found and fixed**: forced air scaled like natural convection (`heatsink_convection_study.py`); the base read half a cell above its face (`base_spreading_study.py`); table D compared the worst-case offset with a node (node column added); constant Tj max column; ψJB route and model agreement not printed by any script (now printed); stale cross-references and dead code; figures 1, 3, 4, 5, 6 redrawn.
* **Found, not fixed (program)**: the top-path loop of `api._solve_with_tc` does not converge on small pads (README 4.11, `INTEGRATION.md`).
* **Reproduced afterwards** (`study_notes_r2.py`): the "perfect contact" table of `NOTES.md` R2 to the printed digit; the fin and thickness numbers did not reproduce (71.2 to 71.8 °C across metals at 6 mm, 1 mm 76.4, 3 mm 73.8, 6 mm 71.2 °C; the earlier values were about 0.5 K higher) and were replaced by the printed ones.
