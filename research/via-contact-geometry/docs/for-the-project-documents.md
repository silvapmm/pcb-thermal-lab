# Text for the project documents (only when the work is adopted)

## `docs/theory.md` 2.6, the barrel length

The barrel of a via between the nodes of two copper layers is a conductor of length `d + 0.5 t_bar`, with `d` the dielectric gap and `t_bar` the mean copper thickness of the two layers: the copper nodes are at the mid-planes of the layers, a full `t_bar` would count the barrel through the whole copper thickness, but the plane around the barrel shunts it there, so the measured effective extra length is half of the thickness per gap (axisymmetric unit cell, 720 boards: best `a` 0.44 to 0.48 for copper of 35 um and more; the program's earlier `d` alone read the via resistance 9 % too low on average on four- and six-layer boards, 33 % at worst). The constant is measured against one reference and is not derived; a 3D solid (not converged in the cell) shows 40 to 50 % of the deficit.

## `docs/theory.md` 2.6, the contact

The resistance between a plane and the barrel is carried by the lattice of the footprint cells (the well is nearly infinite by construction), so the contact is set by the weights: weights proportional to the sheet conductance of the cells, and a layer whose rim touches no copper is not coupled. On a plane with copper over part of the footprint this removes the numerical cold spot and the over-read of a via just outside a copper edge; a via at the corner of a copper region is read the unsafe way by about 2.3 K at 1 mm (3.8 % of the rise) until a sector well is used.

## `docs/validation.md`

A section with the tables of `research/via-contact-geometry/README.md` 2.2 (the sweep), 3.3 (the fifteen boards, in K and in per cent of the rise) and 3.4 (the cold-spot board).
