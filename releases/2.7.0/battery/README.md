> Tester report kept as a release record: the final battery of 2.7.0 on tip fd49b969, with the later gates added at the end.

# 2.7.0 final battery (tip fd49b969, detached worktree, open boards and Gerber samples linked)

- Whole battery: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests --timeout=900 --timeout-method=thread`
  last line: `3432 passed, 9 skipped, 2 xfailed, 1 warning in 2418.13s (0:40:18)` (02:09 to 02:49; load 1.5 to 2.5, swap flat at 986 MB). The warning is the deliberate numpy overflow of test_save_nonfinite.
- `PCBT_FROZEN_CELLS=2,1,0.5 tests/regression` (four pending files present): 317 passed in 128.9 s.
- `PCBT_COMPAT_V245=1 tests/test_format_compat_245.py`: 5 passed. `PCBT_SCAN_KEY_VALUES=1 tests/test_no_secrets.py`: 4 passed.
- Research tests: analytic-edge-and-transient 9, laminate-slabs-and-local-rule 7, cut-cell-links 30, lumped-zones-adoption 20, lumped-via-groups 16, fast-wave-oscillation 13, imported-copper-edge-film 5 + 1 skipped, strong-edge-laminate 6, via-well-sheet-order 2, imported-via-rim 2, small-model-defects 9, laminate-edge-band 7, via-edge-image 7, theory 5: all passed. fdm-inset-edge and independent-fem-edge have no tests directory.
- Failures: none.

## Later gates (figures from docs/versions.md, 'How 2.7.0 was tested')

- Refreeze branch: `3445 passed` in 40 min 48 s (whole battery).
- Merge of `fix/gui-warning-icons-270` with `develop` 5d95c54f: `3478 passed, 9 skipped, 2 xfailed, 1 warning in 41 min 34 s`; the commits since are documents only.
- On that tree: 5 passed on `tests/test_format_compat_245.py` with `PCBT_COMPAT_V245=1`, 4 passed on `tests/test_no_secrets.py` with `PCBT_SCAN_KEY_VALUES=1`, 317 passed on `tests/regression` at 2, 1 and 0.5 mm against `v2.7.0.json`.
- Other records: `bisect-stale-failures.md` (the 11 stale expectations of candidate 06cb04d6) and `candidate-2-6-1.md` (the 2.6.1 candidate battery, before the version was renamed 2.7.0).
