# Article 1319202: influence coefficient method (Muzychka)

Literature check of IEEE Xplore document 1319202. Status of the source: **N (not obtained)**; everything below comes from metadata and the abstract.

## 1. What it is (S: Crossref, Semantic Scholar, OpenAlex, author page snippet)

* Title: *Influence coefficient method for calculating discrete heat source temperature on finite convectively cooled substrates*.
* Author: Y. S. Muzychka (Memorial University of Newfoundland).
* Venue: Proc. ITherm 2004 (9th Intersociety Conference on Thermal and Thermomechanical Phenomena in Electronic Systems), Las Vegas, 1-4 June 2004, pp. 394-402, IEEE. DOI 10.1109/ITHERM.2004.1319202.
* Journal version: IEEE Trans. Components and Packaging Technologies 29 (3) (2006) 636-643 (from citing reference lists; DOI of the journal version not confirmed).
* Licence: IEEE, closed (OpenAlex and Semantic Scholar: no open copy, no repository full text). The IEEE page returned no content to an automated fetch; the author's page could not be reached (connection refused).
* Abstract (OpenAlex, word order partly lost, our paraphrase): a simple superposition method for the temperature of discrete heat sources on a finite substrate cooled by convection. It uses one single-source solution (mean or maximum temperature of an eccentric uniform rectangular source) and influence coefficients that give the effect of the position and strength of the other sources; the coefficients are local thermal resistances weighted by source strength; for N sources there are the self term and N-1 neighbour terms; isotropic, orthotropic and compound systems; convection in the plane (edge cooling) is handled for isotropic and orthotropic systems; expressions for the centroid and the mean source temperature.
* Reference list (Crossref, 16 items): Negus and Yovanovich infinite images (1983 to 1987), Hein and Kadambi chip-package analyses, Ellison, Morse and Feshbach, Muzychka 2003 (compound/orthotropic), Muzychka, Yovanovich, Culham (AIAA 2003-4187; J. Heat Transfer 2003; J. Thermophys. 2004), Lee/Song/Au/Moran on spreading.

## 2. Relevance to the program (judged from the abstract only)

| Program section or folder | Link | Relation |
| :-- | :-- | :-- |
| `docs/theory.md` 6 (Analytic, cosine series, Robin edge eigenfunctions) | the same family of solutions (Muzychka, Culham, Yovanovich 2003 Part II is already the source of the edge basis) | extends: a closed-form multi-source superposition with convective edges on a rectangle |
| `docs/theory.md` 5 and 7.5 (Lumped rings superposed per heater; spreading of several sources) | the influence coefficient is the same idea as superposing the response of each heater | could give an independent check of the neighbour terms |
| `research/paper-case-studies` (Muzychka cross of five sources, Lee plate) | the five-source cross belongs to the same author's work | possibly the origin of cases already reproduced; not verified |
| `research/effective-conductivity`, `research/analytic-edge-and-transient` | edge cooling on a finite plate | independent reference for the edge error of the Analytic model |
| neighbour effect on fast waves (`fast-wave-oscillation`, limit "the neighbour's wave is not added") | superposition of neighbours | indirect |

It supports the program's approach (superposition, rectangular flux channel with edge cooling); it does not contradict a statement of the theory that we can see. Nothing is claimed beyond the abstract.

## 3. Can we get it?

* Open copy: none found. Not in `papers/` (the local library holds the 2006 Muzychka, Yovanovich, Culham edge-cooling paper, a different one, and the 2003 and 2004 compound papers; `grep` for the title and the DOI found nothing).
* Action for the maintainer: download the IEEE PDF through the institution to `papers/pdf/Muzychka2004InfluenceCoefficient.pdf` (key proposed `[Muzychka2004Influence]`), or ask the author (his page lists it); the journal version (2006) is an equal alternative. The OCR tool then converts it and the reviewer compares pages with the image.

## 4. Proposal (INTEGRATION.md)

See `INTEGRATION.md`: once read, reproduce one published case, then run the models on it.

## 5. What was read and what was not verified

* Read in full: nothing (N). From summaries (S): the metadata and abstract above, the reference list from Crossref, the venue and pages from the author's list quoted by a search snippet.
* Not verified: every formula, every case, every number; the journal DOI; whether the ITherm and journal versions are the same text; the relevance table is a judgment from the abstract.
* Not stored: no text of the paper is in the repository.
