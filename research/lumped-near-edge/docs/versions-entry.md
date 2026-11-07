# Text for `docs/versions.md` 'Planned' (after the investigation `lumped-near-edge`)

* **Lumped near a side or a corner (warning)**: a text warning for a heat source whose gap to the nearest side of the board is at most max(its side, 5 mm) (hottest node up to 22 % too cool; 57 of 58 on
  the sweep, 35 of 37 on random boards). Evidence `research/lumped-near-edge/`.
* **Lumped raster for parts under two cells**: refine the Lumped raster to half the side of the smallest part (not below 0.125 mm), after a check on the frozen boards and with the memory guard.
* After a further review only: the image-potential links of the Lumped (`research/lumped-near-edge/lib/variants.py`), measured better near a side and not for large sources.
