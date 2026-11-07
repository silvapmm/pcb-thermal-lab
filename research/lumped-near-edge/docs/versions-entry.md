# Text for `docs/versions.md` 'Planned' (after the investigation `lumped-near-edge`)

* **Lumped near a side or a corner (warning)**: a text warning for a heat source whose gap to the nearest side of the board is at most max(its side, 5 mm) (hottest node up to 22 % too cool; 57 of 58 on
  the sweep, 35 of 37 on random boards). Evidence `research/lumped-near-edge/`.
* **Lumped raster for parts under two cells**: refine the Lumped raster to half the side of the smallest part (not below 0.125 mm; -0.8 to +1.6 % on 15 cases); no frozen record moves (the smallest source of the 17 boards is 6 mm); only with a memory guard that covers the Lumped (about 1.7 KB per raster cell, one raster per board: 3.3 GB on 200 x 150 mm at 0.125 mm, extrapolated).
* Not yet (research item A23 stays open): the image-potential links of the Lumped (`research/lumped-near-edge/lib/variants.py`), measured better near a side but not robust (a compensation of its two links, large lossy sources, a cooled side +8.6 %).
