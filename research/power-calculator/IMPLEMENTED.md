# Power calculator: what entered the program

Released in **2.4.0** (2026-10-22).

| What | Where |
| :-- | :-- |
| The board model run backwards: `power_from_temperature` (points ring, max, mean, junction, top), `point_temperatures`, `power_band` (best / nominal / worst), `power_from_theta` (route 2) | `pcbthermal/inverse.py` |
| The calculation in the separate process | `pcbthermal/jobs.py` (`job_inverse`) |
| The window: two tabs (route 1 drawn board, route 2 datasheet), the band and its case selector, *Use as the power of a part*, Help button | `pcbthermal/gui/calculator.py`, `pcbthermal/help/calculator.html` |
| The uncertainties of the band (copper ±25 %, h ±30 %, θ ±20 %, ψJT ±30 %, reading ±1 K), editable in Preferences | `pcbthermal/data/defaults.json` (section `calculator`), `pcbthermal/gui/preferences.py` |
| Tests | `tests/test_inverse.py`, `tests/test_calculator_validation.py` |
| Project documents | `docs/calculators.md` (the manual and the validation), `docs/validation.md` section 19, `CHANGELOG.md`, `docs/versions.md`, `pcbthermal/help/index.html` |

Not implemented: the known-power reference (fits only parts with a controllable dissipation; the copper error it removes also goes away with Gerber or KiCad import), the two-point fit (a study only), the datasheet shortcut θJA − ψJT.
