# Text for the project documents (only when the work is adopted)

## `docs/theory.md` 2.6, the barrel length

The barrel of a via between the nodes of two copper layers is a conductor of length `d + 0.5 t_bar`, with `d` the dielectric gap and `t_bar` the mean copper thickness of the two layers: the copper nodes are at the mid-planes of the layers, a full `t_bar` would count the barrel through the whole copper thickness, but the plane around the barrel shunts it there, so the measured effective extra length is half of the thickness per gap (two independent references: an axisymmetric unit cell over 720 boards, best `a` 0.44 to 0.48 for copper of 35 um and more, and a Cartesian 3D cell with the plating resolved on 15 boards, best `a` 0.50 to 0.73 with the planes whole and 0.50 to 0.82 with the inner planes drilled; with `a` = 0.5 the FVM is within -6.5 % of the via resistance on the second, on the unsafe side; the program's earlier `d` alone read it 5 to 29 % too low; `research/via-contact-geometry` README 2.2 and 7.1). The positive error of thin, two-layer or solder-filled boards with a small barrel resistance is the target radius of the well (section 1.5), not the barrel. The rule applies to the FVM, FDM, Lumped and Analytic; the 3D solid draws the barrel through its copper slabs.

## `docs/theory.md` 2.6, the contact

The resistance between a plane and the barrel is carried by the lattice of the footprint cells (the well is nearly infinite by construction), so the contact is set by the weights. A layer whose rim (the circle of the drill) touches no copper is not coupled: the barrel is not connected to copper it does not touch, and the over-read of a via just outside a copper edge (+2.9 K at 1 mm on a 10 mm board) becomes a small loss of the via effect on the safe side (-1.05 K). The weights by sheet conductance, which would also remove the cold spot of section 2.2, were not adopted: they read a via at the corner of a copper region the unsafe way by at least 2.3 K at 1 mm (3.8 % of the rise) and a via beside a part on bare laminate 84 to 93 % too weak (reviewer, `research/via-contact-geometry` README 7.2).

## `docs/validation.md`

A section with the tables of `research/via-contact-geometry/README.md` 2.2 (the sweep), 7.1 (the independent 3D cell), 3.3 (the fifteen boards, in K and in per cent of the rise) and 3.4 (the cold-spot board).
