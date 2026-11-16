# Branch 4 notes (feature/fem-model)

- Worktree .claude/worktrees/fem-model; interpreter = main checkout .venv; pyamg via PYTHONPATH=<scratch>/pyamg_site only.
- Plan: femcore.add_faces label; fem.py (solve_steady, column/surface/point read-outs, power_out by face label); api key + SolverOptions
  (fem_gap_elements, fem_refine, comparison_models/comparison_only in to_dict/from_dict + fileschema); cli; checks; harness fem records (pending add-only);
  tests; docs; diagram D4.
## Log
- fem.py written and runs (60x40 4 layer 1 mm: FEM 29.203 K, FVM 29.253, 3D 29.271); api key + SolverOptions + comparison_models done in api.py; next: results label, cli, checks, fileschema, harness, tests, docs
- cli/checks(check_fem)/api/harness(OPTIONAL fem, FEM_CAP)/make_pending --new-model/test_frozen_numbers edits done; next: generate pending fem-records.json, tests, fileschema(done in api.from_dict), compat v2.7.1, docs, D4
- pending fem-records.json written (29 records, 2/1/0.5 mm those under FEM_CAP 130000); tests/test_fem_model.py and test_format_compat_271.py written; now running them
- case 2 solved: heater on thick outer copper -> face flux (femmesh); FEM surface = paper to 0.01 K, column within 0.09 of 3D column mean
- docs edited (theory 4a, models 2.8, README, CHANGELOG, versions, decisions-log, CLAUDE.md, user guide + test_help words), fig_52_fem_flow drawn and looked at; frozen run (b1rorwbti) in progress; next: docs/license/version/help/tooltips/shortcuts/api/cli/project/memory/theory tests, git add by path, commits
- frozen: 346 passed (317 old untouched + 29 fem) at 2,1,0.5 mm, 193 s. next: wider tests
