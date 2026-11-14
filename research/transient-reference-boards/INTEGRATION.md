# Integration: what the transient reference proposes

Nothing here is implemented; every item is a proposal with its measured impact (`README.md` section 2) and the risk to the frozen numbers (`tests/regression`, the times to 63 % of the 17 harness
boards at 2, 1 and 0.5 mm). The program, the tests and the project documents are untouched by this branch.

## Summary of the evidence

| model | plateau | time to 63 % | first seconds | slow wave (peak / swing) |
| :-- | :-- | :-- | :-- | :-- |
| FVM, FDM at 0.5 mm | -0.3 to +0.1 % | -0.5 to +2.2 % | -58 to -4 % at 0.3 s (cool) | +0.3 to -3.0 % / +2.2 to -4.5 % |
| FVM, FDM at 1 mm | -0.4 to +0.35 % | -1.1 to +3.2 % | FVM -10 %, FDM +2 to +6 % on via boards | -3.4 to +1.2 % / -4.8 to +5.9 % |
| FVM, FDM at 2 mm | -4.5 to -0.4 % | up to +28 % (6 mm part = 3 cells) | -60 to -16 % | -10 to -1 % / -13 to -3 % |
| Lumped (0.5 mm) | -0.7 to +0.2 % | -0.4 to +1.3 % | -47 % (two layers), +2.5 % (vias) | -2.8 to +0.5 % / -3.9 to +1.5 % |
| Analytic (0.5 mm) | -0.6 to -0.3 % | +1.0 to +3.9 % | -59 % (two layers), -22 % (vias; -8 % read at the right point, item 3) | -3.4 to -2.0 % / -11 to -3.5 % (vias -1.9 % swing at the right point) |

The program's transient is sound where the time to 63 % and the plateau decide, and understates the first seconds on every board (one node per layer) and the swing of a wave slower than about
1 Hz by 2 to 5 % (11 % for the Analytic with vias, because it reads the wrong point: item 3). The 2.7.0 slab rule moved the time to 63 % of a small part on a four-layer board from +18.5 % to +2.2 % of the reference: it was right.

## Proposals

1. **Text for the first seconds of a transient (no number moves).** True as measured (review README 4.2: a limit of one node per layer, not a difference of definition). Where: the
   warnings of a transient run (`results.TransientResult.warnings`, the animation and the `transient` command) and of a profile run (the profile summary), for every model, fired once per run
   when a heated part lies on a layer with a laminate gap next to it (every board of two or more layers). Proposed wording (long):
   'The first seconds of the response are read too cool: each copper layer is one node that holds its copper and half of the next laminate gap, while under a part the copper heats
   first on its own. Against an independent finite-element solution at the hottest point (a sample, not a bound): a 10 mm part on a two-layer 1.6 mm board -58 / -30 / -9 % of the rise at
   0.3 / 1 / 3 s, a 6 mm part on a four-layer board -10 % at 0.3 s and -2 % at 1 s, at every cell; the time to 63 % and the steady value are within about 3 %. Read the first seconds of a
   step, and the swing of a square wave whose on or off stretch is a few seconds or less, as too low.' Short: 'First seconds read too cool (one node per layer: -58 % at 0.3 s, -9 % at
   3 s on a two-layer board); time to 63 % and steady value within 3 %.' Do not give the threshold rule `d^2 / kappa` in the text (a guide, not measured as a threshold); do not claim
   anything for waves above 1 Hz (not covered; the closed form of the profile decision handles the fast waves it moves to `average + ripple`). Also `docs/models.md` (the transient section:
   one sentence), `docs/validation.md` (a new section with Table 2 and README 4.2), the user guide (the transient and the power profile pages: one sentence each). Frozen risk: none.
   Tests: the text appears with a transient or profile run and not with a steady run; `tests/test_warning_texts_plain.py` (no folder names).
2. **Coarse cell: no new warning; add the transient numbers to the existing one.** The author's proposal (warn above a third of the narrow side) is the threshold of the existing input
   check (`checks.check_problem`, 'only N cells wide', fires on the 6 mm part at 2 mm: 3.0 cells). The +28 % in the time to 63 % is a source whose edges fall in the middle of cells; on cell
   lines the same cell reads -10 % (review README 4.4). Proposed addition to the long text of that warning: 'In a time response such a part is also uncertain in its time to 63 %
   (+26 % or -10 % at three cells on a four-layer board, depending on where its edges fall on the cells).' Frozen risk: none.
3. **Analytic with vias or heatsinks: a defect of the program, fix on a `fix/` branch.** The cause is found (review README 4.3): `analytic._local_dynamics` keeps the `points` of
   `_modal_dynamics(..., 0.0, 0.0)`, the hottest cell of the board WITHOUT vias and heatsinks, so the step responses, the profile curves and the profile decision read a point that is not the
   hottest of the board they solve (on `vias` the centre over the cluster, 2 mm from the hottest cell; steady value there 112.59 against the steady maximum 113.24 K/W). Fix: in
   `_local_dynamics`, after `solve_steady` (already computed there), take the served heater's point as the hottest cell of that steady field within the heater's footprint (the solo problem
   has only that heater powered), before the calibration and the output rows. Measured on a copy: `vias` plateau -0.62 to -0.04 %, time to 63 % +1.01 to +0.18 %, 0.3 s -21.7 to -7.9 %, wave
   swing -11.2 to -1.9 %; example board U1 +0.69 % plateau and -1.0 % time to 63 % (the other part bit-identical). It moves the Analytic step-response records of the frozen boards with vias or
   heatsinks (`example_board`, `profile_board`, `plate_vias`, `plate_lone_via` and any with a heatsink; times to 63 % by about 1 %): a pending file. To check on the branch: several parts, a
   heatsink (the heatsink warning's '5 to 7 % low' square-wave peak with two parts over vias may be the same defect), the footprint restriction of the argmax, and the steady value equal to
   `solve_steady`'s maximum to the calibration tolerance. The text-only alternative (if the fix waits): add to the Analytic transient note 'with vias or a heatsink the time curves are read
   at the hottest point of the board without them (on a test board the step response 22 % low at 0.3 s and the swing of a 20 s wave 11 % low)'.
4. **Do not add a face term to the FVM/FDM step response.** A top node split in copper and laminate (or the quasi-static face offset of the profile curves applied to the step response) would
   remove the first-seconds error, but it changes every step response and every time to 63 % of every board with a part (the 17 boards, three cells: dozens of records) and the decision of the
   profiles; the gain is only in the first seconds, where the closed-form floor of 2.6.0 already acts for waves. Recommended only after item 1 shows users meet the limit.
5. **The tool.** Record in `research/independent-fem-extensions` (on its next reopening, not here): the wave by time stepping from the steady state of the mean needs five slow time constants, and
   the periodicity of the swing does not show the missing ones (overstated peaks 0.8 to 1.6 % after six periods). Not a program issue.

## Frozen-number risk, per item

| item | moves frozen numbers | pending file |
| :-- | :-- | :-- |
| 1, 2 (texts) | no | no |
| 3 (the fix) | Analytic step responses and profile curves of boards with vias or heatsinks, about 1 % in time to 63 % | yes |
| 4 (face term) | all FVM/FDM transients with a part and the profile decision | yes, large |

## Decisions for the maintainer

* Texts 1 and 2: yes or no, on a `fix/` branch of texts. They touch `results.TransientResult.warnings`, the profile summary and the text of `checks.check_problem`; the open branch
  `fix/via-and-edge-warning-texts` changes other functions of `checks.py` (`check_model_limits`, `check_edge_laminate`, `check_reduced_edge_laminate`, `check_via_limits`): no conflict of
  content, but merge that branch first and start this one from the new `development`.
* Item 3: the reviewer recommends the fix (a defect, not a limit), on its own `fix/` branch with a pending frozen-number file.
* Whether the transient needs a second independent check on the profile decision itself (waves above 1 Hz); not done here.
