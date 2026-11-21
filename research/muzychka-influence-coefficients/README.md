# Influence coefficients for several sources on a convectively cooled plate (Muzychka)

Literature note on the influence coefficient method of Y. S. Muzychka (ITherm 2004, journal version IEEE Trans. CPT 2006), key `[Muzychka2004Influence]` in `research/theory/BIBLIOGRAPHY.md`. **The article itself was not obtained (status N)**; what is known of its content comes from the metadata, the abstract (S) and a secondary source read on the page image (a doctoral thesis supervised by the same author, section 2 below). Nothing was run; the plan to reproduce a case is in `INTEGRATION.md`.

## 1. The source

* Title: *Influence coefficient method for calculating discrete heat source temperature on finite convectively cooled substrates*; author Y. S. Muzychka (Memorial University of Newfoundland).
* Conference version: Proc. ITherm 2004 (Ninth Intersociety Conference on Thermal and Thermomechanical Phenomena in Electronic Systems), pp. 394-402, doi 10.1109/ITHERM.2004.1319202 (Crossref record).
* Journal version: IEEE Trans. Components and Packaging Technologies 29 (3) (2006) 636-643, doi 10.1109/TCAPT.2006.880477 (Crossref record; the DOI was "not confirmed" in the first version of this note). Whether the two texts are the same was not checked.
* Access: IEEE, paywalled. No open copy was found (OpenAlex, Semantic Scholar, a web search; the IEEE page gives nothing to an automated fetch). Not in the local `papers/` (it holds other Muzychka papers: [Muzychka2003], [Muzychka2003Part1], [Muzychka2003Part2], [Muzychka2004Orthotropic], [Muzychka2006EdgeCooling]).
* Abstract (S, our paraphrase): a superposition method for the temperature of several discrete sources on a finite substrate cooled by convection; one single-source solution (mean or centroid temperature of an eccentric uniform rectangular source) plus influence coefficients that carry the effect of the position and the strength of the other sources; isotropic, orthotropic and compound substrates; convection in the source plane for isotropic and orthotropic substrates; expressions for the centroid and the mean source temperature.

## 2. What a secondary source shows (read on the page image)

S. M. Razavi, *Advanced thermal analysis of microelectronics using spreading resistance models*, PhD thesis, Memorial University of Newfoundland (2016), supervisors S. Kocabiyik and Y. S. Muzychka, open copy in the university repository (handle 20.500.14783/9133), key `[Razavi2016Thesis]`. Section 2.4, printed pages 55 and 56 (PDF 78 and 79), compared with the page image:

* Eq. 2.71: the mean temperature excess of source `j` is the sum over the sources `i` of `Q_i f_ij`.
* Eq. 2.72: `f_ij` is the mean, over the area of source `j` (centre `X_c,j`, `Y_c,j`, sides `c_j`, `d_j`), of the Fourier-series solution for source `i` alone: a constant `B_0^i`, two single series in `cos(lambda_m X_c,j) sin(lambda_m c_j / 2) / (lambda_m c_j)` and in `delta_n`, and a double series. This is the form of the eccentric-source solution of [Muzychka2003] (status R), averaged over another source's footprint; the coefficients `B^i` are not defined in section 2.4 and were not read.
* Eq. 2.73 and 2.74: the matrix form `theta = F Q` and the reciprocity `f_ij = f_ji`, so `(N^2 + N)/2` coefficients are computed for `N` sources.
* Razavi's text says the method was later extended to multilayer systems with interface resistance (Muzychka, Bagnall, Wang; not opened).
* Note: Razavi's thesis cites the journal version (2006) once with the conference DOI; the two Crossref records above are the reliable references.

What this does **not** give: the paper's own examples, any printed number, the treatment of edge cooling and of the source-plane film, the orthotropic and compound forms. Every statement on those rests on the abstract only.

## 3. Relevance to the program (a judgement from sections 1 and 2)

| Program section or folder | Relation |
| :-- | :-- |
| `docs/theory.md` 6 (Analytic, cosine series, Robin edge eigenfunctions) | same family of series; the influence coefficient is the Analytic's single-source series read at another source. Superposition itself is not new to the program: the Analytic is linear in the powers. |
| `docs/theory.md` 5 (Lumped rings superposed per heater) | the neighbour term `f_ij` is a cheap independent check of how the Lumped adds a neighbour's rise |
| `research/effective-conductivity` (README 4.6), `research/muzychka-case2-analytic` | the published multi-source cases already reproduced are those of [Muzychka2003]: case 1 (a) two sources, case 2 four sources, case 3 the cross of five sources. The first version of this note called the cross "possibly" from this paper: it is case 3 of [Muzychka2003], which is a different paper. |
| `research/analytic-edge-and-transient`, `research/analytic-edge-spatial` | edge cooling on a finite plate (eq. of [Muzychka2003Part2], [Muzychka2006EdgeCooling], both R in part); this paper adds nothing seen here |

No statement of the theory is contradicted by what was read. Nothing is claimed from the paper beyond the abstract.

## 4. Review

Reviewer's checks of the first version of this note (folder `article-1319202`, named by a document number, renamed to the topic):
* The article was searched again (web search, Crossref, the university repository of the author's group): still not obtained, status N confirmed; the journal DOI is now confirmed by Crossref.
* A secondary source with the method's equations was found and read on the page image (section 2); it shows the coefficient is the eccentric-source series of [Muzychka2003] averaged over another source.
* Corrected: the five-source cross is case 3 of [Muzychka2003], not "possibly" from this paper; "the author's page lists it" was a search snippet, not checked, and is removed; the plan (`INTEGRATION.md`) now names the independent solver, the cases and the acceptance rule; entries added to `research/theory/BIBLIOGRAPHY.md` and the registers.
* Verdict: GO for merging as a literature note and a plan; nothing to reproduce yet.

## 5. What was read and what was not verified

* **Read in full**: nothing of the paper (status **N**).
* **Read on the page image**: Razavi (2016) section 2.4, printed pages 55 and 56 (equations 2.71 to 2.74); the rest of that thesis was not read.
* **From summaries (S)**: the abstract (OpenAlex), the two Crossref records (title, venue, pages, DOIs), the reference list of the conference paper (Crossref, 16 items).
* **Not verified**: every formula, case and number of the paper itself; whether the ITherm and journal texts are the same; the definition of `B^i` in Razavi's thesis; the relevance table is a judgement.
* **Not run**: no script, no solver, no reproduction; this folder has no `scripts/`, `lib/`, `tests/` or `figures/` yet (the diagram of the case and the study come with the reproduction, `INTEGRATION.md`).
* **Not stored**: no text or page of either source is in the repository.
