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
| Analytic (0.5 mm) | -0.6 to -0.3 % | +1.0 to +3.9 % | -59 % (two layers), -22 % (vias) | -3.4 to -2.0 % / -11 to -3.5 % |

The program's transient is sound where the time to 63 % and the plateau decide, and understates the first seconds on every board (one node per layer) and the swing of a wave slower than about
1 Hz by 2 to 5 % (11 % for the Analytic with vias). The 2.7.0 slab rule moved the time to 63 % of a small part on a four-layer board from +18.5 % to +2.2 % of the reference: it was right.

## Proposals

1. **Warning text for the first seconds of a transient (no number moves).** Where: the post-run warnings of the transient and profile results (`results.TransientResult.warnings`, the profile
   summary), next to the Analytic heatsink and via notes. Text: the response of a part is read too cool for the first moments because a layer is one node that holds its copper plus half of the
   adjacent laminate; measured against a finite-element solver at the hottest point: two layers -58 / -30 / -9 % at 0.3 / 1 / 3 s (a 10 mm part), four layers -10 / -2 % at 0.3 / 1 s (a 6 mm
   part), at every cell; the time to 63 % and the plateau are not affected (within 3 %); a wave with a shortest stretch under about 3 s (two layers) or 0.3 s (four) should be read with that in
   mind. Fire only when a transient or a profile is run and a part has a heat capacity under it (a plain rule: half gap `d` over a part: `d^2 / kappa` above the shortest time of interest). Frozen
   risk: none (text). Tests: the warning appears only with a transient run; texts name the numbers above.
2. **Warning for a transient cell that is coarse for the part (no number moves).** At 2 mm a 6 mm part (3 cells) reads -4.5 % in the plateau and +28 % in the time to 63 % (FVM and FDM); the
   decision's step response already shrinks the cell to a quarter of the narrow side of the part with a profile (`api.response_cell_mm`), but the animation and `transient` command run at the
   cell of the user. Proposal: warn when the transient cell exceeds a third of the narrow side of a heated part (quote the +28 % and -4.5 %), name the control (`uicontext`). Frozen risk: none.
3. **Analytic with vias: add the measured offset to the existing transient warning (text), and look at the cause on a `fix/` branch.** The Analytic reads about 1 K/W cooler than the FVM at every
   time on the via board (22 % at 0.3 s, 0.9 % at the plateau, 11 % on the swing of a 20 s wave; the same board without vias is within 0.5 %); the existing note says 'couplings instead of
   smearing' but no number. Cause not isolated (the local modal system of `analytic_local.py` and its single factor on the via couplings are the candidates; the series length is not). A fix
   would move the Analytic transient records of the via boards (`plate_vias`, `example_board`, `profile_board`: times to 63 % by about 1 %) and needs a pending file; do not adopt before the
   investigation finds the cause. Frozen risk of the text: none.
4. **Do not add a face term to the FVM/FDM step response.** A top node split in copper and laminate (or the quasi-static face offset of the profile curves applied to the step response) would
   remove the first-seconds error, but it changes every step response and every time to 63 % of every board with a part (the 17 boards, three cells: dozens of records) and the decision of the
   profiles; the gain is only in the first seconds, where the closed-form floor of 2.6.0 already acts for waves. Recommended only after item 1 shows users meet the limit.
5. **The tool.** Record in `research/independent-fem-extensions` (on its next reopening, not here): the wave by time stepping from the steady state of the mean needs five slow time constants, and
   the periodicity of the swing does not show the missing ones (overstated peaks 0.8 to 1.6 % after six periods). Not a program issue.

## Frozen-number risk, per item

| item | moves frozen numbers | pending file |
| :-- | :-- | :-- |
| 1, 2, 3 (texts) | no | no |
| 3 (the fix) | Analytic transients of boards with vias, about 1 % in time to 63 % | yes |
| 4 (face term) | all FVM/FDM transients with a part and the profile decision | yes, large |

## Decisions for the maintainer

* Texts 1 to 3: yes or no, on a `fix/` branch of texts with `checks.py` (merges before any other branch that touches it).
* The Analytic-with-vias transient offset: a research question (cause) before a fix.
* Whether the transient needs a second independent check on the profile decision itself (waves above 1 Hz); not done here.
