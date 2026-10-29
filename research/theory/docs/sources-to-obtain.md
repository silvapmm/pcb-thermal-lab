# Sources to obtain: what is still unread, where it is, and what to extract

What could be had without cost was opened (see `../BIBLIOGRAPHY.md`). This file lists what is left, with the addresses, so that a person with access (a library, a purchase, a registration) or a person who converts a scan can supply it. For each source: **where**, **what to extract**, **what it closes**. How to hand a source over: the text of the pages, photographs or scans of the pages, or the path of the file; the extraction is then recorded in the bibliography with the page and the status R. A source passes from M or S to R only for what was read, with the page.

## 1. Papers with no open copy found (library, publisher, interlibrary loan)

Searches for open copies were made for all of them (titles, authors, DOIs); none was found.

| # | Source | Address | Extract | Closes |
| --: | :-- | :-- | :-- | :-- |
| 1 | **Churchill and Chu**, Int. J. Heat Mass Transfer 18 (11) (1975) 1323-1329 | https://doi.org/10.1016/0017-9310(75)90243-4 | the general and the laminar correlations of the isothermal vertical plate with their ranges (Ra, Pr), the constants `0.825`, `0.387`, `0.492`, `0.68`, `0.670` and the exponents `1/6`, `9/16`, `8/27`, `4/9`; which form the authors recommend below Ra 1e9 | the choice between the two forms (`research/effective-conductivity/` 4.7, 4.8 B) |
| 2 | **Churchill**, AIChE J. 23 (1) (1977) 10-16 | https://doi.org/10.1002/aic.690230103 | the exponent of the combination of natural and forced convection and the rule for assisting, opposing and transverse flow | whether the blending rule of the program is Churchill's |
| 3 | **Bar-Cohen and Rohsenow**, J. Heat Transfer 106 (1) (1984) 116-123 | https://doi.org/10.1115/1.3246622 | the composite correlation of isothermal and isoflux plates, `S_opt` and `Nu_opt`, the two limits | the composite quoted in topic 13 (reproduced only as quoted) |
| 4 | **Elenbaas**, Physica 9 (1942), *Heat dissipation of parallel plates by free convection* (pages 1 to 23 in the reference lists found; 1 to 28 in the compilation) | ScienceDirect, Physica volume 9 (search the title; the DOI was not confirmed) | the page range and the original form of the correlation | the original of equation 1 of Martin and others |
| 5 | **Hollands, Raithby and Konicek**, Int. J. Heat Mass Transfer 19 (7) (1975) 879-884 | https://doi.org/10.1016/0017-9310(75)90179-9 | horizontal layers of air and water | the enclosure correlation family |
| 6 | **Hollands**, Int. J. Heat Mass Transfer 27 (3) (1984) 466-468 | https://doi.org/10.1016/0017-9310(84)90295-3 | the exponent inside the logarithm (`Ra^(1/3)` in the code of the library `ht`, `Ra^(1/5)` in its documentation) | topic 25, the gap above 7 mm |
| 7 | **Hollands, Unny, Raithby and Konicek**, J. Heat Transfer 98 (1976) 189-193 | publisher (ASME Digital Collection); DOI not confirmed | the inclined-layer form | topic 25 |
| 8 | **Hashin and Shtrikman**, J. Appl. Phys. 33 (10) (1962) 3125-3131 | https://doi.org/10.1063/1.1728579 | optional now: Milton (2002) gives the bound in d dimensions; the original statement for heat conductivity | closes the original |
| 9 | **Lee, Song, Au and Moran** (1995), constriction/spreading resistance model for electronics packaging | not located (two rounds of searches, not in the Waterloo archive) | the venue; the closed form for a rectangular source on a rectangular plate with a film coefficient | the formulas that the 1998 article of Seri Lee shows only as images |

## 2. Scans in the open Waterloo archive: pages not yet read (a person or a tool can convert them)

Address pattern: `https://www.mhtlab.uwaterloo.ca/pdf_papers/<name>.pdf`; the index is https://www.mhtlab.uwaterloo.ca/MHTLarchive.html. These are scans without a text layer; convert the pages to images (for example PyMuPDF `page.get_pixmap(dpi=100)`) and read them, or run an OCR.

| File | Paper | Read so far | Still to read |
| :-- | :-- | :-- | :-- |
| [mhtl91-11](https://www.mhtlab.uwaterloo.ca/pdf_papers/mhtl91-11.pdf) | Martin, Raithby, Yovanovich, low-Rayleigh asymptote, parallel-plate channel (1991) | pages 1 and 2 of 7 | pages 3 to 7: the full numerical solution and the conclusion on boundary conditions |
| [mhtl93-4](https://www.mhtlab.uwaterloo.ca/pdf_papers/mhtl93-4.pdf) | Yovanovich, general expression for laminar forced and natural convection from isothermal plates (1993) | pages 1 to 4 of 7 | pages 5 to 7: the general expression and its comparison |
| [mhtl95-4](https://www.mhtlab.uwaterloo.ca/pdf_papers/mhtl95-4.pdf) | Teertstra, Culham, Yovanovich, packaging density and effective conductivity (1995) | pages 1 to 4 of 13 | pages 5 to 13: the experiments and the relationship with the packaging density |
| [mhtl92-1](https://www.mhtlab.uwaterloo.ca/pdf_papers/mhtl92-1.pdf) | Lemczyk and others, PCB trace thermal analysis and effective conductivity (1992) | pages 1 and 2 of 7 | pages 3 to 7: the trace results and the effective conductivity |
| [mhtl98-3](https://www.mhtlab.uwaterloo.ca/pdf_papers/mhtl98-3.pdf) | Culham and Yovanovich (1998) | pages 1 to 7 of 8 | page 8: the references |
| [mhtl99-6](https://www.mhtlab.uwaterloo.ca/pdf_papers/mhtl99-6.pdf) | thermal wake effects in printed circuit boards | none | all |
| [mhtl95-1](https://www.mhtlab.uwaterloo.ca/pdf_papers/mhtl95-1.pdf) | natural convection from isothermal cuboids and rectangular heat sinks | none | all |
| [mhtl91-6](https://www.mhtlab.uwaterloo.ca/pdf_papers/mhtl91-6.pdf) | geometry and orientation in laminar natural convection from isothermal bodies | none | all |
| [mhtl03-9](https://www.mhtlab.uwaterloo.ca/pdf_papers/mhtl03-9.pdf), [mhtl03-10](https://www.mhtlab.uwaterloo.ca/pdf_papers/mhtl03-10.pdf), [mhtl01-6](https://www.mhtlab.uwaterloo.ca/pdf_papers/mhtl01-6.pdf) | rectangular flux channels (geometric equivalences, edge cooling), compound and orthotropic spreading | none (fonts the text extraction cannot read) | all |
| text papers with a text layer, abstract only read | [mhtl98-2](https://www.mhtlab.uwaterloo.ca/pdf_papers/mhtl98-2.pdf), [mhtl99-2](https://www.mhtlab.uwaterloo.ca/pdf_papers/mhtl99-2.pdf), [mhtl04-27](https://www.mhtlab.uwaterloo.ca/pdf_papers/mhtl04-27.pdf), [mhtl04-14](https://www.mhtlab.uwaterloo.ca/pdf_papers/mhtl04-14.pdf), [mhtl00-3](https://www.mhtlab.uwaterloo.ca/pdf_papers/mhtl00-3.pdf) | abstracts | the formulas (they can be read as text) |

## 3. Standards

| # | Standard | Address | Extract |
| --: | :-- | :-- | :-- |
| 10 | **JEDEC JESD15-3** (two-resistor compact thermal model), **JESD51-3**, **JESD51-7**, **JESD51-14** | https://www.jedec.org/ (free after registration; the site refused the fetch tool) | title, revision and status; the JEDEC board (dimensions, layers, copper); the two resistances of JESD15-3; the junction-to-case measurement of JESD51-14 |
| 11 | **ASTM D5470** (D5470-17(2024), active) | https://store.astm.org/standards/d5470 , https://doi.org/10.1520/D5470-17R24 | the test method for thermal impedance, the extrapolation to zero thickness, the precision |
| 12 | **ASME V&V 20** | https://www.asme.org/codes-standards/publications-information/verification-validation-uncertainty | the comparison error and the validation uncertainty |
| 13 | **IPC-2152**, **IPC-4761** | https://www.ipc.org/ | IPC-2152: effect of copper planes, thickness and vias on conductor temperature rise; IPC-4761: the via protection types |

## 4. Books (library)

| # | Book | Address | Extract |
| --: | :-- | :-- | :-- |
| 14 | **Incropera and DeWitt**, *Fundamentals of Heat and Mass Transfer* (fix the edition; Bergman and others, *Introduction to Heat Transfer*, 6th edition, is the edition cited by the library `ht` for the worked example) | publisher | the fin efficiency and the natural convection correlations; Example 9.2 |
| 15 | **Patankar** (1980) | https://www.routledge.com/Numerical-Heat-Transfer-and-Fluid-Flow-1st-Edition/Patankar/p/book/9780891165224 | the control-volume discretisation and the harmonic mean of the face conductivity |
| 16 | **Carslaw and Jaeger**, 2nd edition (1959) | https://search.worldcat.org/title/Conduction-of-heat-in-solids/oclc/535528 | the reference solutions of the verification |
| 17 | **Torquato** (2002) | https://link.springer.com/book/10.1007/978-1-4757-6355-3 | effective conductivity bounds and the microstructures that attain them |
| 18 | **Briggs, Henson and McCormick**, *A Multigrid Tutorial*, 2nd edition (2000) | https://epubs.siam.org/doi/book/10.1137/1.9780898719505 | the two-grid and V-cycle analysis |

## 5. Smaller items

* **Ucamco Gerber Layer Format Specification, revision 2026.05** (free): https://www.ucamco.com/en/guest/downloads/gerber-format , file `gerber-layer-format-specification-revision-2026-05_en.pdf`; read the revision on the cover.
* **Nexperia AN11261** in full (only a summary was seen): https://mouser.com/pdfDocs/AN11261-3.pdf
* **pyamg documentation** for the multigrid topic; **Milton chapters 17 and 28** (only their titles were seen); the Electronics Cooling articles marked S in the bibliography (equations that the page converter turned into images: Seri Lee 1998, Simons 2004, Lush 2004: open them in a browser and paste the equations).

## 6. What was done with no purchase

The effective conductivity, spreading and layered-idealisation checks of `research/effective-conductivity/` (Seri Lee's edge and corner values, the cases of Muzychka and others, the layer orders of Culham and Yovanovich, the channel correlations) were reproduced with an independent solver; the papers read for them are listed in its README, section "What was read and what was not verified".
