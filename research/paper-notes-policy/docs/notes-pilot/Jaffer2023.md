# Note: Jaffer2023 (a pilot of the policy, illustration only; not adopted)

- Key: Jaffer2023
- Citation: A. G. Jaffer, "Natural Convection Heat Transfer From an Isothermal Plate", Thermo 3(1) 148-175 (2023), article 10, DOI 10.3390/thermo3010010; preprint arXiv:2201.02612v6.
- Reading status: R for equation 2 (page 5 of arXiv v6), Table 1 (page 4) and Table 6 (page 15), compared with the page images by the reviewer; S for the measurement sets themselves (the originals were not obtained).
- Licence of the source: the journal version is CC BY 4.0 (status S: the MIT DSpace record of the published version, handle 1721.1/148015, as returned by a search; the MDPI page and the DSpace page refused the fetch); the arXiv copy, which is the one we read, carries the arXiv non-exclusive licence (status R, abstract page). What a note may keep: summary, formulas with numbers, short quotes.
- Class: open-access journal article (the most permissive class).

## Summary

The paper re-examines published natural-convection data for isothermal plates and proposes new correlations for the upward and downward faces of horizontal plates, with a length scale built from the plate shape. For the vertical plate it takes the Churchill and Chu correlation as the reference: the rms relative errors against the data, computed with its own formula and with Churchill and Chu, differ by less than one percent. Most of the measurements it tests against were captured from the graphs of earlier papers, so they carry the digitising error.

## Equations used as facts

- Vertical plate, all Rayleigh numbers (equation 2): `Nu^(1/2) = 0.825 + 0.387 Ra^(1/6) / [1 + (0.492/Pr)^(9/16)]^(8/27)`, stated for `1 <= Ra <= 1e12`; `Nu` and `Ra` on the plate height. Symbols: Nu mean Nusselt number, Ra Rayleigh number, Pr Prandtl number.
- Bias of the author's own vertical formula (his equation 55) against four data sets, Table 6: +11.1 % (King), +3.1 % (Jakob), -15.4 % (Cheesewright), -1.2 % (Saunders, mercury). These are not the biases of equation 2.

## Numerical cases we test against

Bias values above, air Pr 0.70 for the first three sets (Table 1: Ra from 3.6e3 up to 1e12 over the three air sets); reproduced in `research/plate-h-level/`.

## Limits and caveats

Data are digitised from plots, not the original tables; the author presents his formulas as derived, not fitted, and his thermodynamic argument was not evaluated here; we only compare them with plot values.

## Used in the program

`pcbthermal/convection.py` laminar and general vertical forms are checked against this equation (topic 08).

