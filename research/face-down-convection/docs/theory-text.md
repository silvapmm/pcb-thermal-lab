# Text for `docs/theory.md` 8, `docs/models.md` 2 and 5 (to adopt with the proposal in `../INTEGRATION.md`)

**Natural convection, horizontal plate, the face turned down** (replaces the line "hot face down `Nu = 0.27 Ra^{1/4}`" and the paragraph "Limit of the face turned down"):

Hot face down (and cold face up): `Nu = 0.52 Ra^{1/5}` with `L = A/P` (area over perimeter of one face), `Pr` about 0.7. The constant and the range, `10^4 <= Ra <= 10^9`, are the ones Incropera and DeWitt give in the later editions of Chapter 9 for the
lower surface of a heated plate (status M until the book page is read). Two further sources read give the same exponent and the same level for air: the mean of the laminar constants of Goldstein and Lau, `0.475 Ra^{1/5}`, and their numerical strip, `0.524 Ra^{1/5}` for `40 < Ra < 8000`
(Yovanovich and Jafarpur 1993, page 8, R); VDI gives `0.6 (Ra f_1)^{1/5} = 0.486 Ra^{1/5}` (S). Lienhard prints the exponent 1/5 for the lower side of a hot plate (eq. 8.38, Fujii and Imura, a two-dimensional plate on its width, water; eq. 8.39, Kadambi and Drake, a disc). The program used `0.27 Ra^{1/4}` (the McAdams form) until this change:
it was 20 to 27 % below the 1/5 level at `Ra` 1e3, 10 to 18 % at 1e4 and above it from `Ra` 1e6.

Limits: the flow under a plate is stable and starts at the centre of the face (figure); the laws assume the air can leave freely at the edges (Lienhard p 436), so a board in a case, over a wall or with components under it has a lower coefficient than the law;
the constant depends on the shape of the face (a long strip is 17 % above the mean level, a square 14 % below it, Jaffer 2023); the published levels scatter by 30 to 40 % at `Ra` 1e3 to 1e4. No law was compared with a measured copper board.

Sources (keys of `research/theory/BIBLIOGRAPHY.md`): [IncroperaDeWitt] M, [YovanovichJafarpur1993Bounds] R, [GoldsteinLau1983] N, [Lienhard2024] R, [FujiiImura1972] N, [Jaffer2023] R, [McAdams], [VDI] S.
