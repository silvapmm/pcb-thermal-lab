# Bibliography of the theory

One list for every topic of this folder. Each entry has a **key** (used in the `Sources` of the topic files, for example `[Patankar1980]`), the citation as the repository records it, the address as recorded, a **reading status** and the topics that use it.

**Reading status** (the rule of `CLAUDE.md`, "Method and honesty": never present a guess as a finding):

| Code | Meaning |
| :-- | :-- |
| **R** | **recorded as read** by the project document that cites it (`docs/research.md`, `docs/validation.md`, the READMEs of the investigations); the repository cannot show how much of each page was seen, and the session notes in `CLAUDE.md` say that WebFetch reached few sites, so some "read" pages were seen through a search summary; where a topic leans on one number, the topic says so |
| **S** | seen only as a search summary, a snippet or a converted text with missing figures; not a citation to lean on |
| **M** | named by the project documents (`docs/theory.md` section 12 and others) or known from memory; **not opened** in this work; the journal details marked "memory" were not checked |
| **N** | named and wanted, but could not be opened (host blocked, login wall) or not yet obtained |
| **L** | local: an own computation in the repository (a study script), not a publication |

This file records what the repository already says, **plus one round of checks made later** from the session: the web search tool worked (it returns summaries, so what it confirms has status S), the page-fetch tool and direct downloads were blocked for every host tried (Wikipedia, Ucamco, Mouser, the ReadTheDocs pages), and only the Python package index could be read (status R for package metadata). That round confirmed the citations of Churchill and Chu (1975), Churchill (1977), Culham and Yovanovich (1998), Patankar (1980), Milton and Torquato (2002), Briggs and others (2000), the Nexperia note on Foster and Cauer, the version and licence of pyamg; it could not find Lee et al. (1995) at all. The properties of the 2D effective-medium formulas were checked numerically in `scripts/check_mapping_formulas.py`. The list of what should still be read to close the gaps is at the end (section 14).

Topic numbers (30 orientation, 31 program architecture and API, 32 the removed program against the current one, 33 time-dependent results were added after 24 to 29; 24 to 29: 24 thermal interfaces and metals, 25 contact area, air gap and chain, 26 plate spreading, 27 datasheet numbers and compact models, 28 continuum and sources, 29 verification ladder): 01 layered idealisation, 02 finite volumes, 03 finite differences, 04 3D solid, 05 Lumped rings, 06 Analytic series, 07 time stepping, 08 heat transfer coefficients, 09 parts and the junction, 10 power profiles, 11 metal blocks and fins, 12 Foster chain (planned), 13 heatsink scenarios (planned), 14 virtual JEDEC test and known-power reference (planned), 15 import and power list (planned), 16 multigrid (planned), 17 copper mapping and the tensor, 18 spreading resistance, 19 nets, current and Joule heat, 20 board outline, 21 vias and fills, 22 stack-up, 23 the Power calculator.

## 1. Numerical methods: finite volumes, differences, time, solvers, verification

### [Patankar1980]
S. V. Patankar, *Numerical Heat Transfer and Fluid Flow*, Hemisphere (McGraw-Hill), 1980, xiii + 197 pages (publisher and size from library catalogue records seen in a search; the book itself was not opened). **Status M** for the content, **S** for the citation. Used for the finite-volume discretisation, harmonic means of the conductivity at interfaces and the theta method of time stepping (`docs/theory.md` section 12). Topics 02, 03, 07.

### [EymardGallouetHerbin]
R. Eymard, T. Gallouët, R. Herbin, *Finite Volume Methods*, https://raphaeleh.github.io/PUBLI/bookevol.pdf. **Status S** (cited in `docs/validation.md` section 10 for the statement that a finite-volume method is a balance on every cell, so the energy is conserved locally and globally, while finite differences work on point values). Topics 02, 03.

### [SpringerFVHeat]
*Finite Volume Method in Heat Conduction*, Springer reference work entry, https://link.springer.com/rwe/10.1007/978-94-007-2739-7_896. **Status S.** Same use as above. Topic 02.

### [Khouider]
A. Khouider, lecture notes on the finite volume method, https://www.pims.math.ca/files/Khouider_1.pdf. **Status S.** Same use. Topic 02.

### [Roache]
P. J. Roache, grid convergence index (safety factor 1.25 for three grids), as used in ASME V&V 20. The standard was **not read**; the formula is the common three-grid GCI. **Status M.** Summaries read: *In search of grid converged solutions*, NASA, https://ntrs.nasa.gov/api/citations/20100027422/downloads/20100027422.pdf (**S**) and *Application of grid convergence index in FE computation*, https://bibliotekanauki.pl/articles/201974.pdf (**S**). Topics 04, 18.

### [AgelasEymardHerbin2009]
L. Agelas, R. Eymard, R. Herbin, cell-centred nine-point finite-volume scheme for heterogeneous anisotropic media, Comptes Rendus Mathématique (2009), https://comptes-rendus.academie-sciences.fr/mathematique/item/10.1016/j.crma.2009.03.013.pdf. **Status S** (a search result; the article was not read). Topic 17.

### [Positivity9pt]
A paper on the positivity of nine-point schemes (a linear nine-point scheme that is monotone and second order does not exist for any anisotropic diffusion on distorted meshes), https://journal.global-sci.org/intro/article_detail/cicp/12482.html. **Status S**; the authors and the title were not recorded. Topic 17.

### [MFEMStaticCond]
MFEM documentation, static condensation (the Schur complement used by finite-element codes), https://docs.mfem.org/4.6/staticcond_8hpp_source.html. **Status S.** Topics 06, 11.

### [Kron2022]
Kron reduction of a network, https://arxiv.org/pdf/2204.05554 (authors and title not recorded). **Status S.** Topics 06, 11.

### [PMC11410250]
*A modeling method for thermal steady-state simulation of the four-layer printed circuit board*, https://pmc.ncbi.nlm.nih.gov/articles/PMC11410250/. **Status R** (text read, `docs/validation.md` section 10): Fourier series for the insulating layers combined with a lateral-only finite-volume discretisation of the metal layers, the same architecture as the FVM and Analytic pair of this program; 1.8 to 2.5 % against COMSOL at the hot region and 4 to 5 % against measurements on a real board; under 9 minutes against about 50 for COMSOL. Topics 01, 06.

### [FourierMultilayerJCU]
Fourier-series multilayer analytical models against finite elements, 1 to 4 % in the studies found by a search (https://researchonline.jcu.edu.au/86884/ and others). **Status S** (figures from search summaries). Topic 06.

### [FDvsFVSpringer]
A comparison of finite differences and finite volumes on 1D steady conduction, https://link.springer.com/chapter/10.1007/978-981-97-0037-0_9. **Status N** (login wall; not read). Topic 03.

### [Pyamg]
PyAMG: Algebraic Multigrid Solvers in Python, https://github.com/pyamg/pyamg ; developed by L. Olson, J. Schroder and B. Southworth; licence MIT, version 5.3.0 (PyPI metadata, read through the package index, the one host reachable from the session); requires NumPy and SciPy; paper in the Journal of Open Source Software, doi 10.21105/joss.05495 (named on the package page). Named in `docs/roadmap.md`, "Solvers and validation". **Status R for the package metadata, N for the paper.** Topic 16.

### [Briggs2000]
W. L. Briggs, V. E. Henson, S. F. McCormick, *A Multigrid Tutorial*, 2nd edition, SIAM, 2000. **Status S** (citation seen in course notes found by a search; the book was not opened): the standard introduction to the V-cycle, restriction, prolongation and smoothing. Topic 16.

### [McCormickTamstorf]
S. McCormick and R. Tamstorf, a multigrid primer (https://grandmaster.colorado.edu/~stevem/mgprimer.pdf, found in a search). **Status S** (snippet): V-cycles aim for a convergence factor per cycle bounded independently of the grid at a cost proportional to the number of unknowns of the finest level; covers the V-cycle, the W-cycle and full multigrid. Lecture notes found with it state that the smoother damps the high-frequency error and the coarse grid handles the smooth error. Topic 16.

### [SciPySuperLU]
SciPy's sparse direct solver (SuperLU) with the symmetric minimum-degree ordering is the program's direct solver (`docs/theory.md` section 2); the library documentation is not recorded as a source. **Status M.** Topic 02.

## 2. Heat conduction theory, spreading resistance, fins

### [CarslawJaeger]
H. S. Carslaw and J. C. Jaeger, *Conduction of Heat in Solids* (edition not recorded). **Status M.** Fourier-series solutions, Green functions of the fin equation (K0), disc sources (I0, I1) (`docs/theory.md` section 12). Topics 05, 06, 18.

### [Lee1995]
S. Lee, S. Song, V. Au, K. P. Moran, constriction/spreading resistance model for electronics packaging, 1995 (the venue is not recorded in the repository; a search for the title and the 1995 ASME/JSME conference found no record of it, so even the citation is unconfirmed). **Status M/N**; `research/block-and-fins/README.md` says it "could not be read and was not used". The program's plate model is compared with the published spreading resistance of a small source on a plate (+4.5 %, `docs/theory.md` section 7). Topics 11, 18.

### [EC1998Spreading]
Electronics Cooling, "Calculating spreading resistance in heat sinks", 1998. **Status M** (named in `docs/theory.md` section 12; address not recorded). Topic 18.

### [YovanovichMuzychkaEllison]
Yovanovich and Muzychka, Ellison: spreading resistance of a small source on a larger plate (`R = R0 + Rc`, accurate to about 5 % for aspect ratio below 2.5), as summarised in `research/component-heatsink/NOTES.md`. **Status M/S** (the notes record the claim from literature searches). Topic 18.

### [Yovanovich2003]
M. M. Yovanovich, *Thermal Resistances of Circular Source on Finite Circular Cylinder With Side and End Cooling*, J. Electronic Packaging 125 (2003) 169-177, https://www.mhtlab.uwaterloo.ca/pdf_papers/mhtl03-20.pdf. **Status R for Table 3** (the dimensionless spreading resistance of an isoflux circular source on a flux tube; the values 0.9401, 0.8009, 0.6649, 0.5337 for epsilon 0.1 to 0.4 are recorded in the script); the rest of the paper was not re-read. Topics 04, 18.

### [IncroperaDeWitt]
F. P. Incropera, D. P. DeWitt, *Fundamentals of Heat and Mass Transfer* (edition not recorded). **Status M.** Fin and sheet equations, fin efficiency of a straight fin with a convecting tip (corrected length Hc = H + t/2), natural and forced convection correlations, radiation. Also the general statement of fin efficiency at https://www.sciencedirect.com/topics/engineering/fin-efficiency (**S**). Topics 01, 08, 11.

### [ElenbaasBCR]
W. Elenbaas (1942), optimum spacing of vertical parallel plates in natural convection; A. Bar-Cohen and W. M. Rohsenow, *Thermally Optimum Spacing of Vertical, Natural Convection Cooled, Parallel Plates*, J. Heat Transfer 106 (1984) 116-123, as described at https://abcm.org.br/anais/cobem/2003/html/pdf/COB03-1466.pdf. **Status S**: the constants of the composite correlation could not be read there and are not used. Topics 11, 13.

## 3. Convection and radiation

### [ChurchillChu1975]
S. W. Churchill and H. H. S. Chu, *Correlating Equations for Laminar and Turbulent Free Convection from a Vertical Plate*, Int. J. Heat Mass Transfer 18 (11) (1975) 1323-1329, doi 10.1016/0017-9310(75)90243-4 (citation and the form of the single expression with the constants 0.825, 0.387 and the exponent 8/27 confirmed by secondary sources in a search, among them the documentation of the `ht` library; the paper itself was not opened). **Status S** (the form used in `convection.py` matches). Topic 08.

### [LloydMoran1974]
J. R. Lloyd and W. R. Moran (1974), natural convection from horizontal plates, with a characteristic length `L = A/P` that collapses circular, square, rectangular and triangular plates; cited by `docs/models.md` section 18. The publication details are not recorded and the paper was not opened. **Status M.** Topic 30.

### [ChurchillBlend]
S. W. Churchill, *A comprehensive correlating equation for laminar, assisting, forced and free convection*, AIChE Journal 23 (1) (1977) 10 (the citation is confirmed by reference lists of other papers in a search). The blending rule used by the program, `h = (h_n^3 + h_f^3)^(1/3)` (`docs/theory.md` sections 8 and 12 call it "Churchill's blending rule"), was **not confirmed** by any text read: whether it is the exponent-3 rule of this paper is from memory. **Status S for the citation, M for the rule.** Topic 08.

### [AirProperties]
Dry air at 1 atm, Sutherland-type fits for viscosity and conductivity between 250 and 450 K, as used in `convection.py` (`docs/theory.md` section 8): the program's fits are checked against textbook values (1 to 3 %), no single source is recorded. **Status M.** Topic 08.

## 4. Packages, the junction, compact models, datasheets

### [JESD15-3]
JEDEC JESD15-3, *Two-Resistor Compact Thermal Model Guideline*. **Status R** (text read, through a mirror at http://www.simu-cad.com/userfiles/images/ZaiXianXiaZai/ef8f29116ed54c67a8a8d77502611043.pdf): definitions of theta-JB and theta-JC-top, replacing theta-JB by theta-JC-bottom for exposed-pad packages, psi-JB as a substitute, psi-JT not allowed, the block-and-plate construction, accuracy "30 % or less". Topics 09, 12, 14.

### [JESD51family]
JEDEC JESD51 family (JESD51-1 electrical test method and K-factor; -2A still air; -3 low-k board; -5 thermal vias; -7 high-k 2s2p board; -8; -9; -10; -12; -14). **Status S/N**: only as summarised in Electronics Cooling (below); the standards themselves were not read (JESD51-1 is behind a login: index pages https://www.jedec.org/node/3931 and https://www.vektrex.com/news-articles/measuring-led-junction-temperature-tj/ , **S**). Topics 09, 14, 23.

### [NISTIR7648]
J. Stori, K. Brady, T. Thurman, *Representation of a Thermal Resistor Network Model of a Packaged Component in STEP AP210 Edition 2*, NISTIR 7648, 2008, https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir7648.pdf. **Status R**: JESD15 family, 2R with three nodes and two resistances, DELPHI with shunt resistors. Topic 09.

### [TI-SPRA953B]
Texas Instruments, *Semiconductor and IC Package Thermal Metrics*, SPRA953B, 2012, https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/171/4745.TI_5F00_PackageThermalMetrics_5F00_spra953b.pdf. **Status R**: definitions of theta-JC, theta-JB, psi-JT, psi-JB, the three-resistor estimate, the theta-JB redistribution problem, 75 to 95 % of the heat through the PCB. Topics 09, 14, 23.

### [Renesas-Thermal]
Renesas, *Thermal Characterization of Packaged Semiconductor Devices*, https://www.renesas.com/en/document/whp/thermal-characterization-packaged-semiconductor-devices. **Status R**: psi-JB within about 15 % of theta-JB, psi-JT, mould compound emissivity about 0.95, theta-JA = theta-JC + theta-CS + theta-SA. Topics 09, 23.

### [SemiDigest2007]
*Compact Thermal Modeling: Impacting the Industry*, Semiconductor Digest, 2007, https://sst.semiconductor-digest.com/2007/03/compact-thermal-modeling-impacting-the-industry/. **Status R**: DELPHI within 10 %, boundary-condition independence, dynamic models in standardisation. Topic 09.

### [Siemens-CTM]
Siemens, *Experiment vs. Simulation, Part 4: Compact Thermal Models*, https://blogs.sw.siemens.com/simulating-the-real-world/2013/04/05/experiment-vs-simulation-part-4-compact-thermal-models/. **Status R**: standard 2R and DELPHI lack thermal capacitance; RC ladders from transient measurements add it. Topics 09, 12.

### [EC2007Compact]
Electronics Cooling, *Compact thermal modeling in electronics design* (2007), https://www.electronics-cooling.com/2007/05/compact-thermal-modeling-in-electronics-design/. **Status R**: 2R about 30 % or less, DELPHI within 10 %, typical errors under 5 % against detailed models, lack of theta-JB data from some manufacturers. Topic 09.

### [EC2019JEDEC]
Electronics Cooling, *JEDEC Thermal Standards: Developing a Common Understanding* (2019), https://www.electronics-cooling.com/2019/11/jedec-thermal-standards-developing-a-common-understanding/. **Status R**: JESD51-2, -3, -5, -6, -7, -8, -9, -14, JESD15-3 and -4; test boards of at least 76 x 114 mm. Topics 09, 14.

### [EC1999RJB]
Electronics Cooling, *Use of junction-to-board thermal resistance in predictive engineering* (1999), https://www.electronics-cooling.com/1999/01/use-of-junction-to-board-thermal-resistance-in-predictive-engineering/. **Status R**: R-JB depends on the board, about 10 % scatter, errors under 25 % in a CFD study. Topic 09.

### [EC2024JESD5114]
Electronics Cooling, *The Applicability of JESD51-14 for the Determination of Junction to Case Thermal Resistance* (2024), https://www.electronics-cooling.com/2024/04/the-applicability-of-jesd51-14-for-the-determination-of-junction-to-case-thermal-resistance/. **Status R**: single-path packages, Rjb/Rjc above about 10, an overmolded BGA 0.82 against 1.79 K/W. Topic 09.

### [RichtekAN061]
Richtek, *Application and Definition of Thermal Resistances on Datasheet*, AN061 (2020), https://www.richtek.com/Design%20Support/Technical%20Document/~/media/AN%20PDF/AN061_EN.ashx. **Status R**: theta-JB on the lead foot for leaded parts, theta-JA/JC/JB not applicable to another board, the psi-JB and psi-JT estimates and their measured check. Topics 09, 14, 23.

### [TI-AN2020]
Texas Instruments, *AN-2020 Thermal Design by Insight, Not Hindsight*, SNVA419C (2013), https://www.ti.com/lit/an/snva419c/snva419c.pdf. **Status R**: theta-Cu, theta-VIA, copper weight, board-area rule of thumb, heatsink on the bottom against the top. Topics 09, 21.

### [ROHM-64AN113E]
ROHM, *Thermal resistance and thermal characterization parameter*, 64AN113E, https://fscdn.rohm.com/en/products/databook/applinote/ic/power/switching_regulator/thermal_resistance_appli-e.pdf. **Status R**: JEDEC test boards 114.3 x 76.2 mm, 70 um traces, 74.2 mm planes of 35 um, thermal vias diameter 0.30 mm at 1.2 mm pitch. Topics 14, 23.

### [ROHM-65AN114E]
ROHM, *theta-JA and psi-JT*, 65AN114E, https://fscdn.rohm.com/en/products/databook/applinote/common/theta_ja_and_psi_jt_an-e.pdf. **Status R**: why theta-JA and psi-JT change in other applications. Topic 23.

### [ROHM-2R-not-used]
ROHM application note "two-resistor model", https://fscdn.rohm.com/en/products/databook/applinote/common/two_resistor_model_for_thermal_simulation-e.pdf. **Not used** as a source for the 2R model: it defines junction-to-board and board-to-ambient resistances, which is not the JESD15-3 definition. Topic 09.

### [Infineon-AN2012-03]
Infineon, *OptiMOS Power MOSFET Datasheet Explanation*, AN 2012-03, https://www.infineon.com/assets/row/public/documents/24/42/infineon-mosfet-optimos-datasheet-explanation-applicationnote-en.pdf. **Status R**: Ptot, RthJA conditions, ZthJC. Topics 09, 12.

### [Datasheets]
Datasheets read for the parts (`docs/research.md`, evidence list): Texas Instruments CSD17308Q3 (SLPS262C, https://www.ti.com/lit/ds/symlink/csd17308q3.pdf; RthetaJC 4.5, RthetaJA 46 typical and 58 maximum on 1 in2 of 2 oz copper), LMR36510 (SNVSBD7B, https://www.ti.com/lit/ds/symlink/lmr36510.pdf), TPS7A47 (https://www.ti.com/lit/ds/symlink/tps7a47.pdf; RthetaJA 32.5, theta-JC(bot) 1.7, psi-JT 0.3, psi-JB 11.9 K/W); SX Semiconductor SS12 to SS120 (**R**); SS54 SMC rectifier (**R**); Vishay WSL power metal strip resistors (https://www.vishay.com/docs/30100/wsl.pdf, **R**: power rating at 70 C and the derating curve). Samsung LED high-power datasheets: the thermal figures came from a search summary and the files were **not read** (**N**). Topics 09, 14.

### [Nexperia-AN11261]
Nexperia, AN11261, *Using RC thermal models* (Foster and Cauer networks), https://mouser.com/pdfDocs/AN11261-3.pdf (the older NXP edition; the current one is Rev. 5.0, March 2021; the host cannot be opened from the session). **Status S**: a search summary says that a Foster model comes from fitting a curve to `Zth` (a one-dimensional RC chain whose values do **not** correspond to places in the device), that a Cauer model maps to physical layers and gives access to internal nodes and can be connected to external networks (heatsink, PCB), that `Zth` is measured from step power pulses of different lengths and reaches a plateau equal to `Rth` after about a second, and that for a square pulse `Zth` read from the datasheet times the power gives the rise, while pulsed or sinusoidal power needs the RC ladder. Nexperia's own device models use a Foster network (for example eight `Rth, Cth` pairs for one MOSFET). Topic 12.

### [TI-SLUAAT8]
Texas Instruments SLUAAT8, *Using MOSFET Transient Thermal Impedance Curves in Your Design*, https://www.ti.com/lit/pdf/sluaat8 (repetitive pulses, `D + (1 - D) z(t)`). **Status S.** Topic 12.

### [Microchip-Thermal]
Microchip, *Thermal parameters of an IC*, https://support.microchip.com/s/article/Thermal-parameters-of-an-IC; Texas Instruments SLRR012 one-page thermal reference, http://www.ti.com/lit/pdf/SLRR012. **Status S.** Topics 09, 14.

## 5. Heatsinks and interfaces

### [HeatsinkCatalogues]
The catalogue entries of theta-SA with air flow and test conditions behind the heatsink library (11 entries, `docs/models.md` and `docs/research.md` R2, R3, R6). The research folder `component-heatsink/NOTES.md` records which were read and which are search summaries. **Status R/S per entry.** Topics 11, 13.

### [VolumetricGuide]
The forced-convection factors on theta-SA (1, 0.31, 0.18 and 0.10 at 0, 1, 2.5 and 5 m/s) of a volumetric heatsink guide, recorded in `docs/roadmap.md` ("Heatsink air flow") and `docs/research.md` R3; the guide itself is named in `research/component-heatsink/NOTES.md`. **Status S.** Topic 13.

### [ASTMD5470]
ASTM D5470, thermal interface material measurement: named through Electronics Cooling (2014) in `docs/theory.md` section 12; the standard was not read. **Status M.** Topics 09, 11.

### [MetalTables]
Metal property tables read by the heatsink study (`docs/research.md` R2): Ferrotec material table and Engineering ToolBox (aluminium 204 W/mK, 2.71 g/cm3, 0.90 J/gK; copper 386, 8.96, 0.385; brass 111, 8.49, 0.34; stainless 304 about 14, 8.01, 0.46; carbon steel 54, 0.49 J/gK, a textbook value). Addresses not recorded. **Status R as recorded.** Topic 24.

### [GreaseValues]
Typical thermal grease and pad values read by the heatsink study (`docs/research.md` R2): bond line of 7 to 20 um at best and 0.05 to 0.1 K cm2/W in the laboratory (Dow Corning); in assembly 25 to 100 um and 1 to 5 W/mK; gap pads 1 to 6 W/mK and 0.5 to 1.2 mm; adhesives 0.5 to more than 6 W/mK; phase-change pads like grease above 55 to 60 C. Addresses not recorded. **Status R as recorded.** Topic 24.

### [ECD5470RoundRobin]
Electronics Cooling (2014) on ASTM D5470 thermal interface measurements, an inter-laboratory round robin: a paste 32 mm2K/W = 0.32 K cm2/W at 300 kPa (30.9 at a 23.5 um bond line), a ceramic paste 41 mm2K/W, a 1.575 mm gap pad 12.1 K cm2/W at 690 kPa; the joint formula `R = BLT/(kA) + (R''c1 + R''c2)/A`. Address not recorded. **Status R as recorded.** Topic 24.

### [ECHowToSelectHeatsink]
Electronics Cooling, "How to select a heat sink": `Rja = Rjc + Rcs + Rsa`, `Rsa = (Ts - Ta)/Q - Rjc - Rcs`, spreading of a source much smaller than the base adds 5 to 30 %, the volumetric performance `C = R V` of 500 to 800 cm3K/W in natural convection falling to 150-250, 80-150 and 50-80 at 1, 2.5 and 5 m/s, interface values 0.07 to 0.81 in2 C/W. Address not recorded (the notes in `docs/research.md` R6 cite it by title). **Status R as recorded.** Topics 13, 24.

### [AlphaNovatech]
Alpha Novatech and similar heatsink catalogues: natural convection `W = beta dT^1.25`, so the resistance falls as `dT^(-0.25)` (a heatsink at 30 K rise 1.257 times worse than at 75 K); a bad orientation about 25 % worse; anodised aluminium (emissivity about 0.8) against bare (about 0.1). Address not recorded. **Status R as recorded.** Topic 13.

### [ECSimpleSpreading2004]
Electronics Cooling, "Simple formulas for estimating thermal spreading resistance" (2004): reported errors -2 to +5 %. Address not recorded. **Status S** (named in `docs/research.md` R3). Topics 25, 26.

### [GapHandbooks]
Heat-transfer handbooks, the documentation of the `ht` library and Purdue ME 418 notes, as named by `docs/research.md` R3, for conduction of still air across a gap, radiation between parallel faces and the critical Rayleigh number of a horizontal layer (1708). Addresses not recorded. **Status R as recorded.** Topic 25.

### [Hollands]
The Hollands correlation for natural convection in a horizontal layer heated from below, named in `docs/research.md` R3 for gaps above about 7 mm; the publication is not recorded. **Status M.** Topic 25.

## 6. Inverse problems and power estimation

### [Chen-style]
*A method to measure heat dissipation from component on PCB*, https://www.researchgate.net/publication/241629467_A_method_to_measure_heat_dissipation_from_component_on_PCB: inverse heat-transfer estimate of the power of a component, calibration with a heater of known input, about 10 % error, multi-layer boards need an adjustment for the board conductance. **Status S.** Topics 14, 23.

### [ArXiv2307.08354]
*Component-wise Power Estimation of Electrical Devices Using Thermal Imaging*, https://arxiv.org/html/2307.08354v2: resistors of known power; mean error of 10 % with consumer infrared cameras above 300 mW. **Status S.** Topic 23.

### [OSTI21026063]
*Theoretical and experimental characterization of heat dissipation in a board-level microelectronic component*, https://www.osti.gov/etdeweb/biblio/21026063: black paint for a usable infrared reading; validation against finite elements and a thermal test die. **Status S.** Topic 23.

### [IITPalakkad]
IIT Palakkad, *Studies on influence of anisotropic thermal conductivity* (inverse estimation of in-plane conductivity of PCBs with different copper layouts), https://publications.iitpkd.ac.in/publication/studies-on-influence-of-anisotropic-thermal-conductivity-1. **Status S.** Topic 23.

### [PohankaRaudensky]
Pohanka and Raudensky, thermocouple disturbance of the field in inverse problems, https://engmechx.it.cas.cz/improc/2002/Pohanka.pdf. **Status S.** A Missouri S&T poster, quoted in `docs/calculators.md`, notes that fitting k and h together is weakly identifiable for a good conductor (**S**; no address). Topic 23.

## 7. Printed circuit boards: models, vias, stack-ups

### [EC2010Tiled]
Electronics Cooling (2010) on tiled conductivity maps of PCBs, quoted in `docs/theory.md` section 12; see [Blackmore2010]. **Status R through a converted text** (below). Topics 04, 17.

### [EC1998Conduction]
Electronics Cooling, *Conduction heat transfer in a printed circuit board*, May 1998, https://www.electronics-cooling.com/1998/05/conduction-heat-transfer-in-a-printed-circuit-board/ (found in a search for [CulhamYovanovich1998]; not opened). **Status N.** Topic 17.

### [Shen2019]
Y. Shen, H. Wang, F. Blaabjerg, H. Zhao, T. Long, *Thermal Modeling and Design Optimization of PCB Vias and Pads*, IEEE Trans. Power Electronics (2019), https://tenglong.eng.cam.ac.uk/files/thermalmodelinganddesignoptimizationofpcbviasandpads.pdf. **Status S** (abstract and structure read: analytical via-array and pad models verified by CFD and measurements). Topic 21.

### [ViaGuides]
Via fill and thermal via guides: JLCPCB https://jlcpcb.com/blog/via-filling-guide (table of fill materials, IPC-4761 types V to VII, **R as recorded**); ALLPCB https://www.allpcb.com/allelectrohub/how-to-choose-the-optimal-via-fill-material-for-pcb-design (**R**); Atlas PCB https://www.atlaspcb.com/blog/thermal-via-pcb-heat-dissipation-array-design (192 K/W per via; its 185 K/W for an epoxy-filled via is not a model of the fill, **R as recorded**); JLCPCB / RayPCB: 4 thermal vias about 40 K/W, 16 about 10 K/W (as recorded in `docs/roadmap.md`, **S**). The IPC-4761 standard was **not read** (**N**). Topic 21.

### [StackupTables]
Fabricator stack-up tables (`docs/validation.md` sections 10 and 14, read): OSH Park four-layer https://docs.oshpark.com/services/four-layer; Bittele https://www.7pcb.com/Upload_file/Multi-layer-stack-up.pdf; PCBGOGO https://www.pcbgogo.com/pcbgogo-standard-stackup-for-multilayer-pcbs.pdf; AdvancedPCB https://www.advancedpcb.com/en-us/resources/stackups/; NextPCB https://www.nextpcb.com/tech-center/pcb-layer-stack-up (prepreg thicknesses only); JLCPCB https://jlcpcb.com/impedance; PCBWay https://www.pcbway.com/multi-layer-laminated-structure.html and the older blog table https://www.pcbway.com/blog/Engineering_Technical/stackup___pcbway.html; Eurocircuits https://www.eurocircuits.com/standard-multilayer-builds/ (only the catalogue of cores and prepregs readable); Sierra Circuits https://www.protoexpress.com/kb/no-touch-pcbs-specs/ (no layer tables). **Status R/partial per page**, as the validation document says. Topic 22.

## 8. Copper to cells: effective conductivity, upscaling, composites, orientation

### [Sampson2017]
R. L. Sampson, *The Problem with Effective Thermal Conductivity*, Electronics Cooling, 28 April 2017, https://www.electronics-cooling.com/2017/04/problem-effective-thermal-conductivity/ (method in ASME IPACK2005-73013, 2005). **Status R through a converted text supplied by the maintainer** (the equations were reconstructed by the converter; tables and figures missing). The flow-based faces are his procedure. Topic 17.

### [Guenin2015]
B. Guenin, *Strategies for the Thermal Modeling of Metal Traces on Printed Circuit Boards*, Electronics Cooling, 20 March 2015, https://www.electronics-cooling.com/2015/03/strategies-for-the-thermal-modeling-of-metal-traces-on-printed-circuit-boards/. **Status R** (converted text, same limits). Topics 17, 21.

### [Blackmore2010]
B. Blackmore, *Creating PCB Thermal Conductivity Maps Using Image Processing*, Electronics Cooling, 13 September 2010, https://www.electronics-cooling.com/2010/09/creating-pcb-thermal-conductivity-maps-using-image-processing/ (validation in Blackmore, SEMI-THERM 2009, pp. 76-86). **Status R** (converted text). His tile formulas are the `lambda = 0` bound of the program's mappings. Topic 17.

### [CulhamYovanovich1998]
J. R. Culham and M. M. Yovanovich, *Factors affecting the calculation of effective conductivity in printed circuit boards*, Proc. Sixth Intersociety Conference on Thermal and Thermomechanical Phenomena in Electronic Systems (ITherm'98), pp. 460-467 (1998) (citation from a 2019 Springer chapter that cites it, seen in a search). Secondhand: the paper treats the board as one homogeneous body with an effective conductivity and compares three averaging schemes, and later work reports that volumetric weighting overestimates the effective conductivity, especially normal to the board; that agrees with [Sampson2017]. **Status S for the citation, N for the paper.** Topic 17.

### [Lush2004]
A. Lush, *Modeling Heat Conduction in Printed Circuit Boards Using Finite Element Analysis*, Electronics Cooling, May 2004 (cited by Blackmore and Sampson). **Status N.** Topic 17.

### [Durlofsky2005]
L. J. Durlofsky, *Upscaling and gridding of fine scale geological models for flow simulation* (2005), https://pangea.stanford.edu/departments/ere/dropbox/SmartFields/SFC_publications/2005_Durlofsky_upsc_grid_review_ifrs.pdf: local, extended-local and global upscaling; transmissibility. **Status S.** Topic 17.

### [PowerLawAveraging]
*Power-law averaging of permeability* (exponents between -1 and 1; the geometric mean for isotropic 2D media), https://ccg-server.engineering.ualberta.ca/CCG%20Publications/Other/CVD%20Papers/02-Conference/2002/power-law-averaging02.PDF. **Status S.** Topic 17.

### [KellerDykhne]
J. B. Keller (1964) and A. M. Dykhne (1970; JETP 7, 110 (1970) per a course solution at https://www.tau.ac.il/~kantor/QUIZ/01/A07.01.html): duality of two-phase two-dimensional conductivity; the effective conductivity of a random (or chessboard) two-phase medium at equal fractions is sqrt(k1 k2). The mechanism, from summaries of arXiv cond-mat/0007022, 2512.20401 and cond-mat/0002181: a local 90-degree rotation maps divergence-free current fields to curl-free electric fields, so swapping the conductivities with their inverses gives `k_e(s1, s2) k_e(1/s1, 1/s2) = 1`; Efros and Shklovskii extended Dykhne's formula near percolation (arXiv cond-mat/0310065). Other summaries: arXiv:1105.0954, cond-mat/0410073, a 2017 note in Comptes Rendus Mecanique. Neither original paper was found or opened. **Status S** (secondary sources only). Topic 17.

### [HashinShtrikman]
Z. Hashin and S. Shtrikman, *J. Mech. Phys. Solids* 11 (1963) 127-140 (citation from a search snippet): optimal bounds on the effective conductivity of isotropic composites. The explicit 2D forms used in `conduction.py` and the 2D Bruggeman equation `k^2 - (a - b)(2f - 1)k - ab = 0` were written from memory and, in this work, **checked by their properties** (`research/theory/scripts/check_mapping_formulas.py`, not by a textbook): the Bruggeman root satisfies `f (a - k)/(a + k) + (1 - f)(b - k)/(b + k) = 0` to 2e-16; it gives sqrt(ab) at f = 1/2 and `k(f) k(1 - f) = ab` (the Keller-Dykhne duality); the Hashin-Shtrikman bounds bracket the Bruggeman value and are bracketed by the two Wiener bounds; and the upper bound is the dual of the lower one (`1 / HS_upper = HS_lower` of the dual medium) to 1e-15. Searches also report that the Bruggeman equation in 2D is self-dual and lies between the Hashin-Shtrikman bounds (arXiv 2512.20401 and 2503.18715, search summaries). A second round of searches found the **general-dimension forms**, which the program's 2D formulas match with d = 2: Bruggeman, `sum_i f_i (s_i - s_B) / (s_i + (d - 1) s_B) = 0` with a unique positive root (seen in the summary of arXiv 2512.20401; for d = 2 the denominator is `s_i + s_B`, which is the equation checked in `check_mapping_formulas.py`); Hashin-Shtrikman, `s_1 + f_2 / (1 / (s_2 - s_1) + f_1 / (d s_1))` with the matrix phase as `s_1` (lower bound with the poorer phase as matrix, upper with the better one), seen in summaries of arXiv 1204.2934, a lecture note of MIT course 10.626 and arXiv 2503.18715; with d = 2 and the poorer phase `b` as matrix this is the expression `b + f / (1 / (a - b) + (1 - f) / (2 b))` of `conduction.py`. A lattice-conductivity paper (arXiv math-ph/0111048, summary) reports that in 2D the Bruggeman approximation is very accurate for random multi-phase lattices (exact up to fourth order, deviating at fifth). None of these is a primary source and none was opened. **Status S for the general-d forms and the properties, M for the textbooks and the 1963 paper.** Topic 17.

### [Milton2002]
G. W. Milton, *The Theory of Composites*, Cambridge University Press, 2002 (Cambridge Monographs on Applied and Computational Mathematics, vol. 6; it has a chapter on the Hashin-Shtrikman bounds and one on duality transformations in two-dimensional media); and S. Torquato, *Random Heterogeneous Materials: Microstructure and Macroscopic Properties*, Springer, 2002 (another listing says 2001): the places to check the 2D closed forms. Both exist per catalogue records seen in a search; no 2D formula was seen in them. **Status S for the citations, N for the content.** Topic 17.

### [Wiener1912]
O. Wiener, bounds of the effective conductivity of a two-phase medium (parallel and series, arithmetic and harmonic means); the program's `low` and `up` bounds. Named in the research code; no publication details are recorded. **Status M.** Topic 17.

### [StructureTensor]
Structure tensor and coherence (the dominant orientation of an image and its coherence (l1 - l2)/(l1 + l2)): DTU notes https://people.compute.dtu.dk/vand/notes/ST_intro.pdf, Brox et al. https://www.mia.uni-saarland.de/Publications/brox-pp141.pdf, the G'MIC tutorial https://gmic.eu/oldtutorial/_structuretensors.html. **Status S.** Topic 17.

## 9. Electrical networks, Joule heat, supply networks

### [PDNSim]
OpenROAD PDNSim documentation (supply pins as voltage sources, loads as current sources, the metal as resistances), https://openroad.readthedocs.io/. **Status S** (a search excerpt). Topic 19.

### [AltiumPDN]
Altium PDN Analyzer example guide, https://altium.com/documentation/altium-nexus/pdn-analyzer-example-guide-v2 (a source with internal resistance, a load as a current sink, shapes that dropped a 5 V rail to 4.5 V). **Status S.** Topic 19.

### [CadenceJoule]
Cadence, *The influence of the Joule heating effect on PCBs and ICs*, and the IR-drop analysis pages, https://resources.pcb.cadence.com/. **Status S.** Topic 19.

### [IPC2152]
IPC-2152, trace current against temperature rise (named in `docs/roadmap.md`, idea 1). **Status N** (standard not read). Topic 19.

### [OpenToolsIdeas]
Open-source thermal and power-integrity projects read as web summaries for ideas (`docs/roadmap.md`, "Ideas from similar projects and tools"): KiCad_Thermal_Sim (Dietschi10), pcb-sim-toolkit (mgburr), kicad-electrothermal-sim (krosa-laboratory), KiPIDA (kbralten), SPIKE (krishna-swaroop), KITS (SchrodingersGat, MIT), FYPA (Tomachie, fork of anarthrous-eda, AGPL-3.0), padne (atx, AGPL-3.0), altium_monkey (wavenumber-eng, AGPL-3.0), the Elmer and OpenFOAM write-up https://jrainimo.com/build/2024/11/oss-thermal-simulation-of-pcbs/. **Status S**; the AGPL projects are **ideas only**, no code is copied (`CLAUDE.md`, "Licences"). Topics 15, 19.

## 10. File formats, readers, outline

### [UcamcoGerber]
Ucamco, *The Gerber Layer Format Specification*, https://www.ucamco.com/en/gerber (the latest revision named by encyclopedia pages in a search is 2024.05; revision 2023.08 in an older copy). **Status N**: the specification was not read (the host is blocked); searches confirmed, from KiCad's source and forum posts, `TF.FileFunction` examples such as `Copper,L1,Top` (L1 is always the top copper), drill spans `1,4`, and the `G04 #@!` comment form of `TF` and `TA` attributes; the syntax of `TO.N` was **not** confirmed by any result. The maintainer pasted the text of the Ucamco format page (not the specification), which says that attributes carry net names and the function of an object (`TO.N`, `TA.AperFunction`) and that a job file exists. Topics 15, 19, 20.

### [Gerbonara]
gerbonara, https://pypi.org/project/gerbonara/ (documentation https://gerbolyze.gitlab.io/gerbonara); licence Apache-2.0 (PyPI, version 1.6.3); its companion shapely (https://shapely.readthedocs.io/) is BSD-3-Clause. **Status R as a tool** (used as the vector reference of `research/gerber-import`). Topics 15, 20.

### [GerberTools]
pygerber (2.4.3), pcb-tools (0.1.6) and Ucamco's gerber-writer, used as comparison tools (`research/gerber-import/README.md` 4.22 and 4.24). **Status R as tools.** Topic 15.

### [KiCadFormat]
KiCad `.kicad_pcb` file format (text, s-expressions), version 20171130, as in the MIT-licensed Stormduino project https://github.com/Chromico/stormduino. **Status R** (read by `research/gerber-import/lib/kicad_pcb.py`). Topics 15, 19.

### [ProfileLayer]
The board outline as the Gerber profile layer (web searches, snippets only): the X2 file attribute `TF.FileFunction,Profile,NP` (DipTrace forum https://diptrace.com/forum/viewtopic.php?p=33620; https://en.wikipedia.org/wiki/Gerber_format); Altium on a closed path (https://altium.com/documentation/node/304685/printable/print?version=22); KiCad forum threads on strokes and gaps (https://forum.kicad.info/t/kicad-edge-cuts-rejected-by-jlcpcb/27159, https://forum.kicad.info/t/gerber-file-errors-due-to-edge-cuts-not-connected/9467, https://forum.kicad.info/t/how-to-define-the-board-outline-pcb-edge/32166); MacroFab https://help.macrofab.com/knowledge/how-to-ensure-the-board-outline-is-correct. **Status S.** No source gave a rule for the size of a gap to close. Topic 20.

## 11. Own computations (status L)

These are not publications; they are the repository's own studies that give numbers quoted in the topics. Paths are from the repository root.

| Key | What | Topics |
| :-- | :-- | :-- |
| `[L-validation]` | `docs/validation.md` and `research/models-comparison/` (19 scenarios, five models, grids, solvers, time) | 01 to 07 |
| `[L-solid3d]` | `research/solid3d-verification/` (Yovanovich Table 3, GCI, the finite-element check, the axisymmetric solver of README 4.3) | 04, 18 |
| `[L-block]` | `research/block-and-fins/` (fin against a 2D fin, the block in Lumped and Analytic, 74 cases) | 11 |
| `[L-parts]` | `research/component-heatsink/` (package prototype, top path, heatsink convection scenarios) | 09, 12, 13 |
| `[L-calc]` | `research/power-calculator/` (datasheet validation, error, ways to reduce it) | 14, 23 |
| `[L-outline]` | `research/outline/` (the rectangle of the same area) | 20 |
| `[L-stackup]` | `research/stackup/` | 22 |
| `[L-via]` | `research/via-fill/` | 21 |
| `[L-legacy]` | the removed wxPython program (tag `legacy-wxpython-1.0.0`, commit `641da87`) run on the example board, `docs/validation.md` section 6 | 32 |
| `[L-gerber]` | `research/gerber-import/`, `research/gerber-models/`, `research/gerber-nets/` (reader, mappings, tensor, nets) | 15, 17, 19, 20 |

## 12. Textbooks and standards that the project documents name but that were not opened

For honesty, the list of sources whose content in the topics comes from the project documents and from memory: [Patankar1980], [IncroperaDeWitt], [CarslawJaeger], [Lee1995], [ChurchillChu1975], [ChurchillBlend], [JESD51family], [ASTMD5470], [Roache], [HashinShtrikman], [Wiener1912], [IPC2152], [UcamcoGerber]. A statement taken only from one of these is marked "(memory)" or "(from the project documents)" in the topic.

## 13. Licences of the quoted material

Numbers and facts with their source are quoted; no text, figure or file of a third party is copied here. The AGPL projects of [OpenToolsIdeas] are ideas only.

## 14. What should be read next to close the gaps

1. The texts that are named as the base of a method and were not opened (some now have a confirmed citation, none was read): Patankar (1980), Carslaw and Jaeger, Incropera and DeWitt, Churchill and Chu (1975), Churchill (1977) and whether the program's blending rule is its rule, Lee et al. (1995) (the citation itself is unconfirmed), Culham and Yovanovich (1998), Lush (2004), Milton and Torquato for the 2D closed forms, the Ucamco specification, Briggs and others for multigrid.
2. For the planned topics: the Nexperia note AN11261 in full (only a summary was seen), Briggs and others and the pyamg documentation, Elenbaas and Bar-Cohen and Rohsenow in the originals.
3. The JEDEC standards themselves (JESD51 family), IPC-4761 and IPC-2152.
4. Replace every "M" and "S" entry by a read source, or keep the statement marked, when a topic is adopted into `docs/theory.md`.
