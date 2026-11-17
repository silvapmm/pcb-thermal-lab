# Errata of the formula rows of the 2.8.0 audit

`formulas.csv` is the frozen record of the 2.8.0 audit and is not rewritten. A later review of the formula index found these stale lines; the living documents (`docs/theory.md`, `research/theory/BIBLIOGRAPHY.md`) already carry the correct values.

| Row | Stale line | Correct |
| :-- | :-- | :-- |
| F-002 | coefficient 0.15, "from memory" | the code uses the printed 0.14 with the Prandtl factor (1 + 0.0107 Pr) / (1 + 0.01 Pr) (`convection.py`) |
| F-005 | equation 8.13a on p. 420 / PDF 434 | 8.13a is on printed p. 419 / PDF 433; 8.13b on p. 420 / PDF 434 |
| F-013 | Table A.6 on p. 755, "offset uncertain" | printed p. 755 is PDF 769, verified |
| F-017 | bound `q'' t / (2k)` cited as "YCT1998 eqs 1-60" | own derivation: the one-dimensional column with a linear profile |
| F-073 | Saad eq 4.47 pages 146-147 both verified | PDF 147 (printed 127) was read by image but has no verification record; the formula matches `fvm.sor_omega` |
| F-096 | Table A.1 transcribed | no transcription: read by image, PDF 753 (printed 739) |

No row changes a number or a model.
