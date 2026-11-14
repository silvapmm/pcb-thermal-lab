# Note: Jaffer2023 (ILLUSTRATION ONLY, a pilot for the policy; not adopted)

- Key: Jaffer2023
- Citation: A. G. Jaffer, "Natural Convection Heat Transfer From an Isothermal Plate", Thermo 3(1) 10 (2023), DOI 10.3390/thermo3010010; preprint arXiv:2201.02612v6.
- Reading status: R for equation 2 and the vertical-plate conformance table (arXiv text compared with the checks recorded in `research/theory/BIBLIOGRAPHY.md`); S for the measurement sets themselves.
- Licence of the source: the journal version is CC BY 4.0 (class: MDPI open access; status M, the MDPI page was not reachable, see README 2); the arXiv copy carries the arXiv non-exclusive licence (status R, abstract page). What a note may keep: summary, formulas with numbers, short quotes.
- Class: open-access journal article (the most permissive class).

## Summary

The paper re-examines published natural-convection data for isothermal plates and proposes new correlations for the upward and downward faces of horizontal plates, with a length scale built from the plate shape. For the vertical plate it takes the Churchill and Chu correlation as the reference and shows that its own formula differs from it by under one percent in rms relative error. The measurements it tests against are digitised from earlier graphs, so they carry the digitising error.

## Equations used as facts

- Vertical plate, all Rayleigh numbers (equation 2): `Nu^(1/2) = 0.825 + 0.387 Ra^(1/6) / [1 + (0.492/Pr)^(9/16)]^(8/27)`, stated for `1 <= Ra <= 1e12`; `Nu` and `Ra` on the plate height. Symbols: Nu mean Nusselt number, Ra Rayleigh number, Pr Prandtl number.
- Conformance of the vertical formula to four data sets (the table of vertical conformance): bias +11.1 % (King), +3.1 % (Jakob), -15.4 % (Cheesewright), -1.2 % (Saunders, mercury).

## Numerical cases we test against

Bias values above, air Pr 0.70 for the first three sets (Ra from 3.6e3 up to 1e12 over the sets); reproduced in `research/plate-h-level/`.

## Limits and caveats

Data are digitised from plots, not the original tables; the author's own thermodynamic argument was not evaluated; his horizontal-plate fits are fits to plot values.

## Used in the program

`pcbthermal/convection.py` laminar and general vertical forms are checked against this equation (topic 08).

