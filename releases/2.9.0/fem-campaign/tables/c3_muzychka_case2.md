tree 0fbabbec, program 2.8.0
independent 3D solver (0.5 mm, 8 sub-slabs): column mean at the centroids 95.35 / 99.15 / 97.49 / 97.01, surface centroid 97.41 / 103.85 / 101.31 / 99.95 degC
paper (Table 4) centroid 97.40 / 103.82 / 101.28 / 99.94, mean 96.85 / 102.33 / 100.10 / 99.07 degC

### Column read-out: centroid of each source minus the column mean of the independent 3D solver, K (S1 / S2 / S3 / S4)
| model | 2 mm | 1 mm | 0.5 mm |
| :-- | :-- | :-- | :-- |
| FEM | -0.00 / -0.01 / -0.01 / -0.00 | +0.03 / +0.09 / +0.07 / +0.06 | +0.09 / +0.09 / +0.09 / +0.09 |
| FVM | +0.03 / +0.04 / +0.03 / +0.03 | +0.04 / +0.09 / +0.07 / +0.06 | +0.10 / +0.08 / +0.09 / +0.09 |
| FDM | -0.13 / -0.09 / -0.11 / -0.11 | +0.08 / +0.05 / +0.06 / +0.07 | +0.07 / +0.10 / +0.09 / +0.08 |
| 3D solid | +0.02 / +0.05 / +0.04 / +0.04 | +0.04 / +0.10 / +0.07 / +0.06 | +0.09 / +0.09 / +0.09 / +0.09 |
| Analytic | +0.04 / +0.09 / +0.07 / +0.06 | +0.04 / +0.09 / +0.07 / +0.06 | +0.10 / +0.08 / +0.09 / +0.09 |
| Lumped | +0.30 / -0.74 / -0.20 / -0.24 | +0.30 / -0.74 / -0.20 / -0.24 | +0.40 / -0.70 / -0.14 / -0.16 |

### Surface read-out: centroid of each source on the surface map minus the paper's printed centroid, K (S1 / S2 / S3 / S4); the independent 3D solver's own surface minus the paper is +0.01 / +0.03 / +0.03 / +0.01
| model | 2 mm | 1 mm | 0.5 mm |
| :-- | :-- | :-- | :-- |
| FEM | -0.08 / -0.21 / -0.17 / -0.12 | -0.00 / -0.00 / -0.00 / -0.00 | +0.07 / +0.03 / +0.05 / +0.05 |
| FVM | +0.50 / +1.25 / +1.00 / +0.75 | +0.52 / +1.29 / +1.04 / +0.78 | +0.57 / +1.29 / +1.06 / +0.81 |
| FDM | +0.35 / +1.12 / +0.86 / +0.61 | +0.56 / +1.25 / +1.03 / +0.79 | +0.55 / +1.30 / +1.06 / +0.80 |
| 3D solid | -0.02 / -0.04 / -0.03 / -0.02 | +0.03 / +0.08 / +0.06 / +0.05 | +0.10 / +0.12 / +0.12 / +0.11 |

The Lumped has no surface map (the Analytic has one, shown in study_compare_c4.py). The column minus the paper is not a comparison (the paper prints the surface).
