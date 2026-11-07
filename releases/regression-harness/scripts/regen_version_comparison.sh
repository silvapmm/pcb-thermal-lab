#!/bin/sh
#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
# Regenerates docs/version-comparison.md from the result sets in out/ (see make_version_comparison.py).
# Order: study_run_suite.py --label v2.5.0 (the tree of the release); study_baseline_release.py / compat_run.py for every tag (labels v2.0.0 ... v2.4.5);
# study_references.py; then this script, from the repository root.
O=research/release-regression-245/out
${PY:-.venv/bin/python} research/release-regression-245/scripts/make_version_comparison.py \
  $O/v2.0.0.json $O/v2.1.0.json $O/v2.2.0.json $O/v2.3.0.json $O/v2.4.0.json $O/v2.4.1.json $O/v2.4.2.json $O/v2.4.3.json $O/v2.4.4.json $O/v2.4.5.json $O/v2.5.0.json \
  --link ../research/release-regression-245/figures/ --references $O/references.json \
  --pair-notes research/release-regression-245/reference/version_notes.json \
  --table research/release-regression-245/reference/expected_shifts_2.5.0.json --out docs/version-comparison.md \
  --note "**How to read this document.** Each version is run on the same 17 test boards with the same five models; the document shows what moved between consecutive versions and why. The tables of mean error against an independent 3D conduction solver (below) are the at-a-glance summary: lower is better. Between two versions, a paragraph in the section of that pair says what was implemented and why the numbers moved. The last pair, v2.4.5 to v2.5.0, is the release." \
  --note "**At a glance (error of the rise against the independent solver, mean over the four reference boards, cell 1 mm).** FVM 4.80 % (v2.0.0) to 2.21 % (v2.4.2) to 1.01 % (v2.4.5, laminate nodes for patterned copper); FDM 8.75 % to 6.64 %; Lumped 9.30 % to 7.01 %; Analytic 23.84 % to 22.98 %; 3D solid 10.59 % (v2.3.0) to 0.07 % (v2.4.2). From v2.4.5 to v2.5.0 these four reference boards do not move at all (they have insulated edges, one source and no vias), so the table does not show the gains of the 2.5.0 work; those are in the section of the last pair and in docs/validation.md." \
  --note "**Honest limit of this comparison.** The 17 harness boards reach only part of the 2.5.0 features. The Gerber reader, the import window, imported copper, the parts from the paste layers, the exposed-pad heat source and the project format 2 need an import that no harness board has; the memory guard, the memory law and the warnings change refusals and text, not temperatures; the laminate options keep their defaults; the face term acts on the profile curves, which the harness does not run; the laminar convection default applies to new projects only. Only the zonal Lumped model, the Lumped footprint potentials and the Analytic Robin edge move numbers here (all three were held by pending-shift files until the refreeze), and the symmetric LU moves the last bits of the sums."
