# Text for the project documents (when the capped first ring is adopted)

## docs/theory.md, section 5.1, after equation (5.1)

The first ring is also capped at the equivalent radius of the footprint: `E1 = min(max(1.5 min(Δx,Δy), 0.04 E_max), max(1.5 min(Δx,Δy), a_eq), 0.5 E_max)`, `a_eq = sqrt(N0 Δx Δy / π)` (`N0` the cells the footprint touches). Without the cap the ring next to a small part is `0.04 E_max` wide, which grows with the board; the link between ring means takes each half ring as a strip of length `area / width` (eq. 5.2), and for a ring several footprint radii wide the strip has 0.53 (five radii) to 0.43 (ten radii) of the resistance of the annulus that the heat really crosses, so the part read cool (a 1 mm part on a uniform two-layer board, centred: 60 x 40 mm -1 %, 100 x 80 mm -14 %, 200 x 150 mm -25 % against the FVM). A footprint larger than `0.04 E_max` is unchanged. Sources: own derivation (the ring construction has no published source); checked against the FVM and an independent 3D layered solver in `research/lumped-ring-uniform-deficit` (no source was opened there; the solver's own checks are in `research/effective-conductivity`).

## docs/validation.md, new paragraph in the Lumped section

Uniform sheets, one source: a 1 mm part on a 100 x 80 mm two-layer board read -13.7 % (200 x 150 mm: -25.3 %) against the FVM before the capped first ring and +0.3 % (+2.5 %) after; 2 mm sources on 100 x 80 mm at 1, 2 and 4 layers, fill 1 and 0.6, 10 to 200 W/m2K, with and without edge convection: -5.5 to -10.8 % become -1.1 to -4.3 %; the independent 3D solver puts the 1 mm part off centre at -15.0 % before and -3.0 % after. A source near a board edge or corner is still 5 to 15 % cool in the Lumped (the Analytic is exact there), and the Lumped on imported copper is still dominated by the copper structure below the cell.

## CHANGELOG.md (Unreleased, Fixed)

The Lumped model read small parts cool on large boards (a 1 mm part on a 200 x 150 mm uniform board -25 %): the first ring of its network was as wide as 0.04 of the distance to the farthest cell of the board; it is now at most one equivalent radius of the footprint wide. Boards where the first ring was already narrower than the footprint (every board of the frozen numbers, the via studies and the example board) are unchanged.
