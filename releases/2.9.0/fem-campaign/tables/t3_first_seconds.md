tree 0fbabbec, program 2.8.0

### T3a. plate_uniform, 8 mm part of 5 W, response cell 2 mm; hottest column cell under the part, K/W at the sample time nearest to the nominal time; % = model against the FEM (6 gap elements)
| nominal t s | sample t s (FEM) | FEM 6 gap elements | FEM 12 gap elements (% vs 6) | FVM (%) | FDM (%) | Lumped (%) | Analytic (%) |
| --: | --: | --: | --: | --: | --: | --: | --: |
| 0.1 | 0.113 | 4.137 | 4.197 (+1.4) | 1.235 (-70.2) | 1.235 (-70.2) | 1.692 (-59.1) | 1.254 (-69.7) |
| 0.3 | 0.34 | 6.493 | 6.519 (+0.4) | 3.319 (-48.9) | 3.319 (-48.9) | 3.901 (-39.9) | 3.401 (-47.6) |
| 1 | 1.02 | 9.067 | 9.079 (+0.1) | 7.089 (-21.8) | 7.089 (-21.8) | 7.556 (-16.7) | 7.151 (-21.1) |
| 3 | 3.06 | 11.772 | 11.776 (+0.0) | 11.422 (-3.0) | 11.422 (-3.0) | 11.842 (+0.6) | 11.429 (-2.9) |
| 10 | 9.18 | 14.559 | 14.559 (+0.0) | 15.006 (+3.1) | 15.006 (+3.1) | 15.494 (+6.4) | 14.996 (+3.0) |

plateau K/W: FEM 26.281, FVM 26.810, FDM 26.810, Lumped 27.326, Analytic 26.816, FEM 12 gap elements 26.282

### T3b. board without copper (60 x 60 mm, laminate k 0.3 W/mK, rho c 1.665e+06 J/m3K, thickness 1.53 mm, 8 mm part), surface of the part, K/W
closed form z(t) = 2 sqrt(t/pi) / (e A), e = 706.8 W s^0.5/m2K, A = 64 mm2; holds for t below about 0.3 thickness^2/alpha = 3.9 s and while the penetration sqrt(alpha t) is below the source size
| nominal t s | sample t s | closed form | FEM 6 (%) | FEM 12 (%) | FVM (%) | FDM (%) |
| --: | --: | --: | --: | --: | --: | --: |
| 0.1 | 0.104 | 8.039 | 6.901 (-14.2) | 7.127 (-11.3) | 3.902 (-51.5) | 3.902 (-51.5) |
| 0.3 | 0.312 | 13.924 | 12.758 (-8.4) | 12.920 (-7.2) | 9.905 (-28.9) | 9.905 (-28.9) |
| 1 | 0.935 | 24.117 | 22.775 (-5.6) | 22.902 (-5.0) | 21.119 (-12.4) | 21.119 (-12.4) |
| 3 | 2.8 | 41.772 | 39.665 (-5.0) | 39.757 (-4.8) | 38.797 (-7.1) | 38.797 (-7.1) |
| 10 | 10.5 | 80.891 | 72.898 (-9.9) | 72.997 (-9.8) | 72.864 (-9.9) | 72.864 (-9.9) |


