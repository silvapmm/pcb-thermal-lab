# final (2.8.0) against v2.7.1 (2.7.1)

## final against v2.7.1

Records identical in every number: 54; skipped or failed in both: 6; alarms (unexplained, must-not-move or out of range): **0**.

| Class | Shifted numbers |
| :-- | --: |
| expected | 3882 |
| expected_out_of_range | 0 |
| to_be_explained | 0 |
| unexplained | 0 |
| must_not_move | 0 |
| warnings_only | 0 |

### Alarms (to be looked at before the release)

None.

### Shift of the maximum temperature and of the unknowns, every record that moved

| Board | Model | Cell [mm] | Tmax old | Tmax new | Shift [K] | Class (Tmax) | Rules | Unknowns old to new |
| :-- | :-- | --: | --: | --: | --: | :-- | :-- | :-- |
| drawn_ell | analytic | 0.5 | 80.1663 | 80.1664 | +0.0000 | expected | R1 |  |
| drawn_ell | fdm | 0.5 | 105.6977 | 111.8438 | +6.1462 | expected | R4 |  |
| drawn_ell | fvm | 0.5 | 108.7979 | 112.6807 | +3.8828 | expected | R5 |  |
| drawn_ell | lumped | 0.5 | 81.2118 | 81.5469 | +0.3351 | expected | R6 |  |
| drawn_ell | analytic | 1 | 79.6856 | 79.6856 | +0.0000 | expected | R1 |  |
| drawn_ell | fdm | 1 | 87.9662 | 91.9550 | +3.9888 | expected | R4 |  |
| drawn_ell | fvm | 1 | 118.8577 | 124.0347 | +5.1770 | expected | R5 |  |
| drawn_ell | lumped | 1 | 80.9332 | 81.6238 | +0.6906 | expected | R6 |  |
| drawn_ell | analytic | 2 | 79.6856 | 79.6856 | +0.0000 | expected | R1 |  |
| drawn_ell | fdm | 2 | 81.4707 | 99.3245 | +17.8538 | expected | R4 |  |
| drawn_ell | fvm | 2 | 86.0010 | 92.7857 | +6.7847 | expected | R5 |  |
| drawn_ell | lumped | 2 | 80.9332 | 81.6238 | +0.6906 | expected | R6 |  |
| drawn_inset_square | analytic | 0.5 | 76.7679 | 76.7679 | +0.0000 | expected | R1 |  |
| drawn_inset_square | fdm | 0.5 | 82.6202 | 84.2472 | +1.6270 | expected | R4 |  |
| drawn_inset_square | fvm | 0.5 | 83.0425 | 83.8723 | +0.8298 | expected | R5 |  |
| drawn_inset_square | lumped | 0.5 | 77.9153 | 78.2024 | +0.2871 | expected | R6 |  |
| drawn_inset_square | analytic | 1 | 76.3623 | 76.3623 | +0.0000 | expected | R1 |  |
| drawn_inset_square | fdm | 1 | 82.1447 | 84.5813 | +2.4366 | expected | R4 |  |
| drawn_inset_square | fvm | 1 | 83.4275 | 84.1863 | +0.7588 | expected | R5 |  |
| drawn_inset_square | lumped | 1 | 77.4531 | 78.0402 | +0.5871 | expected | R6 |  |
| drawn_inset_square | analytic | 2 | 76.3623 | 76.3623 | +0.0000 | expected | R1 |  |
| drawn_inset_square | fdm | 2 | 77.4122 | 85.6423 | +8.2301 | expected | R4 |  |
| drawn_inset_square | fvm | 2 | 79.3078 | 83.1835 | +3.8758 | expected | R5 |  |
| drawn_inset_square | lumped | 2 | 77.4531 | 78.0402 | +0.5871 | expected | R6 |  |
| drawn_stripes_pad | analytic | 0.5 | 82.8518 | 82.8518 | +0.0000 | expected | R1 |  |
| drawn_stripes_pad | fdm | 0.5 | 97.0826 | 100.1543 | +3.0717 | expected | R4 |  |
| drawn_stripes_pad | fvm | 0.5 | 98.2768 | 99.9317 | +1.6549 | expected | R5 |  |
| drawn_stripes_pad | lumped | 0.5 | 83.0643 | 83.3445 | +0.2802 | expected | R6 |  |
| drawn_stripes_pad | analytic | 1 | 82.1978 | 82.1978 | +0.0000 | expected | R1 |  |
| drawn_stripes_pad | fdm | 1 | 92.2897 | 100.4586 | +8.1689 | expected | R4 |  |
| drawn_stripes_pad | fvm | 1 | 95.1450 | 100.4494 | +5.3045 | expected | R5 | 2000 to 1994 |
| drawn_stripes_pad | lumped | 1 | 81.1425 | 81.7196 | +0.5771 | expected | R6 |  |
| drawn_stripes_pad | analytic | 2 | 82.1978 | 82.1978 | +0.0000 | expected | R1 |  |
| drawn_stripes_pad | fdm | 2 | 81.5349 | 100.5120 | +18.9771 | expected | R4 |  |
| drawn_stripes_pad | fvm | 2 | 83.6730 | 101.5848 | +17.9118 | expected | R5 |  |
| drawn_stripes_pad | lumped | 2 | 81.1425 | 81.7196 | +0.5771 | expected | R6 |  |
| example_board | analytic | 0.5 | 84.9131 | 84.9131 | +0.0000 | expected | R1 |  |
| example_board | fdm | 0.5 | 85.3766 | 85.3766 | +0.0000 | expected | R2, R4 |  |
| example_board | fvm | 0.5 | 85.4119 | 85.4119 | +0.0000 | expected | R3, R5 |  |
| example_board | lumped | 0.5 | 85.6784 | 86.4426 | +0.7642 | expected | R6 |  |
| example_board | analytic | 1 | 84.7958 | 84.7958 | +0.0000 | expected | R1 |  |
| example_board | fdm | 1 | 85.3999 | 85.3999 | +0.0000 | expected | R2, R4 |  |
| example_board | fvm | 1 | 85.4650 | 85.4650 | +0.0000 | expected | R3, R5 |  |
| example_board | lumped | 1 | 86.8660 | 86.9055 | +0.0395 | expected | R6 |  |
| example_board | analytic | 2 | 84.7958 | 84.7958 | +0.0000 | expected | R1 |  |
| example_board | fdm | 2 | 84.5189 | 84.6226 | +0.1037 | expected | R2, R4 |  |
| example_board | fvm | 2 | 85.2938 | 85.2926 | -0.0012 | expected | R3, R5 |  |
| example_board | lumped | 2 | 86.8660 | 86.9055 | +0.0395 | expected | R6 |  |
| example_cut_to_T | analytic | 0.5 | 91.1430 | 91.1430 | +0.0000 | expected | R1 |  |
| example_cut_to_T | fdm | 0.5 | 94.6068 | 94.6068 | +0.0000 | expected | R2, R4 |  |
| example_cut_to_T | fvm | 0.5 | 94.6691 | 94.6691 | +0.0000 | expected | R3, R5 |  |
| example_cut_to_T | lumped | 0.5 | 93.1716 | 93.6813 | +0.5097 | expected | R6 |  |
| example_cut_to_T | analytic | 1 | 91.1088 | 91.1088 | +0.0000 | expected | R1 |  |
| example_cut_to_T | fdm | 1 | 94.6192 | 94.6192 | +0.0000 | expected | R2, R4 |  |
| example_cut_to_T | fvm | 1 | 94.7421 | 94.7421 | +0.0000 | expected | R3, R5 |  |
| example_cut_to_T | lumped | 1 | 93.3705 | 94.3905 | +1.0200 | expected | R6 |  |
| example_cut_to_T | analytic | 2 | 91.1088 | 91.1088 | +0.0000 | expected | R1 |  |
| example_cut_to_T | fdm | 2 | 93.9740 | 94.1011 | +0.1271 | expected | R2, R4 |  |
| example_cut_to_T | fvm | 2 | 94.6725 | 94.6686 | -0.0038 | expected | R3, R5 |  |
| example_cut_to_T | lumped | 2 | 93.3705 | 94.3905 | +1.0200 | expected | R6 |  |
| finned_block | analytic | 0.5 | 129.8918 | 130.0177 | +0.1259 | expected | R7 |  |
| finned_block | fdm | 0.5 | 129.9653 | 130.0049 | +0.0396 | expected | R2 |  |
| finned_block | fvm | 0.5 | 129.9657 | 130.0052 | +0.0396 | expected | R3 |  |
| finned_block | lumped | 0.5 | 129.0404 | 130.0180 | +0.9777 | expected | R6 |  |
| finned_block | analytic | 1 | 129.7004 | 129.8262 | +0.1258 | expected | R7 |  |
| finned_block | fdm | 1 | 129.8998 | 129.9394 | +0.0396 | expected | R2 |  |
| finned_block | fvm | 1 | 129.9011 | 129.9407 | +0.0396 | expected | R3 |  |
| finned_block | lumped | 1 | 132.1207 | 132.7984 | +0.6777 | expected | R6 |  |
| finned_block | analytic | 2 | 129.7004 | 129.8262 | +0.1258 | expected | R7 |  |
| finned_block | fdm | 2 | 129.6429 | 129.6825 | +0.0396 | expected | R2 |  |
| finned_block | fvm | 2 | 129.6477 | 129.6873 | +0.0396 | expected | R3 |  |
| finned_block | lumped | 2 | 132.1207 | 132.7984 | +0.6777 | expected | R6 |  |
| hatched_copper | analytic | 0.5 | 111.6704 | 111.6705 | +0.0000 | expected | R1 |  |
| hatched_copper | fdm | 0.5 | 112.2980 | 112.2980 | +0.0000 | expected | R2 |  |
| hatched_copper | fvm | 0.5 | 112.2984 | 112.2984 | +0.0000 | expected | R3 |  |
| hatched_copper | lumped | 0.5 | 112.1111 | 112.1202 | +0.0091 | expected | R6 |  |
| hatched_copper | analytic | 1 | 111.5028 | 111.5028 | +0.0000 | expected | R1 |  |
| hatched_copper | fdm | 1 | 112.2389 | 112.2389 | +0.0000 | expected | R2 |  |
| hatched_copper | fvm | 1 | 112.2401 | 112.2401 | +0.0000 | expected | R3 |  |
| hatched_copper | lumped | 1 | 115.1232 | 115.6910 | +0.5678 | expected | R6 |  |
| hatched_copper | analytic | 2 | 111.5028 | 111.5028 | +0.0000 | expected | R1 |  |
| hatched_copper | fdm | 2 | 112.0085 | 112.0085 | +0.0000 | expected | R2 |  |
| hatched_copper | fvm | 2 | 112.0119 | 112.0119 | +0.0000 | expected | R3 |  |
| hatched_copper | lumped | 2 | 115.1232 | 115.6910 | +0.5678 | expected | R6 |  |
| one_layer_full | analytic | 0.5 | 55.3803 | 55.3803 | +0.0000 | expected | R1 |  |
| one_layer_full | fdm | 0.5 | 55.4638 | 55.4639 | +0.0000 | expected | R2 |  |
| one_layer_full | fvm | 0.5 | 55.4638 | 55.4639 | +0.0000 | expected | R3 |  |
| one_layer_full | lumped | 0.5 | 55.5318 | 55.3882 | -0.1436 | expected | R6 |  |
| one_layer_full | analytic | 1 | 55.2803 | 55.2803 | +0.0000 | expected | R1 |  |
| one_layer_full | fdm | 1 | 55.4415 | 55.4415 | +0.0000 | expected | R2 |  |
| one_layer_full | fvm | 1 | 55.4415 | 55.4415 | +0.0000 | expected | R3 |  |
| one_layer_full | lumped | 1 | 55.6332 | 55.9376 | +0.3043 | expected | R6 |  |
| one_layer_full | analytic | 2 | 55.2803 | 55.2803 | +0.0000 | expected | R1 |  |
| one_layer_full | fdm | 2 | 55.3551 | 55.3551 | +0.0000 | expected | R2 |  |
| one_layer_full | fvm | 2 | 55.3551 | 55.3551 | +0.0000 | expected | R3 |  |
| one_layer_full | lumped | 2 | 55.6332 | 55.9376 | +0.3043 | expected | R6 |  |
| one_layer_pad | analytic | 0.5 | 71.0705 | 71.0705 | +0.0000 | expected | R1 |  |
| one_layer_pad | fdm | 0.5 | 92.0624 | 92.0624 | +0.0000 | expected | R2 |  |
| one_layer_pad | fvm | 0.5 | 92.9336 | 92.9337 | +0.0000 | expected | R3 |  |
| one_layer_pad | lumped | 0.5 | 85.7873 | 85.6574 | -0.1299 | expected | R6 |  |
| one_layer_pad | analytic | 1 | 70.8632 | 70.8633 | +0.0000 | expected | R1 |  |
| one_layer_pad | fdm | 1 | 91.2874 | 91.2875 | +0.0000 | expected | R2 |  |
| one_layer_pad | fvm | 1 | 93.7159 | 93.7159 | +0.0000 | expected | R3 |  |
| one_layer_pad | lumped | 1 | 87.1423 | 87.4166 | +0.2743 | expected | R6 |  |
| one_layer_pad | analytic | 2 | 70.8632 | 70.8633 | +0.0000 | expected | R1 |  |
| one_layer_pad | fdm | 2 | 89.6830 | 89.6830 | +0.0000 | expected | R2 |  |
| one_layer_pad | fvm | 2 | 95.5649 | 95.5649 | +0.0000 | expected | R3 |  |
| one_layer_pad | lumped | 2 | 87.1423 | 87.4166 | +0.2743 | expected | R6 |  |
| part_across_outline | analytic | 0.5 | 208.9189 | 208.9189 | +0.0001 | expected | R1 |  |
| part_across_outline | fdm | 0.5 | 229.8351 | 229.8351 | +0.0001 | expected | R2 |  |
| part_across_outline | fvm | 0.5 | 229.7637 | 229.7638 | +0.0001 | expected | R3 |  |
| part_across_outline | lumped | 0.5 | 196.5914 | 200.8143 | +4.2229 | expected | R6 |  |
| part_across_outline | analytic | 1 | 208.9276 | 208.9276 | +0.0001 | expected | R1 |  |
| part_across_outline | fdm | 1 | 230.4143 | 230.4143 | +0.0001 | expected | R2 |  |
| part_across_outline | fvm | 1 | 229.8287 | 229.8288 | +0.0001 | expected | R3 |  |
| part_across_outline | lumped | 1 | 202.5516 | 208.1033 | +5.5517 | expected | R6 |  |
| part_across_outline | analytic | 2 | 208.9276 | 208.9276 | +0.0001 | expected | R1 |  |
| part_across_outline | fdm | 2 | 230.7508 | 230.7508 | +0.0001 | expected | R2 |  |
| part_across_outline | fvm | 2 | 229.3981 | 229.3982 | +0.0001 | expected | R3 |  |
| part_across_outline | lumped | 2 | 202.5516 | 208.1033 | +5.5517 | expected | R6 |  |
| part_top_path | analytic | 0.5 | 69.3366 | 69.3366 | +0.0000 | expected | R1 |  |
| part_top_path | fdm | 0.5 | 73.8309 | 73.8309 | +0.0000 | expected | R2 |  |
| part_top_path | fvm | 0.5 | 73.9659 | 73.9659 | +0.0000 | expected | R3 |  |
| part_top_path | lumped | 0.5 | 74.1595 | 72.6512 | -1.5083 | expected | R6 |  |
| part_top_path | analytic | 1 | 69.2222 | 69.2222 | +0.0000 | expected | R1 |  |
| part_top_path | fdm | 1 | 73.6795 | 73.6795 | +0.0000 | expected | R2 |  |
| part_top_path | fvm | 1 | 74.0988 | 74.0988 | +0.0000 | expected | R3 |  |
| part_top_path | lumped | 1 | 74.4007 | 73.0559 | -1.3448 | expected | R6 |  |
| part_top_path | analytic | 2 | 69.2222 | 69.2222 | +0.0000 | expected | R1 |  |
| part_top_path | fdm | 2 | 72.9399 | 72.9399 | +0.0000 | expected | R2 |  |
| part_top_path | fvm | 2 | 74.7114 | 74.7114 | +0.0000 | expected | R3 |  |
| part_top_path | lumped | 2 | 74.4007 | 73.0559 | -1.3448 | expected | R6 |  |
| plate_lone_via | analytic | 0.5 | 150.4901 | 150.4902 | +0.0000 | expected | R1 |  |
| plate_lone_via | fdm | 0.5 | 150.1039 | 150.1039 | +0.0000 | expected | R2 |  |
| plate_lone_via | fvm | 0.5 | 150.2895 | 150.2896 | +0.0000 | expected | R3 |  |
| plate_lone_via | lumped | 0.5 | 154.4511 | 153.9136 | -0.5374 | expected | R6 |  |
| plate_lone_via | analytic | 1 | 150.3692 | 150.3693 | +0.0000 | expected | R1 |  |
| plate_lone_via | fdm | 1 | 149.9180 | 149.9180 | +0.0000 | expected | R2 |  |
| plate_lone_via | fvm | 1 | 150.4323 | 150.4323 | +0.0000 | expected | R3 |  |
| plate_lone_via | lumped | 1 | 154.4958 | 155.6344 | +1.1386 | expected | R6 |  |
| plate_lone_via | analytic | 2 | 150.3692 | 150.3693 | +0.0000 | expected | R1 |  |
| plate_lone_via | fdm | 2 | 148.7465 | 148.7465 | +0.0000 | expected | R2 |  |
| plate_lone_via | fvm | 2 | 151.5694 | 151.5694 | +0.0000 | expected | R3 |  |
| plate_lone_via | lumped | 2 | 154.4958 | 155.6344 | +1.1386 | expected | R6 |  |
| plate_pad | analytic | 0.5 | 171.5339 | 171.5339 | +0.0000 | expected | R1 |  |
| plate_pad | fdm | 0.5 | 345.6246 | 345.6247 | +0.0001 | expected | R2 |  |
| plate_pad | fvm | 0.5 | 349.5995 | 349.5995 | +0.0001 | expected | R3 |  |
| plate_pad | lumped | 0.5 | 303.4649 | 302.9249 | -0.5400 | expected | R6 |  |
| plate_pad | analytic | 1 | 170.9966 | 170.9966 | +0.0000 | expected | R1 |  |
| plate_pad | fdm | 1 | 342.5098 | 342.5098 | +0.0001 | expected | R2 |  |
| plate_pad | fvm | 1 | 353.3838 | 353.3838 | +0.0001 | expected | R3 |  |
| plate_pad | lumped | 1 | 307.4351 | 308.5779 | +1.1428 | expected | R6 |  |
| plate_pad | analytic | 2 | 170.9966 | 170.9966 | +0.0000 | expected | R1 |  |
| plate_pad | fdm | 2 | 336.3037 | 336.3038 | +0.0001 | expected | R2 |  |
| plate_pad | fvm | 2 | 362.6071 | 362.6071 | +0.0001 | expected | R3 |  |
| plate_pad | lumped | 2 | 307.4351 | 308.5779 | +1.1428 | expected | R6 |  |
| plate_uniform | analytic | 0.5 | 159.5285 | 159.5285 | +0.0000 | expected | R1 |  |
| plate_uniform | fdm | 0.5 | 159.6365 | 159.6365 | +0.0000 | expected | R2 |  |
| plate_uniform | fvm | 0.5 | 159.6365 | 159.6365 | +0.0000 | expected | R3 |  |
| plate_uniform | lumped | 0.5 | 160.3733 | 159.7881 | -0.5851 | expected | R6 |  |
| plate_uniform | analytic | 1 | 159.0820 | 159.0821 | +0.0000 | expected | R1 |  |
| plate_uniform | fdm | 1 | 159.5161 | 159.5161 | +0.0000 | expected | R2 |  |
| plate_uniform | fvm | 1 | 159.5161 | 159.5161 | +0.0000 | expected | R3 |  |
| plate_uniform | lumped | 1 | 160.3896 | 161.6293 | +1.2397 | expected | R6 |  |
| plate_uniform | analytic | 2 | 159.0820 | 159.0821 | +0.0000 | expected | R1 |  |
| plate_uniform | fdm | 2 | 159.0524 | 159.0525 | +0.0000 | expected | R2 |  |
| plate_uniform | fvm | 2 | 159.0524 | 159.0525 | +0.0000 | expected | R3 |  |
| plate_uniform | lumped | 2 | 160.3896 | 161.6293 | +1.2397 | expected | R6 |  |
| plate_vias | analytic | 0.5 | 136.1127 | 136.1128 | +0.0000 | expected | R1 |  |
| plate_vias | fdm | 0.5 | 136.4137 | 136.4137 | +0.0000 | expected | R2 |  |
| plate_vias | fvm | 0.5 | 136.3193 | 136.3193 | +0.0000 | expected | R3 |  |
| plate_vias | lumped | 0.5 | 136.5230 | 136.1390 | -0.3840 | expected | R6 |  |
| plate_vias | analytic | 1 | 135.9405 | 135.9405 | +0.0000 | expected | R1 |  |
| plate_vias | fdm | 1 | 137.3099 | 137.3100 | +0.0000 | expected | R2 |  |
| plate_vias | fvm | 1 | 135.6818 | 135.6819 | +0.0000 | expected | R3 |  |
| plate_vias | lumped | 1 | 136.5230 | 136.1390 | -0.3840 | expected | R6 |  |
| plate_vias | analytic | 2 | 135.9405 | 135.9405 | +0.0000 | expected | R1 |  |
| plate_vias | fdm | 2 | 133.5042 | 133.5043 | +0.0000 | expected | R2 |  |
| plate_vias | fvm | 2 | 137.8147 | 137.8147 | +0.0000 | expected | R3 |  |
| plate_vias | lumped | 2 | 136.5230 | 136.1390 | -0.3840 | expected | R6 |  |
| profile_board | analytic | 0.5 | 84.9131 | 84.9131 | +0.0000 | expected | R1 |  |
| profile_board | fdm | 0.5 | 85.3766 | 85.3766 | +0.0000 | expected | R2, R4 |  |
| profile_board | fvm | 0.5 | 85.4119 | 85.4119 | +0.0000 | expected | R3, R5 |  |
| profile_board | lumped | 0.5 | 85.6784 | 86.4426 | +0.7642 | expected | R6 |  |
| profile_board | analytic | 1 | 84.7958 | 84.7958 | +0.0000 | expected | R1 |  |
| profile_board | fdm | 1 | 85.3999 | 85.3999 | +0.0000 | expected | R2, R4 |  |
| profile_board | fvm | 1 | 85.4650 | 85.4650 | +0.0000 | expected | R3, R5 |  |
| profile_board | lumped | 1 | 86.8660 | 86.9055 | +0.0395 | expected | R6 |  |
| profile_board | analytic | 2 | 84.7958 | 84.7958 | +0.0000 | expected | R1 |  |
| profile_board | fdm | 2 | 84.5189 | 84.6226 | +0.1037 | expected | R2, R4 |  |
| profile_board | fvm | 2 | 85.2938 | 85.2926 | -0.0012 | expected | R3, R5 |  |
| profile_board | lumped | 2 | 86.8660 | 86.9055 | +0.0395 | expected | R6 |  |
| reference_board | analytic | 0.5 | 90.1404 | 90.1404 | +0.0000 | expected | R1 |  |
| reference_board | fdm | 0.5 | 90.1527 | 90.1527 | +0.0000 | expected | R2 |  |
| reference_board | fvm | 0.5 | 90.1528 | 90.1528 | +0.0000 | expected | R3 |  |
| reference_board | lumped | 0.5 | 89.3632 | 89.9240 | +0.5609 | expected | R6 |  |
| reference_board | analytic | 1 | 90.0904 | 90.0904 | +0.0000 | expected | R1 |  |
| reference_board | fdm | 1 | 90.1354 | 90.1355 | +0.0000 | expected | R2 |  |
| reference_board | fvm | 1 | 90.1359 | 90.1359 | +0.0000 | expected | R3 |  |
| reference_board | lumped | 1 | 89.6889 | 90.7935 | +1.1046 | expected | R6 |  |
| reference_board | analytic | 2 | 90.0904 | 90.0904 | +0.0000 | expected | R1 |  |
| reference_board | fdm | 2 | 90.0675 | 90.0675 | +0.0000 | expected | R2 |  |
| reference_board | fvm | 2 | 90.0689 | 90.0689 | +0.0000 | expected | R3 |  |
| reference_board | lumped | 2 | 89.6889 | 90.7935 | +1.1046 | expected | R6 |  |
| round_outline | analytic | 0.5 | 175.8954 | 175.8955 | +0.0000 | expected | R1 |  |
| round_outline | fdm | 0.5 | 175.5747 | 175.5748 | +0.0000 | expected | R2 |  |
| round_outline | fvm | 0.5 | 175.5756 | 175.5756 | +0.0000 | expected | R3 |  |
| round_outline | lumped | 0.5 | 174.3606 | 176.2195 | +1.8589 | expected | R6 |  |
| round_outline | analytic | 1 | 175.3291 | 175.3291 | +0.0000 | expected | R1 |  |
| round_outline | fdm | 1 | 175.4616 | 175.4616 | +0.0000 | expected | R2 |  |
| round_outline | fvm | 1 | 175.4603 | 175.4603 | +0.0000 | expected | R3 |  |
| round_outline | lumped | 1 | 179.6124 | 180.8009 | +1.1885 | expected | R6 |  |
| round_outline | analytic | 2 | 175.3291 | 175.3291 | +0.0000 | expected | R1 |  |
| round_outline | fdm | 2 | 175.0195 | 175.0196 | +0.0000 | expected | R2 |  |
| round_outline | fvm | 2 | 175.0222 | 175.0222 | +0.0000 | expected | R3 |  |
| round_outline | lumped | 2 | 179.6124 | 180.8009 | +1.1885 | expected | R6 |  |
| t_outline | analytic | 0.5 | 136.8173 | 136.8174 | +0.0000 | expected | R1 |  |
| t_outline | fdm | 0.5 | 186.7211 | 186.7211 | +0.0000 | expected | R2 |  |
| t_outline | fvm | 0.5 | 186.8700 | 186.8700 | +0.0000 | expected | R3 |  |
| t_outline | lumped | 0.5 | 134.3579 | 134.8882 | +0.5303 | expected | R6 |  |
| t_outline | analytic | 1 | 136.7720 | 136.7720 | +0.0000 | expected | R1 |  |
| t_outline | fdm | 1 | 186.6300 | 186.6301 | +0.0000 | expected | R2 |  |
| t_outline | fvm | 1 | 186.9867 | 186.9867 | +0.0000 | expected | R3 |  |
| t_outline | lumped | 1 | 134.6913 | 135.8097 | +1.1184 | expected | R6 |  |
| t_outline | analytic | 2 | 136.7720 | 136.7720 | +0.0000 | expected | R1 |  |
| t_outline | fdm | 2 | 186.3869 | 186.3870 | +0.0000 | expected | R2 |  |
| t_outline | fvm | 2 | 187.2092 | 187.2092 | +0.0000 | expected | R3 |  |
| t_outline | lumped | 2 | 134.6913 | 135.8097 | +1.1184 | expected | R6 |  |
| two_layer_partial | analytic | 0.5 | 152.9389 | 152.9389 | +0.0000 | expected | R1 |  |
| two_layer_partial | fdm | 0.5 | 163.1650 | 163.1650 | +0.0000 | expected | R2, R4 |  |
| two_layer_partial | fvm | 0.5 | 163.3370 | 163.3370 | +0.0000 | expected | R3, R5 |  |
| two_layer_partial | lumped | 0.5 | 159.2607 | 160.7662 | +1.5055 | expected | R6 |  |
| two_layer_partial | analytic | 1 | 152.7128 | 152.7129 | +0.0000 | expected | R1 |  |
| two_layer_partial | fdm | 1 | 162.9192 | 162.9192 | +0.0000 | expected | R2, R4 |  |
| two_layer_partial | fvm | 1 | 163.4742 | 163.4743 | +0.0000 | expected | R3, R5 |  |
| two_layer_partial | lumped | 1 | 162.8601 | 162.3165 | -0.5435 | expected | R6 |  |
| two_layer_partial | analytic | 2 | 152.7128 | 152.7129 | +0.0000 | expected | R1 |  |
| two_layer_partial | fdm | 2 | 161.3255 | 163.1314 | +1.8059 | expected | R2, R4 |  |
| two_layer_partial | fvm | 2 | 162.6262 | 162.8083 | +0.1821 | expected | R3, R5 |  |
| two_layer_partial | lumped | 2 | 162.8601 | 162.3165 | -0.5435 | expected | R6 |  |

## The SOR runs (2 mm)

| Board | Sweeps v2.7.1 | Sweeps final | Omega v2.7.1 | Omega final | Fall-back v2.7.1 | Fall-back final | Tmax v2.7.1 | Tmax final |
| :-- | --: | --: | --: | --: | :-- | :-- | --: | --: |
| example_board | 356.0 | 357.0 | 1.9388539661194308 | 1.9389241373034027 |  |  | 85.2938 | 85.2926 |
| plate_lone_via | 277.0 | 277.0 | 1.9198526441604808 | 1.91985266593983 |  |  | 151.5694 | 151.5694 |
| plate_uniform | 297.0 | 297.0 | 1.9173745444698083 | 1.9173745678407297 |  |  | 159.0524 | 159.0525 |
| plate_vias | 278.0 | 278.0 | 1.9199053878759145 | 1.9199054096415615 |  |  | 137.8147 | 137.8147 |
| two_layer_partial | 230.0 | 230.0 | 1.9030623016973167 | 1.9032258235713209 |  |  | 162.6262 | 162.8083 |

Shifts of the SOR temperatures: {'expected': 108, 'expected_out_of_range': 0, 'to_be_explained': 0, 'unexplained': 0, 'must_not_move': 0, 'warnings_only': 0}

## Time to 63 % of the steady resistance (first part)

| Board | Model | Part | Old [s] | New [s] | Change | Class | Rules |
| :-- | :-- | :-- | --: | --: | --: | :-- | :-- |
| drawn_ell | analytic | U | 17.755750048699316 | 17.755752653388726 | +0.00 % | expected | T1, T0 |
| drawn_ell | fdm | U | 19.768614386809624 | 21.05721520072066 | +6.52 % | expected | T2 |
| drawn_ell | fvm | U | 20.0829210002517 | 20.10596028782406 | +0.11 % | expected | T3 |
| drawn_ell | lumped | U | 18.05285231862641 | 17.624883007808112 | -2.37 % | expected | T4 |
| drawn_inset_square | analytic | U | 19.22140475672128 | 19.221407798932727 | +0.00 % | expected | T5, T0 |
| drawn_inset_square | fdm | U | 20.949659874043952 | 26.593270598554582 | +26.94 % | expected | T6 |
| drawn_inset_square | fvm | U | 22.954935656142037 | 24.372015147445055 | +6.17 % | expected | T7 |
| drawn_inset_square | lumped | U | 19.421067677423544 | 19.075836471802553 | -1.78 % | expected | T8 |
| drawn_stripes_pad | analytic | U | 16.74800013271544 | 16.748002678234048 | +0.00 % | expected | T9, T0 |
| drawn_stripes_pad | fdm | U | 19.61866421561312 | 22.680810511249827 | +15.61 % | expected | T10 |
| drawn_stripes_pad | fvm | U | 21.235951980260847 | 19.462904149282913 | -8.35 % | expected | T11 |
| drawn_stripes_pad | lumped | U | 18.584079201546782 | 18.271219602254153 | -1.68 % | expected | T12 |
| example_board | analytic | U1 | 10.13397700609714 | 10.133989602743899 | +0.00 % | expected | T13 |
| example_board | analytic | U2 | 2.145565558449155 | 2.1455676451191503 | +0.00 % | expected | T13, T0 |
| example_board | fdm | U1 | 10.954182165800745 | 10.987904218110785 | +0.31 % | expected | T14 |
| example_board | fdm | U2 | 2.649399966184774 | 2.678960907260234 | +1.12 % | expected | T14 |
| example_board | fvm | U1 | 10.522172585479927 | 10.524187811550371 | +0.02 % | expected | T15 |
| example_board | fvm | U2 | 2.3098964441980776 | 2.309601000230454 | -0.01 % | expected | T15 |
| example_board | lumped | U1 | 8.843082205829434 | 8.814164703434914 | -0.33 % | expected | T16 |
| example_board | lumped | U2 | 2.426189249533564 | 1.9427844558628864 | -19.92 % | expected | T16 |
| example_cut_to_T | fdm | U1 | 16.341413039409126 | 16.324225017638682 | -0.11 % | expected | T17 |
| example_cut_to_T | fdm | U2 | 4.464885868432135 | 4.490683807019725 | +0.58 % | expected | T17 |
| example_cut_to_T | fvm | U1 | 15.64730450573634 | 15.65156675765408 | +0.03 % | expected | T18 |
| example_cut_to_T | fvm | U2 | 3.8935986001867513 | 3.893690276255372 | +0.00 % | expected | T18 |
| finned_block | fdm | U | 15.328445581478459 | 15.342257255412571 | +0.09 % | expected | T19 |
| finned_block | fvm | U | 15.3326329765003 | 15.34642735894604 | +0.09 % | expected | T20 |
| hatched_copper | analytic | U | 18.53932157482015 | 18.539332973262443 | +0.00 % | expected | T0 |
| hatched_copper | fdm | U | 17.989049456670063 | 17.98906054606933 | +0.00 % | expected | T0 |
| hatched_copper | fvm | U | 17.992442787919302 | 17.992453882785014 | +0.00 % | expected | T0 |
| hatched_copper | lumped | U | 17.174657359218468 | 16.988245846505198 | -1.09 % | expected | T21 |
| one_layer_full | analytic | U | 22.670011495551524 | 22.670031668112365 | +0.00 % | expected | T0 |
| one_layer_full | fdm | U | 20.840618149515127 | 20.840638134111355 | +0.00 % | expected | T0 |
| one_layer_full | fvm | U | 20.840618149515016 | 20.840638134111106 | +0.00 % | expected | T0 |
| one_layer_full | lumped | U | 20.57662967762928 | 20.153006873984342 | -2.06 % | expected | T22 |
| one_layer_pad | analytic | U | 19.44361230793717 | 19.443617413496362 | +0.00 % | expected | T0 |
| one_layer_pad | fdm | U | 58.6826899609161 | 58.682713805468616 | +0.00 % | expected | T0 |
| one_layer_pad | fvm | U | 58.810296986565945 | 58.810322770270375 | +0.00 % | expected | T0 |
| one_layer_pad | lumped | U | 57.42925906530277 | 57.102223704122935 | -0.57 % | expected | T23 |
| part_across_outline | fdm | U | 32.899126200913905 | 32.8991643834854 | +0.00 % | expected | T24 |
| part_across_outline | fvm | U | 33.588296886003036 | 33.58833570448175 | +0.00 % | expected | T25 |
| part_top_path | analytic | Q1 | 19.304365144094763 | 19.30439596066328 | +0.00 % | expected | T26 |
| part_top_path | fdm | Q1 | 17.351464283326386 | 17.351475045015306 | +0.00 % | expected | T0 |
| part_top_path | fvm | Q1 | 14.532535740267855 | 14.53254405625515 | +0.00 % | expected | T0 |
| part_top_path | lumped | Q1 | 17.55001934200666 | 17.25043393512648 | -1.71 % | expected | T27 |
| plate_lone_via | analytic | U | 21.108009635980693 | 21.108041279413907 | +0.00 % | expected | T28 |
| plate_lone_via | fdm | U | 21.887993537262453 | 21.888025873567184 | +0.00 % | expected | T29 |
| plate_lone_via | fvm | U | 20.180281198378093 | 20.180311239136966 | +0.00 % | expected | T30 |
| plate_lone_via | lumped | U | 18.789690180169675 | 18.20006841553178 | -3.14 % | expected | T31 |
| plate_pad | analytic | U | 17.648110541452667 | 17.648122907134386 | +0.00 % | expected | T0 |
| plate_pad | fdm | U | 59.986741457507705 | 59.98676389581435 | +0.00 % | expected | T0 |
| plate_pad | fvm | U | 59.73015575884846 | 59.73018019298431 | +0.00 % | expected | T0 |
| plate_pad | lumped | U | 56.19358669146683 | 55.87719302759006 | -0.56 % | expected | T32 |
| plate_uniform | analytic | U | 19.227632740592284 | 19.227663012615917 | +0.00 % | expected | T33 |
| plate_uniform | fdm | U | 19.112266078509702 | 19.112295670114616 | +0.00 % | expected | T34 |
| plate_uniform | fvm | U | 19.11226607851112 | 19.112295670115135 | +0.00 % | expected | T35 |
| plate_uniform | lumped | U | 18.463241235701652 | 17.85366184403289 | -3.30 % | expected | T36 |
| plate_vias | analytic | U | 31.34953742152679 | 31.349578606729004 | +0.00 % | expected | T37 |
| plate_vias | fdm | U | 33.26016738011926 | 33.260210339762686 | +0.00 % | expected | T38 |
| plate_vias | fvm | U | 29.46350325095784 | 29.463543930345676 | +0.00 % | expected | T39 |
| plate_vias | lumped | U | 30.94195109588101 | 31.279780114910995 | +1.09 % | expected | T40 |
| profile_board | analytic | U1 | 10.13397700609714 | 10.133989602743899 | +0.00 % | expected | T41 |
| profile_board | analytic | U2 | 2.145565558449155 | 2.1455676451191503 | +0.00 % | expected | T41, T0 |
| profile_board | fdm | U1 | 10.954182165800745 | 10.987904218110785 | +0.31 % | expected | T42 |
| profile_board | fdm | U2 | 2.649399966184774 | 2.678960907260234 | +1.12 % | expected | T42 |
| profile_board | fvm | U1 | 10.522172585479927 | 10.524187811550371 | +0.02 % | expected | T43 |
| profile_board | fvm | U2 | 2.3098964441980776 | 2.309601000230454 | -0.01 % | expected | T43 |
| profile_board | lumped | U1 | 8.843082205829434 | 8.814164703434914 | -0.33 % | expected | T44 |
| profile_board | lumped | U2 | 2.426189249533564 | 1.9427844558628864 | -19.92 % | expected | T44 |
| reference_board | analytic | Heater 1 | 18.83525584060958 | 18.835268731087943 | +0.00 % | expected | T0 |
| reference_board | fdm | Heater 1 | 18.742210219137423 | 18.74222293997376 | +0.00 % | expected | T0 |
| reference_board | fvm | Heater 1 | 18.743731173821228 | 18.743743897629304 | +0.00 % | expected | T0 |
| reference_board | lumped | Heater 1 | 17.938930477938207 | 17.63145087655142 | -1.71 % | expected | T45 |
| round_outline | fdm | U | 38.626398907253126 | 38.62644896627999 | +0.00 % | expected | T46 |
| round_outline | fvm | U | 38.63627912539224 | 38.636329212551146 | +0.00 % | expected | T47 |
| t_outline | fdm | U | 48.48946376450158 | 48.48948971911807 | +0.00 % | expected | T0 |
| t_outline | fvm | U | 48.18219706042092 | 48.18222324727731 | +0.00 % | expected | T0 |
| two_layer_partial | analytic | U | 19.59754908897273 | 19.597565217760852 | +0.00 % | expected | T0 |
| two_layer_partial | fdm | U | 24.41317246471664 | 24.384977382555686 | -0.12 % | expected | T48 |
| two_layer_partial | fvm | U | 24.537519556789423 | 24.578116436183418 | +0.17 % | expected | T49 |
| two_layer_partial | lumped | U | 22.77365261811549 | 22.972694623932426 | +0.87 % | expected | T50 |

Time to 63 %: 0 identical, 80 changed.

## Checks that each set must satisfy by itself

| Set | Check | Board | Model | Value | Ok |
| :-- | :-- | :-- | :-- | --: | :-- |
| v2.7.1 | all 219 checks | | | | yes |
| final | all 219 checks | | | | yes |

## Warnings added and removed (texts only, not shifts)

* drawn_ell / analytic / 0.5 mm: + Analytic: copper coverage varies around the heaters (spread 0.43): the Analytic model spreads the copper of ea; + The Analytic model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the ; + U: a copper edge or hatching crosses its footprint (copper fill 0.90); the LPTN and Analytic models are unreli; - The Analytic model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the ; - U: a copper edge or hatching crosses its footprint (copper fill 0.90); the Lumped and Analytic models are unre; - analytic: copper coverage varies around the heaters (spread 0.43): the Analytic model spreads the copper of ea
* drawn_ell / lumped / 0.5 mm: + The LPTN model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the edge; + U: a copper edge or hatching crosses its footprint (copper fill 0.90); the LPTN and Analytic models are unreli; - The Lumped model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the ed; - U: a copper edge or hatching crosses its footprint (copper fill 0.90); the Lumped and Analytic models are unre
* drawn_ell / analytic / 1 mm: + Analytic: copper coverage varies around the heaters (spread 0.42): the Analytic model spreads the copper of ea; + The Analytic model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the ; + U: a copper edge or hatching crosses its footprint (copper fill 0.90); the LPTN and Analytic models are unreli; - The Analytic model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the ; - U: a copper edge or hatching crosses its footprint (copper fill 0.90); the Lumped and Analytic models are unre; - analytic: copper coverage varies around the heaters (spread 0.42): the Analytic model spreads the copper of ea
* drawn_ell / lumped / 1 mm: + The LPTN model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the edge; + U: a copper edge or hatching crosses its footprint (copper fill 0.90); the LPTN and Analytic models are unreli; - The Lumped model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the ed; - U: a copper edge or hatching crosses its footprint (copper fill 0.90); the Lumped and Analytic models are unre
* drawn_ell / analytic / 2 mm: + Analytic: copper coverage varies around the heaters (spread 0.42): the Analytic model spreads the copper of ea; + The Analytic model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the ; + U: a copper edge or hatching crosses its footprint (copper fill 0.94); the LPTN and Analytic models are unreli; - The Analytic model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the ; - U: a copper edge or hatching crosses its footprint (copper fill 0.94); the Lumped and Analytic models are unre; - analytic: copper coverage varies around the heaters (spread 0.42): the Analytic model spreads the copper of ea
* drawn_ell / lumped / 2 mm: + The LPTN model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the edge; + U: a copper edge or hatching crosses its footprint (copper fill 0.94); the LPTN and Analytic models are unreli; - The Lumped model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the ed; - U: a copper edge or hatching crosses its footprint (copper fill 0.94); the Lumped and Analytic models are unre
* drawn_inset_square / analytic / 0.5 mm: + Analytic: copper coverage varies around the heaters (spread 0.34): the Analytic model spreads the copper of ea; + The Analytic model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the ; - The Analytic model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the ; - analytic: copper coverage varies around the heaters (spread 0.34): the Analytic model spreads the copper of ea
* drawn_inset_square / lumped / 0.5 mm: + The LPTN model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the edge; - The Lumped model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the ed
* drawn_inset_square / analytic / 1 mm: + Analytic: copper coverage varies around the heaters (spread 0.33): the Analytic model spreads the copper of ea; + The Analytic model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the ; - The Analytic model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the ; - analytic: copper coverage varies around the heaters (spread 0.33): the Analytic model spreads the copper of ea
* drawn_inset_square / lumped / 1 mm: + The LPTN model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the edge; - The Lumped model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the ed
* drawn_inset_square / analytic / 2 mm: + Analytic: copper coverage varies around the heaters (spread 0.33): the Analytic model spreads the copper of ea; + The Analytic model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the ; - The Analytic model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the ; - analytic: copper coverage varies around the heaters (spread 0.33): the Analytic model spreads the copper of ea
* drawn_inset_square / lumped / 2 mm: + The LPTN model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the edge; - The Lumped model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the ed
* drawn_stripes_pad / analytic / 0.5 mm: + Analytic: copper coverage varies around the heaters (spread 0.44): the Analytic model spreads the copper of ea; + The Analytic model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the ; - The Analytic model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the ; - analytic: copper coverage varies around the heaters (spread 0.44): the Analytic model spreads the copper of ea
* drawn_stripes_pad / lumped / 0.5 mm: + The LPTN model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the edge; - The Lumped model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the ed
* drawn_stripes_pad / analytic / 1 mm: + Analytic: copper coverage varies around the heaters (spread 0.37): the Analytic model spreads the copper of ea; + The Analytic model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the ; - The Analytic model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the ; - analytic: copper coverage varies around the heaters (spread 0.37): the Analytic model spreads the copper of ea
* drawn_stripes_pad / lumped / 1 mm: + The LPTN model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the edge; - The Lumped model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the ed
* drawn_stripes_pad / analytic / 2 mm: + Analytic: copper coverage varies around the heaters (spread 0.37): the Analytic model spreads the copper of ea; + The Analytic model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the ; - The Analytic model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the ; - analytic: copper coverage varies around the heaters (spread 0.37): the Analytic model spreads the copper of ea
* drawn_stripes_pad / lumped / 2 mm: + The LPTN model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the edge; - The Lumped model keeps the edge film of the laminate at the copper temperature (no laminate nodes along the ed
* example_board / lumped / 0.5 mm: + U1: 9 vias under the footprint; the LPTN model joins the planes through a well and the barrel of each ring, so; - U1: 9 vias under the footprint; the Lumped model joins the planes through a well and the barrel of each ring, 
* example_board / lumped / 1 mm: + U1: 9 vias under the footprint; the LPTN model joins the planes through a well and the barrel of each ring, so; - U1: 9 vias under the footprint; the Lumped model joins the planes through a well and the barrel of each ring, 
* example_board / lumped / 2 mm: + U1: 9 vias under the footprint; the LPTN model joins the planes through a well and the barrel of each ring, so; - U1: 9 vias under the footprint; the Lumped model joins the planes through a well and the barrel of each ring, 
* example_cut_to_T / analytic / 0.5 mm: + Analytic: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.86; - analytic: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.86
* example_cut_to_T / lumped / 0.5 mm: + 2 parts (U2, U1) are within one side of the part (and at least 5 mm) of a side of the board (the nearest, U2, ; + LPTN: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.862) a; + U1: 9 vias under the footprint; the LPTN model joins the planes through a well and the barrel of each ring, so; - 2 parts (U2, U1) are within one side of the part (and at least 5 mm) of a side of the board (the nearest, U2, ; - U1: 9 vias under the footprint; the Lumped model joins the planes through a well and the barrel of each ring, ; - lumped: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.862)
* example_cut_to_T / analytic / 1 mm: + Analytic: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.86; - analytic: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.86
* example_cut_to_T / lumped / 1 mm: + 2 parts (U2, U1) are within one side of the part (and at least 5 mm) of a side of the board (the nearest, U2, ; + LPTN: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.862) a; + U1: 9 vias under the footprint; the LPTN model joins the planes through a well and the barrel of each ring, so; - 2 parts (U2, U1) are within one side of the part (and at least 5 mm) of a side of the board (the nearest, U2, ; - U1: 9 vias under the footprint; the Lumped model joins the planes through a well and the barrel of each ring, ; - lumped: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.862)
* example_cut_to_T / analytic / 2 mm: + Analytic: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.86; - analytic: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.86
* example_cut_to_T / lumped / 2 mm: + 2 parts (U2, U1) are within one side of the part (and at least 5 mm) of a side of the board (the nearest, U2, ; + LPTN: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.862) a; + U1: 9 vias under the footprint; the LPTN model joins the planes through a well and the barrel of each ring, so; - 2 parts (U2, U1) are within one side of the part (and at least 5 mm) of a side of the board (the nearest, U2, ; - U1: 9 vias under the footprint; the Lumped model joins the planes through a well and the barrel of each ring, ; - lumped: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.862)
* finned_block / analytic / 0.5 mm: + Analytic: the metal block is represented as a graph of tiles in the Green-function correction: within about 5 ; - analytic: the metal block is represented as a graph of tiles in the Green-function correction: within about 5 
* finned_block / lumped / 0.5 mm: + LPTN: the metal block is represented as one more layer of the ring network: on the cool side of the FVM, withi; - lumped: the metal block is represented as one more layer of the ring network: within about 5 % of the FVM in t
* finned_block / analytic / 1 mm: + Analytic: the metal block is represented as a graph of tiles in the Green-function correction: within about 5 ; - analytic: the metal block is represented as a graph of tiles in the Green-function correction: within about 5 
* finned_block / lumped / 1 mm: + LPTN: the metal block is represented as one more layer of the ring network: on the cool side of the FVM, withi; - lumped: the metal block is represented as one more layer of the ring network: within about 5 % of the FVM in t
* finned_block / analytic / 2 mm: + Analytic: the metal block is represented as a graph of tiles in the Green-function correction: within about 5 ; - analytic: the metal block is represented as a graph of tiles in the Green-function correction: within about 5 
* finned_block / lumped / 2 mm: + LPTN: the metal block is represented as one more layer of the ring network: on the cool side of the FVM, withi; - lumped: the metal block is represented as one more layer of the ring network: within about 5 % of the FVM in t
* hatched_copper / analytic / 0.5 mm: + U: a copper edge or hatching crosses its footprint (copper fill 0.50); the LPTN and Analytic models are unreli; - U: a copper edge or hatching crosses its footprint (copper fill 0.50); the Lumped and Analytic models are unre
* hatched_copper / lumped / 0.5 mm: + U: a copper edge or hatching crosses its footprint (copper fill 0.50); the LPTN and Analytic models are unreli; - U: a copper edge or hatching crosses its footprint (copper fill 0.50); the Lumped and Analytic models are unre
* hatched_copper / analytic / 1 mm: + U: a copper edge or hatching crosses its footprint (copper fill 0.50); the LPTN and Analytic models are unreli; - U: a copper edge or hatching crosses its footprint (copper fill 0.50); the Lumped and Analytic models are unre
* hatched_copper / lumped / 1 mm: + U: a copper edge or hatching crosses its footprint (copper fill 0.50); the LPTN and Analytic models are unreli; - U: a copper edge or hatching crosses its footprint (copper fill 0.50); the Lumped and Analytic models are unre
* hatched_copper / analytic / 2 mm: + U: a copper edge or hatching crosses its footprint (copper fill 0.50); the LPTN and Analytic models are unreli; - U: a copper edge or hatching crosses its footprint (copper fill 0.50); the Lumped and Analytic models are unre
* hatched_copper / lumped / 2 mm: + U: a copper edge or hatching crosses its footprint (copper fill 0.50); the LPTN and Analytic models are unreli; - U: a copper edge or hatching crosses its footprint (copper fill 0.50); the Lumped and Analytic models are unre
* one_layer_pad / analytic / 0.5 mm: + Analytic: copper coverage varies around the heaters (spread 0.50): the Analytic model spreads the copper of ea; - analytic: copper coverage varies around the heaters (spread 0.50): the Analytic model spreads the copper of ea
* one_layer_pad / analytic / 1 mm: + Analytic: copper coverage varies around the heaters (spread 0.50): the Analytic model spreads the copper of ea; - analytic: copper coverage varies around the heaters (spread 0.50): the Analytic model spreads the copper of ea
* one_layer_pad / analytic / 2 mm: + Analytic: copper coverage varies around the heaters (spread 0.50): the Analytic model spreads the copper of ea; - analytic: copper coverage varies around the heaters (spread 0.50): the Analytic model spreads the copper of ea
* part_across_outline / analytic / 0.5 mm: + Analytic: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.96; - analytic: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.96
* part_across_outline / lumped / 0.5 mm: + LPTN: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.966) a; + U: the part is 0.0 mm from a side of the board; the LPTN model does not see the side that sends the heat back ; - U: the part is 0.0 mm from a side of the board; the Lumped model reads a part near a side or a corner of the b; - lumped: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.966)
* part_across_outline / analytic / 1 mm: + Analytic: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.96; - analytic: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.96
* part_across_outline / lumped / 1 mm: + LPTN: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.966) a; + U: the part is 0.0 mm from a side of the board; the LPTN model does not see the side that sends the heat back ; - U: the part is 0.0 mm from a side of the board; the Lumped model reads a part near a side or a corner of the b; - lumped: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.966)
* part_across_outline / analytic / 2 mm: + Analytic: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.96; - analytic: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.96
* part_across_outline / lumped / 2 mm: + LPTN: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.966) a; + U: the part is 0.0 mm from a side of the board; the LPTN model does not see the side that sends the heat back ; - U: the part is 0.0 mm from a side of the board; the Lumped model reads a part near a side or a corner of the b; - lumped: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.966)
* part_top_path / analytic / 0.5 mm: + Analytic: copper coverage varies around the heaters (spread 0.49): the Analytic model spreads the copper of ea; - analytic: copper coverage varies around the heaters (spread 0.49): the Analytic model spreads the copper of ea
* part_top_path / analytic / 1 mm: + Analytic: copper coverage varies around the heaters (spread 0.49): the Analytic model spreads the copper of ea; - analytic: copper coverage varies around the heaters (spread 0.49): the Analytic model spreads the copper of ea
* part_top_path / analytic / 2 mm: + Analytic: copper coverage varies around the heaters (spread 0.49): the Analytic model spreads the copper of ea; - analytic: copper coverage varies around the heaters (spread 0.49): the Analytic model spreads the copper of ea
* plate_lone_via / analytic / 0.5 mm: + Analytic model: one or two vias beside or under a part were measured up to 16 % too small in the via effect (a; - Analytic model: one or two vias beside or under a part were measured up to 16 % too small in the via effect (a
* plate_lone_via / lumped / 0.5 mm: + U: 1 via under the footprint; the LPTN model joins the planes through a well and the barrel of each ring, so i; - U: 1 via under the footprint; the Lumped model joins the planes through a well and the barrel of each ring, so
* plate_lone_via / analytic / 1 mm: + Analytic model: one or two vias beside or under a part were measured up to 16 % too small in the via effect (a; - Analytic model: one or two vias beside or under a part were measured up to 16 % too small in the via effect (a
* plate_lone_via / lumped / 1 mm: + U: 1 via under the footprint; the LPTN model joins the planes through a well and the barrel of each ring, so i; - U: 1 via under the footprint; the Lumped model joins the planes through a well and the barrel of each ring, so
* plate_lone_via / analytic / 2 mm: + Analytic model: one or two vias beside or under a part were measured up to 16 % too small in the via effect (a; - Analytic model: one or two vias beside or under a part were measured up to 16 % too small in the via effect (a
* plate_lone_via / lumped / 2 mm: + U: 1 via under the footprint; the LPTN model joins the planes through a well and the barrel of each ring, so i; - U: 1 via under the footprint; the Lumped model joins the planes through a well and the barrel of each ring, so
* plate_pad / analytic / 0.5 mm: + Analytic: copper coverage varies around the heaters (spread 0.50): the Analytic model spreads the copper of ea; - analytic: copper coverage varies around the heaters (spread 0.50): the Analytic model spreads the copper of ea
* plate_pad / analytic / 1 mm: + Analytic: copper coverage varies around the heaters (spread 0.50): the Analytic model spreads the copper of ea; - analytic: copper coverage varies around the heaters (spread 0.50): the Analytic model spreads the copper of ea
* plate_pad / analytic / 2 mm: + Analytic: copper coverage varies around the heaters (spread 0.50): the Analytic model spreads the copper of ea; - analytic: copper coverage varies around the heaters (spread 0.50): the Analytic model spreads the copper of ea
* plate_vias / lumped / 0.5 mm: + U: 16 vias under the footprint; the LPTN model splits this footprint into the core of the vias and the rest of; - U: 16 vias under the footprint; the Lumped model splits this footprint into the core of the vias and the rest 
* plate_vias / lumped / 1 mm: + U: 16 vias under the footprint; the LPTN model splits this footprint into the core of the vias and the rest of; - U: 16 vias under the footprint; the Lumped model splits this footprint into the core of the vias and the rest 
* plate_vias / lumped / 2 mm: + U: 16 vias under the footprint; the LPTN model splits this footprint into the core of the vias and the rest of; - U: 16 vias under the footprint; the Lumped model splits this footprint into the core of the vias and the rest 
* profile_board / lumped / 0.5 mm: + U1: 9 vias under the footprint; the LPTN model joins the planes through a well and the barrel of each ring, so; - U1: 9 vias under the footprint; the Lumped model joins the planes through a well and the barrel of each ring, 
* profile_board / lumped / 1 mm: + U1: 9 vias under the footprint; the LPTN model joins the planes through a well and the barrel of each ring, so; - U1: 9 vias under the footprint; the Lumped model joins the planes through a well and the barrel of each ring, 
* profile_board / lumped / 2 mm: + U1: 9 vias under the footprint; the LPTN model joins the planes through a well and the barrel of each ring, so; - U1: 9 vias under the footprint; the Lumped model joins the planes through a well and the barrel of each ring, 
* round_outline / analytic / 0.5 mm: + Analytic: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.82; - analytic: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.82
* round_outline / lumped / 0.5 mm: + LPTN: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.827) a; - lumped: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.827)
* round_outline / analytic / 1 mm: + Analytic: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.82; - analytic: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.82
* round_outline / lumped / 1 mm: + LPTN: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.827) a; - lumped: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.827)
* round_outline / analytic / 2 mm: + Analytic: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.82; - analytic: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.82
* round_outline / lumped / 2 mm: + LPTN: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.827) a; - lumped: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.827)
* t_outline / analytic / 0.5 mm: + Analytic: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.70; - analytic: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.70
* t_outline / lumped / 0.5 mm: + LPTN: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.707) a; + U: the part is 4.0 mm from a side of the board; the LPTN model does not see the side that sends the heat back ; - U: the part is 4.0 mm from a side of the board; the Lumped model reads a part near a side or a corner of the b; - lumped: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.707)
* t_outline / analytic / 1 mm: + Analytic: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.70; - analytic: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.70
* t_outline / lumped / 1 mm: + LPTN: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.707) a; + U: the part is 4.0 mm from a side of the board; the LPTN model does not see the side that sends the heat back ; - U: the part is 4.0 mm from a side of the board; the Lumped model reads a part near a side or a corner of the b; - lumped: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.707)
* t_outline / analytic / 2 mm: + Analytic: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.70; - analytic: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.70
* t_outline / lumped / 2 mm: + LPTN: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.707) a; + U: the part is 4.0 mm from a side of the board; the LPTN model does not see the side that sends the heat back ; - U: the part is 4.0 mm from a side of the board; the Lumped model reads a part near a side or a corner of the b; - lumped: the board has an outline: computed on a rectangle of the same area (box and positions scaled by 0.707)
* two_layer_partial / analytic / 0.5 mm: + Analytic: copper coverage varies around the heaters (spread 0.42): the Analytic model spreads the copper of ea; - analytic: copper coverage varies around the heaters (spread 0.42): the Analytic model spreads the copper of ea
* two_layer_partial / analytic / 1 mm: + Analytic: copper coverage varies around the heaters (spread 0.42): the Analytic model spreads the copper of ea; - analytic: copper coverage varies around the heaters (spread 0.42): the Analytic model spreads the copper of ea
* two_layer_partial / analytic / 2 mm: + Analytic: copper coverage varies around the heaters (spread 0.42): the Analytic model spreads the copper of ea; - analytic: copper coverage varies around the heaters (spread 0.42): the Analytic model spreads the copper of ea

## What each board should show (from `reference/expected_shifts.json`)

| Board | FVM | FDM | Lumped | Analytic | 3D solid |
| :-- | :-- | :-- | :-- | :-- | :-- |

## Records present in one set only

Only in v2.7.1: []
Only in final: [['drawn_ell', 'fem', 0.5, 'direct'], ['drawn_ell', 'fem', 1.0, 'direct'], ['drawn_ell', 'fem', 2.0, 'direct'], ['drawn_inset_square', 'fem', 0.5, 'direct'], ['drawn_inset_square', 'fem', 1.0, 'direct'], ['drawn_inset_square', 'fem', 2.0, 'direct'], ['drawn_stripes_pad', 'fem', 0.5, 'direct'], ['drawn_stripes_pad', 'fem', 1.0, 'direct'], ['drawn_stripes_pad', 'fem', 2.0, 'direct'], ['example_board', 'fem', 0.5, 'direct'], ['example_board', 'fem', 1.0, 'direct'], ['example_board', 'fem', 2.0, 'direct'], ['example_cut_to_T', 'fem', 0.5, 'direct'], ['example_cut_to_T', 'fem', 1.0, 'direct'], ['example_cut_to_T', 'fem', 2.0, 'direct'], ['finned_block', 'fem', 0.5, 'direct'], ['finned_block', 'fem', 1.0, 'direct'], ['finned_block', 'fem', 2.0, 'direct'], ['hatched_copper', 'fem', 0.5, 'direct'], ['hatched_copper', 'fem', 1.0, 'direct'], ['hatched_copper', 'fem', 2.0, 'direct'], ['one_layer_full', 'fem', 0.5, 'direct'], ['one_layer_full', 'fem', 1.0, 'direct'], ['one_layer_full', 'fem', 2.0, 'direct'], ['one_layer_pad', 'fem', 0.5, 'direct'], ['one_layer_pad', 'fem', 1.0, 'direct'], ['one_layer_pad', 'fem', 2.0, 'direct'], ['part_across_outline', 'fem', 0.5, 'direct'], ['part_across_outline', 'fem', 1.0, 'direct'], ['part_across_outline', 'fem', 2.0, 'direct'], ['part_top_path', 'fem', 0.5, 'direct'], ['part_top_path', 'fem', 1.0, 'direct'], ['part_top_path', 'fem', 2.0, 'direct'], ['plate_lone_via', 'fem', 0.5, 'direct'], ['plate_lone_via', 'fem', 1.0, 'direct'], ['plate_lone_via', 'fem', 2.0, 'direct'], ['plate_pad', 'fem', 0.5, 'direct'], ['plate_pad', 'fem', 1.0, 'direct'], ['plate_pad', 'fem', 2.0, 'direct'], ['plate_uniform', 'fem', 0.5, 'direct'], ['plate_uniform', 'fem', 1.0, 'direct'], ['plate_uniform', 'fem', 2.0, 'direct'], ['plate_vias', 'fem', 0.5, 'direct'], ['plate_vias', 'fem', 1.0, 'direct'], ['plate_vias', 'fem', 2.0, 'direct'], ['profile_board', 'fem', 0.5, 'direct'], ['profile_board', 'fem', 1.0, 'direct'], ['profile_board', 'fem', 2.0, 'direct'], ['reference_board', 'fem', 0.5, 'direct'], ['reference_board', 'fem', 1.0, 'direct'], ['reference_board', 'fem', 2.0, 'direct'], ['round_outline', 'fem', 0.5, 'direct'], ['round_outline', 'fem', 1.0, 'direct'], ['round_outline', 'fem', 2.0, 'direct'], ['t_outline', 'fem', 0.5, 'direct'], ['t_outline', 'fem', 1.0, 'direct'], ['t_outline', 'fem', 2.0, 'direct'], ['two_layer_partial', 'fem', 0.5, 'direct'], ['two_layer_partial', 'fem', 1.0, 'direct'], ['two_layer_partial', 'fem', 2.0, 'direct']]
