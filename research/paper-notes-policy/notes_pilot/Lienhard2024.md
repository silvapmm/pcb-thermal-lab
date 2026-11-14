# Note: Lienhard2024 (ILLUSTRATION ONLY, a pilot for the policy; not adopted)

- Key: Lienhard2024
- Citation: J. H. Lienhard IV and J. H. Lienhard V, *A Heat Transfer Textbook*, 6th ed., version 6.00, Phlogiston Press (2024); free to read at ahtt.mit.edu.
- Reading status: R for pages 419 to 421 and 435 to 437 (page images compared, as recorded in `research/theory/BIBLIOGRAPHY.md`).
- Licence of the source: copyright kept by the authors; free to download is not an open licence (status S: search result, no licence text found). What a note may keep: references only (equation, page) plus our own account.
- Class: book.

## Summary

The chapter on natural convection gives a laminar and an all-range correlation for the vertical plate, and for the horizontal plate a pair of correlations built on the area over perimeter length, with a correction when the Nusselt number is small. A worked example uses the laminar form. We use the book as the printed check of the correlations our code implements and as a source of air properties.

## Equations used as facts (references, no text)

- Eq. 8.13a (laminar vertical form) and 8.13b (all-range form), book pages 419 to 421; Example 8.1 prints Nu 47.33 and h 4.22 W/m2K (Pr 0.71, Ra 6.78e7, L 0.30 m).
- Eq. 8.35 and 8.37a/b, pages 435 to 436: horizontal plates, `L* = A/P`, valid `1 < Ra* < 1e7` for the second.
- The book does NOT print our horizontal laws 0.54 / 0.15 / 0.27 (we say so in the theory).

## Numerical cases we test against

Example 8.1: our laminar form gives 4.233 against 4.22 W/m2K (the general form 4.86); Example 6.5: 21.39 against 21.4 W/m2K.

## Limits and caveats

Our reading is of version 6.00; page numbers are printed pages (PDF page is 14 more).

## Used in the program

`pcbthermal/convection.py`; `docs/theory.md` 8.
