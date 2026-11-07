# Sources of the cut-cell links study: reading status and what is used

Text for `research/theory/BIBLIOGRAPHY.md` (that file is on `develop` and is not edited from this branch; the statuses below are to be copied into it by the reviewer or the maintainer).
Status: R read in full (the pages named), S from a summary, M from memory, N not obtained.

| Key | What was used | Status here |
| :-- | :-- | :-- |
| [SchwartzEtAl2006] | divergence over the cut volume (eq. 1, 4, 5), truncation estimates O(h/kappa) on cut cells (eq. 11 to 13, p. 7), the remark that a linear three-face interpolation of the partial-face flux was unstable (p. 5) | R for printed pages 1 to 16 (read by the earlier folder `rotated-square-3d`; not re-opened here) |
| [CalhounLeVeque2000] | centroid unknowns, capacity function, no stability restriction from small cells for implicit steps (Claim 2, p. 178 as quoted by the task; the earlier folder read pp. 143 to 151) | R for pp. 143 to 151; Claim 2 on p. 178 is **not** among the pages read there, so it is M here |
| [JohansenColella1998] | partial-face flux with the aperture (eq. 15, 16), reproduced Problem 1 | R for pp. 1 to 18 (earlier folder) |
| [BarrettEtAl2022] | the Robin condition on a cut cell: boundary flux with the signed distance of the cell centre to the boundary (eq. 12 to 14), attributed there to Bochkov and Gibou | R for sections 1 to 3.1 and 3.3 (earlier folder) |
| [BochkovGibou2019] | the aperture with the film at the boundary, symmetric scheme | **N**: the journal page is paywalled; `core.ac.uk/download/199470815.pdf` (found by search) answers HTTP 403 from the fetch tool; a search finds only the abstract (two finite-volume schemes for Poisson-type equations with Robin conditions on piecewise smooth boundaries, one symmetric and one not, with a hierarchical geometric reconstruction for the integrals over implicitly defined geometries; INIS record) and the MaRDI entry. What the study implements as "aperture + film" is the form written in [BarrettEtAl2022] eq. 12 to 14, not the paper's own text |
| [PapacEtAl2010] | the symmetric Robin discretisation on a Cartesian grid | **N** (search record and abstract page only) |

Nothing of a third party is stored in the repository.
