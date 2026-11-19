# Design note: the FEM transient (branch `feature/fem-transient`, 3.0.0 item a)

**Status: planning only.** Nothing in this note was run: no solve, no `pytest`, no figure. Every number is either quoted from a document named next to it, or is hand arithmetic marked "arithmetic", or is a hypothesis marked H1, H2, ... that the first commits must measure. The program is not touched. Tree read: `development` at 6c225276 (2.8.0 not yet released; the steady FEM, its window and the speed-up are merged). No dates.

**What this note is for.** `releases/3.0.0/PLAN.md` (2.2, 3) asks for a one-page design note before the code of `feature/fem-transient`, so that the reviewer is called early on three things: the memory law per stage, the statement about the first seconds, and the profile runner interface. This note answers those and the rest of the formulation, so that the executor can start from it and the reviewer can reject a choice before it is coded.

## 0. The question and what would answer it

**Question.** How does the FEM (`femcore.py`, `femmesh.py`, `fem.py`) advance in time, so that the time simulation (power step with animation, and power profiles through `profiles.run_windows`) can be run with it as a comparison model, with the same results objects as the FVM and FDM, at a cost the memory guard can predict?

**Why it matters.** The FEM is the only model that resolves the thickness of the board (copper slabs and dielectric gaps as elements). The other models carry one node per layer, so their first seconds are read too cool (`research/transient-reference-boards` README 4.2: at 0.3 / 1 / 3 / 10 s the FVM, FDM and Analytic read -58 / -30 / -9 / -1.4 % on `two2`, tagged there as a limit of one node per layer, not of the mesh). The comparison campaign (`releases/2.8.0/fem-model/COMPARE_PLAN.md`, rows T1 to T3, validation section 57) cannot run without this branch, and the Difference view (item b) needs frames of the FEM in time.

**What answers it.** A closed form for the integrator (a 1D mode with an exact decay rate, a lumped RC, the semi-infinite solid), the FVM and FDM transient on the same boards, the research transient tool as an independent reference, the energy balance in time, convergence in dt and in the mesh. Section 3.

## 1. Formulation

### 1.1 The semi-discrete system

The steady FEM assembles (`femcore.Model.assemble`) the Galerkin stiffness plus the Robin face matrix `A`, and the unit load `f` of the sources, on the unknowns that belong to elements (`used`), with the ambient at zero (the field is a rise above the ambient). The transient adds a heat capacity matrix `M` of the same sparsity:

    M dT/dt + A T = p(t) f ,        M_ij = integral of (rho c) N_i N_j dV   (consistent)

with `p(t)` the power factor (one scalar for the power step; one per heater in the profile runner, so `f` becomes a matrix `F = [f_1 ... f_nh]`, see 1.7). Q1 hexahedra, 2 x 2 x 2 Gauss rule, the same quadrature and the same chunks (20 000 elements) as the stiffness, so `M` costs one more pass of the element loop and no new mesh data. This is exactly the semi-discrete system of the research tool `research/independent-fem-extensions/lib/transient.py` (read in full, the class `Transient` and `lumped_mass`, `consistent_mass`), which is what the port test must reproduce.

### 1.2 Lumped or consistent mass

| | consistent | lumped (row sums) |
| :-- | :-- | :-- |
| Matrix | same 27-point pattern as `A`, so `A + M/dt` has the fill of `A` | diagonal |
| Cost over the steady model | storage of one more matrix pattern (arithmetic: 27 nonzeros x (8 + 4) bytes = about 0.3 kB per unknown, against the 6.7 kB per unknown of the CG law, `memory.FEM_K1`); the assembly of `M` after `A` is stored, never together with the triplets of `A` | none (a vector) |
| Early times | validated: the step response of the disc board is -2.8 % (0.01 s) to +0.2 % (500 s) against the axisymmetric modal reference, consistent mass, 21 411 unknowns (`independent-fem-extensions` README 8.3, read) | the research found the lumped mass 2 to 3 points lower in the step response at 0.01 s, and the 20 Hz swing -4.7 % against -2.5 % consistent (same README, 8.3, read) |
| Known drawback | the consistent mass is not monotone: a sharp front (a heat flux switched on at a surface) can undershoot ahead of itself at small steps | satisfies a discrete maximum principle for implicit Euler on well-shaped elements |

**Choice: the consistent mass, the lumped mass kept as a switch for tests and a diagnostic (`mass="consistent"|"lumped"` in the transient function, not in the saved options).** Reason: it is the integrator that was validated against an independent solver, the lumped one is measurably worse in the first seconds that this model exists to resolve, and the memory cost is about 4 % of the law. Check in the first commit (study, not asked for a decision): the semi-infinite solid test (3.1 d) at the first element-diffusion times, to see the undershoot of the consistent mass and to set the Rannacher start (1.3) accordingly.

### 1.3 Time integration: implicit Euler, Crank-Nicolson, BDF2

The system is stiff in the extreme. Arithmetic, with the program's constants (copper 390 W/mK and 8960 x 385 J/m3K, FR-4 0.3 W/mK through and 1850 x 900 J/m3K) and assumed element sizes: a half-slab of 35 um copper (17.5 um) has `dz^2 / alpha` = (17.5e-6)^2 / 1.13e-4 = 2.7e-6 s; a fine dielectric element of 20 um has (20e-6)^2 / 1.8e-7 = 2.2e-3 s; the board time constant is of the order of 100 to 200 s (201 s for the 60 x 40 mm study plate, `independent-fem-extensions` README 8.3). The spectrum spans about eight decades, and no explicit method is thinkable.

| Method | Order | L-stable (amplification at lambda dt -> infinity) | Fit with the program |
| :-- | :-- | :-- | :-- |
| implicit Euler (theta = 1) | 1 | yes (0) | the default of `fvm.solve_transient` and of `ProfileOptions.theta`; robust, damps the stiff modes at once; error visible in a step response at a few steps per decade |
| Crank-Nicolson (theta = 1/2) | 2 | **no** (-1): a stiff mode excited by a jump of the load rings with alternating sign and is not damped | validated reference (the research tool); needs the Rannacher start (two implicit-Euler half steps after every change of load) |
| BDF2 | 2 | yes | variable-step BDF2 is zero-stable only for a step ratio below 1 + sqrt 2 = 2.41 (textbook result, status M, not opened here): the doubling stages of the animation (ratio 2) are close to the limit and the ratio 3 of `step_responses` is outside it. Rejected. |

**Choice.**
* The **step response and the animation** use theta = 1/2 with the Rannacher start (two implicit-Euler half steps at t = 0, the only change of load) as the default for the FEM, because that is the validated integrator; `theta_scheme=1.0` is honoured (like `fvm.solve_transient`, same signature: `solve_transient(problem, t_end, n_out, cell_mm, substeps, theta_scheme, log_times)`). The time grid is the program's: ten stages with the step doubling (`log_times`), one factorisation per stage; or linear with `substeps`. n_out frames, one step per frame in the logarithmic mode, so the frames of the FEM sit at the same times as the FVM's and the Difference view subtracts like for like.
* The **profile runner** uses the `theta` of `ProfileOptions` (1.0 by default, 0.5 allowed) with **no** Rannacher: the runner feeds the exact mean of the wave over every step (`profiles.run_windows`), so the load changes at every step and a half-step restart at every step would double the cost for nothing. Under CN the stiff modes excited by a step-mean jump ring with factor -1 per step; their amplitude is the projection of the jump on stiff modes, small away from the heated elements. **H2**: the ring is negligible for theta = 1/2 at 10 or more steps per shortest feature (the runner's `n_per`); if not, the FEM adapter forces implicit Euler and says so in a warning. Measured in 3.2 b before the adapter is finished.
* A **like-for-like** comparison between models uses the same theta and the same time grid on all of them (campaign rule): the option exists in every model. The accuracy statement of the FEM (within 0.5 % of an independent reference at the plateau and the time to 63 %) is made with theta = 1/2 + Rannacher.

### 1.4 Step control and the edges of the power profile

* **Power step** (animation, step response, the unit-power response): the only edge is t = 0, so it is aligned by construction; the Rannacher half steps sit there.
* **Profile runner**: the plan is shared (`profiles.plan_run`: `n_per = ceil(window / (shortest / 10))`, `dt = window / n_per`, constant) and is not changed by this branch (it would move the FVM and FDM profile records). The edges of a square wave then fall inside a step unless `duty x n_per` is an integer. This is harmless for energy (the power of a step is the exact mean over the step: `waves[i].mean_power(t_start, t_start + dt)`), and costs first-order accuracy of the edge position, the same in every model. The research tool aligns the steps to the edges (`march` with segments, `square_segments`), so the independent reference is aligned and the program is not: the validation (3.3) reports the FEM run unaligned against the aligned reference, the difference to be measured and stated, **H3**: below 1 % of the swing at 10 steps per shortest feature. If H3 fails, the proposal is an optional `edges` list in the plan (a second small branch, not this one, because it touches every model).
* The runner needs **one factorisation or one hierarchy for the whole run** (constant dt); the step response needs one per stage (ten for the doubling grid, plus one for the half step of the Rannacher start).

### 1.5 Initial condition

* Power step: the board at ambient (rise 0).
* Profiles: the steady state of the average power (`ProfileOptions.initial = "average"`, the runner's default; for a one-shot profile, the steady state of its first power) or a uniform temperature. The steady states (`th_avg`, `th_init`, `th_peak`, which give `steady_average_max` and `steady_peak_max`) are **three right-hand sides of one steady matrix**: the steady solve must accept several (direct: one factorisation, several back substitutions; CG: one hierarchy, three solves, which the E8 measurement says keeps the iteration count exactly, `research/fem-amg-thin-layers` README 7.6 (a)). New in `femcore`: `Model.solve_many(rhs_list)` (S).
* The frequency-domain periodic state of the research tool (`harmonic_response`, `periodic_wave`) is **not brought in**: complex SuperLU is limited to 25 000 unknowns there and the runner already finds the periodic state by windows. It stays in the research folder as the reference (3.3).

### 1.6 Heat capacity per element (`femmesh`)

`rho c` per element, in the same places where `femmesh.build` assigns `kx, ky, kz` (README of the mesh: "Materials per element", `femmesh.py` around line 1112 to 1230; this was read from the source, only the places named here):

| Region | rho c |
| :-- | :-- |
| Copper slab of fill `f` (the zone fill of the element) | `f rho_cu cp_cu + (1 - f) rho c of the adjacent laminate` (as `fvm.Network.C`: `f m.rho_copper m.cp_copper tc + diel_t rho_cp_lam`, `fvm.py` line 233, and `Board.layer_inplane_props`) |
| Dielectric gap element | `rho cp` of the gap (`Board.gap_properties()`, third return) |
| Via barrel (patch elements) | copper |
| Via as a rod (the fallback under a drill) | `via_frac rho_cu cp_cu + (1 - via_frac) rho c of the gap` (the same blend as the `kz` of the rod) |
| Metal block and its interface pad slab | block material `rho c`; the pad slab has the capacity of its own thickness |
| Heater (part) | nothing: the programs model a part as a source with no body mass (thermal-capacity inventory e11 is a separate small item, PLAN 6.6) |
| Films (Robin faces) | nothing (no capacity) |

**Identity test** (a closed form of the mesh, the first test of the branch): the total capacity `sum(M)` equals `integral rho c dV` of the layered description, and equals the FVM's total `net.C.sum()` on the plain boards to the precision of the copper area fills; any difference on a board with vias, a block or a laminate band is explained by the feature (the FVM adds laminate sub-nodes by `laminate.build`, the FEM resolves the gap), never silently. **To read before coding** (not read in this pass): whether the FVM/FDM counts the capacity of the via barrel; if it does not, the FEM must still count it (it is the model of the physics) and the difference is recorded, not tuned away.

### 1.7 Loads in time

The steady FEM sums all heaters into one `f`. The transient needs the load of each heater separately: `F` (n x nh, sparse: a heater touches few elements), built by a helper `Model.load_vector(elem_ids, q)` (Gauss quadrature of `N q`) from `mesh.heater_elems`, plus the face-flux loads of parts on a thick outer layer (`add_faces(flux=)`, one label per heater). The sum `F @ p` must equal the steady `f` at the heater powers: the first assertion of the load test. Radiation and `h`: the transient takes the **plain `h` of `problem.board`**, as the steady FEM does (the computed-h loop of the API sets them before the call; the profile run takes `sim.effective_problem`, so it carries the same coefficients). No nonlinear term is added.

### 1.8 Read-outs per step (the three read-outs of the steady model, `DESIGN.md` 5.4 of 2.8.0)

The steady read-outs are **linear in the nodal field** except the point maximum: `column = Rcol T`, `surface = Rsurf T`, with `Rcol` (layers x ny x nx rows, n columns) and `Rsurf` (2 x ny x nx rows) sparse operators made once from the Gauss weights and the cell shares that `solve_steady` already computes (`_gauss_weights`, `_cell_shares`, `_to_cells`, `_fill_empty`). Building them once and applying one `matvec` per frame replaces the Python loops of the steady read-out (which would be the slowest part of a many-step run). Empty-cell filling (`_fill_empty`) is a fixed gather, so it joins the operator.

| Read-out | In the transient | Where it goes |
| :-- | :-- | :-- |
| **column** (headline, like for like) | every step in the runner (for `observe`: the hottest of the board and per heater, over the footprint cells, `peak_values` for the peak map) and every output frame in the step response | `TransientResult.frames`, `t_max`, `t_mean` (area-weighted by the cell cover, as `fvm.mean_weights`); `ProfileResult.frames`, `t_max`, `t_heaters`, `peak_map` |
| **surface** | the output frames only (never every step): `Rsurf T`, two faces | optional `arrays["T_surface"]` of the result (the `TransientResult` gains an optional `arrays: dict = {}` field; default empty, so the other models and the saved projects are untouched); resolved, not an estimate |
| **point** (hottest node, per part face peak) | the maximum of `T` over the used nodes at every step (a vector maximum, cheap) and the hottest node under each footprint (precomputed index sets) | `extras["t_max_point"]`-like series (`t_max_point(t)`), reported beside the column, never replacing it |

Decision 5 of PLAN 6 holds: the column is the headline. What the **energy balance** needs per step is `gam . T` (the heat leaving through the films) and `M . T` (stored heat), both vectors of the system; they are free.

### 1.9 What the results object holds

* `fem.solve_transient(...)` returns the same `results.TransientResult` as `fvm.solve_transient`: `times`, `t_max`, `t_mean`, `frames` (n_out, layers, ny, nx) in degC, `steady_t_max` (the steady FEM column maximum: one more steady solve, a back substitution if the factor is kept, one CG otherwise), `ambient`, `grid="cells"`, `warnings`. New optional fields only (`arrays` as above; `extras` with the energy residual, the solver per stage and the step count). The animation tab, `plots.plot_transient`, `plots.save_transient_gif` and the CSV of the CLI work unchanged.
* `profiles.run_fem(problem, decisions, options, cell_mm, progress)` returns the same `ProfileResult` through `run_windows` with a `_FEMAdapter` that has the interface of `_FVMAdapter`: `dx, dy, ambient, steady_average_max, steady_peak_max`, `begin`, `prepare(dt)`, `advance`, `observe`, `frame`, `peak_values`, `shape_field`, `offset = 0.5` (the cells of the run grid), `warnings`. The face-term machinery of `_FVMAdapter._face_setup` is **not** needed (the FEM resolves the laminate under a part, so a part over absent copper has its own face temperature; `observe` reads the per-heater column maximum, and the part face peak is the extra `t_max_point` series).

## 2. Solver strategy

### 2.1 One matrix per dt

The matrix is `B = M/dt + theta A` (`A + M/dt` for implicit Euler, `M/dt + A/2` for Crank-Nicolson), symmetric positive definite, with the sparsity of `A`. It changes with dt and theta only, never with the power.

* **Power step**: one matrix per stage (ten stages on the doubling grid, plus one with the half step), 4 to 6 steps per stage. **Profile runner**: one matrix for the whole run.
* The right-hand side of a step needs `M T/dt - (1 - theta) A T`: two matrix-vector products, **no assembled `B_rhs`** (the FVM forms it as a matrix; here it would store a third pattern).

### 2.2 Direct or AMG, and what to reuse

| | Direct (SuperLU, symmetric mode, `n <= FEM_DIRECT_MAX = 30 000`) | CG with pyamg smoothed aggregation (above) |
| :-- | :-- | :-- |
| Per matrix | one factorisation (steady, measured: 0.7 s at 22 509 unknowns, 3.9 s at 57 523 in `DESIGN.md` 5.3 of 2.8.0) | hierarchy setup: 1 to 5 % of a solve at the default variant (0.07 s at 2 mm, 0.51 s of 10.2 s at 1 mm, `fem-amg-thin-layers` README 7.6) |
| Per step | back substitution, milliseconds | CG iterations, each a matvec and a V cycle |
| Memory | the factor, 15.9 kB per unknown (`memory.FEM_DIRECT_BYTES`), freed before the next is built (as `fvm.transient_from_network`: one factor alive) | the matrix, the hierarchy (rebuilt per stage, the old freed first) |
| Warm start | not applicable | `x0` = previous field (or the linear extrapolation `2 T_n - T_{n-1}` after the first step of a stage) |

**Reuse of the AMG hierarchy, from the measurements of `research/fem-amg-thin-layers`** (reviewed, closed; its column preconditioner is not adopted; the program keeps the default pyamg setup):
* the same matrix with other sources keeps the iteration count exactly (E8 a): one hierarchy for the three steady right-hand sides and for the whole profile run;
* a stale hierarchy after a film change by factors 0.5 to 2 costs at most 4 % more iterations (E8 b), so the hierarchy of the steady stage could even serve the computed-h loop;
* a hierarchy of `K` used for `K + s x (mean diagonal)` with s from 0.01 to 10 was a **poor preconditioner**, 2405 to 5000 (not converged) iterations against 525 fresh (E8 c). That test used a made-up scale (the transient matrix did not exist then, the research text says so), and the reverse direction (the hierarchy of stage j for stage j + 1, whose matrix differs by a factor 2 in `M/dt`) was not measured. **So the design does not rely on stale hierarchies across stages: it builds one per stage, since the setup is 1 to 5 % of a solve.** The measurement of the cross-stage reuse is a study of the first commits (M1 of 3.2), not a premise.
* **H1** (the reason the transient CG should be cheap): `M/dt` adds a positive diagonal that shrinks the condition number, so the iteration count per step is a few at small dt and rises toward the steady count (280 at 1 mm on the example board, 276 000 unknowns, `REVIEW_SPEED` as quoted in the AMG README 1) only for dt of the order of the board time constant. To measure: iterations per step against `dt / tau_board`, at 3 sizes (M2).

### 2.3 Cost per step and the estimate

Hand arithmetic from the measured steady figures, not a prediction: the steady CG solve of the example board at 1 mm is about 15 s for 280 iterations, so one iteration is of the order of 0.05 s at 276 000 unknowns (V cycle + matvec; the build and assembly are the other 30 %). A step response of 40 frames with 10 to 30 iterations per step on average: about 40 x 20 x 0.05 s = 40 s plus 10 hierarchy setups (0.5 s each) and the operators of the read-out: **under two minutes at 276 000 unknowns (to measure)**. A profile run of 12 windows x 200 steps = 2400 steps at 10 iterations is 2400 x 10 x 0.05 s = 20 minutes at that size: **too slow to offer without a verdict**, so the guard needs a work bound (2.4). For the direct range (up to 30 000 unknowns) the steps are milliseconds and the factorisation (about 1 s) per stage dominates: seconds for a step response, a minute at most for a profile run.

### 2.4 Memory law and time law (what to measure; new coefficients of `memory.py`)

The present law (`memory.CONTINUOUS["fem"]`: `peak = base + safety x k1 x N`, k1 = 6700 B, safety 1.15, p = 1, a = 0; direct 15 900 B per unknown) is a steady law, and `check(..., transient=True)` multiplies it by `TRANSIENT_FACTOR = 2.0` (two factors alive in the FVM, "measured 1.9, one-factor fix"). For the FEM the transient is not two factors. Predicted stages (to be measured, hypotheses H4):

| Stage | Contents | Prediction |
| :-- | :-- | :-- |
| mesh + assembly of `A` | as steady (the peak of the steady law: the triplet lists) | 6.7 kB/unknown, unchanged |
| assembly of `M` | triplets of `M` while `A` is stored | below the steady peak (A as csc is about 0.3 kB/unknown, the triplets of M as much as those of A): about the same peak, not additive |
| `B = A + M/dt`, hierarchy or factor | one extra matrix + the hierarchy / the factor | CG: +0.3 kB (B) + hierarchy (about the steady hierarchy); direct: the factor 15.9 kB, same as steady |
| state | `T`, the previous `T`, a few work vectors, the operators `Rcol`, `Rsurf` (sparse, about one nonzero set per used copper element, below 0.5 kB/unknown), `F` | small |
| frames | `n_out x L x ny x nx` float64 (+ the surface frames, 2 faces) | per run, computed exactly like the other models |

So **H4: the FEM transient factor is 1.1 to 1.3 of the steady law on the CG path and 1.0 on the direct path**, not 2.0. What to measure, in one fresh process per run with the peak `ru_maxrss` (the method of `releases/2.8.0/fem-model/scripts/measure_fem_law.py` and `measure_fem_cost.py`): the same 10 boards as the steady law at 2, 1 and 0.5 mm where the harness caps allow (vias, block, outline, one layer), a step response of 40 frames and a profile run of 2 windows; the memory growth over the build (the quantity the steady law fits), with the frames and results held. The coefficient is stored as `FEM_TRANSIENT_FACTOR` (a constant of `memory.py`, applied as `factor` of the FEM row in `check`), the safety factor kept at the largest measured growth x 1.1 as in the steady fit.

**Time law**: seconds = build (the steady build time law, `TIME_LAWS["fem"]`: 15.7 s at N_REF, q = 0.69, a lower bound) + stages x setup + steps x iterations x cost per iteration. To measure: iterations per step (H1) and cost per iteration against N, giving `memory.fem_transient_seconds(unknowns, steps, stages)`; the verdict "slow" at `SLOW_SECONDS` and a **work bound** `unknowns x steps` above which the guard refuses with the message that already exists for `ProfileError` ("the time simulation needs about N steps ...", `profiles.plan_run`): a coarser cell, fewer windows, a higher oscillation threshold. The number of the bound is a **decision** after the measurement (7).

### 2.5 Cancel and progress

`jobs.job_transient` today reports nothing ("the solvers report nothing"). A step loop makes real progress possible: `progress("Time step k of n", k / n)` once per frame (the step response) or once per window (the runner already calls `progress(f"Window ...")`); a **cooperative cancel** per step through the same `cancel` callable as the assembly (`femcore.FemCancelled`), on top of the process termination the job system already uses. The assembly stays chunked (20 000 elements).

## 3. Validation plan

Independent references first (CLAUDE.md 9, 13 and 14); the program's own models are compared second.

### 3.1 Closed forms (in the battery, small meshes, `femcore.structured_model` with `rho_c`)

a. **Lumped RC**: a plate of one element across the thickness with `Bi = h t / k << 1` and a source, uniform temperature: `T(t) = (q / hA)(1 - exp(-t / tau))`, `tau = rho c V / (h A)`. Tests `M`, the film matrix and the step.
b. **1D mode with an exact rate**: a bar with insulated ends, initial `cos(k pi x / L)`, decay `exp(-alpha (k pi / L)^2 t)`. Temporal order: implicit Euler 1, Crank-Nicolson 2 (halve dt, ratio of the errors 2 and 4); spatial order on the mesh refinement. Shows the lumped mass against the consistent one on a smooth mode.
c. **1D slab with a flux at one face and convection at the other**: the series of exponentials with the roots of `lambda tan(lambda) = Bi`: derived in the test, summed numerically to 1e-12 and cross-checked with the lumped RC for `Bi -> 0` (source status of the formula: M, the classical Carslaw and Jaeger / Incropera slab solution; **not obtained** in this pass).
d. **Semi-infinite solid**: surface rise `2 q sqrt(t / (pi k rho c))` before the heat reaches the far face: the first seconds, the test that chooses between lumped and consistent mass and that sets whether the Rannacher start is enough.
e. **Energy balance in time** at every step: `M (T_n - T_0)` stored + `integral gam . T dt` lost = `integral p f dt` input, residual below 1e-9 of the input (the research tool reaches 2.6e-12 on the disc board and 1e-9 at most on the plate runs).
f. **Steady limit**: after 10 `tau` the transient field equals the steady solve (research: 174.35599 against 174.35726 K/W, 7e-6).
g. **Load**: `F p` equals the steady `f`; `sum(M)` equals the integral of `rho c`.

### 3.2 Against the independent solver and against the program's models

a. **Port test** (first test after the mass assembly, as `tests/test_fem_port.py`): the same structured model, the same `rho c`, the same steps: the program's `femcore` stepper against `research/independent-fem-extensions/lib/transient.py` (`Transient.march` and `step_response`), the fields agree to solver tolerance. The research copy stays as the independent reference and its README numbers stay.
b. **Integrator study** (a script of the branch, `study_fem_transient_integrator.py`): theta 1 and 1/2, Rannacher on and off, at 10, 20 and 40 steps per shortest feature, on a square wave and a step (H2 and H3); lumped against consistent mass (the 1.2 check).
c. **Cross-stage hierarchy reuse** (M1) and **iterations per step against dt / tau** (M2): the two measurements behind 2.2 (H1).
d. **The program's FVM and FDM on the same boards** (the five boards of `research/transient-reference-boards`: plain plates, via boards, a block board; those folders hold the boards and the reference results already): time to 63 %, plateau, the response at 0.3 / 1 / 3 / 10 s, the peak and swing of a slow and of a fast square wave, **column read-out for all** (like for like). **The first seconds**: the FEM is mesh-resolved and the other models are not, so they differ there and the text must say which is right. The transient-reference-boards numbers are the control: at 0.3 s the FVM, FDM and Analytic read -58 % against the reference, the FEM is expected to follow the reference (-2.8 % at 0.01 s is the disc-board result with the consistent mass, 21 411 unknowns). The statement for the document: the FEM is the reference of the first seconds up to the stated residual, with the shown limit that the fast swing of a footprint mean of a small source reads 0.5 to 3.5 % low (`independent-fem-extensions` README 8.3, read).
e. **The average-or-resolve windows**: the FEM runs the plan of `profiles.decide` with the same decisions as the others; checks: the periodicity of the last two windows (peak and valley repeat within `stable_c`), the energy per window (mean loss through the films equals mean power in, to 1e-6 at convergence), and the swing against the research periodic state (frequency domain, up to 25 000 unknowns) and against the closed-form floor (`stackimpedance`, theory 10.5), as the research did for 20 Hz, 30 %, 1 W on the 60 x 40 mm plate (reference centre 0.63788 K/W per watt of on-power, program closed form -0.38 %).
f. **Convergence**: dt halved (tolerance on the time to 63 % and the swing), mesh `cell_mm` 2, 1, 0.5 where the cap allows, gap elements 6, 12, 24; the unaligned-edge sensitivity of H3.
g. **Stress** (GUI/API tests in `tests/test_gui_stress.py`): start, cancel in the middle of the stages, a long profile that the work bound refuses, a memory-refused board, a board with an outline refused as the steady FEM refuses it, the FEM ticked with the Analytic and Lumped on a board with a block (those two refuse transients there, `RECTANGLE_ONLY`), the 3D solid ticked next to it (still steady only).

### 3.3 Published cases (rule 14), and what the papers library offers

Read in this pass: the research folders named above (their README sections quoted here), `profiles.py`, `fvm.py` transient, `api.py` and `jobs.py` where cited, `femcore.py`, `fem.py` and `memory.py` where cited. The papers library was only searched by its index (`papers/notes/INDEX.md` and the file list of `papers/pdf/`, **no paper opened**): the entries that touch transient heat flow are `Ibragimov2023PeacemanTimeDependent.pdf` (time-dependent Peaceman well, arXiv:2309.05372: about wells, a way to the via in time, not a board case) and `TI-SLUAAT8.pdf` (a MOSFET transient thermal impedance, Foster network from datasheet curves: a package, not a board with a mesh), both with only the first page checked in the index; the classical sources (Carslaw and Jaeger 1959, Patankar 1980, Incropera) are books or paywalled and listed as not obtained in the index. **No published numerical transient case of a board that the papers library lets this pass reproduce was found.** Proposal for the branch (a first step with the researcher, since the rule asks for a published case): obtain the tabulated roots and Heisler-type values of the slab with convection (open copy, to be searched: the fetch tools work from the maintainer's machine), and Rannacher's paper on irregular data in diffusion problems (Numer. Math. 43, 1984, the origin of the start; not obtained, status N; the Rannacher start is used from the research tool as a measured practice, not from the paper). Until a published number is reproduced, the status of the transient in `validation.md` 57 is "independent solver of a different construction and closed forms", which is what the 2.8.0 research did, and says so.

## 4. Window, command line, project file

* **Project file**: no new key. The FEM is already stored as `comparison_models: ["fem"]` (`SolverOptions.to_dict`), and the same ticked model now also runs in time. No format version change; 2.7.1 reads the project as before (the file compatibility test stays). No new option is saved: the mass is fixed consistent, the integrator comes from `ProfileOptions.theta` and the animation's `theta_scheme`, the cell from the run's cell. If a measured need adds an option (for example a work bound), it is stored under a key older readers drop, as `comparison_models` is.
* **API** (`api.py`): `TIME_MODELS` gains "fem" **only as a model that runs** and not as the reference of the decision (`ref = next(m for m in TIME_MODELS if m in usable)`: the FVM, then the others; the FEM never becomes the reference); `SKIPPABLE_MODELS` is split so that "fem" stays skippable for time runs (memory refusal, no pyamg, no mesh, a work bound) when other models run next to it, and "solid3d" remains the steady-only one. `_run_profiles` gets an `elif name == "fem"` branch (`profiles.run_fem`) that turns a refusal into a profile warning, not an error that stops the others. The `RECTANGLE_ONLY` rule for a block does not apply to the FEM.
* **Jobs** (`jobs.job_transient`): the model "fem" branch with the guard (`memory.check(..., ("fem",), cell, transient=True)`), the per-step progress and cancel.
* **Command line**: `transient --model fem` (the `choices` list of `cli.py`), `--theta` as for the others, `run` and `profiles` include the FEM when ticked; the guard and the exit code 3 as for every model.
* **Window**: the Models list says "steady and time" instead of "steady state only" for the FEM (tooltip in `panels.py` near line 1571, guide section `#fem` and the table row of `help/index.html` line 246, 251, 298); the animation tab offers the FEM in its model chooser when it is ticked and available; the Results profile page draws the FEM curve as a comparison curve (theme tokens, no new colour concept) and the summary table adds its row; the Display Layer entries and the Difference view (item b) work on the frames of the FEM because they are on the run grid in the layout of the others; the surface frames appear as the Layer entry 'Surface (top)' / '(bottom)' in the animation, from `arrays["T_surface"]`. Tooltips for every new control (none new is expected: only the model chooser entry), `tests/test_tooltips.py` and `tests/test_help.py` words updated by the maintainer in the same branch.
* **Warnings** (`checks.py`): the existing FEM text (mesh, copper fill, imported copper) is shared; one new after-run warning when the integrator was forced to implicit Euler (H2) or the run was cut by a limit.

## 5. Files to touch, tests to add, effort, order, risks

### 5.1 Files and size

| Piece | File | What | Size |
| :-- | :-- | :-- | :-- |
| 1 | `pcbthermal/femcore.py` | `assemble_mass`, `Model.load_vector`, `solve_many`, the stepper class with its factor/hierarchy cache (one alive), consistent and lumped | M |
| 2 | `pcbthermal/femmesh.py` | `rho c` per element, `rho_c` in `FemMesh`, heater loads `F`, total capacity | M |
| 3 | `pcbthermal/fem.py` | read-out operators `Rcol`, `Rsurf`, `solve_transient`, energy balance, `TransientResult` building | M |
| 4 | `pcbthermal/profiles.py` | `_FEMAdapter`, `run_fem`; nothing of `plan_run` or the others | M |
| 5 | `pcbthermal/results.py` | optional `arrays` on `TransientResult` | S |
| 6 | `pcbthermal/api.py`, `jobs.py`, `cli.py` | wiring in 4 | S to M |
| 7 | `pcbthermal/memory.py` | `FEM_TRANSIENT_FACTOR`, the time law, the work bound, `check` | M (and the heavy measurement, run alone on a quiet machine) |
| 8 | `pcbthermal/checks.py`, `gui/panels.py`, `gui/animation.py`, `gui/profile_page.py`, `gui/profile_results.py`, `gui/tips.py`, `help/index.html` | texts and the chooser | S to M |
| 9 | `releases/regression-harness/` | FEM time records (time to 63 %, plateau, surface at the peak) and the FEM frozen records with surface (e4); pending file `fem-transient.json` (additions only; the others do not move) | S |
| 10 | `docs/` (maintainer): `theory.md` (a section after 2.4 / 4a with its picture), `models.md`, `validation.md` 57, `versions.md`, `CHANGELOG.md`, the guide | S to M |

Total: **L** as in the PLAN (about 9 agent days with review and battery: this note 1, code 6 (1 + 1 + 1.5 + 1.5 + 1 for the rest), measurement and law 1, review 2).

### 5.2 Tests to add (all in the branch; no test is run here)

`tests/test_fem_transient_closed_forms.py` (3.1 a to g), `tests/test_fem_transient_port.py` (3.2 a), `tests/test_fem_transient_load.py` (loads, capacity, identity), `tests/test_fem_transient_readouts.py` (operators against the steady read-out on the same field: `Rcol T` equals `solve_steady`'s column to round-off), `tests/test_fem_profile_adapter.py` (interface of the adapter, periodicity and energy per window on a small plate, equal results with theta 1 against a direct FVM-style stepper on the same matrices), `tests/test_fem_transient_memory.py` (the law: the estimate against recorded peaks, the refusal, the work bound), the stress scenarios in `tests/test_gui_stress.py`, `tests/test_help.py` and `tests/test_tooltips.py` words. Research side (`research/fem-transient-*` is not opened; the studies of the branch live in `releases/3.0.0/fem-transient/scripts/` or in the campaign folder): `study_fem_transient_integrator.py`, `study_fem_transient_amg.py` (M1, M2), `study_fem_transient_memory.py`.

### 5.3 Order of the commits

1. Mass assembly, `load_vector`, `solve_many`, the stepper in `femcore`, with 3.1 a, b, e, f and the port test. (Stops here if the port test fails.)
2. `femmesh` capacity and the identity tests (3.1 g); the first study M1 and M2 (the iteration counts and the cross-stage reuse) and the integrator study (H2) run at this point, to fix the design before the adapter is written.
3. `fem.py` read-out operators and `solve_transient`; the step response against the closed forms (3.1 c, d) and the program's models on the plain boards (3.2 d).
4. `profiles._FEMAdapter` and `run_fem`; windows and edges (3.2 e, H3).
5. `api`, `jobs`, `cli`, GUI texts and the model chooser; stress tests.
6. The memory and time law (alone, quiet machine), the work bound, the guard tests.
7. Harness records and the pending file; documents by the maintainer; the reviewer's pass.

The reviewer is called on this note first, and again after step 4 (the numerics) and at the end.

### 5.4 Risks

1. **A second solver path**: the stepper and the adapter are code with their own numerics. Mitigation: the port test against the independent research tool, the identity and energy tests, and no change of `plan_run` or of any FVM/FDM number.
2. **The first seconds**: the FEM resolves the thickness, the others do not, so the comparison tables differ there by tens of percent (the FVM -58 % at 0.3 s). Mitigation: the text says which is right and why (limit of one node per layer), a campaign row (T3) that is not a pass criterion, the Difference view labelled.
3. **Crank-Nicolson ringing** in the runner (H2) and **edge alignment** (H3): measured before the adapter; fallbacks named (implicit Euler with a warning; an optional edge list as a separate branch).
4. **Cost of the CG per step** (H1) unknown until measured: a profile run could be too slow at large meshes. Mitigation: the work bound and the verdicts; the direct path up to 30 000 unknowns is cheap.
5. **The memory law is new and heavy to measure**, on a machine that is busy: measured in series, alone (the rule of CLAUDE.md 12); until measured, a conservative `FEM_TRANSIENT_FACTOR = 2.0` is the safe default (the present transient factor), which only makes the guard refuse earlier.
6. **Heaters on a face flux and the per-heater load matrix**: a part on a thick outer layer enters through a face flux in the steady model; the load matrix must carry it. Test 3.1 g.
7. **Shared files**: `femcore`, `femmesh`, `fem`, `memory`, `checks`, `api`, `gui/panels.py` and the results pages are shared with the other 3.0.0 code branches: this branch goes after compare-differences and before the surface read-out branches, one at a time (PLAN 2.3).
8. **Capacity of the via barrel and the laminate**: read the FVM/FDM before coding (1.6), so that a difference is explained, not tuned.
9. **The published case**: none is available in the library; the rule 14 of CLAUDE.md is met only partly (3.3) and the validation text says so.

## 6. Diagram plan (CLAUDE.md 9.7: every planned model has a picture)

`releases/3.0.0/fem-transient/scripts/make_diagrams.py` (written, **not run**; no data, no program; shapes from `research/diagram_kit.py`) draws, written to `figures/fig_NN_*.png` when it is run by the branch:

| Figure | Content |
| :-- | :-- |
| fig_01_transient_section | the cross-section of the board as the FEM sees it in time: copper slabs and gaps as elements each with its `rho c`, a via barrel, a rod, a metal block and its pad, a part as a source with no body mass, the Robin films top and bottom, and the three heat paths (stored in the capacity, conducted, lost through the films) |
| fig_02_mass_matrix | one hexahedron and the row of the mass matrix: lumped (the 1/8 of the capacity at each corner) against consistent (the coupling with the seven other nodes), and the 1D picture of why the consistent mass can undershoot at a front |
| fig_03_time_methods | the amplification factor of implicit Euler, Crank-Nicolson and BDF2 against `lambda dt` (a textbook curve, marked illustrative), and the stiffness spectrum of the board by arithmetic (copper element, dielectric element, in-plane cell, the board), with the Rannacher half steps |
| fig_04_time_grid_and_edges | the time axis of a step response (ten doubling stages, one factor each) and of a profile run (constant dt, step-mean power over an unaligned edge, against the aligned reference) |
| fig_05_solver_strategy | the flow of one run: mesh, `A` and `M`, per dt the factor or the hierarchy (one alive), the step loop with warm start, the operators `Rcol` and `Rsurf`, the results, the progress and the cancel |
| fig_06_readouts_in_time | the cross-section with the three read-outs (column, surface, point) at one instant, and the operator picture `Rcol T` |
| fig_07_validation_map | which reference covers which case: closed forms, the research tool, the FVM and FDM, the windows (the design of 3.1 to 3.3 as a matrix) |
| fig_08_memory_stages | the stack of bytes per unknown by stage (assembly of `A`, assembly of `M`, `B`, hierarchy or factor, state, operators, frames), a schematic with the hypothesis H4 marked as unmeasured |

When the branch runs the script, the pictures that carry data (energy balance, step response against the references, the first seconds) are `make_figures.py` and quote only the numbers the README of the branch holds.

## 7. Decisions left to the maintainer

| # | Decision | Recommendation |
| :-- | :-- | :-- |
| 1 | Consistent mass as the default (lumped only as a test switch) | Yes: validated, better in the first seconds, 4 % of the memory law. |
| 2 | Default theta of the FEM step response: 1/2 with the Rannacher start (validated) or 1.0 like the FVM | 1/2 with Rannacher for the FEM; the campaign runs every model at the same theta. |
| 3 | The profile runner stays unaligned to the edges (the plan is shared by all models) | Yes; an optional edge list only if H3 fails, as its own branch. |
| 4 | The work bound for a profile run on the FEM and the unknown cap of the transient | After the measurement of H1 and H4 (commits 2 and 6 of 5.3); a number now would be a guess. Suggest the guard says "slow" and refuses, never silently drops the FEM when it is the only model. |
| 5 | The published case: obtain the slab tables and the Rannacher paper before the branch, or ship with closed forms and the independent research solver only | Obtain first (an open copy; the fetch tools work from the maintainer's machine); ship without them if none is found, with the validation text saying so. |
| 6 | The frequency-domain periodic state (research tool) is not brought in | Not brought in: the windows find the periodic state; it stays as the reference. |
| 7 | The capacity of the part body (thermal-capacity inventory, e11) | In this branch only if small, as PLAN 6.6 says; it needs a tooltip and a guide sentence. |

## 8. What was read and what was not verified

| Source | Status | Notes |
| :-- | :-- | :-- |
| `releases/3.0.0/PLAN.md` (branch `docs/plan-2-9-0` copy, sections 1 to 6) | R (sections about the transient) | items a, e4, e11, order, decisions 5 and 6 |
| `releases/2.8.0/fem-model/DESIGN.md` (sections 5.3 to 5.5, 7, 11 to 13 read; the rest by headings) | R in part | the branch 8 section 7, the law of 5.3 |
| `releases/2.8.0/fem-model/COMPARE_PLAN.md` | S | rows T1 to T3, the reserved sections 56 and 57 |
| `pcbthermal/femcore.py` (`assemble`, `solve`, `Model`) and `fem.py` (`solve_steady`) | R (these functions); no mass matrix exists | |
| `pcbthermal/fvm.py` `solve_transient`, `transient_from_network`, `step_responses` | R | |
| `pcbthermal/profiles.py` (`ProfileOptions`, `plan_run`, `run_windows`, `_FVMAdapter`, `run_fvm`) | R | |
| `pcbthermal/api.py` (`_step_response`, `_run_profiles`, model constants), `jobs.py` `job_transient`, `memory.py` constants and laws | R (the parts quoted) | |
| `pcbthermal/femmesh.py` (material assignment) | S (grep and the lines quoted); not read end to end | read before coding (1.6) |
| `docs/theory.md` 2.4, 2.5 | R | `docs/validation.md` transient sections were found by search, not re-read |
| `research/independent-fem-extensions/lib/transient.py` | R (class `Transient`, `lumped_mass`, `consistent_mass`) | the reference |
| `research/independent-fem-extensions/README.md` 8.3 | R | the numbers of 1.2 and 3.2 are quoted from it |
| `research/transient-reference-boards/README.md` | S (head, the lines about the first seconds) | |
| `research/fem-amg-thin-layers` README (state, sections 1, 4, 7.6, 10) and INTEGRATION | R (E8 and the reuse text) | reviewed and closed; the AMG variants are not adopted |
| `papers/` | N (index and file list only) | no paper opened; see 3.3 |
| Textbook results (stability of BDF2 with variable step, the slab with convection, the semi-infinite solid, Rannacher start) | M | formulas to be derived in the tests, the papers to be obtained |
| Everything labelled H1 to H4 and every cost estimate of 2.3 | not measured | hypotheses and arithmetic |

Nothing was run for this note: the machine is busy with batteries and reviews.
