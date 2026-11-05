# Part A (in progress)

Runner: scripts/run_part_a.py (running; outputs in out/, git-ignored, summary out/part_a.json). Comparison with the READMEs is not written yet.

First comparison: analytic-partial-copper study_baseline: Lumped, Analytic, 3D solid columns equal the README to the printed digit; FVM and FDM columns differ from the README table (README predates the 2.4.5 laminate rule) and sit within 0.1 point of the 2.4.5 reproduction values.

## Folders compared so far

* analytic-2-6 (7 scripts): UNCHANGED. Section 6.1 table (-8.64/-5.18 ... -3.83/-0.03), frozen impact (+0.004 / -0.003 / -0.001 K, seven boards bit-identical), frozen transient (+18.0 -> +3.8 %, +4.5 -> +5.9, +3.2 -> +4.3), t63 table (74.33 s, +0.6 % ...) all equal the README (reviewed on the 2.5.0 tree).
* analytic-edge-spatial (6 scripts): study_review_checks 4b (-8.64, +5.46, -6.87, +5.42, +3.22, -1.99, -7.32 %) and the strip/variant tables equal the README. study_frozen_impact prints "Robin vs program +0.00 %" on every board where the README (written before the adoption) says +0.29 to +0.70 %: EXPLAINED, the program now is the Robin edge (item: Robin Analytic edge).
* analytic-partial-copper (5 scripts, study_baseline read): Lumped, Analytic, 3D columns equal the README; FVM and FDM columns differ from the README by the 2.4.5 laminate rule (already explained in reproduction-245), within 0.1 point of those values. study_candidate/rows/review not yet compared.
* Not yet compared: the rest (runner in progress).
