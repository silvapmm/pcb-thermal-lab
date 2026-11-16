# Branch 3 notes (feature/fem-mesh-and-guard)

- Worktree: .claude/worktrees/fem-mesh; fem-core merged (no-op or merge commit).
- pyamg 5.4.1 installed with `pip install --target <scratch>/pyamg_site` (numpy/scipy removed from it); run with PYTHONPATH=<scratch>/pyamg_site. License metadata: MIT License.
- Plan: femmesh.py (plan axes + via O-grid patches + extrusion + partial block slabs), memory law 'fem', requirements pyamg, docs, diagrams D2/D3.

## Done (all committed on feature/fem-mesh-and-guard)
- femmesh.py + tests/test_fem_mesh.py (15 tests), memory law + tests/test_fem_memory.py (6), measure_fem_law.py (21 runs: CG 6.4-7.0 kB/unknown, direct 9.6-12.3).
- pyamg>=5.4 in requirements.txt, README row, About box sentence + test_help, CLAUDE.md, CHANGELOG, theory 4a, models 2.8, versions.md, figures 50 (from the program's mesh) and 51.
- Checks run: test_docs, license header, version, help, tooltips, test_memory, fem tests (with and without pyamg), frozen numbers at 2 mm (153 passed), research/theory tests.
- Open for the reviewer: point value of a part over bare laminate (drawn_ell) is mesh-sensitive; refine/gap options not yet in SolverOptions (branch 4).
