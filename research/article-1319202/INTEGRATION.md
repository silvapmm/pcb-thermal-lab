# Proposal after the paper is read

Nothing here is done; it waits for the PDF (status N now).

1. Read it (render to images or use the OCR tool; reviewer compares with the page image). Add `[Muzychka2004Influence]` to `research/theory/BIBLIOGRAPHY.md` with equation and page numbers, numbers read from plots marked "plot".
2. Pick one published multi-source case on a finite convectively cooled rectangle (the paper's own example, or the five-source cross of the related Muzychka papers). Reproduce it with an independent solver in `lib/` (own influence-coefficient code, checked against a closed form and an energy balance).
3. Run the program's models on the same case (FVM at 1, 0.5, 0.25 mm; FDM; Lumped; Analytic with the Robin edge) on the closest representable layout (a single isotropic or orthotropic layer, h on the faces, h_side on the edges), and the independent hexahedral FEM of `research/independent-fem-edge` as a third reference.
4. Report the agreement and limits; if the method gives a cheap neighbour term better than the Lumped superposition, write it as a proposal with measured impact. No edit of `pcbthermal/` from the research branch.
5. Add the folder to `research/README.md` and `ROADMAP.md` only if the maintainer decides to open it as a topic branch.
