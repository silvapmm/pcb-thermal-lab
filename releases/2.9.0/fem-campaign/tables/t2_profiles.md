tree 0fbabbec, program 2.8.0; default stepping of the program (Crank-Nicolson with the Rannacher start)

### plate, slow wave: period 100 s, duty 0.5, 6 windows, cell 2 mm; part peak = hottest column cell under the part, last window
reference: FEM, 160 steps per period (8 times the rule), peak 244.6496 degC, swing 157.5945 K, 1.9 s
| model | steps per period | peak degC | (K vs ref) | swing K | (% of ref swing) | curve: largest difference, % of ref swing | run s |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| FEM | 20 | 244.1413 | -0.5082 | 156.5621 | -0.7 | 6.5 | 0.5 |
| FEM, 12 elements across a gap | 20 | 244.1508 | -0.4987 | 156.5786 | -0.6 | 6.4 | 1.4 |
| FVM | 20 | 243.6709 | -0.9787 | 155.8953 | -1.1 | 12.9 | 0.0 |
| FDM | 20 | 243.6181 | -1.0314 | 155.8320 | -1.1 | 12.9 | 0.0 |
| Lumped | 20 | 252.9312 | +8.2817 | 165.0522 | +4.7 | 13.4 | 0.0 |
| Analytic | 20 | 246.7801 | +2.1306 | 159.4234 | +1.2 | 1.6 | 0.1 |

### plate, fast wave (20 Hz): period 0.05 s, duty 0.3, 12 windows, cell 1 mm; part peak = hottest column cell under the part, last window
reference: FEM, 272 steps per period (8 times the rule), peak 113.1603 degC, swing 5.0083 K, 36.0 s
| model | steps per period | peak degC | (K vs ref) | swing K | (% of ref swing) | curve: largest difference, % of ref swing | run s |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| FEM | 34 | 113.0688 | -0.0915 | 4.8977 | -2.2 | 0.4 | 6.5 |
| FEM, 12 elements across a gap | 34 | 113.8361 | +0.6758 | 6.0734 | +21.3 | 15.0 | 16.3 |
| FVM | 34 | 110.9729 | -2.1874 | 0.7464 | -85.1 | 42.1 | 0.2 |
| FDM | 34 | 110.9689 | -2.1914 | 0.7464 | -85.1 | 42.2 | 0.2 |
| Lumped | 34 | 113.0571 | -0.1032 | 1.2621 | -74.8 | 72.7 | 0.0 |
| Analytic | 34 | 110.8056 | -2.3547 | 0.7465 | -85.1 | 45.5 | 0.4 |
independent reference of this wave (axisymmetric stack solver of research/fast-wave-oscillation README 1, quoted, not re-run): swing 6.3 K (the program's closed form of the decision 6.35 K against 6.37 K)

### example board, first part on a 20 s wave: period 20 s, duty 0.5, 4 windows, cell 2 mm; part peak = hottest column cell under the part, last window
reference: FEM, 160 steps per period (8 times the rule), peak 72.6325 degC, swing 29.9381 K, 38.9 s
| model | steps per period | peak degC | (K vs ref) | swing K | (% of ref swing) | curve: largest difference, % of ref swing | run s |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| FEM | 20 | 72.4734 | -0.1591 | 29.6278 | -1.0 | 7.7 | 21.0 |
| FVM | 20 | 74.2066 | +1.5741 | 31.3553 | +4.7 | 12.4 | 0.2 |
| FDM | 20 | 73.4707 | +0.8382 | 30.4876 | +1.8 | 12.1 | 0.1 |
| Lumped | 20 | 75.9997 | +3.3672 | 32.8371 | +9.7 | 13.9 | 0.1 |
| Analytic | 20 | 73.9355 | +1.3030 | 31.8369 | +6.3 | 4.4 | 2.5 |
