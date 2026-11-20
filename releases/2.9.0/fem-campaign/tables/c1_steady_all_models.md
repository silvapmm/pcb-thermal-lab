Tree 9d1ebb1e, program 2.8.0, harness `tests/regression/regress_harness.py`, steady runs, `macOS-27.2.1-arm64-arm-64bit-Mach-O`.

### Hottest column rise [K] and difference to the FEM [% of the FEM rise], cell 2 mm

| board | FVM | FDM | Lumped | Analytic | 3D solid | FEM |
| :-- | --: | --: | --: | --: | --: | --: |
| example_board | 60.293 (+2.8) | 59.623 (+1.7) | 61.905 (+5.6) | 59.796 (+2.0) | 60.483 (+3.1) | 58.639 |
| profile_board | 60.293 (+2.8) | 59.623 (+1.7) | 61.905 (+5.6) | 59.796 (+2.0) | 60.483 (+3.1) | 58.639 |
| reference_board | 65.069 (+0.3) | 65.068 (+0.3) | 65.794 (+1.4) | 65.090 (+0.3) | 65.200 (+0.5) | 64.899 |
| example_cut_to_T | 69.669 (+2.9) | 69.101 (+2.0) | 69.390 (+2.5) | 66.109 (-2.4) | 69.129 (+2.1) | 67.714 |
| plate_uniform | 134.052 (+2.0) | 134.052 (+2.0) | 136.629 (+4.0) | 134.082 (+2.0) | 134.251 (+2.2) | 131.407 |
| plate_pad | 337.607 (+7.5) | 311.304 (-0.9) | 283.578 (-9.7) | 145.997 (-53.5) | 347.761 (+10.7) | 314.061 |
| plate_vias | 112.815 (+3.9) | 108.504 (-0.1) | 111.139 (+2.3) | 110.940 (+2.1) | 111.869 (+3.0) | 108.626 |
| plate_lone_via | 126.569 (+2.1) | 123.747 (-0.1) | 130.634 (+5.4) | 125.369 (+1.2) | 128.354 (+3.6) | 123.916 |
| round_outline | 150.022 (-) | 150.020 (-) | 155.801 (-) | 150.329 (-) | 150.636 (-) | skipped |
| t_outline | 162.209 (+0.7) | 161.387 (+0.2) | 110.810 (-31.2) | 111.772 (-30.6) | 162.320 (+0.8) | 161.083 |
| two_layer_partial | 137.808 (+1.1) | 138.131 (+1.4) | 137.317 (+0.8) | 127.713 (-6.3) | 138.082 (+1.3) | 136.280 |
| one_layer_full | 30.355 (+2.3) | 30.355 (+2.3) | 30.938 (+4.2) | 30.280 (+2.0) | 30.363 (+2.3) | 29.680 |
| one_layer_pad | 70.565 (+8.1) | 64.683 (-0.9) | 62.417 (-4.4) | 45.863 (-29.8) | 72.012 (+10.3) | 65.303 |
| finned_block | 104.687 (+0.6) | 104.683 (+0.6) | 107.798 (+3.6) | 104.826 (+0.7) | 105.251 (+1.1) | 104.099 |
| part_top_path | 49.711 (+2.2) | 47.940 (-1.4) | 48.056 (-1.2) | 44.222 (-9.1) | 50.091 (+3.0) | 48.643 |
| hatched_copper | 87.012 (+1.3) | 87.008 (+1.3) | 90.691 (+5.5) | 86.503 (+0.7) | 86.941 (+1.2) | 85.934 |
| part_across_outline | 204.398 (+1.0) | 205.751 (+1.7) | 183.103 (-9.5) | 183.928 (-9.1) | 204.482 (+1.1) | 202.275 |
| drawn_inset_square | 58.184 (+4.0) | 60.642 (+8.4) | 53.040 (-5.2) | 51.362 (-8.2) | 55.777 (-0.3) | 55.958 |
| drawn_stripes_pad | 76.585 (+7.2) | 75.512 (+5.7) | 56.720 (-20.6) | 57.198 (-19.9) | 59.981 (-16.0) | 71.414 |
| drawn_ell | 67.786 (+5.2) | 74.325 (+15.4) | 56.624 (-12.1) | 54.686 (-15.1) | 62.428 (-3.1) | 64.425 |

### Hottest column rise [K] and difference to the FEM [% of the FEM rise], cell 1 mm

| board | FVM | FDM | Lumped | Analytic | 3D solid | FEM |
| :-- | --: | --: | --: | --: | --: | --: |
| example_board | 60.465 (+1.3) | 60.400 (+1.2) | 61.905 (+3.7) | 59.796 (+0.2) | 60.975 (+2.2) | 59.687 |
| profile_board | 60.465 (+1.3) | 60.400 (+1.2) | 61.905 (+3.7) | 59.796 (+0.2) | 60.975 (+2.2) | 59.687 |
| reference_board | 65.136 (-0.1) | 65.135 (-0.1) | 65.794 (+0.9) | 65.090 (-0.2) | 65.267 (+0.1) | 65.191 |
| example_cut_to_T | 69.742 (+1.4) | 69.619 (+1.2) | 69.390 (+0.9) | 66.109 (-3.9) | 69.838 (+1.5) | 68.774 |
| plate_uniform | 134.516 (+0.4) | 134.516 (+0.4) | 136.629 (+2.0) | 134.082 (+0.1) | 134.718 (+0.5) | 134.006 |
| plate_pad | 328.384 (+2.6) | 317.510 (-0.8) | 283.578 (-11.4) | 145.997 (-54.4) | 335.493 (+4.8) | 320.087 |
| plate_vias | 110.682 (+0.9) | 112.310 (+2.4) | 111.139 (+1.3) | 110.940 (+1.2) | 110.395 (+0.7) | 109.673 |
| plate_lone_via | 125.432 (+0.5) | 124.918 (+0.1) | 130.634 (+4.6) | 125.369 (+0.4) | 127.345 (+2.0) | 124.855 |
| round_outline | 150.460 (-) | 150.462 (-) | 155.801 (-) | 150.329 (-) | 151.091 (-) | skipped |
| t_outline | 161.987 (+0.1) | 161.630 (-0.1) | 110.810 (-31.5) | 111.772 (-30.9) | 162.168 (+0.2) | 161.793 |
| two_layer_partial | 138.474 (+0.5) | 137.919 (+0.1) | 137.317 (-0.4) | 127.713 (-7.3) | 138.969 (+0.8) | 137.827 |
| one_layer_full | 30.441 (+0.5) | 30.441 (+0.5) | 30.938 (+2.2) | 30.280 (+0.0) | 30.450 (+0.6) | 30.278 |
| one_layer_pad | 68.716 (+2.7) | 66.287 (-0.9) | 62.417 (-6.7) | 45.863 (-31.4) | 69.925 (+4.5) | 66.883 |
| finned_block | 104.941 (-0.3) | 104.939 (-0.3) | 107.798 (+2.5) | 104.826 (-0.4) | 105.504 (+0.3) | 105.211 |
| part_top_path | 49.099 (+0.6) | 48.679 (-0.3) | 48.056 (-1.6) | 44.222 (-9.4) | 49.484 (+1.4) | 48.820 |
| hatched_copper | 87.240 (+0.4) | 87.239 (+0.4) | 90.691 (+4.4) | 86.503 (-0.5) | 87.168 (+0.3) | 86.910 |
| part_across_outline | 204.829 (+0.2) | 205.414 (+0.5) | 183.103 (-10.5) | 183.928 (-10.1) | 205.133 (+0.3) | 204.491 |
| drawn_inset_square | 59.186 (+1.4) | 59.581 (+2.1) | 53.040 (-9.1) | 51.362 (-12.0) | 60.238 (+3.2) | 58.372 |
| drawn_stripes_pad | 75.449 (+1.3) | 75.459 (+1.3) | 56.720 (-23.8) | 57.198 (-23.2) | 73.020 (-1.9) | 74.454 |
| drawn_ell | 99.035 (+17.8) | 66.955 (-20.3) | 56.624 (-32.6) | 54.686 (-34.9) | 113.831 (+35.4) | 84.056 |

### Hottest column rise [K] and difference to the FEM [% of the FEM rise], cell 0.5 mm

| board | FVM | FDM | Lumped | Analytic | 3D solid | FEM |
| :-- | --: | --: | --: | --: | --: | --: |
| example_board | 60.412 (-) | 60.377 (-) | 61.443 (-) | 59.913 (-) | skipped | skipped |
| profile_board | 60.412 (-) | 60.377 (-) | 61.443 (-) | 59.913 (-) | skipped | skipped |
| reference_board | 65.153 (-) | 65.153 (-) | 64.924 (-) | 65.140 (-) | skipped | skipped |
| example_cut_to_T | 69.669 (-) | 69.607 (-) | 68.681 (-) | 66.143 (-) | skipped | skipped |
| plate_uniform | 134.637 (-0.0) | 134.637 (-0.0) | 134.788 (+0.1) | 134.528 (-0.1) | 134.839 (+0.1) | 134.659 |
| plate_pad | 324.600 (+0.5) | 320.625 (-0.7) | 277.925 (-13.9) | 146.534 (-54.6) | 330.066 (+2.2) | 322.874 |
| plate_vias | 111.319 (+0.4) | 111.414 (+0.5) | 111.139 (+0.3) | 111.113 (+0.2) | 111.353 (+0.5) | 110.850 |
| plate_lone_via | 125.290 (-0.1) | 125.104 (-0.2) | 128.914 (+2.8) | 125.490 (+0.1) | 126.346 (+0.8) | 125.377 |
| round_outline | 150.576 (-) | 150.575 (-) | 151.219 (-) | 150.895 (-) | 151.211 (-) | skipped |
| t_outline | 161.870 (-0.1) | 161.721 (-0.1) | 109.888 (-32.1) | 111.817 (-31.0) | skipped | 161.956 |
| two_layer_partial | 138.337 (+0.1) | 138.165 (-0.1) | 135.766 (-1.8) | 127.939 (-7.5) | skipped | 138.265 |
| one_layer_full | 30.464 (+0.1) | 30.464 (+0.1) | 30.388 (-0.1) | 30.380 (-0.2) | 30.472 (+0.1) | 30.429 |
| one_layer_pad | 67.934 (+0.6) | 67.062 (-0.7) | 60.657 (-10.1) | 46.071 (-31.8) | 68.957 (+2.1) | 67.507 |
| finned_block | 105.005 (-0.5) | 105.005 (-0.5) | 105.018 (-0.4) | 105.018 (-0.4) | 105.560 (+0.1) | 105.491 |
| part_top_path | 48.966 (-0.0) | 48.831 (-0.3) | 47.651 (-2.7) | 44.337 (-9.5) | 49.309 (+0.7) | 48.986 |
| hatched_copper | 87.298 (+0.2) | 87.298 (+0.2) | 87.120 (-0.0) | 86.670 (-0.6) | 87.226 (+0.1) | 87.155 |
| part_across_outline | 204.764 (-0.1) | 204.835 (-0.1) | 175.814 (-14.2) | 183.919 (-10.3) | 205.136 (+0.1) | 204.941 |
| drawn_inset_square | 58.872 (-0.8) | 59.247 (-0.1) | 53.202 (-10.3) | 51.768 (-12.7) | 59.497 (+0.3) | 59.320 |
| drawn_stripes_pad | 74.932 (-1.0) | 75.154 (-0.7) | 58.345 (-22.9) | 57.852 (-23.5) | 76.107 (+0.6) | 75.671 |
| drawn_ell | 87.681 (-8.0) | 86.844 (-8.9) | 56.547 (-40.7) | 55.166 (-42.1) | 100.811 (+5.8) | 95.325 |

### Largest and mean absolute difference of the hottest column rise [% of the reference rise], over the boards where both numbers exist

| cell mm | model | against | boards | mean abs | largest abs (board) | signed range |
| --: | :-- | :-- | --: | --: | :-- | :-- |
| 2 | FVM | FEM | 19 | 3.05 | 8.06 (one_layer_pad) | +0.3 to +8.1 |
| 2 | FDM | FEM | 19 | 2.53 | 15.37 (drawn_ell) | -1.4 to +15.4 |
| 2 | Lumped | FEM | 19 | 7.09 | 31.21 (t_outline) | -31.2 to +5.6 |
| 2 | Analytic | FEM | 19 | 10.36 | 53.51 (plate_pad) | -53.5 to +2.1 |
| 2 | 3D solid | FEM | 19 | 3.62 | 16.01 (drawn_stripes_pad) | -16.0 to +10.7 |
| 2 | FVM | 3D solid | 20 | 2.58 | 27.68 (drawn_stripes_pad) | -2.9 to +27.7 |
| 2 | FDM | 3D solid | 20 | 4.54 | 25.89 (drawn_stripes_pad) | -10.5 to +25.9 |
| 2 | Lumped | 3D solid | 20 | 6.02 | 31.73 (t_outline) | -31.7 to +4.3 |
| 2 | Analytic | 3D solid | 20 | 9.56 | 58.02 (plate_pad) | -58.0 to -0.1 |
| 2 | FEM | 3D solid | 19 | 3.64 | 19.06 (drawn_stripes_pad) | -9.7 to +19.1 |
| 1 | FVM | FEM | 19 | 1.80 | 17.82 (drawn_ell) | -0.3 to +17.8 |
| 1 | FDM | FEM | 19 | 1.79 | 20.34 (drawn_ell) | -20.3 to +2.4 |
| 1 | Lumped | FEM | 19 | 8.09 | 32.64 (drawn_ell) | -32.6 to +4.6 |
| 1 | Analytic | FEM | 19 | 11.61 | 54.39 (plate_pad) | -54.4 to +1.2 |
| 1 | 3D solid | FEM | 19 | 3.31 | 35.42 (drawn_ell) | -1.9 to +35.4 |
| 1 | FVM | 3D solid | 20 | 1.41 | 13.00 (drawn_ell) | -13.0 to +3.3 |
| 1 | FDM | 3D solid | 20 | 3.31 | 41.18 (drawn_ell) | -41.2 to +3.3 |
| 1 | Lumped | 3D solid | 20 | 8.87 | 50.26 (drawn_ell) | -50.3 to +4.0 |
| 1 | Analytic | 3D solid | 20 | 12.69 | 56.48 (plate_pad) | -56.5 to +0.5 |
| 1 | FEM | 3D solid | 19 | 2.79 | 26.16 (drawn_ell) | -26.2 to +2.0 |
| 0.5 | FVM | FEM | 15 | 0.83 | 8.02 (drawn_ell) | -8.0 to +0.6 |
| 0.5 | FDM | FEM | 15 | 0.88 | 8.90 (drawn_ell) | -8.9 to +0.5 |
| 0.5 | Lumped | FEM | 15 | 10.18 | 40.68 (drawn_ell) | -40.7 to +2.8 |
| 0.5 | Analytic | FEM | 15 | 14.97 | 54.62 (plate_pad) | -54.6 to +0.2 |
| 0.5 | 3D solid | FEM | 13 | 1.03 | 5.76 (drawn_ell) | +0.1 to +5.8 |
| 0.5 | FVM | 3D solid | 14 | 1.55 | 13.02 (drawn_ell) | -13.0 to +0.1 |
| 0.5 | FDM | 3D solid | 14 | 1.75 | 13.85 (drawn_ell) | -13.9 to +0.1 |
| 0.5 | Lumped | 3D solid | 14 | 9.04 | 43.91 (drawn_ell) | -43.9 to +2.0 |
| 0.5 | Analytic | 3D solid | 14 | 13.88 | 55.60 (plate_pad) | -55.6 to -0.2 |
| 0.5 | FEM | 3D solid | 13 | 1.00 | 5.44 (drawn_ell) | -5.4 to -0.1 |

### Mean column rise under the first part [K] and difference to the FEM [% of the FEM value], cell 1 mm (the 'part mean' read-out of `analysis.heater_stats`)

| board | FVM | FDM | Lumped | Analytic | 3D solid | FEM |
| :-- | --: | --: | --: | --: | --: | --: |
| example_board | 55.256 (+1.4) | 54.892 (+0.7) | 56.500 (+3.6) | 54.573 (+0.1) | 54.857 (+0.6) | 54.515 |
| profile_board | 55.256 (+1.4) | 54.892 (+0.7) | 56.500 (+3.6) | 54.573 (+0.1) | 54.857 (+0.6) | 54.515 |
| reference_board | 56.231 (+0.0) | 56.079 (-0.3) | 56.603 (+0.7) | 56.169 (-0.1) | 56.330 (+0.2) | 56.230 |
| example_cut_to_T | 64.255 (+1.2) | 63.830 (+0.6) | 63.793 (+0.5) | 62.607 (-1.4) | 63.841 (+0.6) | 63.479 |
| plate_uniform | 122.840 (+0.5) | 121.622 (-0.5) | 124.794 (+2.1) | 122.344 (+0.1) | 122.998 (+0.7) | 122.202 |
| plate_pad | 317.345 (+2.7) | 305.258 (-1.2) | 272.143 (-11.9) | 132.894 (-57.0) | 324.435 (+5.0) | 308.885 |
| plate_vias | 104.919 (+1.2) | 104.113 (+0.4) | 104.609 (+0.9) | 104.667 (+0.9) | 104.693 (+1.0) | 103.702 |
| plate_lone_via | 116.959 (+0.4) | 115.768 (-0.6) | 119.530 (+2.6) | 116.494 (+0.0) | 117.254 (+0.7) | 116.487 |
| round_outline | 139.164 (-) | 137.987 (-) | 144.397 (-) | 142.220 (-) | 139.658 (-) | - |
| t_outline | 152.744 (+0.2) | 152.860 (+0.3) | 102.038 (-33.1) | 107.095 (-29.7) | 152.856 (+0.3) | 152.445 |
| two_layer_partial | 125.683 (+0.6) | 124.525 (-0.4) | 124.343 (-0.5) | 114.051 (-8.7) | 126.189 (+1.0) | 124.969 |
| one_layer_full | 27.831 (+0.6) | 27.563 (-0.3) | 28.315 (+2.4) | 27.670 (+0.1) | 27.838 (+0.7) | 27.655 |
| one_layer_pad | 66.265 (+2.9) | 63.574 (-1.3) | 59.925 (-7.0) | 40.903 (-36.5) | 67.479 (+4.8) | 64.413 |
| finned_block | 93.119 (-0.1) | 92.570 (-0.7) | 95.824 (+2.8) | 92.944 (-0.3) | 93.551 (+0.4) | 93.194 |
| part_top_path | 46.883 (+0.8) | 45.978 (-1.2) | 45.689 (-1.8) | 40.795 (-12.3) | 47.280 (+1.6) | 46.517 |
| hatched_copper | 77.237 (+1.3) | 76.678 (+0.6) | 80.053 (+5.0) | 75.984 (-0.3) | 77.177 (+1.2) | 76.240 |
| part_across_outline | 187.483 (+0.2) | 186.614 (-0.2) | 171.562 (-8.3) | 169.969 (-9.1) | 187.844 (+0.4) | 187.067 |
| drawn_inset_square | 57.217 (+1.6) | 56.610 (+0.5) | 51.042 (-9.4) | 49.142 (-12.8) | 58.232 (+3.4) | 56.327 |
| drawn_stripes_pad | 73.465 (+1.4) | 72.574 (+0.2) | 54.740 (-24.4) | 54.227 (-25.1) | 70.795 (-2.3) | 72.432 |
| drawn_ell | 64.887 (+2.9) | 61.386 (-2.7) | 54.444 (-13.7) | 52.040 (-17.5) | 66.763 (+5.9) | 63.070 |

### Summary against the FEM by group of boards: mean of the absolute differences and the largest (board), signed range, [% of the FEM value]

| group | cell mm | model | read-out | boards | mean abs | largest abs (board) | signed range |
| :-- | --: | :-- | :-- | --: | --: | :-- | :-- |
| all | 1 | FVM | peak | 19 | 1.80 | 17.82 (drawn_ell) | -0.3 to +17.8 |
| all | 1 | FVM | part mean | 19 | 1.12 | 2.88 (drawn_ell) | -0.1 to +2.9 |
| all | 1 | FDM | peak | 19 | 1.79 | 20.34 (drawn_ell) | -20.3 to +2.4 |
| all | 1 | FDM | part mean | 19 | 0.69 | 2.67 (drawn_ell) | -2.7 to +0.7 |
| all | 1 | 3D solid | peak | 19 | 3.31 | 35.42 (drawn_ell) | -1.9 to +35.4 |
| all | 1 | 3D solid | part mean | 19 | 1.64 | 5.86 (drawn_ell) | -2.3 to +5.9 |
| all | 0.5 | FVM | peak | 15 | 0.83 | 8.02 (drawn_ell) | -8.0 to +0.6 |
| all | 0.5 | FVM | part mean | 15 | 0.40 | 1.00 (drawn_ell) | -1.0 to +1.0 |
| all | 0.5 | FDM | peak | 15 | 0.88 | 8.90 (drawn_ell) | -8.9 to +0.5 |
| all | 0.5 | FDM | part mean | 15 | 0.60 | 2.76 (drawn_ell) | -2.8 to +0.8 |
| all | 0.5 | 3D solid | peak | 13 | 1.03 | 5.76 (drawn_ell) | +0.1 to +5.8 |
| all | 0.5 | 3D solid | part mean | 13 | 0.72 | 2.33 (plate_pad) | +0.1 to +2.3 |
| without the three drawn boards | 1 | FVM | peak | 16 | 0.86 | 2.74 (one_layer_pad) | -0.3 to +2.7 |
| without the three drawn boards | 1 | FVM | part mean | 16 | 0.97 | 2.88 (one_layer_pad) | -0.1 to +2.9 |
| without the three drawn boards | 1 | FDM | peak | 16 | 0.64 | 2.40 (plate_vias) | -0.9 to +2.4 |
| without the three drawn boards | 1 | FDM | part mean | 16 | 0.61 | 1.30 (one_layer_pad) | -1.3 to +0.7 |
| without the three drawn boards | 1 | 3D solid | peak | 16 | 1.40 | 4.81 (plate_pad) | +0.1 to +4.8 |
| without the three drawn boards | 1 | 3D solid | part mean | 16 | 1.23 | 5.03 (plate_pad) | +0.2 to +5.0 |
| without the three drawn boards | 0.5 | FVM | peak | 12 | 0.22 | 0.63 (one_layer_pad) | -0.5 to +0.6 |
| without the three drawn boards | 0.5 | FVM | part mean | 12 | 0.28 | 0.99 (hatched_copper) | -0.4 to +1.0 |
| without the three drawn boards | 0.5 | FDM | peak | 12 | 0.29 | 0.70 (plate_pad) | -0.7 to +0.5 |
| without the three drawn boards | 0.5 | FDM | part mean | 12 | 0.40 | 0.80 (plate_pad) | -0.8 to +0.8 |
| without the three drawn boards | 0.5 | 3D solid | peak | 10 | 0.68 | 2.23 (plate_pad) | +0.1 to +2.2 |
| without the three drawn boards | 0.5 | 3D solid | part mean | 10 | 0.73 | 2.33 (plate_pad) | +0.1 to +2.3 |
| without the drawn and the pad boards | 1 | FVM | peak | 14 | 0.60 | 1.41 (example_cut_to_T) | -0.3 to +1.4 |
| without the drawn and the pad boards | 1 | FVM | part mean | 14 | 0.70 | 1.36 (example_board) | -0.1 to +1.4 |
| without the drawn and the pad boards | 1 | FDM | peak | 14 | 0.62 | 2.40 (plate_vias) | -0.3 to +2.4 |
| without the drawn and the pad boards | 1 | FDM | part mean | 14 | 0.52 | 1.16 (part_top_path) | -1.2 to +0.7 |
| without the drawn and the pad boards | 1 | 3D solid | peak | 14 | 0.93 | 2.16 (example_board) | +0.1 to +2.2 |
| without the drawn and the pad boards | 1 | 3D solid | part mean | 14 | 0.70 | 1.64 (part_top_path) | +0.2 to +1.6 |
| without the drawn and the pad boards | 0.5 | FVM | peak | 10 | 0.15 | 0.46 (finned_block) | -0.5 to +0.4 |
| without the drawn and the pad boards | 0.5 | FVM | part mean | 10 | 0.21 | 0.99 (hatched_copper) | -0.4 to +1.0 |
| without the drawn and the pad boards | 0.5 | FDM | peak | 10 | 0.21 | 0.51 (plate_vias) | -0.5 to +0.5 |
| without the drawn and the pad boards | 0.5 | FDM | part mean | 10 | 0.32 | 0.79 (hatched_copper) | -0.5 to +0.8 |
| without the drawn and the pad boards | 0.5 | 3D solid | peak | 8 | 0.30 | 0.77 (plate_lone_via) | +0.1 to +0.8 |
| without the drawn and the pad boards | 0.5 | 3D solid | part mean | 8 | 0.34 | 0.91 (hatched_copper) | +0.1 to +0.9 |

### Against the independent layered 3D solver (`tests/helpers/layered3d.py`, the same cell as the model), rise of the hottest top-copper cell under the source [% of the reference rise]

| board | cell mm | reference K | FVM | FDM | Lumped | Analytic | 3D solid | FEM |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: |
| plate_uniform | 2 | 134.251 | -0.1 | -0.1 | +1.8 | -0.1 | +0.0 | -2.1 |
| plate_uniform | 1 | 134.718 | -0.1 | -0.1 | +1.4 | -0.5 | +0.0 | -0.5 |
| plate_uniform | 0.5 | 134.839 | -0.1 | -0.1 | -0.0 | -0.2 | +0.0 | -0.1 |
| plate_pad | 2 | 347.761 | -2.9 | -10.5 | -18.5 | -58.0 | +0.0 | -9.7 |
| plate_pad | 1 | 335.493 | -2.1 | -5.4 | -15.5 | -56.5 | +0.0 | -4.6 |
| plate_pad | 0.5 | 330.066 | -1.7 | -2.9 | -15.8 | -55.6 | +0.0 | -2.2 |
| one_layer_full | 2 | 30.363 | -0.0 | -0.0 | +1.9 | -0.3 | +0.0 | -2.3 |
| one_layer_full | 1 | 30.450 | -0.0 | -0.0 | +1.6 | -0.6 | +0.0 | -0.6 |
| one_layer_full | 0.5 | 30.472 | -0.0 | -0.0 | -0.3 | -0.3 | +0.0 | -0.1 |
| one_layer_pad | 2 | 72.012 | -2.0 | -10.2 | -13.3 | -36.3 | +0.0 | -9.3 |
| one_layer_pad | 1 | 69.925 | -1.7 | -5.2 | -10.7 | -34.4 | +0.0 | -4.4 |
| one_layer_pad | 0.5 | 68.957 | -1.5 | -2.7 | -12.0 | -33.2 | +0.0 | -2.1 |

### Limit of the cell sequence 2, 1, 0.5 mm of the hottest column rise [K] (Richardson with the observed order p in brackets; '-' where a cell is skipped or the sequence is not monotone with an order between 0.3 and 3)

| board | FVM | FDM | 3D solid | FEM | layered 3D reference (four boards) |
| :-- | --: | --: | --: | --: | --: |
| example_board | - | - | - | - | - |
| profile_board | - | - | - | - | - |
| reference_board | 65.16 (2.0) | 65.16 (2.0) | - | - | - |
| example_cut_to_T | - | - | - | - | - |
| plate_uniform | 134.68 (1.9) | 134.68 (1.9) | 134.88 (1.9) | 134.88 (2.0) | 134.88 (1.9) |
| plate_pad | 321.97 (1.3) | 323.76 (1.0) | 325.76 (1.2) | 325.27 (1.1) | 325.76 (1.2) |
| plate_vias | - | - | - | - | - |
| plate_lone_via | 125.27 (3.0) | 125.14 (2.7) | - | 126.03 (0.8) | - |
| round_outline | 150.62 (1.9) | 150.61 (2.0) | 151.26 (1.9) | - | - |
| t_outline | 161.74 (0.9) | 161.78 (1.4) | - | 162.00 (2.1) | - |
| two_layer_partial | - | - | - | 138.44 (1.8) | - |
| one_layer_full | 30.47 (1.9) | 30.47 (1.9) | 30.48 (1.9) | 30.48 (2.0) | 30.48 (1.9) |
| one_layer_pad | 67.36 (1.2) | 67.79 (1.0) | 68.12 (1.1) | 67.91 (1.3) | 68.12 (1.1) |
| finned_block | 105.03 (2.0) | 105.03 (2.0) | 105.58 (2.2) | 105.59 (2.0) | - |
| part_top_path | 48.93 (2.2) | 48.87 (2.3) | 49.24 (1.8) | - | - |
| hatched_copper | 87.32 (2.0) | 87.32 (2.0) | 87.25 (2.0) | 87.24 (2.0) | - |
| part_across_outline | - | - | - | 205.06 (2.3) | - |
| drawn_inset_square | - | 59.09 (1.7) | - | 59.93 (1.3) | - |
| drawn_stripes_pad | 74.50 (1.1) | - | 77.07 (2.1) | 76.48 (1.3) | - |
| drawn_ell | - | - | - | 110.51 (0.8) | - |

### Differences above 3 % of the FEM rise at 1 mm and the warnings the run of that model printed (a count and the first words)

| board | model | difference % | warnings of the run |
| :-- | :-- | --: | :-- |
| example_board | Lumped | +3.7 | 1: U1: 9 vias under the footprint; the LPTN model joins the pla |
| profile_board | Lumped | +3.7 | 1: U1: 9 vias under the footprint; the LPTN model joins the pla |
| example_cut_to_T | Analytic | -3.9 | 1: Analytic: the board has an outline: computed on a rectangle  |
| plate_pad | Lumped | -11.4 | 0 (silent) |
| plate_pad | Analytic | -54.4 | 1: Analytic: copper coverage varies around the heaters (spread  |
| plate_pad | 3D solid | +4.8 | 0 (silent) |
| plate_lone_via | Lumped | +4.6 | 1: U: 1 via under the footprint; the LPTN model joins the plane |
| t_outline | Lumped | -31.5 | 2: LPTN: the board has an outline: computed on a rectangle of t; U: the part is 4.0 mm from a side of the board; the LPTN mod |
| t_outline | Analytic | -30.9 | 1: Analytic: the board has an outline: computed on a rectangle  |
| two_layer_partial | Analytic | -7.3 | 1: Analytic: copper coverage varies around the heaters (spread  |
| one_layer_pad | Lumped | -6.7 | 0 (silent) |
| one_layer_pad | Analytic | -31.4 | 1: Analytic: copper coverage varies around the heaters (spread  |
| one_layer_pad | 3D solid | +4.5 | 0 (silent) |
| part_top_path | Analytic | -9.4 | 1: Analytic: copper coverage varies around the heaters (spread  |
| hatched_copper | Lumped | +4.4 | 1: U: a copper edge or hatching crosses its footprint (copper f |
| part_across_outline | Lumped | -10.5 | 3: LPTN: the board has an outline: computed on a rectangle of t; U: 21 % of the footprint is outside the board; its full powe; U: the part is 0.0 mm from a side of the board; the LPTN mod |
| part_across_outline | Analytic | -10.1 | 2: Analytic: the board has an outline: computed on a rectangle ; U: 21 % of the footprint is outside the board; its full powe |
| drawn_inset_square | Lumped | -9.1 | 1: The LPTN model keeps the edge film of the laminate at the co |
| drawn_inset_square | Analytic | -12.0 | 2: Analytic: copper coverage varies around the heaters (spread ; The Analytic model keeps the edge film of the laminate at th |
| drawn_inset_square | 3D solid | +3.2 | 0 (silent) |
| drawn_stripes_pad | Lumped | -23.8 | 1: The LPTN model keeps the edge film of the laminate at the co |
| drawn_stripes_pad | Analytic | -23.2 | 2: Analytic: copper coverage varies around the heaters (spread ; The Analytic model keeps the edge film of the laminate at th |
| drawn_ell | FVM | +17.8 | 0 (silent) |
| drawn_ell | FDM | -20.3 | 0 (silent) |
| drawn_ell | Lumped | -32.6 | 2: The LPTN model keeps the edge film of the laminate at the co; U: a copper edge or hatching crosses its footprint (copper f |
| drawn_ell | Analytic | -34.9 | 3: Analytic: copper coverage varies around the heaters (spread ; The Analytic model keeps the edge film of the laminate at th; U: a copper edge or hatching crosses its footprint (copper f |
| drawn_ell | 3D solid | +35.4 | 0 (silent) |

### Heat balance (power out / power in - 1, worst of the boards) and skipped records

| model | worst balance error | records ok | skipped | errors |
| :-- | --: | --: | --: | --: |
| FVM | 5.33e-12 | 60 | 0 | 0 |
| FDM | 5.20e-12 | 60 | 0 | 0 |
| Lumped | 2.63e-13 | 60 | 0 | 0 |
| Analytic | 9.00e-07 | 60 | 0 | 0 |
| 3D solid | 3.35e-12 | 54 | 6 | 0 |
| FEM | 5.33e-11 | 53 | 7 | 0 |

Skipped or failed records:

* example_board, 3D solid, 0.5 mm: skipped, 512000 unknowns, more than 150000
* example_board, FEM, 0.5 mm: skipped, 1054251 unknowns, more than 300000
* profile_board, 3D solid, 0.5 mm: skipped, 512000 unknowns, more than 150000
* profile_board, FEM, 0.5 mm: skipped, 1054251 unknowns, more than 300000
* reference_board, 3D solid, 0.5 mm: skipped, 400000 unknowns, more than 150000
* reference_board, FEM, 0.5 mm: skipped, 580644 unknowns, more than 300000
* example_cut_to_T, 3D solid, 0.5 mm: skipped, 512000 unknowns, more than 150000
* example_cut_to_T, FEM, 0.5 mm: skipped, 843111 unknowns, more than 300000
* round_outline, FEM, 2 mm: skipped, no finite-element mesh: the FEM needs a rectangular or axis-aligned outline in this version: the outline has a slanted or curved side (use t
* round_outline, FEM, 1 mm: skipped, no finite-element mesh: the FEM needs a rectangular or axis-aligned outline in this version: the outline has a slanted or curved side (use t
* round_outline, FEM, 0.5 mm: skipped, no finite-element mesh: the FEM needs a rectangular or axis-aligned outline in this version: the outline has a slanted or curved side (use t
* t_outline, 3D solid, 0.5 mm: skipped, 192000 unknowns, more than 150000
* two_layer_partial, 3D solid, 0.5 mm: skipped, 192000 unknowns, more than 150000

### Surface read-out (C2): top-face surface peak minus column peak [K], cell 1 mm (where the model has a surface map)

| board | FVM | FDM | Lumped | Analytic | 3D solid | FEM |
| :-- | --: | --: | --: | --: | --: | --: |
| example_board | +0.00 | +0.00 | - | +0.00 | +0.00 | +0.00 |
| profile_board | +0.00 | +0.00 | - | +0.00 | +0.00 | +0.00 |
| reference_board | +0.00 | +0.00 | - | +0.00 | +0.00 | +0.00 |
| example_cut_to_T | +0.00 | +0.00 | - | +0.00 | +0.00 | +0.00 |
| plate_uniform | +0.00 | +0.00 | - | +0.00 | +0.00 | +0.00 |
| plate_pad | +0.00 | +0.00 | - | +0.00 | +0.00 | +0.00 |
| plate_vias | +0.00 | +0.00 | - | +0.00 | +0.00 | +0.00 |
| plate_lone_via | +0.00 | +0.00 | - | +0.00 | +0.00 | +0.00 |
| round_outline | +0.00 | +0.00 | - | +0.00 | +0.00 | - |
| t_outline | +0.00 | +0.00 | - | +0.00 | +0.00 | +0.00 |
| two_layer_partial | +0.00 | +0.00 | - | +0.00 | +0.00 | +0.00 |
| one_layer_full | +0.00 | +0.00 | - | +0.00 | +0.00 | +0.00 |
| one_layer_pad | +0.00 | +0.00 | - | +0.00 | +0.00 | +0.00 |
| finned_block | +0.00 | +0.00 | - | +0.00 | +0.00 | +0.00 |
| part_top_path | +0.00 | +0.00 | - | +0.00 | +0.00 | +0.00 |
| hatched_copper | +1.22 | +1.22 | - | - | +1.22 | +0.00 |
| part_across_outline | +0.00 | +0.00 | - | +0.00 | +0.00 | +0.00 |
| drawn_inset_square | +0.00 | +0.00 | - | +0.00 | +0.00 | +0.00 |
| drawn_stripes_pad | +0.00 | +0.00 | - | +0.00 | +0.00 | +0.00 |
| drawn_ell | +3.65 | +3.65 | - | - | +3.65 | +2.28 |

### Time of each record [s], cell 1 mm (one machine, information only)

| board | FVM | FDM | Lumped | Analytic | 3D solid | FEM |
| :-- | --: | --: | --: | --: | --: | --: |
| example_board | 0.3 (39052) | 0.2 (40092) | 0.0 (None) | 0.8 (None) | 6.4 (128000) | 11.3 (275724) |
| profile_board | 0.3 (39052) | 0.3 (40092) | 0.0 (None) | 0.8 (None) | 6.4 (128000) | 11.4 (275724) |
| reference_board | 0.1 (24608) | 0.1 (25058) | 0.0 (None) | 0.0 (None) | 1.6 (100000) | 5.4 (147456) |
| example_cut_to_T | 0.2 (37588) | 0.2 (38574) | 0.0 (None) | 0.8 (None) | 2.3 (128000) | 9.0 (222318) |
| plate_uniform | 0.0 (7200) | 0.0 (7442) | 0.0 (None) | 0.0 (None) | 0.4 (36000) | 1.7 (51984) |
| plate_pad | 0.1 (17412) | 0.1 (18098) | 0.0 (None) | 0.0 (None) | 0.4 (36000) | 1.6 (51984) |
| plate_vias | 0.0 (9888) | 0.0 (10178) | 0.0 (None) | 0.0 (None) | 0.4 (36000) | 2.1 (53181) |
| plate_lone_via | 0.0 (9888) | 0.0 (10178) | 0.0 (None) | 0.0 (None) | 0.4 (36000) | 1.9 (52623) |
| round_outline | 0.1 (9252) | 0.0 (9710) | 0.0 (None) | 0.0 (None) | 1.6 (36000) | - |
| t_outline | 0.1 (12720) | 0.0 (13068) | 0.0 (None) | 0.0 (None) | 0.3 (48000) | 1.5 (40140) |
| two_layer_partial | 0.1 (24000) | 0.1 (24705) | 0.0 (None) | 0.0 (None) | 0.6 (48000) | 2.6 (72000) |
| one_layer_full | 0.0 (7200) | 0.0 (7442) | 0.0 (None) | 0.0 (None) | 0.3 (32400) | 1.4 (40328) |
| one_layer_pad | 0.1 (17412) | 0.1 (18098) | 0.0 (None) | 0.0 (None) | 0.3 (32400) | 1.3 (40328) |
| finned_block | 0.0 (7200) | 0.0 (7503) | 0.0 (None) | 0.1 (None) | 0.6 (33600) | 2.2 (55488) |
| part_top_path | 0.1 (12308) | 0.1 (12858) | 0.0 (None) | 0.1 (None) | 1.0 (25000) | 4.4 (36864) |
| hatched_copper | 0.1 (18000) | 0.1 (18605) | 0.0 (None) | 0.0 (None) | 0.4 (36000) | 2.0 (57600) |
| part_across_outline | 0.0 (4880) | 0.0 (5189) | 0.0 (None) | 0.0 (None) | 0.2 (16000) | 0.6 (24192) |
| drawn_inset_square | 0.0 (1700) | 0.0 (1962) | 0.0 (None) | 0.0 (None) | 0.1 (4000) | 0.2 (9216) |
| drawn_stripes_pad | 0.0 (1994) | 0.0 (2205) | 0.0 (None) | 0.0 (None) | 0.1 (4000) | 0.2 (8928) |
| drawn_ell | 0.0 (1877) | 0.0 (2139) | 0.0 (None) | 0.0 (None) | 0.1 (4000) | 0.2 (9216) |