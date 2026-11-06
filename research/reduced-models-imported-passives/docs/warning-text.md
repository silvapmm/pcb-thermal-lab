# Text for the project documents (when the maintainer decides)

Proposed replacement of `copper.REDUCED_MODEL_WARNING` (one string, no number of the program moves). The review rewrote the first proposal: it quoted size classes by the square root of the paste-hull area (which the user does not see), track widths that the study did not measure (0.1 to 0.3 mm), and "every time it was measured" without saying that the figures are a sample.

> imported copper on the Lumped / Analytic model: these models read the copper only as its average over a cell of 0.5 to 1 mm, so they do not see the pad of a part and the narrow tracks that feed it, which set most of the temperature rise of a small part; on 42 parts of three imported boards, with 1 W in one part at a time, they read 17 to 82 % too cool against the finite-volume model at a 0.5 mm cell, the most on the smallest parts (39 to 81 % for 0402-size passives); these figures are a sample, not a bound, and the finite-volume model itself reads the smallest parts hotter still at a finer cell; use the finite-volume model for the result

Numbers: `README.md` 3.3 (pooled ranges 17 to 82 %; the smallest class, 19 of whose 20 parts are 0402 hulls of 0.97 mm2: Lumped 52 to 81 %, Analytic 39 to 77 %) and 3.2 / 6.2 (the reference moves 3 to 30 % from 0.5 to 0.25 mm).

Where it goes: `docs/validation.md` 27.7 (a paragraph with the cause: the FVM rise grows 1.2 to 4.5 times from the layer-average sheet to the imported pattern, while the Lumped and Analytic change by -12 to +32 %), the user guide (Models, imported copper), `docs/theory.md` 1.7 or 5 (one sentence: the reduced models read the copper as a cell average). `tests/test_imported_copper.py` checks the new words.
