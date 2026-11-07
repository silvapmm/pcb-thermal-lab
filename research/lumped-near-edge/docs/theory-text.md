# Text for `docs/theory.md` 5 (Lumped): a part near a side of the board

The ring network of a heater is built on the cells of the board: the rings are the contours of the distance to the footprint cut by the board, the cell counts of a ring, its contour length
(area over thickness) and its edge loss are those of the cells that exist, so a ring that a side clips is a partial ring with the right area and the right loss. What the construction cannot hold is the
shape of the flux: near an insulated side the heat of the part is pushed away from it (method of images: the field is that of the part plus its mirror image), the equipotentials are not the circles the rings
follow, and the link of the footprint to the first ring, which carries most of the deficit, is that of the part alone. The result is a deficit of the footprint temperature that grows as the part approaches a side (hottest node -9 % at a side,
-15 % in a corner, mean over 5 mm and 10 mm parts on a 100 x 80 mm two-layer board, against the FVM; as low as -22 %), and that falls to the uniform-sheet value (-2 to -3 %) at a gap of about 30 mm. A part smaller than
the 0.5 mm raster cell is spread over the cells it touches (the FVM does the same): -19 to +6 % at 0.5 mm for parts of 0.1 to 0.5 mm, position dependent; a raster of half the side removes it.
Sources: method of images, Carslaw and Jaeger (from memory, status M); the numbers are `research/lumped-near-edge/README.md` 3 and 6. Pictures: `research/lumped-near-edge/figures/` 1 and 2.
