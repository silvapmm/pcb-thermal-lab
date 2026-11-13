# Text for `docs/theory.md` (FDM, in-plane face) if the correction is adopted

**Adopted**: the text of `docs/theory.md` 3 (`fix/fdm-copper-edge-faces`) replaces this draft; it adds that only the faces whose nodal fill differs from the face fill are replaced.

The copper fill of a node is the covered share of its control volume and carries the capacity, the vertical links, the faces to the air and the sources. The in-plane face between
two nodes of a copper layer does not take its sheet from the two nodal values: the cell between the two nodes is uniform along the face, so the sheet of the face is
`S_face = (A_face + B f_face) c_face`, with `B = (k_cu - k_lam) t_cu`, `A` the sheet of the node with no copper (laminate and the part of the sub-gaps the node keeps), `f_face` the
mean copper fill of the cells flanking the face and `c_face` the mean outline cover of the two nodes. A copper edge that falls on a node then leaves the face on the bare side bare and
the face on the copper side copper; with the harmonic mean of the nodal sheets the node on the edge read half copper and the first copper link 0.67 of the copper sheet. The picture is
`research/fdm-inset-edge/figures/fig_01_copper_edge_between_nodes.png`; sources: none beyond the program's own comparison (finite-element limits and the independent 3D solver of
`research/fdm-inset-edge/README.md` 3 and 5).
