# Project-memory entries, phase 3

Ready to apply to `CLAUDE.md` when the maintainer adopts the work (updated 2026-10-23). Nothing here has been applied: a research branch does not edit `CLAUDE.md`.

## New entries for the Decisions Log (newest first)

- 2026-10-23: **Electrical side** (`research/gerber-nets`, README 4.36, 4.40): `Problem.electrical` (terminals, `vsource`, `isink`, `link`; part current and net) is the design, prototype `lib/pdn.py`; the form of the inputs is left open by the maintainer; a link between pieces of one net makes 18 times the heat of the copper in the prototype; a net in several pieces needs a current per pad and link elements for a Joule estimate, not a voltage.
- 2026-10-23: **Nets and Joule heat are feasible** (README 4.20): the net comes from the file (pads and tracks; zone fills may carry none, so use connectivity) or from a netlist, and `joule.py` turns a current into a heat map that sums exactly to I²R.
