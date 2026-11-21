tree 0fbabbec, program 2.8.0

### case 3, cross (100 x 100 x 10 mm, k 50, h 50), cell 1 mm; printed centroids 80.61 degC (the paper prints the surface)
| model | read-out | centroids degC | shortfall paper - model, % of the paper rise (first source) | seconds |
| :-- | :-- | :-- | :-- | --: |
| FEM | column | 79.70 | +1.6 | 8.2 |
| FEM | surface | 80.61 | -0.0 | 8.2 |
| FVM | column | 79.69 | +1.6 | 0.0 |
| FVM | surface | 80.62 | -0.0 | 0.0 |
| FDM | column | 79.69 | +1.7 | 0.0 |
| FDM | surface | 80.61 | -0.0 | 0.0 |
| 3D solid | column | 79.70 | +1.6 | 3.4 |
| 3D solid | surface | 80.63 | -0.0 | 3.4 |
| Analytic | column | 79.69 | +1.7 | 0.0 |
| Analytic | surface | 80.62 | -0.0 | 0.0 |
| Lumped | column | 79.41 | +2.2 | 0.1 |

### case 2, baseplate (50 x 50 x 10 mm, k 150, h 400), cell 1 mm; printed centroids 97.40 / 103.82 / 101.28 / 99.94 degC (the paper prints the surface)
| model | read-out | centroids degC | shortfall paper - model, % of the paper rise (first source ... all) | seconds |
| :-- | :-- | :-- | :-- | --: |
| FEM | column | 95.38 / 99.24 / 97.55 / 97.06 | +2.8 / +5.8 / +4.9 / +3.8 | 1.3 |
| FEM | surface | 97.40 / 103.82 / 101.28 / 99.94 | +0.0 / +0.0 / +0.0 / +0.0 | 1.3 |
| FVM | column | 95.39 / 99.23 / 97.56 / 97.07 | +2.8 / +5.8 / +4.9 / +3.8 | 0.0 |
| FVM | surface | 97.92 / 105.11 / 102.32 / 100.72 | -0.7 / -1.6 / -1.4 / -1.0 | 0.0 |
| FDM | column | 95.43 / 99.19 / 97.54 / 97.08 | +2.7 / +5.9 / +4.9 / +3.8 | 0.0 |
| FDM | surface | 97.96 / 105.07 / 102.31 / 100.73 | -0.8 / -1.6 / -1.3 / -1.0 | 0.0 |
| 3D solid | column | 95.38 / 99.24 / 97.56 / 97.07 | +2.8 / +5.8 / +4.9 / +3.8 | 0.5 |
| 3D solid | surface | 97.43 / 103.90 / 101.34 / 99.99 | -0.0 / -0.1 / -0.1 / -0.1 | 0.5 |
| Analytic | column | 95.39 / 99.24 / 97.56 / 97.07 | +2.8 / +5.8 / +4.9 / +3.8 | 0.0 |
| Analytic | surface | 97.92 / 105.12 / 102.32 / 100.72 | -0.7 / -1.6 / -1.4 / -1.0 | 0.0 |
| Lumped | column | 95.65 / 98.40 / 97.29 / 96.76 | +2.4 / +6.9 / +5.2 / +4.2 | 0.0 |

### case 1a, thick plate (300 x 300 x 10 mm, k 10, h 10), cell 2.5 mm; printed centroids 84.97 / 108.43 degC (the paper prints the surface)
| model | read-out | centroids degC | shortfall paper - model, % of the paper rise (first source ... all) | seconds |
| :-- | :-- | :-- | :-- | --: |
| FEM | column | 79.97 / 100.94 | +8.3 / +9.0 | 13.6 |
| FEM | surface | 85.24 / 108.83 | -0.4 / -0.5 | 13.6 |
| FVM | column | 80.09 / 101.11 | +8.1 / +8.8 | 0.1 |
| FVM | surface | 85.51 / 109.24 | -0.9 / -1.0 | 0.1 |
| FDM | column | 79.84 / 100.81 | +8.6 / +9.1 | 0.1 |
| FDM | surface | 85.26 / 108.94 | -0.5 / -0.6 | 0.1 |
| 3D solid | column | 80.13 / 101.18 | +8.1 / +8.7 | 4.4 |
| 3D solid | surface | 85.45 / 109.15 | -0.8 / -0.9 | 4.4 |
| Analytic | column | 80.09 / 101.12 | +8.1 / +8.8 | 0.1 |
| Analytic | surface | 85.52 / 109.25 | -0.9 / -1.0 | 0.1 |
| Lumped | column | 78.39 / 95.56 | +11.0 / +15.4 | 0.2 |

### case 1b, spreader (2 mm, k 350, on 10 mm, k 10), cell 2.5 mm; printed centroids 56.55 / 59.94 degC (the paper prints the surface)
| model | read-out | centroids degC | shortfall paper - model, % of the paper rise (first source ... all) | seconds |
| :-- | :-- | :-- | :-- | --: |
| FEM | column | 56.51 / 59.89 | +0.1 / +0.1 | 51.4 |
| FEM | surface | 56.54 / 59.94 | +0.0 / +0.0 | 51.4 |
| FVM | column | 56.51 / 59.89 | +0.1 / +0.2 | 0.1 |
| FVM | surface | 56.54 / 59.93 | +0.0 / +0.0 | 0.1 |
| FDM | column | 56.47 / 59.86 | +0.2 / +0.2 | 0.1 |
| FDM | surface | 56.50 / 59.90 | +0.1 / +0.1 | 0.1 |
| 3D solid | - | not run: MemoryGuardError: the 3D solid (finite volumes) model would have 360000 unknowns and nee | | |
| Analytic | column | 56.51 / 59.89 | +0.1 / +0.2 | 0.1 |
| Analytic | surface | 56.54 / 59.93 | +0.0 / +0.0 | 0.1 |
| Lumped | column | 56.58 / 59.07 | -0.1 / +2.5 | 0.2 |

The Lumped has no surface map. A shortfall of the column read-out is the through-thickness term that one node per layer cannot hold (docs/validation.md 55.1).
