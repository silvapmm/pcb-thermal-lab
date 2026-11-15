# Branch 3 notes (feature/fem-mesh-and-guard)

- Worktree: .claude/worktrees/fem-mesh; fem-core merged (no-op or merge commit).
- pyamg 5.4.1 installed with `pip install --target <scratch>/pyamg_site` (numpy/scipy removed from it); run with PYTHONPATH=<scratch>/pyamg_site. License metadata: MIT License.
- Plan: femmesh.py (plan axes + via O-grid patches + extrusion + partial block slabs), memory law 'fem', requirements pyamg, docs, diagrams D2/D3.
