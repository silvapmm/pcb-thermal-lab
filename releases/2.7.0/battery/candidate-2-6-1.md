> Tester report kept as a release record: the battery of the 2.6.1 candidate (detached worktree at 24882dfb); the version was later renamed 2.7.0.

# Battery on develop 24882dfb (2.6.1 candidate)

Whole battery: 2 failed, 3277 passed, 8 skipped, 2 xfailed, 1 warning in 2380.79s. Load at start 1.2, at end about 3.2.

## The two failures
`tests/test_solid3d_verification.py::test_circular_source_spreading_resistance_matches_the_published_table[0.2]` and `[0.3]`:
`MemoryGuardError: 3D solid, 105000 unknowns, about 10.7 GB at 1 mm, more than the 9.6 GB allowed (60 % of 16 GB)`; the base was 7.16 GB.

Cause: an order effect of the memory guard, not a model defect.
- Run alone on 24882dfb: 2 passed (22 s).
- `memory.baseline_bytes()` is read once per process, at the first estimate. In a whole battery the pytest process is large when an in-process call reads it. A spy plugin on a reproduced run showed the baseline set to 3.19 GB after `tests/test_model_io.py::test_cli_run_writes_outputs` (CLI run in-process); in the full battery it was 7.16 GB.
- Forcing the baseline on both trees: v2.6.0 and 24882dfb give identical results: 3.19 GB passes, 7.156 GB fails, both tests, both trees. So the test is fragile to the baseline on v2.6.0 too. It is not a 2.6.1 regression; no bisect needed.
- The v2.6.0 battery passed only because the process was smaller when the baseline was frozen.

Suggested test fix (for the executor, not done): the test should fix the baseline (`memory.reset_baseline()` with a fake `resident_bytes`, as `tests/test_memory.py` does) or use `solid3d.size_limit` window.

## Other runs (all on the worktree)
- `PCBT_FROZEN_CELLS=2,1,0.5 tests/regression`: 317 passed (144 s)
- `PCBT_COMPAT_V245=1 tests/test_format_compat_245.py`: 5 passed
- `PCBT_SCAN_KEY_VALUES=1 tests/test_no_secrets.py`: 4 passed
- research tests: analytic-edge-and-transient 9, laminate-slabs-and-local-rule 7, cut-cell-links 30, lumped-zones-adoption 20, fast-wave-oscillation 13: all passed
