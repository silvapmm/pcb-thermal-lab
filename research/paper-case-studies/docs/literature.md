# Literature status after the planning pass

The full records are in `research/theory/BIBLIOGRAPHY.md`. R read in full, S summary, M memory, N not obtained, "plot" a number read from a figure. Nothing is reproduced by a study yet.

| Source | Pages and items read here | Status | What is missing |
| :-- | :-- | :-- | :-- |
| Soleymani Koohbanani (2016), SFU MSc thesis | pp 56 to 64: equations 17 to 29 (page images), Tables 9 and 10, Fig. 33 (plot, pixel read), page 62 text | R for these pages; the rest S | the guarded heat-flux-meter chapter and its uncertainty analysis (p 77 of the contents); the thickness and foil of the samples are not stated |
| Shen and others, IEEE TPEL 35 (1) 882-900 (2020) | Table II, Figs. 23 to 25, section IV text, equations 37 to 42; the review read pages 14 to 17 as images: Fig. 18 (CFD theta_via, plot), Fig. 20 (theta_ta about 360 to 385 degC/W at the rises of Table II, plot), Fig. 22 (structure and network); equation 42 drops the 1 / theta_ta term of the line above it (the exact inversion is used) | R (plot for Figs. 18 and 20) | heatsink and TIM resistances, array extent and layers of the experimental board; Fig. 16(b) not needed |
| Muzychka, Yovanovich, Culham, JTHT 18 (1) (2004) | pp 49 and 50: equations 37 to 58 (50 and 51 from the page image) | R | the three isotropic parents cited there (Muzychka 2003, Yovanovich 1998) are read elsewhere (`research/theory-sources`) |
| mean reciprocal distance of a unit square, 2.9732 (half-space constant 0.4732) | computed in a test by a double integral | derived; also published | none: Yovanovich, Muzychka and Culham, J. Thermophys. Heat Transfer 13 (4) (1999) pages 498 and 499 (page images, read by the review): equation 19 (the deep square channel, the same series as equation 50 of Muzychka 2004 in that limit) and its correlation, equation 20, 0.47320 - 0.62075 eps + 0.1198 eps^3 (0.3 %), reproduced by `lib/flux_channel.py` to 0.003 % (a test) |
