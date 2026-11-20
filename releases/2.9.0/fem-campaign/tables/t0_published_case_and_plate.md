tree 0fbabbec
== Part A: NAFEMS T3 (36.60 degC at x = 0.08 m, t = 32 s)
A1 exact series (4000 / 20000 terms): 36.603116 / 36.603116 degC; published 36.6; difference +0.0031
A1b method of lines (Radau, tol 1e-11), 200 / 400 intervals: 36.601236 / 36.602646; Richardson limit 36.603116 degC (independent of the series)
A2 FEM, Crank-Nicolson, 3200 steps, elements -> T(0.08, 32), error vs exact
   n=  20    36.7969   +0.1938
   n=  50    36.6333   +0.0302
   n= 100    36.6106   +0.0075
   n= 200    36.6050   +0.0019
   n= 400    36.6036   +0.0005
A3 FEM, n = 100, steps -> CN and implicit Euler
   steps=  100  CN   36.6090 ( +0.0059)   Euler   36.4515 ( -0.1516)
   steps=  400  CN   36.6105 ( +0.0074)   Euler   36.5708 ( -0.0323)
   steps= 1600  CN   36.6106 ( +0.0075)   Euler   36.6007 ( -0.0024)
   steps= 3200  CN   36.6106 ( +0.0075)   Euler   36.6057 ( +0.0025)
A4 FEM, n = 100, 3200 steps, held end as film h
   h=   1e+04    30.2580   -6.3451
   h=   1e+06    36.5408   -0.0623
   h=   1e+10    36.6106   +0.0075
A5 published mesh results, 5 / 10 linear elements, 32 implicit-Euler steps of 1 s
   n=  5  MOOSE EDGE2 40.280676: program FEM 40.280668 (-8.2e-06), own 1D consistent 40.280676;  Abaqus DC1D2 34.54: own 1D lumped 34.5383
   n= 10  MOOSE EDGE2 36.893145: program FEM 36.893138 (-7.1e-06), own 1D consistent 36.893145;  Abaqus DC1D2 35.51: own 1D lumped 35.5063
== Part B: plate with held edges and a power step, centre temperature against the exact double series (default stepping of 2.9.0, the FEM added)
B0 plate 0.1 m square, 1 mm, k 35, rho c 3.172e+06, P 10.0 W, edge film 1e+05 W/m2K, slowest-mode tau 45.9 s, run to 92 s, 20 frames, default stepping
   largest relative error of the centre column temperature over the frames after 10 s, against the exact Robin double series
| model | 5 mm | 2.5 mm | 1.25 mm |
| :-- | --: | --: | --: |
| FVM | 0.54 % | 0.46 % | 0.43 % |
| FDM | 0.31 % | 0.36 % | 0.41 % |
| FEM | 0.32 % | 0.40 % | 0.42 % |
| Analytic | 0.00 % | 0.01 % | 0.01 % |

Review (`study_compare_t0.py --stepping`):

tree 721bf828
B1 (review) the same plate: default stepping against 40 linear frames of 16 steps, largest error after 10 s [%] (time of it)
| model | cell mm | default | linear 40 x 16 |
| :-- | --: | --: | --: |
| FVM | 2.5 | +0.456 (91.8 s) | -0.036 (23.0 s) |
| FVM | 1.25 | +0.435 (91.8 s) | -0.013 (23.0 s) |
| FDM | 2.5 | +0.363 (91.8 s) | -0.080 (41.3 s) |
| FDM | 1.25 | +0.412 (91.8 s) | -0.023 (39.0 s) |
| FEM | 2.5 | +0.398 (68.8 s) | -0.034 (91.8 s) |
