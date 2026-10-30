# A spot without copper under a source (A12): summary

**Question.** Does one node per copper layer, with the laminate averaged through its thickness, underestimate the temperature where the hottest cell under a part has no copper, and does a node count or a bare-spot-aware vertical resistance remove the error against a resolved 3D solid?

**Read.** Muzychka, Culham and Yovanovich (2003) Eqs. 16 to 28 (reproduced as the closed-form check of the reference); Muzychka, Yovanovich and Culham (2004) the orthotropic transformation (Eqs. 37 to 42); vendor notes and search summaries on the number of cells through a board (status S); two sources not opened (status N). No source prescribes the vertical discretisation of a laminate under a bare spot.

**Done.** An independent resolved 3D finite-volume solver (orthotropic laminate, patterned copper, films on both faces; energy balance 1e-9; mean source rise within 0.20 % of the closed series at 0.1 mm); the program's FVM, FDM, 3D solid, Lumped and Analytic against it on four stack-ups, windows of 0 to 20 mm, two cells, windows through every layer and a half-bare footprint; three real-board windows (the Stormduino, as in `zone-union`); a copy of the layered FVM with the gaps cut into sub-gaps (reproduces the program to 1e-9), a vertical correction, laminate nodes only next to bare cells, and an empirical lateral cut (rejected).

**Found.** The FVM is 3.7 to 4 % low on the typical 4- and 6-layer stack-ups (the vertical correction removes it) and 4 to 23 % low on 0.8 and 1.6 mm two-layer boards (laminate nodes next to the bare cells bring it to 0.5 to 3 %, 9 % for a window narrower than the gap); the 3D solid is within 0.2 to 2 %; the Analytic does not see windows (-11 to -63 % for windows up to 12 mm); the Lumped is erratic.

**Open.** FDM with the construction, the transient capacity of the new nodes, the Lumped and Analytic (A2, A6), the patterned copper of a one-layer board (A11) with the same mask, windows narrower than the gap.
