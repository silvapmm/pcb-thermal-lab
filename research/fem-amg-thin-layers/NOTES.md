# NOTES (working log, in English)

## Log (tree development 6c225276, machine of the maintainer, pyamg 5.4.1, nice 10)
* pyamg 5.4.1 names checked: smoothed_aggregation_solver/ruge_stuben_solver/rootnode_solver arguments exist as used. pyamg default smoother is block_gauss_seidel (symmetric) = pointwise on CSR: `base` passes none, like the program. `aggregate='pairwise'` REFUSED by 5.4.1 with csr_matrix and with csr_array (TypeError AggOp).
* pyamg prints "Inner denominator was zero." to stdout on `rs`: parent now takes the last JSON line.
* E0: program solve (Model.solve force='cg') at example_1mm = 275 724 unknowns: 280 CG iterations, 9.7 s CG, 11.2 s whole solve incl. assembly, balance 1.000000000003. The reviewer's 331 is NOT reproduced here (280). base run of the study: 280 its, 0.51 + 9.64 s; field differs from the program's run by 1.7e-10 K (not bitwise repeatable).
* example_2mm has 67 229 unknowns (README guessed 40 000).
* E1..E7 on example_2mm and a subset on example_1mm: no variant gains 10 % (best 0.97 of base). Stopping rule: negative for E1-E6.
* Unplanned finding: a column (vertical line) block solve as preconditioner (`colblock` in study_extras.py) gives 0.55 of base total at 1mm, 0.16 at 2mm.
