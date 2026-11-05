# Text for the project documents (to adopt with the decision; nothing here is in `docs/`)

## For `docs/theory.md` section 8 (horizontal faces), if option A (keep) is chosen

The horizontal laws are `Nu = 0.54 Ra^(1/4)` (face up, Ra up to 1e7, then `0.15 Ra^(1/3)`) and `Nu = 0.27 Ra^(1/4)` (face down) on `L = A/P`.
The first is the Lloyd and Moran form as the textbooks print it (mass transfer, range 2.2e4 to 8e6; [YovanovichJafarpur1993] p. 7), the second has no published form in the range of the boards.
Boards of 40 to 200 mm at 5 to 80 K sit at Ra 5e2 to 5e5 on A/P (100 x 80 mm: 5e3 to 5e4). Against Raithby and Hollands (Lienhard eq. 8.37a/b, 1 < Ra < 1e7, read) the face up is -7 % at Ra 3e2, -1 % at 1e3, +9 % at 1e4 and +15 % at 1e5
(coefficient only); against the mean Goldstein-Lau law `0.475 Ra^(1/5)` ([YovanovichJafarpur1993] p. 8, read) the face down is -20 % at Ra 1e3, -10 % at 1e4 and +1 % at 1e5. The hottest rise of a horizontal board
with computed h moves by -0.9 to +1.0 % (radiation included; -1.7 to +2.9 % without) when both faces are changed to those laws (`research/convection-laws/` 6, 17 boards, FVM 2 mm): the limit is real and its effect on the temperature of a board is small,
because about half of the film coefficient of a board is radiation and the copper spreads the heat. The laws are not proven conservative on either face.

## For `docs/theory.md` section 8, if option B is adopted

Face up: Raithby and Hollands, `Nu = 0.560 Ra^(1/4) / [1 + (0.492/Pr)^(9/16)]^(4/9)` with `L = A/P`, replaced by `1.4 / ln(1 + 1.4/Nu)` when `Nu <= 10`, for 1 < Ra < 1e7 (Lienhard 6.00, eq. 8.37a/b, p. 436, read in the page image), and
`0.14 Ra^(1/3) (1 + 0.0107 Pr)/(1 + 0.01 Pr)` from 1e7 (eq. 8.35, p. 435; the two equations differ by 25 % at 1e7, a discontinuity of the source).
Face down: `Nu = 0.475 Ra^(1/5)` on `A/P`, the mean of the Pr 0.71 results of Goldstein and Lau (1983) as quoted by Yovanovich and Jafarpur (1993, p. 8, read; the paper of Goldstein and Lau was not obtained); their numerical strip is 0.524 for 40 < Ra < 8e3.
