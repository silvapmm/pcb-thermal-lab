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

### T3b. board without copper (60 x 60 mm, laminate k 0.3 W/mK, rho c 1.665e+06 J/m3K, thickness 1.53 mm, 8 mm part), hottest column cell under the part (the top layer, here laminate; review: not the face), K/W
closed form z(t) = 2 sqrt(t/pi) / (e A), e = 706.8 W s^0.5/m2K, A = 64 mm2; holds for t below about 0.3 thickness^2/alpha = 3.9 s and while the penetration sqrt(alpha t) is below the source size
| nominal t s | sample t s | closed form | FEM 6 (%) | FEM 12 (%) | FVM (%) | FDM (%) |
| --: | --: | --: | --: | --: | --: | --: |
| 0.1 | 0.104 | 8.039 | 6.901 (-14.2) | 7.127 (-11.3) | 3.902 (-51.5) | 3.902 (-51.5) |
| 0.3 | 0.312 | 13.924 | 12.758 (-8.4) | 12.920 (-7.2) | 9.905 (-28.9) | 9.905 (-28.9) |
| 1 | 0.935 | 24.117 | 22.775 (-5.6) | 22.902 (-5.0) | 21.119 (-12.4) | 21.119 (-12.4) |
| 3 | 2.8 | 41.772 | 39.665 (-5.0) | 39.757 (-4.8) | 38.797 (-7.1) | 38.797 (-7.1) |
| 10 | 10.5 | 80.891 | 72.898 (-9.9) | 72.997 (-9.8) | 72.864 (-9.9) | 72.864 (-9.9) |

Review, tree 721bf828 (the program of 7886ac42), `study_compare_t3.py --part b` (the T3b rows above reproduced to the digit):

#### T3c. the same runs against the closed form of the read-out (review): mean over the top 35 um layer, top film h 10 W/m2K, in-plane k 0.9 W/mK
each factor is a ratio to the plain face value: layer mean = mean of 2 q sqrt(alpha t)/k ierfc(z / 2 sqrt(alpha t)) over 0 < z < t_cu (Carslaw and Jaeger 2.9); film = (1 - exp(b^2) erfc(b)) / (2 b / sqrt(pi)) with b = h sqrt(t)/e (Lienhard eqn 5.56 family); spreading = the centre of a square source on an anisotropic half-space, integral of erf(a / (4 sqrt(alpha_in s)))^2 / sqrt(s) over s against the same integral without it
| nominal t s | sample t s | layer mean | film | spreading | reference | FEM 6 (%) | FEM 12 (%) | FVM (%) | FDM (%) |
| --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| 0.1 | 0.104 | 0.8921 | 0.9960 | 1.0000 | 7.142 | 6.901 (-3.38) | 7.127 (-0.21) | 3.902 (-45.37) | 3.902 (-45.37) |
| 0.3 | 0.312 | 0.9364 | 0.9930 | 1.0000 | 12.947 | 12.758 (-1.46) | 12.920 (-0.21) | 9.905 (-23.49) | 9.905 (-23.49) |
| 1 | 0.935 | 0.9628 | 0.9880 | 1.0000 | 22.941 | 22.775 (-0.72) | 22.902 (-0.17) | 21.119 (-7.94) | 21.119 (-7.94) |
| 3 | 2.8 | 0.9784 | 0.9794 | 0.9949 | 39.822 | 39.665 (-0.39) | 39.757 (-0.16) | 38.797 (-2.57) | 38.797 (-2.57) |
