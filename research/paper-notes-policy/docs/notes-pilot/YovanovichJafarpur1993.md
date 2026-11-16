# Note: YovanovichJafarpur1993 (a pilot of the policy, illustration only; not adopted)

- Key: YovanovichJafarpur1993
- Citation: M. M. Yovanovich, K. Jafarpur, "Bounds on laminar natural convection from isothermal disks and finite plates of arbitrary shape for all orientations and Prandtl numbers", report of the Waterloo Microelectronics Heat Transfer Laboratory (1993), 18 pages (the exact venue was not confirmed).
- Reading status: R for pages 1 to 15 (transcription); pages 1, 3, 8 and 11 (equations 1, 25, 26 and the face-down constants) compared with the page images by the reviewer of this folder.
- Licence of the source: all rights reserved (the publisher or author class is not established; status N for terms). What a note may keep: summary, formulas with numbers and equation numbers, our own account.
- Class: publisher or institution report (copyrighted).

## Summary

The report brackets the mean heat transfer of a laminar natural-convection plate of any outline between an upper and a lower bound, built from a conduction limit for a still fluid plus a boundary-layer term. The square root of the plate area is the length scale. The bounds hold for all Prandtl numbers through one Prandtl function and for different orientations through a gravity factor. Its text also reports the earlier face-down measurements and the range of the constant of the face-down law.

## Equations used as facts

- Equation 1: `Nu = Nu_inf + F(Pr) G Ra^(1/4)` on the length `sqrt(A)`.
- Equation 25 (upper bound, air, length sqrt(A)): `3.545 + 0.571 Ra^(1/4)`; the figure legends print 0.570 (an inconsistency inside the report).
- Equation 26 (lower bound, air): `2.257 + 0.382 Ra^(1/4)`.
- Page 8: for the face looking down, the constant C of `Nu = C Ra^(1/5)` in the integral-method results that Goldstein and Lau (1983) summarised spans 0.44 to 0.527, and its mean over the Pr 0.71 results is 0.475 (this is a number we adopted).

## Numerical cases we test against

None of our own; we use the constant 0.475 and the 1/5 exponent for the face turned down (`pcbthermal/convection.py`).

## Limits and caveats

The 0.475 is a mean of values the report quotes from Goldstein and Lau (not obtained); scale choices are not interchangeable.

## Used in the program

`convection.h_natural_horizontal` (face down law, constant `DOWN_COEFFICIENT`); decision recorded in `docs/decisions-log.md`.
