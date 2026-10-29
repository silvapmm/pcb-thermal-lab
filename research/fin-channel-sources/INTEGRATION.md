# Integration: what the source hunt changes in `fin-channel/INTEGRATION.md`

The program is not touched from this branch. This file says what the new sources change in Proposals A and B of `research/fin-channel/INTEGRATION.md` and in the maintainer's decisions of its section 6. Numbers are in `README.md` (section numbers in brackets).

## 1. Proposal A (post-run warning on the channel Rayleigh number)

**Unchanged.** The form of the rule (`Ra_b = g beta theta b^4 Pr / (nu^2 L)`, `phi = [1 + (14.16 / Ra_b^(3/4))^2]^(-1/2)`, warn below 90) is corroborated: the same composite with the same constants is printed by the first author of the 1984 paper (equation 13 of the 2003 paper: 576 and 2.873, identical to 4.6e-5) and the definition of `Ra_b` agrees with the `El` of that paper and with the `Ra*_b` of the Waterloo group [3]. The study's `Ra_b` is the one of the sources; no change of definition, reference temperature or length convention is needed.

**New evidence on a horizontal base** [7]: with the fin length as `L`, the rule fires for the six measured arrays of 5.55 mm gap (`phi` 0.30 to 0.75; the program's coefficient is 1.85 times the measured mean) and not for the 14.35 mm gap (`phi` 0.99 to 1.00). One of the three wide arrays (array 2) is 15 to 28 % below the uniform coefficient and is not flagged (plot data, +-0.3 W/m2K). The text of the warning that says "the block may be in another orientation" can say that for fins up on a horizontal base the measured loss is of the same size.

## 2. Proposal B (the `phi` correction)

**Unchanged in form.** What changes is the evidence for the orientation of the program's examples [7]:

| Case | program today | with `phi`, `L` = fin length | with `phi`, `L` = half the fin length |
| :-- | --: | --: | --: |
| 5.55 mm gap, six arrays, fins up, horizontal base: predicted / measured mean coefficient | 1.85 (1 / 0.54) | 1.10 (0.72 to 1.32) | 1.42 (1.12 to 1.63) |
| 14.35 mm gap: predicted / measured | 1.09 (1 / 0.92) | 1.10 (0.91 to 1.38) | 1.10 |

Consequences for the decisions of `fin-channel/INTEGRATION.md` section 6:

* **Decision 2 (vertical boards only, or also a bound for the horizontal ones)**: the data of one paper support applying `phi` with `L` equal to the length of the fins also to a horizontal base, **as an approximation that leaves the model about 10 % optimistic on average and 32 % at the worst point**, not as a conservative bound; they do not support `L/2`. Before adoption: a second measured set (Leung and Probert, Starner and McManus, Harahap and McManus are the candidates; none was obtainable) and the study of the open-front arrays below 4 mm.
* **Decision 3 (whether C3a comes before the correction)**: C3a is only partly done: a first measured set was found and read; the narrow open-front arrays of Leung and others (3 mm) still lack their original.
* **Decision 5 (plate level)**: the Prandtl function of the laminar Churchill and Chu term is confirmed against the exact similarity solution to 0.44 % for Pr 0.01 to 100 [6]; this removes one doubt about the plate level (the Prandtl dependence) and leaves the others (the constant 0.68, the all-range form against the composite's `0.59 Ra^(1/4)`: 13 % apart) unchanged.

## 3. Items that do not enter the program

* The optimum-spacing constants stay 2.7156 and 1.308 (derived from the composite); the 2.66 and 1.25 of the 2003 paper are not used. If the program ever shows an "optimum spacing" hint it should state which one and why [3].
* The correlation of Tari and Mehrtash for horizontal heat sinks: not proposed. It is a CFD fit outside its range for the program's blocks (`L` 40 mm against 250 to 340 mm), its area basis is not stated in the text read, and against the six measured arrays it is 10 to 40 % low [7].
* The reproduced array of Bar-Cohen, Iyengar and Kraus is a design example (a 0.64 m fin for the least-material case), not a validation of the program.

## 4. Risks and what the maintainer should know

* The evidence for B on a horizontal base is **plot values from one conference paper** with an assumed conductivity and an uncertain loss correction; no existing original was reached for Leung and others, Starner and McManus or Harahap.
* The sources fixed no reference temperature or `beta` convention; the 8 to 10 % difference in the 2003 example between a 20 and a 45 degC ambient (section 4) shows the size of what is left open.
* The review of this folder should check: the pixel reading of Figure 11 and of the six plots, the Table I values read from images, and the reading of the 2.66 as a recorrelation.
