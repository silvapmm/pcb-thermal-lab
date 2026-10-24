# Sources to obtain: what the maintainer has to do

What can be read without cost was opened (see `../BIBLIOGRAPHY.md`: Milton chapters 3 and 23, the multigrid primer, Lush 2004, Seri Lee 1998, the Gerber and ASTM pages). What follows needs a library, a purchase, a registration or a person with access. For each source: **what to get**, **what to extract** (so that a reader of the source knows exactly what to look for), **what it closes** and **how to hand it over** (the text of the page, a photograph of the page, or the path of the PDF; the extraction is then recorded in the bibliography with the page and the status R).

Rule for all of them: a source passes from M or S to R only for what was read, with the page; what stays unread stays marked.

## 1. Papers (university library, publisher, or interlibrary loan)

| # | Source | Extract | Closes | Used by |
| --: | :-- | :-- | :-- | :-- |
| 1 | **Churchill and Chu, Int. J. Heat Mass Transfer 18 (11), 1975, 1323-1329**, doi 10.1016/0017-9310(75)90243-4 | the general correlation for an isothermal vertical plate and the laminar form, with their ranges of validity (Ra, Pr); the constants `0.825`, `0.387`, `0.492`, the exponents `1/6`, `9/16`, `8/27`; the definition of the film temperature and of L | the program uses the general form; the laminar form differs by +6.6 % at Ra 1e5, -5.2 % at 1e7 and -25 % at 1e9 (Pr 0.71): which one applies to a PCB, and from what Ra | convection (topic 8 and the heat transfer coefficient of the program) |
| 2 | **Churchill, AIChE J. 23 (1), 1977, 10-16**, doi 10.1002/aic.690230103 | the exponent of the combination of natural and forced convection and the rule for assisting, opposing and transverse flow | whether the blending rule of the program is Churchill's, and with which exponent | combined convection |
| 3 | **Hollands** (the paper the notes of `docs/research.md` R3 cite is not identified: two candidates are in the bibliography) | first, which paper gives the correlation for a gap above about 7 mm; then the form of the exponent (`Ra^(1/3)` in the code of the library `ht`, `Ra^(1/5)` in its documentation) and the range | the air gap and enclosure correlation | topic 25 |
| 4 | **Elenbaas, Physica 9, 1942** (title *Heat dissipation of parallel plates by free convection*; pages from memory) | the page range; the relation `Nu(Ra*)` for isothermal vertical parallel plates and its two limits | the channel effect between fins, not modelled today | heatsink scenarios |
| 5 | **Bar-Cohen and Rohsenow, J. Heat Transfer 106 (1), 1984, 116-123**, doi 10.1115/1.3246622 | the optimum spacing `S_opt` and the Nusselt number `Nu_opt` for isothermal and isoflux plates, the composite expression, its two limits | to compare with Simons' practical form (50 against 54.3 found) and to size a fin array | heatsink scenarios |
| 6 | **Culham and Yovanovich, ITherm 1998, 460-467**, doi 10.1109/ITHERM.1998.689603 | the three averaging schemes of effective conductivity, the Fourier-series model and its comparison with the in-plane and through-thickness resistance networks | whether one `k_parallel` and one `k_perp` represent a board; the spreading term | stack-up, mapping |
| 7 | **Lee, Song, Au and Moran, 1995** (venue not located; the Electronics Cooling article of 1998 that the studies call by these authors is by Seri Lee alone) | find the venue; the closed form of the spreading resistance of a rectangular source on a rectangular plate with a film coefficient | the formulas that the 1998 article only shows as images | plate spreading (topic 26) |
| 8 | **Hashin and Shtrikman, J. Appl. Phys. 33 (10), 1962, 3125-3131**, doi 10.1063/1.1728579 | optional now (Milton (2002) gives the bound in d dimensions): the original statement for heat conductivity | closes the original; low priority | mapping |
| 9 | **Sampson (Electronics Cooling, 2005 and 2017), Blackmore (2010), Guenin (2015)** | only the ones the bibliography marks S: the equations of the conductance between neighbouring nodes from a local solve | the method that the flow-based faces reproduce | `gerber-models` |

## 2. Standards

| # | Standard | Access | Extract | Closes |
| --: | :-- | :-- | :-- | :-- |
| 10 | **JEDEC JESD15-3** (two-resistor compact thermal model), **JESD51-3**, **JESD51-7**, **JESD51-14** | free on jedec.org after registration | title, revision and status; the board of JESD51-3 and JESD51-7 (dimensions, layers, copper); the definition of the two resistances of JESD15-3 and of the junction-to-case measurement of JESD51-14 | the junction node, theta and psi, the JEDEC board of the calculator validation |
| 11 | **ASTM D5470** (D5470-17(2024)) | paid; institutional access | the test method for thermal impedance, the extrapolation to zero thickness, the stated precision | thermal interfaces (topic 24) |
| 12 | **ASME V&V 20-2009** | paid | the comparison error and the validation uncertainty (how `u_val` combines numerical, input and experimental uncertainty) | the measurement protocol of `models-comparison` |
| 13 | **IPC-2152** and **IPC-4761** | paid | IPC-2152: the effect of copper planes, board thickness and vias on conductor temperature rise; IPC-4761: the via protection types and what each means for the barrel | via fill, the checks on copper |

## 3. Books (library, to confirm what the project names)

| # | Book | Extract |
| --: | :-- | :-- |
| 14 | **Incropera and DeWitt**, *Fundamentals of Heat and Mass Transfer* | **fix the edition** (the project does not say which one it uses), then the fin efficiency of a straight fin with a corrected length and the natural convection correlations of the chapter on free convection |
| 15 | **Patankar** (1980) | the chapters on the control-volume discretisation and the harmonic mean of the face conductivity |
| 16 | **Carslaw and Jaeger**, 2nd edition (1959) | the reference solutions the verification uses (plate, source on a half space) |
| 17 | **Torquato** (2002) | the chapters on effective conductivity bounds and the microstructure that attains them |
| 18 | **Briggs, Henson and McCormick**, *A Multigrid Tutorial*, 2nd edition (2000) | the two-grid and V-cycle analysis, for a multigrid solver |

## 4. Smaller items

* **Ucamco, Gerber Layer Format Specification, revision 2026.05** (free, on the Downloads page of ucamco.com): download the PDF and read the revision on the cover; it replaces 2024.05 as the latest.
* **Nexperia application note AN11261** in full (only a summary was seen).
* **pyamg documentation** (free) for the multigrid topic; **Milton chapters 17 and 28** (only their titles were seen; low priority).
* **Electronics Cooling** articles marked S in the bibliography (free, in a browser): open them and paste the equations that the page converter turned into images.

## 5. A check that needs no purchase

The article of Seri Lee gives, for an aluminium base 100 x 100 x 1.3 mm with a 25 x 25 mm source (`k = 200 W/mK`, `R0 = 1.0 K/W`), the spreading resistance for three positions of the source: **centre 0.66 K/W (reproduced by `block_contact_study.py`), edge midpoint 1.29 K/W and corner 2.38 K/W (not yet compared)**. Running the program's plate model with the source at the edge and at the corner is an independent check that can be done now.
