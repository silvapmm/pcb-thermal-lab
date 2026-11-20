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

Not changed: `fvm.step_responses` (the power profiles, Crank-Nicolson on its own grid; measured by the review below); the Lumped has no power-step run and the Analytic is a closed-form series, so neither shares this stepping.

## Review

Verdict: GO, with the corrections listed here (made on this branch).

**Against an exact reference.** `scripts/check_exact_modal.py` solves the same network exactly in time by its eigenmodes (dense, symmetrised `C^{-1/2} K C^{-1/2}`; the nodes without capacity are checked to be decoupled and stay at zero). The Richardson reference of the study agrees with it to 3e-4 % or better on the two-layer board, the disc, the plate and the example board at 4 mm, and the table above is reproduced to the printed digits (the example and reference boards at 2 mm against Richardson at 256/512 substeps, `--large`). Example board at 4 mm, exact: first frame -12.45 / -15.97 / -18.58 % before (Animation / command line / 20 frames), -0.41 / -0.49 / -0.45 % now.

**The pieces alone** (example board, 2 mm, Animation / command line / 20 frames, first frame): Euler in quarter steps -3.64 / -5.15 / -6.09 %; Crank-Nicolson without the start +0.04 / +1.76 / +6.22 % (worst +1.09 / +2.25 / +6.22 %, a high reading of the undamped stiff modes, not a step back: the peak still rises at every frame); the start alone -6.85 / -9.48 / -11.19 %. So the claim holds: only the three together bring every first frame within 0.6 %. On the reference board, whose part is wide, Crank-Nicolson alone is already good (+0.06 % worst); on the disc it reads +1.9 to +8.2 % high.

**The +1.11 % at 20 frames** is not the start: it is the same with 8 or 16 steps per frame (+1.12 %) and +0.76 % with the start alone; it is Crank-Nicolson in the stages after the first, where 20 frames give two steps per stage, and it falls with the frames (+0.28 % at 40, +0.13 % at 60). It reads HIGH (the safe side), the peak rises monotonically in every run, and no frame passes the steady value (the largest frame is at or below it in every run of the check). A split of 8 takes the first frame to -0.10 to -0.13 % and changes nothing later; 4 is kept, as the FEM.

**The step responses** (`fvm.step_responses`, Crank-Nicolson without a start on its own grid, first step 1e-6 s): `λ_max Δt₀` is 3e-5 to 1e-4 on the boards (1.7 on the plate), so nothing rings; against the exact modal responses `Z` is within 0.36 % wherever it exceeds 1 % of `R_th` and never steps back (implicit Euler on that grid: 3.1 to 4.0 %). No change is needed and no frozen number moves: `PCBT_FROZEN_CELLS=2,1 pytest tests/regression` gave 333 passed on this branch and on `development` c9b923e2 (the frozen times to 63 % come only from `api.step_response`).

**The resolved power-profile run** (`profiles.run_windows`, implicit Euler by default, one step per tenth of the shortest stretch; not changed here), `scripts/check_profile_edge.py`: on `examples/profile_board.pcbt.json` (U2 resolved, U1 held at its average, FVM 2 mm) against the same run with the step divided by 32 and 64 (Richardson), the peak is 0.43 % of the rise low, the minimum within 0.003 K and the swing 0.9 % low, but the sample right after the rising edge reads 10.9 K low out of a 50.6 K swing (then -5.8, -3.3, -2.2 K): one implicit step after a power jump, the same class as the old first frame. Crank-Nicolson without a start reads it 11.9 K high and rings. Not changed in this branch (another code path, its reported peak and minimum are within 0.5 %, and the decision uses `Z`, not the run): recorded in `docs/versions.md` 'Planned' and `docs/theory.md` 10.

**Corrections made by the review.** The default of `fem.solve_transient` is 0.5 too: the FEM animation (the Scheme box is shared) and `transient --model fem` already ran Crank-Nicolson with the start by default, so the CHANGELOG's "the numbers of the FEM do not move" was wrong for them, and the Python default now agrees (tested). The stale texts that still called implicit Euler the default (`docs/theory.md` 4b, the guide's 'FEM in time', manual 7.8) are corrected, and the version wording "up to 2.9.0" / "of 2.9.0 and before" for the OLD stepping is now "before 2.9.0" / "of 2.8". The tooltip said "under 0.1 %" after the first seconds; the measured largest is 0.13 % (the disc on the command line). The screenshots `docs/images/animation.png` and `animation_underlay.png` (and the guide's copy) showed Implicit Euler in the Scheme box: regenerated (only these two of the runs of `examples/make_screenshots.py` and `--views` are kept; the t63 line of the picture now reads 18.6 s instead of 19.5 s, the Euler lag). The theory said the start costs one more factorisation; it costs none (11 factorisations before and after on the example board, the steady one included).

**Tests.** The new tests fail on the old stepping (5 of 8 with `DEFAULT_THETA = 1.0` and `FIRST_STAGE_SPLIT = 1`; the other 3 pass explicit settings). The adapted tests are legitimate: `rannacher=False` where a test measures the order of the plain theta method, `theta_scheme=1.0, first_stage_split=1` where a test compares bit for bit with the old reference, and the monotonicity test keeps implicit Euler strict and bounds the default's step back to 1e-4 of the rise.
