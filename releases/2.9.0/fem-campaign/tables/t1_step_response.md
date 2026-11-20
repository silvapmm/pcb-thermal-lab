tree 0fbabbec, program 2.8.0, numpy 2.5.4

## T1a. Step response at the program's default stepping, options cell 2 mm (the response cell is at least 2 mm); hottest column cell of each part, K/W

plate_uniform, part U: the steady resistance (plateau) and the time to 63 %, then the normalised response z(t)/plateau at fixed times, model minus FEM in points of the plateau
| model | plateau K/W | (vs FEM %) | t63 s | (vs FEM %) | z(0.3 s) | z(1 s) | z(3 s) | z(10 s) | z(30 s) | z(100 s) | run s |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| FEM | 26.2815 | +0.0 | 20.5 | +0.0 | - | - | - | - | - | - | 3.5 |
| FVM | 26.8105 | +2.0 | 19.1 | -6.6 | -12.5 | -8.2 | -2.3 | +0.6 | +0.5 | +0.3 | 0.0 |
| FDM | 26.8105 | +2.0 | 19.1 | -6.6 | -12.5 | -8.2 | -2.3 | +0.6 | +0.5 | +0.3 | 0.0 |
| Lumped | 27.3259 | +4.0 | 17.8 | -12.8 | -10.6 | -6.9 | -1.5 | +1.4 | +1.1 | +0.6 | 0.0 |
| Analytic | 26.8164 | +2.0 | 19.2 | -6.0 | -12.2 | -7.9 | -2.3 | +0.6 | +0.5 | +0.3 | 0.1 |


plate_vias, part U: the steady resistance (plateau) and the time to 63 %, then the normalised response z(t)/plateau at fixed times, model minus FEM in points of the plateau
| model | plateau K/W | (vs FEM %) | t63 s | (vs FEM %) | z(0.3 s) | z(1 s) | z(3 s) | z(10 s) | z(30 s) | z(100 s) | run s |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| FEM | 21.7251 | +0.0 | 32.9 | +0.0 | - | - | - | - | - | - | 3.5 |
| FVM | 22.5629 | +3.9 | 29.5 | -10.4 | -3.6 | -0.8 | +0.8 | +1.6 | +1.3 | +0.7 | 0.1 |
| FDM | 21.7009 | -0.1 | 33.3 | +1.0 | -4.8 | -3.3 | -1.6 | -0.3 | -0.1 | -0.0 | 0.1 |
| Lumped | 22.2278 | +2.3 | 31.3 | -4.9 | -2.7 | -0.6 | +0.5 | +1.0 | +0.6 | +0.4 | 0.0 |
| Analytic | 22.1881 | +2.1 | 31.4 | -4.8 | -3.8 | -1.6 | -0.2 | +0.8 | +0.6 | +0.4 | 0.1 |


one_layer_pad, part U: the steady resistance (plateau) and the time to 63 %, then the normalised response z(t)/plateau at fixed times, model minus FEM in points of the plateau
| model | plateau K/W | (vs FEM %) | t63 s | (vs FEM %) | z(0.3 s) | z(1 s) | z(3 s) | z(10 s) | z(30 s) | z(100 s) | run s |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| FEM | 65.3031 | +0.0 | 59.3 | +0.0 | - | - | - | - | - | - | 1.9 |
| FVM | 70.5649 | +8.1 | 58.8 | -0.8 | -5.3 | -4.0 | -1.9 | -0.5 | -0.1 | +0.3 | 0.2 |
| FDM | 64.6830 | -0.9 | 58.7 | -1.0 | -4.9 | -3.0 | -0.2 | +0.7 | +0.4 | +0.2 | 0.3 |
| Lumped | 62.4166 | -4.4 | 57.2 | -3.6 | -1.2 | +0.8 | +1.7 | +1.8 | +1.4 | +0.6 | 0.0 |
| Analytic | 45.8633 | -29.8 | 19.4 | -67.2 | -5.7 | -2.1 | +8.1 | +21.7 | +25.2 | +11.4 | 0.0 |


part_top_path, part Q1: the steady resistance (plateau) and the time to 63 %, then the normalised response z(t)/plateau at fixed times, model minus FEM in points of the plateau
| model | plateau K/W | (vs FEM %) | t63 s | (vs FEM %) | z(0.3 s) | z(1 s) | z(3 s) | z(10 s) | z(30 s) | z(100 s) | run s |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| FEM | 45.2412 | +0.0 | 15.9 | +0.0 | - | - | - | - | - | - | 2.3 |
| FVM | 47.9116 | +5.9 | 14.5 | -9.0 | -9.0 | -4.8 | -0.9 | +1.2 | +1.4 | +0.7 | 0.2 |
| FDM | 43.5832 | -3.7 | 17.3 | +8.6 | -7.7 | -3.6 | -1.8 | -1.4 | -1.0 | -0.5 | 0.2 |
| Lumped | 43.8516 | -3.1 | 17.2 | +7.9 | -7.7 | -5.1 | -3.0 | -1.4 | -1.0 | -0.4 | 0.0 |
| Analytic | 35.9270 | -20.6 | 19.3 | +21.3 | -5.4 | +1.2 | +5.2 | +1.4 | -4.7 | -3.5 | 0.1 |

   finned_block Lumped: not run (ValueError: this calculation does not support a metal block (the transient of the lumped and analytic )
   finned_block Analytic: not run (ValueError: this calculation does not support a metal block (the transient of the lumped and analytic )

finned_block, part U: the steady resistance (plateau) and the time to 63 %, then the normalised response z(t)/plateau at fixed times, model minus FEM in points of the plateau
| model | plateau K/W | (vs FEM %) | t63 s | (vs FEM %) | z(0.3 s) | z(1 s) | z(3 s) | z(10 s) | z(30 s) | z(100 s) | run s |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| FEM | 17.3498 | +0.0 | 14.6 | +0.0 | - | - | - | - | - | - | 5.3 |
| FVM | 17.4479 | +0.6 | 15.3 | +4.6 | -13.3 | -11.5 | -4.9 | -0.9 | +0.1 | +0.1 | 0.0 |
| FDM | 17.4471 | +0.6 | 15.3 | +4.5 | -13.3 | -11.5 | -4.9 | -0.9 | +0.1 | +0.1 | 0.1 |
| Lumped | - | - | - | - | - | - | - | - | - | - | 0.0 |
| Analytic | - | - | - | - | - | - | - | - | - | - | 0.0 |


reference_board, part 1: the steady resistance (plateau) and the time to 63 %, then the normalised response z(t)/plateau at fixed times, model minus FEM in points of the plateau
| model | plateau K/W | (vs FEM %) | t63 s | (vs FEM %) | z(0.3 s) | z(1 s) | z(3 s) | z(10 s) | z(30 s) | z(100 s) | run s |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| FEM | 12.9798 | +0.0 | 18.7 | +0.0 | - | - | - | - | - | - | 17.1 |
| FVM | 13.0138 | +0.3 | 18.7 | +0.1 | -8.3 | -10.1 | -5.8 | -0.6 | +0.1 | +0.1 | 0.3 |
| FDM | 13.0135 | +0.3 | 18.7 | +0.1 | -8.3 | -10.1 | -5.8 | -0.6 | +0.1 | +0.1 | 0.3 |
| Lumped | 13.1587 | +1.4 | 17.6 | -5.9 | -6.2 | -6.6 | -3.0 | +0.9 | +0.8 | +0.2 | 0.0 |
| Analytic | 13.0181 | +0.3 | 18.8 | +0.7 | -8.3 | -10.1 | -5.8 | -0.6 | +0.0 | -0.0 | 0.1 |


example_board, part U1: the steady resistance (plateau) and the time to 63 %, then the normalised response z(t)/plateau at fixed times, model minus FEM in points of the plateau
| model | plateau K/W | (vs FEM %) | t63 s | (vs FEM %) | z(0.3 s) | z(1 s) | z(3 s) | z(10 s) | z(30 s) | z(100 s) | run s |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| FEM | 13.1838 | +0.0 | 11.6 | +0.0 | - | - | - | - | - | - | 175.2 |
| FVM | 13.6166 | +3.3 | 10.5 | -9.2 | -1.7 | +1.1 | +1.3 | +0.9 | +0.7 | +0.4 | 1.5 |
| FDM | 13.4385 | +1.9 | 11 | -5.2 | -2.2 | +0.5 | +0.7 | +0.5 | +0.4 | +0.2 | 1.5 |
| Lumped | 13.7691 | +4.4 | 8.81 | -24.0 | +0.9 | +2.8 | +3.1 | +2.5 | +1.9 | +0.7 | 0.0 |
| Analytic | 13.4741 | +2.2 | 10.1 | -12.6 | -1.9 | +0.8 | +1.5 | +1.3 | +0.6 | +0.1 | 5.2 |

example_board, part U2: the steady resistance (plateau) and the time to 63 %, then the normalised response z(t)/plateau at fixed times, model minus FEM in points of the plateau
| model | plateau K/W | (vs FEM %) | t63 s | (vs FEM %) | z(0.3 s) | z(1 s) | z(3 s) | z(10 s) | z(30 s) | z(100 s) | run s |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| FEM | 20.5624 | +0.0 | 2.47 | +0.0 | - | - | - | - | - | - | 175.2 |
| FVM | 21.0295 | +2.3 | 2.3 | -6.9 | -3.9 | -0.1 | +0.6 | +0.6 | +0.4 | +0.2 | 1.5 |
| FDM | 20.2918 | -1.3 | 2.67 | +8.0 | -5.3 | -1.5 | -0.5 | -0.3 | -0.2 | -0.1 | 1.5 |
| Lumped | 21.5215 | +4.7 | 1.93 | -22.0 | -1.5 | +1.2 | +2.3 | +2.4 | +2.0 | +0.9 | 0.0 |
| Analytic | 20.9288 | +1.8 | 2.14 | -13.4 | -3.1 | +0.5 | +1.3 | +1.1 | +0.5 | +0.1 | 5.2 |

## T1b. Stepping error of each model against itself (per_stage 4 against 16 on the same 2 mm mesh), largest difference of the response over the times, percent of the fine value
| board | model | t63 default s | t63 fine s | change of t63 % | largest change of z over 0.3, 1, 3, 10, 30, 100 s [%] |
| :-- | :-- | --: | --: | --: | --: |
| plate_uniform | FVM | 19.1 | 19.3 | -0.83 | 0.22 |
| plate_uniform | FDM | 19.1 | 19.3 | -0.83 | 0.22 |
| plate_uniform | FEM | 20.5 | 20.6 | -0.80 | 0.20 |
| finned_block | FVM | 15.3 | 15.4 | -0.72 | 0.24 |
| finned_block | FDM | 15.3 | 15.4 | -0.72 | 0.24 |
| finned_block | FEM | 14.6 | 14.7 | -0.71 | 0.20 |
| reference_board | FVM | 18.7 | 18.9 | -0.77 | 0.19 |
| reference_board | FDM | 18.7 | 18.9 | -0.77 | 0.19 |
| reference_board | FEM | 18.7 | 18.8 | -0.67 | 0.15 |

## T1c. plate_uniform at the 1 mm cell (module functions, one element or cell per mm), part 1, K/W
| model | plateau K/W | (vs FEM %) | t63 s | (vs FEM %) | z(0.3 s) % | z(1 s) % | z(3 s) % | z(10 s) % | z(30 s) % | z(100 s) % | run s |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| FEM | 26.8013 | +0.0 | 19 | +0.0 | - | - | - | - | - | - | 27.0 |
| FVM | 26.9032 | +0.4 | 18.8 | -1.0 | -52.9 | -24.3 | -6.0 | +0.4 | +0.4 | +0.4 | 0.2 |
| FDM | 26.9032 | +0.4 | 18.8 | -1.0 | -52.9 | -24.3 | -6.0 | +0.4 | +0.4 | +0.4 | 0.2 |

