# Integration: what this investigation proposes for the program

No defect was found in the models (README sections 1 to 5), so nothing here needs a `fix/` branch with a pending file. The numbers of the board maximum do not move with any proposal; only a warning is proposed.

## P1 (optional, small): warn when part of the footprint of a part is on bare laminate, not only the centre

* **Finding.** `checks.py` (the group that starts near line 865) tests the fill of the cell under the **centre** of the part. On `drawn_ell` the centre is on copper and the corner (1.2 x 1.2 mm, 9 % of the 4 mm footprint) is bare: no warning, while the board maximum reads 6 to 36 % below the resolved value at 1 mm and 11 to 17 % at 0.2 to 0.8 mm (README sections 2 and 3).
* **Proposal.** Add a second test: the share of the footprint on bare laminate (fill below the existing threshold) above a few percent, with a text that says the board maximum of the part (not the mean) reads low and that the heater mean is reliable. Alternatively, extend the existing text of the centre test to "the hottest cell of the part".
* **Impact.** Warnings only; no number moves; no pending file. Needs a test on `drawn_ell`, `hatched_copper` and a part wholly on copper (silent), and the text in the user guide and the tooltip rules of CLAUDE.md section 10. Not measured on the 17 boards of the frozen set: which of them would start to warn was **not** counted here.
* **Decision for the maintainer**: whether the read-out deserves a warning, since the part rows already carry the "bare-laminate" statements of the laminate rule.

## P2 (documentation): say that the board maximum of a part over a copper edge is not mesh-converged

For `docs/validation.md` or `docs/theory.md` (laminate rule section): the heater mean of a part that is partly over bare laminate converges (FVM and FDM within 4 % of the FEM at 1 mm); the board maximum does not (scatter of 30 K between cell sizes of 2, 1 and 0.5 mm, figure 2), because the controlling length (about 0.3 mm for 35 µm copper on 1.6 mm laminate) is below the cell. Text in `docs/` is not written here; the README sections 2 to 4 are the source.

## Not proposed

A change of the FVM or the FDM discretisation: the FVM and the FDM agree from 0.8 mm down (87 to 94 K), and the gap at 1 mm is one grid position against the copper edge.
