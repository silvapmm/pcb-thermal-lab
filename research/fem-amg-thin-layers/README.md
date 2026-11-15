# fem-amg-thin-layers: a cheap AMG for the thin, anisotropic layers of the FEM

**State: planned and written, NOT RUN.** The maintainer was testing the window when this was opened, so no solve, no pytest and no heavy script was executed. Every number below is quoted from the
earlier measurements (`releases/2.8.0/fem-model/REVIEW_SPEED.md`, `DECISIONS_REVIEWER.md` D) with its source; the tables of results are empty on purpose and are filled by the scripts of section 5.

## 1. Question

The finite-element solve (`pcbthermal/femcore.py`, `Model.solve`) above the direct limit is conjugate gradients preconditioned by pyamg smoothed aggregation with
`strength=("symmetric", {"theta": 0.0})`, `max_coarse=200`, V cycle. On the example board at 1 mm (276 000 unknowns) it needs **331 iterations** (70 % of a 15 s run; REVIEW_SPEED, D.2). The reviewer
measured that `strength="evolution"` cuts them to **28 to 34** but its setup costs **37 to 45 s** against 14.5 s of solve, so the total gets worse.

**Can a cheap variant (pyamg only, MIT, no new dependency, all platforms) make the whole solve (setup + CG) faster on thin, strongly anisotropic layered meshes, with the same field?** Why it matters: the
solve is the biggest cost of a FEM run, the memory guard and the 2.8.0 cap are set by it, and the transient FEM repeats solves with one matrix.

![Section of a thin-layer stack with two ways of aggregating](figures/fig_01_thin_layer_coarsening.png)

*Figure 1 (figures/fig_01_thin_layer_coarsening.png, made by scripts/make_diagrams.py, not yet generated): the thin copper slabs couple strongly through the thickness and weakly in the plane; an aggregation that ignores this (a) mixes the two, columns first (b) respects it. Sketch, not to scale.*

## 2. Hypotheses (to be tested, none is a finding)

* H1. `theta = 0.0` calls **every** link strong, so the aggregation cannot see the 1:30 element aspect ratio of a 35 um slab under a 1 mm cell; a small positive theta (0.01 to 0.25) may recover most of the evolution gain for free (the setup of 'symmetric' is cheap: 0.07 to 6 s in the reviewer's table).
* H2. A smoother that relaxes the strongly coupled direction (block Gauss-Seidel on the columns) or two sweeps may cut iterations at modest cost; needs the column ordering of the nodes.
* H3. Evolution with k = 1 and a coarser epsilon may keep most of the iteration gain at a fraction of its setup (reviewer: k 2, epsilon 4 gave 28 iterations for 40 to 45 s: the setup did not shrink with those two knobs).
* H4. The setup can be amortised: the matrix does not change with the power (any number of right-hand sides), changes little with the films (computed-h loop) and is K + M/dt in the transient. A stale or reused hierarchy stays a valid SPD preconditioner for CG, so even an expensive evolution setup may pay.
* H5. A cheaper preconditioner than AMG (ILU, column block-Jacobi) is only a baseline; expected worse in iterations on 276 000 unknowns, to be shown.

## 3. Boards and metrics

| Case key (`lib/cases.py`) | What | Unknowns (expected) |
| :-- | :-- | :-- |
| `example_1mm`, `example_2mm` | `examples.example_board()` at 1 mm and 2 mm | 276 000 (reviewer), about 40 000 |
| `plate_vias_1mm` | frozen board `plate_vias` (2 layers, 4 x 4 vias) | to be printed |
| `case2_plate_1mm` | Muzychka case 2: 50 x 50 x 10 mm, k 150 (the matrix that needs the restart) | up to 828 000 at refinement 4 (REVIEW_BRANCH4 4.2); 1 mm default to be printed |
| `thin4_1mm` | plain 4-layer 100 x 80 mm, 35 um copper, one part | to be printed |
| `big_cap` | example board at the cell whose unknown count is nearest below 800 000 (the program's FEM cap is set by the memory guard, `femmesh.unknowns`) | about 800 000 |
| the 29 frozen records | `tests/regression/data/pending/fem-records.json`, keys `board|fem|cell` | robustness only |

Metrics per (case, variant), printed by `scripts/study_amg_variants.py`: CG iterations (both passes if the program's restart fires), setup seconds, solve seconds, **total**, operator and grid
complexity (hierarchy memory proxy), peak resident GB of the child process, true relative residual, and the largest difference to the base solution in K.

**Acceptance rule (maintainer's):** total time at least **25 % lower** on the cap-size boards (`big_cap`, `case2_plate_1mm`, `example_1mm`), with no loss of robustness (all 29 frozen FEM records still
converge and case 2 at 828 000 unknowns solves) and the read-outs identical within **1e-8 K** of the current default. Also required: a peak below 4 GB per run; a result that does not repeat to
1e-8 K between two runs of the same variant is rejected (some pyamg measures use random vectors; the frozen numbers must stay frozen).

## 4. Experiments in order (cheapest first)

Each family runs on `example_2mm` first (seconds), then `example_1mm`; only the best two or three variants go to the large cases and to the 29 records.

| # | Experiment | Variants (`lib/variants.py`) | Why first / what decides |
| :-- | :-- | :-- | :-- |
| E0 | Reproduce the baseline | `base` | iterations 331 and 15 s on `example_1mm`, or the study is not comparable (reviewer's numbers are one machine) |
| E1 | Strength threshold | `sym_t0.01`, `0.03`, `0.08`, `0.25` | one parameter, same setup cost; tests H1 |
| E1b | CG tolerance | `rtol` 1e-8, 1e-9 with the true-residual check | free; keep only if the field stays within 1e-8 K |
| E2 | Smoothers | `gs2`, `jac` and, if the node ordering allows columns of equal height, block Gauss-Seidel by column (to be written after reading the ordering of `femmesh`; unused nodes make columns irregular) | tests H2 |
| E3 | Prolongation smoothing | `energy` (reviewer: 275 its, 0.5 + 9.5 s), no smoothing (487 its) | already measured at theta 0; repeat with the best theta |
| E4 | Aggregation | `lloyd`, `pairwise`, `naive` | cheap setups |
| E5 | Cheaper evolution | `evo_k1_e2`, `evo_k2_e4`, `evo_k1_e8` (proj_type variants if pyamg offers them) | H3; stop here if setup stays above 25 s |
| E6 | Other AMG families | `rs` (classical Ruge-Stueben), `root` (root-node) | whether classical coarsening sees the anisotropy by itself |
| E7 | Cycle and coarse level | `base_W`, `base_c2000`, `max_levels` | small knobs |
| E8 | Reuse of the hierarchy | `scripts/study_hierarchy_reuse.py`: same matrix with other sources; stale hierarchy with films x0.5 to x2; K + D (transient) | H4; this can make even `evo` worthwhile, a different acceptance (per solve of a series) is then stated in section 6 |
| E9 | Scaling | symmetric diagonal scaling D^-1/2 A D^-1/2 before CG; then the strength measure sees a unit-diagonal matrix | cheap; may be neutral |
| E10 | Baselines | `scipy.sparse.linalg.spilu` preconditioner, column block-Jacobi | context only, small cases |
| E11 | Near-null space | candidate vectors, `improve_candidates` (reviewer: no gain) | last; scalar diffusion has the constant as null space |
| E12 | Robustness and repeat | `scripts/study_frozen_robustness.py` for the best variant; two repeats for bitwise or 1e-8 K determinism; case 2 at 828 000 | decides the acceptance |

**Stopping criteria.** After E1 to E6, if no variant is at least 10 % better in total than `base` on `example_1mm`, close with a negative result (a documented "no cheap variant", the evolution row
quoted) and go to E8 only (reuse), which does not depend on the variant. A variant that fails one frozen record, needs more than 4 GB or differs by 1e-8 K or more is dropped at once.

## 5. Scripts (written, not run)

| Script | Purpose | Cost (estimate, not measured) |
| :-- | :-- | :-- |
| `scripts/study_amg_variants.py` | (case, variant) matrix, child process each, resumable log `out/variants.jsonl`, table | 5 to 60 s a run on the small cases, 2 to 6 min on the large; about 40 variants x 3 small cases = 40 min; 6 variants x 3 large = about 1 h |
| `scripts/study_frozen_robustness.py` | base against a candidate on the 29 frozen records | 5 to 10 min per candidate |
| `scripts/study_hierarchy_reuse.py` | E8 | 10 to 20 min |
| `scripts/make_diagrams.py` | figure 1 | seconds, no program |
| `tests/test_amg_variants.py` | tiny thin-layer system: every accepted variant reaches the direct solution, restart logic, hierarchy reuse | under a minute (tiny) |

Total, if every family runs: 2 to 3 hours of machine time, one job at a time under the lock `mkdir <scratchpad>/heavy_lock`, each job below 4 GB. These are estimates from the earlier timings, not runs.

## 6. Risks

* **Platform differences**: pyamg wheels are compiled C++ without OpenMP; the iteration counts may differ slightly across platforms and Python/NumPy versions (aggregation uses ties and, in some measures, random vectors). The acceptance (1e-8 K) is designed to tolerate this; a second platform run is requested from the maintainer, not done here.
* **Hierarchy memory**: operator complexity above about 1.6 at 800 000 unknowns would add to the peak that the memory law (`memory.py`) prices; the complexity is printed for every run. A variant that raises the peak changes the guard's law: part of the INTEGRATION.
* **Parameter names**: written from the pyamg documentation as remembered; the first run checks them against the installed 5.4.1, and a refusal is recorded.
* A variant that wins on thin boards but loses on 3D-ish cases (case 2, 10 mm thick) is a trade-off, not a fix; the rule is the cap-size boards without a loss on the others.
* Reuse (E8) is valid for CG for any matrix, but a stale hierarchy can cost iterations; measured, not assumed.

## 7. Results

Not yet. Tables to be pasted from `study_amg_variants.py --table` (one per case), the reuse table, the robustness count and the figure of iterations against setup.

## 8. What was read and what was not verified

* **Read in full for this plan:** `pcbthermal/femcore.py` `solve` (lines 352 to 408), `releases/2.8.0/fem-model/REVIEW_SPEED.md` table D.2 and `DECISIONS_REVIEWER.md` D (the numbers of section 1 are from there, not re-measured), `tests/regression/regress_boards.py` names, `tests/test_fem_gui.py` and `tests/test_fem_model.py` case 2.
* **Literature: none opened yet.** The plan is in `docs/bibliography-proposal.md` (what to read, status N for all, and the two items found in the local papers library, not opened here). No claim of the AMG literature is used above except as a labelled hypothesis.
* **Not run:** every script and test of this folder; the parameter spelling of pyamg variants; the column-ordering of the FEM nodes (needed for the line smoother); the assumed mass term of E8(c) (the transient FEM code was not read).
* **Not measured here:** any platform other than the maintainer's; the 25 % target is a rule, not a prediction.
