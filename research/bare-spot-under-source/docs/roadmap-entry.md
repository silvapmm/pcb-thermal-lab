# Entries for `docs/versions.md` (chapter "Planned")

* **Vertical path of a cell without copper** (fix, after the investigation A12): the vertical conductance of a gap in a cell with partial or no copper in an adjacent layer includes the laminate of half the layer thickness on each side of the node, and the maximum under a part on the face adds half the thickness of the top layer. FVM and FDM; no new unknown. Evidence: `research/bare-spot-under-source/README.md` 6.1; the proposal P1 in `INTEGRATION.md`.
* **Laminate nodes next to bare cells** (feature, after the investigations A12 and A11): gaps above 0.5 mm get 2 to 4 nodes in the cells with a layer fill below 1 plus a margin of a gap thickness; the same mask serves the one-layer boards with patterned copper (A11). Evidence: README 6.2 and 7; proposal P2.
* **Warning: a part on bare laminate** (feature, small): `checks.py` names the layered models' low reading. Proposal P3.
