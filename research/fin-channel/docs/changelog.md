# Text for `CHANGELOG.md` (Unreleased), to use when the work is adopted

Proposal A (a `fix/` item):

* The warning about close fins now depends on the length of the channels and the temperature of the block: it warns after the solve when the channel Rayleigh number `Ra_b = g beta theta b^4 Pr / (nu^2 L)` is below 90 (the channel keeps less than 90 % of the isolated-plate coefficient), instead of "gap below 4 mm". It flags the cases where the finned face loses 10 % or more of its conductance that the old rule missed (312 of 612 on the study grid).

Proposal B (a `feature/` item, only if decided):

* Finned blocks on a vertical board: option "channel effect between the fins": the coefficient of the fins is multiplied by the channel fraction `phi(Ra_b)`; steady state; the solve is repeated until the block temperature settles.
