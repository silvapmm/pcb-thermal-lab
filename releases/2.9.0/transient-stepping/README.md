# The default stepping of the power-step run (`fix/transient-default-stepping`)

Question: how large is the time-step error of the FVM and FDM run at the defaults, and does Crank-Nicolson with the Rannacher start and the first stage in quarter steps remove it?

Run: `.venv/bin/python releases/2.9.0/transient-stepping/scripts/study_default_stepping.py` (about 6 minutes; `--quick` runs the two small boards). Tree: `fix/transient-default-stepping`. Reference: the same network with implicit Euler at 128 and 256 substeps between frames, Richardson-extrapolated (reproduces the 5.93 % of `research/transient-published-case` 3 on the plate). Error of the hottest-cell rise, FVM 2 mm (plate 2.5 mm).

First frame and later error (the peak after a third of the time to 63 %), old default against the new one:

| Board, setting | old first frame | new first frame | old later | new later | old worst | new worst |
| :-- | --: | --: | --: | --: | --: | --: |
| example, Animation (60) | -12.36 % | -0.45 % | 0.70 % | 0.03 % | -12.36 % | -0.45 % |
| example, command line (40) | -16.51 % | -0.54 % | 1.02 % | 0.06 % | -16.51 % | -0.54 % |
| example, 20 frames | -19.31 % | -0.46 % | 1.92 % | 0.23 % | -19.31 % | +1.11 % |
| reference board, Animation | -0.65 % | -0.02 % | 1.56 % | 0.05 % | -2.13 % | +0.06 % |
| reference board, command line | -1.13 % | -0.03 % | 1.87 % | 0.10 % | -3.20 % | +0.13 % |
| two-layer (`two2`), Animation | -3.72 % | -0.12 % | 1.13 % | 0.04 % | -4.14 % | -0.12 % |
| two-layer, command line | -5.01 % | -0.17 % | 1.63 % | 0.09 % | -5.26 % | -0.17 % |
| disc, Animation | -12.51 % | -0.39 % | 1.67 % | 0.06 % | -12.51 % | -0.39 % |
| disc, command line | -14.65 % | -0.43 % | 2.42 % | 0.13 % | -14.65 % | -0.43 % |
| plate (held edges), Animation (32 s) | -0.00 % | -0.00 % | 1.27 % | 0.01 % | -1.27 % | -0.01 % |
| plate, command line (600 s) | -0.00 % | -0.00 % | 3.10 % | 0.16 % | -3.10 % | +0.16 % |
| plate, 20 frames, 92 s | -0.00 % | -0.00 % | 5.93 % | 0.43 % | -5.93 % | +0.43 % |

Run time of the example board (14 000 unknowns), Animation: 0.70 s before, 0.59 s after. The study also prints the pieces alone (Euler in quarter steps; Crank-Nicolson without the start; with the start alone) and the ringing of the new default: the peak rises monotonically at 20, 40 and 60 frames for runs of five time constants and 600 s; at 3000 s with 20 frames it steps back by 0.03 % of the rise at most.

Not changed, not verified here: `fvm.step_responses` (the power profiles, Crank-Nicolson on its own grid) was not measured for its first step; the Lumped has no power-step run and the Analytic is a closed-form series, so neither shares this stepping.
