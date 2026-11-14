# Integration: wording of the metal-block warning (proposal, nothing changed in the program)

Proposal after the 1 mm results of `README.md` (to be confirmed at 0.5 mm and by the reviewer before a `fix/` branch):

* Replace "within about 5 % of the FVM in the tests" (`api.py` 1053, `gui/panels.py` 917, `help/index.html`, `docs/models.md`, `docs/validation.md` 17) by text of this form:
  "on a board with one to four pads under parts the Analytic reads the hottest point within 3 % of the FVM and the Lumped within 7 % (2 to 7 % too cool; more when the block is small against the board); the Lumped reads the temperature of a part 6 to 16 % too cool and shares the heat between pads too evenly: use the FVM, FDM or 3D solid for the temperature of a part on a block."
* Numbers to be replaced by the 0.5 mm values once run. Impact: text only, no number moves; the warning stays one line per run.
* Decision for the maintainer: warn per model (Analytic 3 %, Lumped 7 % and the part limit) or keep one text.
