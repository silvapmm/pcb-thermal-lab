# Text for `docs/validation.md` (a section after 55, to adopt with the read-out branch)

**Surface read-out of a thick plate.** Case 2 of Muzychka, Culham and Yovanovich (2003), error against the independent 3D surface at the four source centroids (97.41 / 103.85 / 101.31 / 99.95 C; paper 97.40 / 103.82 / 101.28 / 99.94), cell 0.5 mm:

| read-out | S1 | S2 | S3 | S4 |
| :-- | --: | --: | --: | --: |
| node (column mean), FVM | -1.96 | -4.62 | -3.73 | -2.85 |
| node plus the bound `q'' t/2k` | +1.37 | +3.71 | +2.94 | +2.15 |
| node plus the parabolic term | +0.57 | +1.26 | +1.03 | +0.80 |
| 4 sub-layers, FVM | +0.07 | +0.19 | +0.15 | +0.11 |
| 8 sub-layers, FVM | 0.00 | 0.00 | 0.00 | 0.00 |
| 3D solid, 4 / 8 copper slabs (S2) | | +0.28 / +0.09 | | |

Seri Lee's plate (K/W, 1 W): independent 0.668 / 1.284 / 2.275; FVM node 0.664 / 1.280 / 2.270; with the parabolic read-out 0.668 / 1.284 / 2.274. Thin copper: 35 um, 2 W on 6 x 6 mm, the surface is 1.76 mK (0.0018 %) above the column mean. Limits: one plate geometry for the sub-layer and slab options; the parabola overshoots for `t/a > 0.5`. Numbers: `research/through-thickness-readout/README.md` 4.
