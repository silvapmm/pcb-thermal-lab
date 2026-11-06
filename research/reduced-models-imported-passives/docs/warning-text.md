# Text for the project documents (when the maintainer decides)

Proposed replacement of `copper.REDUCED_MODEL_WARNING` (one string, no number of the program moves):

> imported copper on the Lumped / Analytic model: these models see the copper only as its average in a cell of 0.5 to 1 mm, so the pad of a part and the tracks that feed it (0.1 to 0.3 mm) are invisible to them, and they read too cool every time it was measured: 17 to 82 % on 42 heat sources of three boards (1 W in one part, against the finite-volume model at 0.5 mm; 52 to 81 % for a part under 1.5 mm, 25 to 82 % for 1.5 to 3 mm, 25 to 56 % for a larger one, Lumped; 17 to 77 % Analytic); the finite-volume model, which reads the pattern of the copper, is the result, and it reads still hotter at a finer cell for the smallest parts.

Where it goes: `docs/validation.md` 27.7 (a paragraph with the cause: the FVM rise grows 1.4 to 3.7 times from the layer-average sheet to the imported pattern, while the Lumped and Analytic change by under 10 %), the user guide (Models, imported copper), `docs/theory.md` 1.7 or 5 (one sentence: the reduced models read the copper as a cell average). Numbers: `README.md` 3.1 and 3.3 of this folder.
