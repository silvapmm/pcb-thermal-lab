# Reference compilation supplied by the maintainer

Provenance: a research compilation brought to this work by the maintainer (done in another session); it is kept here as received, apart from the removal of the line that gave the date of the compilation. **It was not re-verified here**, except for the numerical checks listed in the next section. Its own tags say what was read there and what is from memory: `[READ]` content opened and read, `[PARTIAL]` abstract, table of contents or secondary citation only, `[BLOCKED]` exists but could not be opened, `[NOT FOUND]` not resolved; for formulas `(src)` seen in a retrieved source, `(mem)` written from general knowledge, `(calc)` checked numerically there.

## What this repository checked of it

`research/theory/scripts/check_correlations.py` and `check_mapping_formulas.py` (run from the repository root):

| Item | Result here |
| :-- | :-- |
| 2D Hashin-Shtrikman, `s1 = 1`, `s2 = 4`, `phi = 1/2` | lower 13/7 = 1.8571, upper 28/13 = 2.1538, product 4.0000 = `s1 s2`: as the compilation says; and `lower(phi) x upper(1 - phi) = s1 s2` for every `phi` to 1.3e-15 |
| Bar-Cohen and Rohsenow composite | the two limits are reproduced (`Ra*/24` at small `Ra*`, `0.590 Ra*^(1/4)` at large); `2.714^4 = 54.3` |
| Elenbaas | the fully developed limit `Ra*/24` and, at large `Ra*`, `0.62 Ra*^(1/4)` within about 3 % |
| Churchill-Chu all-range | the worked example of the Python `ht` library (Pr 0.69, Gr 2.63e9) gives 147.16, reproduced to the digit |
| Churchill-Chu laminar form against the all-range form | Pr 0.71: laminar form +6.6 % at Ra 1e5, -5.2 % at 1e7, -25 % at 1e9 (the all-range form includes the turbulent rise) |
| Hollands (1984) | **a correction of the compilation**: the `ht` example is `Nu_Nusselt_Rayleigh_Hollands(5.54, 3.21e8)` where the second argument is the **Grashof number** (`Ra = Gr Pr = 1.778e9`), not `Ra = 3.21e8`; and the library's documentation writes `Ra^(1/5)` inside the logarithm while its **code** uses `Ra^(1/3)`; only the code reproduces the library's own example (69.0267). The source of the package (version 1.2.0, MIT) was read for this; the paper itself was not |
| Printed board of the 1998 article | in-plane 17.41 W/mK and through-plane 0.2615 W/mK, as the compilation says |

Other differences with the project's earlier notes, accepted from the compilation: the Hashin-Shtrikman paper for **conductivity** is J. Appl. Phys. 33 (1962) 3125-3131, not the elastic-moduli paper of 1963 that the earlier notes cited; the Gerber specification's latest revision is 2024.05; the May 2004 Electronics Cooling item is by Simons, and "Lush" is not identified.

---

# Reference compilation: composites, PCB thermal modelling, natural convection, multigrid, standards (as received)

Every entry has an **access status** and a **provenance tag** for each formula, so you can see what was actually read and what still needs checking against the primary source.

> **Corrections to the original list (important)**
> 1. **Hashin & Shtrikman, J. Mech. Phys. Solids 11 (1963) 127-140** is the *elastic-moduli* paper ("A variational approach to the theory of the elastic behaviour of multiphase materials"). The *conductivity / permeability / dielectric* bounds are in **J. Appl. Phys. 33 (1962) 3125-3131**, doi 10.1063/1.1728579. For thermal conductivity you want the 1962 JAP paper.
> 2. **"Churchill, AIChE J. 23(1), 1977, p. 10"** resolves to *"A comprehensive correlating equation for laminar, assisting, forced and free convection"*, AIChE J. 23(1), 10-16. It is the mixed-convection (forced + free) blending paper, so it is the right place to check the blending rule.
> 3. **Culham & Yovanovich, ITherm'98, pp. 460-467** resolves to *"Factors affecting the calculation of effective conductivity in printed circuit boards"*.
> 4. **Lush (May 2004, Electronics Cooling)** could **not** be identified (see 1.5).
> 5. **Gerber spec**: latest revision is **2024.05** (July 2024). The Ucamco news page links a PDF whose *filename* says "revision-2022-02", which does not match. Confirm the revision on the title page after download.
> 6. **JESD15-3** is the *Two-Resistor Compact Thermal Model Guideline*. It is free after registration. JESD51-3 and JESD51-7 did not appear in the JEDEC listing page that could be read (see 1.4).

## Part 1: free or easily accessible sources

### 1.1 Milton, *The Theory of Composites* (Cambridge University Press, 2002)
- **Status:** `[BLOCKED]` for the full text. The author's PDF `math.utah.edu/~milton/TheoryCompositesNOPRINT.pdf` is refused by the fetch tool (robots.txt). The table of contents is `[PARTIAL]` from search snippets. Open the PDF directly in a browser; it is on the author's site.
- **Chapters seen:** 14 Series expansions for the fields and effective tensors; 15 Correlation functions and how they enter series expansions; 16 Other perturbation solutions; 17 The general theory of exact relations and links between effective tensors; 18 Analytic properties; 19 Y-tensors; 20 Y-tensors and effective tensors in electrical circuits; 21 Bounds on the properties of composites (p. 425); 22 Classical variational principle bounds (p. 437); 23 Bounds from the Hashin-Shtrikman variational inequalities (p. 457); 24 Bounds using the compensated compactness or translation method (p. 499); 25 Choosing the translations and finding microgeometries that attain the bounds (p. 529); 26 Bounds incorporating three-point correlation functions (p. 553); 27 Bounds using the analytic method (p. 569); 28 Fractional linear transformations as a tool for generating bounds (p. 603); 29 The field equation recursion method; 30 Properties of the G-closure and extremal families of composites; 31 The bounding of effective moduli as a quasiconvexification problem (p. 671).
- **For the 2D-formula check:** Ch. 23 (Hashin-Shtrikman bounds); Ch. 17 (exact relations and phase interchange; Milton's own summary of his papers describes the *Keller-Dykhne-Mendelson phase interchange relation* as the constraint on 2D two-phase conductivity); Ch. 28 (fractional-linear transformations). The chapter that holds the 2D duality transformations was **not confirmed**: use the subject index entries "duality", "phase interchange", "Keller-Dykhne".

### 1.2 McCormick & Tamstorf, multigrid primer
- **Status:** `[READ]`: `grandmaster.colorado.edu/~stevem/mgprimer.pdf` opened. The author names were not shown in the extract; confirm the byline on the title page.
- **Contents:** 1 Introduction; 2 Preliminaries; 3 Smoothing; 4 Coarse-grid correction; 5 A word about residuals; 6 Multilevel solvers (V- and W-cycles); 7 FMG (full multigrid); 8 Basic theory (8.1 cycling as an iterative method, 8.2 FMG as a direct method); 9 Development (algorithm, problem formulation); 10 Summary; References; Appendix A: Approximation properties.
- **Formulas extracted `(src)`:**

| Item | Formula |
| :-- | :-- |
| Smoothing (Richardson, section 3) | `v^h <- v^h - (1/||L^h||)(L^h v^h - g^h)`; error propagation `e^h <- G^h e^h`, `G^h = I^h - L^h/||L^h||` |
| Restriction | `R_h^{2h} = alpha_h (P_{2h}^h)^t`, `alpha_h > 0` free scaling |
| Galerkin coarse operator | `L^{2h} = R_h^{2h} L^h P_{2h}^h` |
| Coarse-grid correction | `v^h <- v^h - P_{2h}^h (L^{2h})^{-1} R_h^{2h} (L^h v^h - g^h)` |
| Two-grid error propagation | `TG^h = G^h T^h`, `T^h = I^h - S^h`, `S^h = P_{2h}^h (L^{2h})^{-1} R_h^{2h} L^h` (energy-orthogonal projector onto range of P) |
| V-cycle (Alg. 3) | relax mu times; restrict residual `g^{2h} = R_h^{2h}(L^h v^h - g^h)`; solve the coarse problem recursively from a zero guess; correct `v^h <- v^h - P_{2h}^h v^{2h}`; relax nu times |
| V-cycle error recursion | `MV^h = G^h ( P_{2h}^h MV^{2h} (L^{2h})^{-1} R_h^{2h} L^h + T^h )` |
| W-cycle | same, but the coarse problem is visited twice per level |
| Two-grid convergence | `||TG^h||^2_{L^h} <= gamma < 1` iff `M_s(t^h) >= delta > 0` on range of `T^h` |
| Strong Approximation Property | `||T^h e^h||^2_{L^h} <= (C/||L^h||) <L^h e^h, L^h e^h>` |
| Theorem 1, V(0,1)-cycle | `||MV^h||^2_{L^h} <= 1 - 1/C` |
| Weak Approximation Property | `||T^h e^h||^2 / ||e^h||^2 <= C M_w(e^h)` |
| Weak / strong measures | `M_w(e) = <Le,e>/(||L|| <e,e>)`, `M_s(e) = <Le,Le>/(||L|| <Le,e>)` |
| FMG accuracy target | `||v^h - u^h||_L <= C h^m` |
| FMG cycle requirement | reduce error by about `2^{-(m+1/2)}` per level; for the model Poisson problem (m = 1) a V(2,1)-cycle is typically enough |

### 1.3 Ucamco, Gerber Layer Format Specification
- **Status:** `[PARTIAL]`: the Ucamco page was read through the fetch tool; the PDF itself was not downloaded.
- **Latest revision:** **2024.05**, dated **03/07/2024** (Ucamco gerber page); Wikipedia also lists 2024.05 (3 July 2024).
- **Links:** landing page `https://www.ucamco.com/en/gerber`; announcement `https://www.ucamco.com/en/news/gerber-layer-format-specification-revision-202405`; downloads `https://www.ucamco.com/en/guest/downloads/gerber-format`.
- **Warning:** the announcement page's PDF link carries the filename `gerber-layer-format-specification-revision-2022-02_en.pdf` while the page text says 2024.05. Download from the Downloads page and read the revision on the cover.
- **Context (src, Wikipedia):** X2 (Feb 2014) added attributes. The `.FileFunction` attribute is the standard way to link a layer to its file, e.g. `%TF.FileFunction,Copper,L1,Top*%` (L1 is always top copper). Related Ucamco documents (not verified individually): XNC drill format, GerberJob.

### 1.4 JEDEC, JESD15-3 and the JESD51 family
- **Status:** `[PARTIAL]`: listing page read; no document downloaded. Every entry seen is **"Free download. Registration or login required."**

| Number | Title | Date |
| :-- | :-- | :-- |
| JESD15-3 | Two-Resistor Compact Thermal Model Guideline | Jul 2008 |
| JESD15-4 | Delphi Compact Thermal Model Guideline | Oct 2008 |
| JESD51-2A | IC thermal test method environmental conditions, natural convection (still air) | Jan 2007 |
| JESD51-5 | Extension of thermal test board standards for packages with direct thermal attachment mechanisms (reaffirmed Feb 2026) | Feb 1999 |
| JESD51-6 | Environmental conditions, forced convection (moving air) | Mar 1999 |
| JESD51-8 | Environmental conditions, junction-to-board | Oct 1999 |
| JESD51-9 | Test boards for area array surface mount package thermal measurements | Jul 2000 |
| JESD51-10 | Test boards for through-hole perimeter leaded packages | Jul 2000 |
| JESD51-11 | Test boards for through-hole area array leaded packages | Jun 2001 |
| JESD51-12.01 | Guidelines for reporting and using electronic package thermal information | Nov 2012 |
| JESD51-13 | Glossary of thermal measurement terms and definitions | Jun 2009 |
| JESD51-14 | Transient dual interface test method for junction-to-case resistance (single heat path) | Nov 2010 |
| JESD51-31 | Thermal test environment modifications for multichip packages | Jul 2008 |
| JESD51-32 | Extension to JESD51 thermal test board standards for multi-chip packages | Dec 2010 |
| JESD51-34 | Guideline for thermal characterization of multichip packages using linear superposition | Apr 2026 |
| JESD51-51A/52A/53A | LED thermal-testing family | Nov/Nov/Oct 2022 |
| JESD88G | Dictionary of terms for solid-state technology | Mar 2025 |

- **JESD51-3 and JESD51-7** (low- and high-effective-conductivity test boards) did **not** appear on the page text that could be read. From general knowledge `(mem)`: JESD51-3 is the low-k board (1s0p) and JESD51-7 the high-k board (2s2p). Search them by number on jedec.org.
- **JESD15-3 scope (src):** defines and constructs a two-resistor compact thermal model from junction-to-case and junction-to-board metrics (as defined in JESD51-8 and JESD51-12); single-die packages only. **Model form (mem):** two resistors `Theta_JC` and `Theta_JB` in parallel from the junction node.

### 1.5 Electronics Cooling articles

**(a) "Conduction heat transfer in a printed circuit board", May 1998: `[READ]`.** URL `https://www.electronics-cooling.com/1998/05/conduction-heat-transfer-in-a-printed-circuit-board/` (Calculation Corner, "Electronics Cooling Editors"). The equations are images on the page; they are the standard layer series/parallel formulas, written `(mem)` and checked against the article's own numbers `(calc)`:

    k_in-plane      = sum_i ( k_i t_i ) / sum_i t_i                 (layers in parallel)
    k_through-plane = sum_i t_i / sum_i ( t_i / k_i )               (layers in series)
    trace layer:      k_i = f_i k_Cu    (f_i = copper coverage fraction of layer i)  (src)

Article's example `(src)`: total thickness 1.59 mm; k_Cu = 390, k_FR4 = 0.25 W/mK; board with 2 internal planes and 2 outer trace layers, each 35 um (1 oz/ft2), 70 um copper in total: about 17.4 W/mK in-plane, about 0.26 W/mK through-plane. `(calc)` With 0.07 mm Cu and 1.52 mm FR-4: k_in = 17.41, k_through = 0.2615. Messages: once a continuous copper path exists in the heat-flow direction it dominates; only layers that can spread heat a useful distance should be counted; for boards with added planes only the planes count (empirical study); for a JEDEC test PCB the trace layers should be included. References of the article: Graebner, Electronics Cooling 1(2), Oct 1995, p. 27; Azar and Graebner, SEMI-THERM XII, Mar 1996, pp. 169-182. Follow-up: "Convection and radiation heat loss from a printed circuit board" (1998).

**(b) "Lush", May 2004: `[NOT FOUND]`.** No Electronics Cooling article by an author named Lush in May 2004. The Calculation Corner for **May 2004** is **R. Simons, "Simple Formulas for Estimating Thermal Spreading Resistance"** (URL `electronics-cooling.com/2004/05/simple-formulas-for-estimating-thermal-spreading-resistance/`; the fetch tool refused that page, so its formulas are not included). Other 2004 items: Guenin, "Thermal Vias, A Packaging Engineer's Best Friend" (Aug 2004); Guenin, "Entrance Effects for Heat Flow Into a Multi-Layer Printed Circuit Board" (Nov 2004). Action: check the original note where "Lush" appeared (a different journal, a misspelling, or a different month).

**(c) Simons, "Estimating Natural Convection Heat Transfer for Arrays of Vertical Parallel Flat Plates", Feb 2002: `[READ]` (equations are images).** URL `https://www.electronics-cooling.com/?p=228`. Content `(src)`: Elenbaas correlation (Eq. 1) in terms of Nu and Ra; channel Rayleigh number (Eq. 2); gap `b` from base width W, number of plates N_f and plate thickness t (Eq. 3); total heat rate with fin efficiency taken as 1 (Eq. 4); **optimum spacing by setting the channel Rayleigh number to about 50** (Eqs. 5-6). No Bar-Cohen-Rohsenow formula; it cites Kraus and Bar-Cohen, *Design and Analysis of Heat Sinks* (1995).

**(d) Other items found:** pixel-based board conductivity map (`electronics-cooling.com/?p=4005`) `(src)`: through-plane k from all pixels in parallel; in-plane `k_x` from rows in parallel, each row's pixels in series: `R_row = N_white L_px/(k_diel W_px t) + N_black L_px/(k_cond W_px t)`, `1/R_total = sum 1/R_row`, `k_x = [L_tile/(W_tile t)] sum(1/R_row)`. Teertstra, "Natural convection modeling of heat sinks using web-based tools" (Sept 2000). Simons, "Estimating Parallel Plate-fin Heat Sink Thermal Resistance" (Feb 2003).

## Part 2: papers (library or paid)

### 2.1 Churchill and Chu, Int. J. Heat Mass Transfer 18(11), 1975, pp. 1323-1329, doi 10.1016/0017-9310(75)90243-4
"Correlating equations for laminar and turbulent free convection from a vertical plate." **Status `[PARTIAL]`**: paper not opened; correlations confirmed from three independent secondary sources (Python `ht` "checked with the original source", pychemqt, Incropera tables).
- Vertical isothermal plate, all `Ra_L` `(src)` (Incropera Eq. 9.26): `Nu_L = { 0.825 + 0.387 Ra_L^(1/6) / [1 + (0.492/Pr)^(9/16)]^(8/27) }^2`.
- Laminar (`Ra_L` up to about 1e9), slightly more accurate `(src)` (Eq. 9.27): `Nu_L = 0.68 + 0.670 Ra_L^(1/4) / [1 + (0.492/Pr)^(9/16)]^(4/9)`.
- `Ra_L = g beta (T_s - T_inf) L^3 / (nu alpha)`, properties at the film temperature `(T_s + T_inf)/2` `(src)`. A vertical cylinder may be treated as a plate if `D/L >= 35 / Gr_L^(1/4)`. Inclined plates: use `g cos(theta)` for theta up to 60 degrees.
- Companion paper (horizontal cylinder): Churchill and Chu, IJHMT 18(9), 1975, p. 1049: `Nu_D = { 0.60 + 0.387 Ra_D^(1/6) / [1 + (0.559/Pr)^(9/16)]^(8/27) }^2`, `Ra_D <= 1e12`. Sphere (Churchill 1983, Incropera Eq. 9.35): `Nu_D = 2 + 0.589 Ra_D^(1/4) / [1 + (0.469/Pr)^(9/16)]^(4/9)`, `Pr >= 0.7`, `Ra_D <= 1e11`.
- Horizontal plates, `L = A_s/P` `(src)` (Incropera 9.30-9.32): upper surface of a hot plate `Nu = 0.54 Ra^(1/4)` (1e4 to 1e7), `Nu = 0.15 Ra^(1/3)` (1e7 to 1e11); lower surface of a hot plate `Nu = 0.27 Ra^(1/4)` (1e5 to 1e10).
- Note (Churchill, 2013 AIChE abstract): the constant 0.60 in the cylinder equation is really (0.60)^2 = 0.36 as Ra tends to 0; an artefact of extending thin-boundary-layer theory to low Ra.

### 2.2 Churchill, AIChE J. 23(1), 1977, pp. 10-16, "A comprehensive correlating equation for laminar, assisting, forced and free convection"
**Status `[PARTIAL]`**: bibliographic identity confirmed (Crossref citation lists and a reference list give "AIChE Journal, 23, pp. 10-16"). **Full text not opened. The equation below is from memory.** Mixed-convection blending `(mem, verify)`: `Nu^n = Nu_forced^n +- Nu_free^n` (+ assisting, - opposing), n = 3 is the commonly used value for external flows. Check the exponent and the sign convention against the paper before concluding that the program's rule is "his". Related Churchill papers confirmed: Churchill and Churchill, AIChE J. 21(3), 1975, p. 604; Churchill, Ind. Eng. Chem. Fundam. 16(1), 1977, 109-116, doi 10.1021/i160061a021; Churchill and Bernstein, J. Heat Transfer 99(2), 1977, 300-306, doi 10.1115/1.3450685; Churchill, Lett. Heat Mass Transfer 4(3), 1977, 193-199.

### 2.3 Churchill and Usagi, and Hashin-Shtrikman, and duality
**Churchill-Usagi, AIChE J. 18, 1972, 1121-1128 (volume and page from memory).** Abstract seen. Rule `(src)`: `Y = (1 + Z^n)^(1/n)`, with Y and Z built from the asymptotic solutions for large and small values of the independent variable; n found from plots of Y vs Z and Y/Z vs 1/Z, insensitive, so the nearest integer is acceptable. Power-mean form `(mem)`: `Phi^n = Phi_0^n + Phi_inf^n`. Extension: Churchill and Usagi, Ind. Eng. Chem. Fundam. 13(1), 1974, 39-44, doi 10.1021/i160049a008. The composite of Bar-Cohen and Rohsenow is exactly this form with n = -2 (see 2.5).

**Hashin and Shtrikman, J. Appl. Phys. 33(10), 1962, 3125-3131, doi 10.1063/1.1728579.** Abstract seen: the bounds are valid for dielectric constant, electric conductivity, **heat conductivity** and diffusivity, and are the most restrictive possible in terms of phase properties and volume fractions for two-phase materials. Isotropic two-phase conductivity in d dimensions (phases s1 < s2, fractions phi1, phi2 = 1 - phi1):

    Wiener (series / parallel) (src):   <s^-1>^-1  <=  s*  <=  <s>
    HS lower (mem):  s_L = s1 + phi2 / [ 1/(s2 - s1) + phi1/(d s1) ]
    HS upper (mem):  s_U = s2 + phi1 / [ 1/(s1 - s2) + phi2/(d s2) ]
    Equivalent upper-bound form (src, arXiv:1808.02553, s2 > s1):  s_U = <s> - phi1 phi2 (s2 - s1)^2 / [ d s2 + (s1 - s2) phi2 ]
    3-D form (src, Milton / arXiv:1105.0954):  (k* - k2)/(k1 - k2) >= 3 phi1 k2 / (phi2 k1 + phi1 k2 + 2 k2)

Realised by space-filling coated spheres or circles, second-rank laminates, Vigdergauz constructions `(src)`. If the percolating phase is the high-conductivity one the upper bound applies, and vice versa. 2D check `(calc)`: s1 = 1, s2 = 4, phi = 1/2: s_L = 13/7 = 1.857, s_U = 28/13 = 2.154, product 4.000 = s1 s2, and sqrt(s1 s2) = 2 lies inside; in 2D at equal fractions the two bounds multiply to s1 s2, consistent with Keller-Dykhne. The elastic companion is Hashin and Shtrikman, J. Mech. Phys. Solids 11, 1963, 127-140; also JMPS 10, 1962, 335-342.

**2D duality (Keller 1964, Dykhne 1970)** `(src)` from arXiv cond-mat/0310065, 0410073, 0403256, 0303622. Keller, J. Math. Phys. 5 (1964) 548. Dykhne, Sov. Phys. JETP 59 (1970) 110 (Russian original, ZhETP). Phase-interchange relation (2D, isotropic, two-phase, fractions x and 1 - x):

    s_eff(x; s1, s2) s_eff(1 - x; s1, s2) = s1 s2
    equal fractions (x = 1/2), statistically symmetric:   s_eff = sqrt(s1 s2)
    inversion form:  s_e at inverted partial conductivities (s_i -> s0^2/s_i) equals s0^4 / s_e  (for s0 = 1: s_e(1/s1, 1/s2) = 1/s_e(s1, s2))

Valid for the chessboard and for a plane of triangles (Dykhne's result holds there). Self-dual extension for compact inclusions, **approximate, not exact**: `s_eff = s1^x s2^(1-x)`. Efros-Shklovskii near percolation: `s_eff = s1 (s2/s1)^s`, s a universal exponent. Milton's 2D result `(src, his summary)`: a proof that laminates generate all possible effective conductivity functions of 2D two-phase materials; the function has a Stieltjes-type representation and satisfies the Keller-Dykhne-Mendelson relation. Related: Helsing, McPhedran and Milton, "Proof of a conjecture on the conductivity of checkerboards".

### 2.4 Culham and Yovanovich, ITherm 1998, pp. 460-467, "Factors affecting the calculation of effective conductivity in printed circuit boards"
**Status `[PARTIAL]`**: title, venue and pages confirmed (Springer reference lists); paper not opened. Known `(src, secondary)`: Culham modelled the PCB as one homogeneous body with an effective conductivity, combining the in-plane and normal conductivities with **three different averaging schemes**. A later paper (Shabany, ITherm 2002, pp. 489-494) showed that averaging methods can mispredict PCB temperature. Same group: Culham, Yovanovich and Lemczyk, ASME J. Electronic Packaging 122(3), 2000, 233-239; Lemczyk, Mack, Culham and Yovanovich, "PCB trace thermal analysis and effective conductivity", SEMI-THERM VII, 1991, 15-22; Ellison, "Thermal analysis of microelectronic packages and PCBs using an analytic solution to the heat conduction equation", WIT Trans. Eng. Sci. 3 (1993), open access at witpress.com. Candidate averaging formulas to compare with the paper `(mem)`: `k_eff = k_par`, `k_eff = k_ser`, `sqrt(k_par k_ser)`, `(k_par + k_ser)/2`. **Which three the paper uses is not confirmed.**

### 2.5 Bar-Cohen and Rohsenow, J. Heat Transfer 106(1), 1984, pp. 116-123, "Thermally optimum spacing of vertical, natural convection cooled, parallel plates"
**Status `[PARTIAL]`**: abstract seen: the idealised configurations (symmetric or asymmetric, isothermal or isoflux plates) allow analytic optimisation by maximising total heat transfer per unit volume or per unit primary area; they combined the fully developed channel and single-plate asymptotes by composite relations. Isothermal symmetric plates `(src)` (a course note reproducing Incropera Eq. 9.45):

    Nu_S = [ 576 / (Ra_S S/L)^2  +  2.873 / (Ra_S S/L)^(1/2) ]^(-1/2)         Ra_S = g beta (T_s - T_inf) S^3 / (nu alpha)

`(calc)` Limits: the first term gives `Nu_S -> Ra*/24` (fully developed), the second `Nu_S -> 0.590 Ra*^(1/4)` (isolated plate), with `Ra* = Ra_S S/L`; a Churchill-Usagi blend with n = -2. Optimum spacing `(mem, verify)`: `S_opt ~ 2.714 L / Ra_L^(1/4)`, `Nu_opt ~ 1.307` for the isothermal symmetric case. `(calc)` `2.714^4 = 54.3`, so `Ra*_opt ~ 54`, close to Simons' "about 50". Other correlations seen: Aung et al. channel correlations `(src, Maya help page)` with `m = -1.9, c = 1.2, C_l = 0.515` (isothermal, air, valid to Ra about 1e5) and `m = -3.5, c = 1.07, H_l = 0.624` (uniform flux, air).

### 2.6 Elenbaas (1942) and Hollands
**Elenbaas, Physica 9 (1942), "Heat dissipation of parallel plates by free convection".** `[PARTIAL]`: the original was not opened; pages "1-28" from memory. Elenbaas correlation `(src)` (isothermal, symmetric, vertical channel, air; range 0.1 < Ra* < 1e5): `Nu = (Ra*/24) [ 1 - exp(-35/Ra*) ]^(3/4)`, `Ra* = Ra_S (S/L) = g beta dT S^4 / (nu alpha L)`. Asymptotes: `Ra*/24` and, for large Ra*, the boundary-layer value about `0.62 Ra*^(1/4)` in Martin-Raithby-Yovanovich's rewriting `Nu_bl = 0.62 Ra*^(1/4) (H/b)^(3/2)` (forms differ by Nu definition). Optimum `Ra* ~ 50` per Elenbaas as reported by Simons. Related: Bodoia and Osterle, J. Heat Transfer 84 (1962); Sparrow and Bahrami, J. Heat Transfer 102 (1980); Bejan (1984/1995); Fujii and Miyatake, Heat Transfer Jap. Res. 1 (1972).

**Hollands, two relevant papers.** (1) Hollands, Unny, Raithby and Konicek, "Free convective heat transfer across inclined air layers", J. Heat Transfer 98 (1976) 189-193 `[PARTIAL]` (existence confirmed in a J. Fluid Mech. reference list); classic form `(mem)`: `Nu = 1 + 1.44 [1 - 1708/(Ra cos(theta))]* + [ (Ra cos(theta)/5830)^(1/3) - 1 ]*` (* = positive part only). (2) Hollands, "Multi-Prandtl number correlation equations for natural convection in layers and enclosures", IJHMT 27(3), 1984, 466-468, doi 10.1016/0017-9310(84)90295-3, in the form of the Python `ht` documentation `(src)`:

    Nu = 1 + [1 - 1708/Ra]* [ k1 + 2 (Ra^(1/3)/k2)^(1 - ln(Ra^(1/5)/k2)) ]* + [ (Ra/5803)^(1/3) - 1 ]*
    k1 = 1.44 / (1 + 0.018/Pr + 0.00136/Pr^2)        k2 = 75 exp(1.5 Pr^(-0.5))

For Ra < Ra_c, Nu = 1. The `ht` example: `Nu(Pr = 5.54, Ra = 3.21e8) = 69.03`. *(Corrected here: the example's second argument is the Grashof number; and the code uses Ra^(1/3) inside the logarithm, see the checks above.)* Ambiguity to resolve: which Hollands paper the program's notes cite is not known; it may also be Raithby and Hollands (Advances in Heat Transfer 11, 1975, p. 265), which the J. Fluid Mech. reference lists cite.

## Part 3: books (library)

| Book | Details confirmed | Status |
| :-- | :-- | :-- |
| **Patankar**, *Numerical Heat Transfer and Fluid Flow* (Hemisphere/McGraw-Hill, 1980) | ISBN 0-89116-522-3 (CRC reissue 978-0-89116-522-4); xiii + 197 pp.; bibliography pp. 189-193. Chapters seen: 1 Introduction; 2 Mathematical description of physical phenomena; later chapters cover discretization, heat conduction, convection-diffusion, flow calculation (SIMPLE) and a final chapter of worked examples | `[PARTIAL]` |
| **Incropera and DeWitt** (et al.), *Fundamentals of Heat and Mass Transfer* (Wiley) | Edition not recorded in the project's list. Equation numbers 9.26/9.27 (plate) and 9.46 (channel) are the 3rd ed. (1990), pp. 543 and 557 `(src, Maya)`. The 6th ed. (2006) is ISBN 978-0-471-45728-2; Intl. "Principles of Heat and Mass Transfer" 7th ed. is ISBN 978-0-470-64615-1, 1048 pp. Chapter 9 = Free Convection. Equation numbers shift between editions | `[PARTIAL]` |
| **Carslaw and Jaeger**, *Conduction of Heat in Solids*, 2nd ed. (Clarendon, Oxford, 1959; paperback reprint 1986) | viii + 510 pp.; ISBN 0-19-853303-9 (hardcover), 0-19-853368-3 (pbk, 1986). First ed. 1946 | `[PARTIAL]` |
| **Torquato**, *Random Heterogeneous Materials: Microstructure and Macroscopic Properties* (Springer, 2002; Interdisciplinary Applied Mathematics vol. 16) | xxi + 701 pp.; ISBN 0-387-95167-9 / 978-0-387-95167-6; eBook DOI 10.1007/978-1-4757-6355-3. Part I microstructure characterisation; Part II effective properties (local and homogenised equations, variational principles, phase-interchange relations, exact results, single-inclusion solutions, effective-medium approximations, cluster expansions, exact contrast expansions, rigorous bounds, evaluation of bounds, cross-property relations) | `[PARTIAL]` |
| **Briggs, Henson and McCormick**, *A Multigrid Tutorial*, 2nd ed. (SIAM, 2000) | ISBN 978-0-89871-462-3; xii + 193 pp. Chapters: 1 Model problems; 2 Basic iterative methods; 3 Elements of multigrid; 4 Implementation; 5 Some theory; 6 Nonlinear problems; 7 Selected applications; 8 Algebraic multigrid (AMG); 9 Multilevel adaptive methods; 10 Finite elements | `[PARTIAL]` |

Standard formulas from these books to check (all `(mem)`): Patankar power-law scheme `a_P phi_P = a_E phi_E + a_W phi_W + b`, `a_E = D_e A(|P_e|) + max(-F_e, 0)`, `a_W = D_w A(|P_w|) + max(F_w, 0)`, `a_P = a_E + a_W + (F_e - F_w)`, `A(|P|) = max(0, (1 - 0.1|P|)^5)`, `P = F/D`; Carslaw and Jaeger transient slab and semi-infinite solid with `erfc`, `(T - T_i)/(T_s - T_i) = erfc( x / (2 sqrt(alpha t)) )`, and the point, line and disc source solutions behind spreading-resistance formulas; multigrid (Briggs) weighted Jacobi with `omega = 2/3` in 1-D as optimal smoother for the model problem, full weighting restriction and linear interpolation as variational pair, V-cycle cost about O(N); Torquato's Wiener, Hashin-Shtrikman, Beran and Milton three-point bounds, Maxwell-Garnett and Bruggeman effective-medium formulae (the exact forms in the book were not retrieved).

## Part 4: paid or registration standards

| Standard | Edition / date | What the retrieved sources say | Status |
| :-- | :-- | :-- | :-- |
| **IPC-2152**, *Standard for Determining Current Carrying Capacity in Printed Board Design* | Aug 2009, 108 pp. | General guide to the relation between current, conductor size and temperature; effect of thermal conductivity, vias, copper planes, power dissipation, board material and thickness. Table of contents file `electronics.org/TOC/IPC-2152.pdf` (not read) | `[PARTIAL]` |
| **IPC-4761**, *Design Guide for Protection of Printed Board Via Structures* | July 2006, 16-28 pp. depending on the vendor | **7 via-protection types (Type I to VII)**: tenting, plugging, filling, capping. Preview PDF with table of contents at `webstore.ansi.org/preview-pages/IPC/preview_IPC+4761-2006.pdf`. Price seen about 173 euro (PDF) | `[PARTIAL]` |
| **ASTM D5470**, *Thermal Transmission Properties of Thermally Conductive Electrical Insulation Materials* | D5470-17 (listed "reapproved 2024" by DIN Media); superseded D5470-12 and -06 | Scope: thermal impedance and an **apparent** thermal conductivity, for materials from liquids to hard solids; steady state, idealised 1-D heat flow. Prices seen about 74 euro (DIN Media), 86 US dollars (ASTM, 06 edition) | `[PARTIAL]` |
| **ASME V&V 20-2009 (R2021)**, *Standard for Verification and Validation in CFD and Heat Transfer* | 2009, reaffirmed 2021, 100 pp. | Quantifies accuracy by comparing simulation S and data D at a validation point, with uncertainty analysis. Contents: 1 Intro to validation methodology; 2 Code and solution verification; 3 Effect of input-parameter uncertainty; 4 Uncertainty of an experimental result; 5 Evaluation of validation uncertainty; 6 Interpretation of validation results; 7 Examples (code verification; fin-tube heat transfer); Appendices A (method of manufactured solutions), B (importance factors), C (additional topics). Contents page on asme.org (`.../21356.pdf`) | `[PARTIAL]` |

Formulas to check in the standards: ASME V&V 20 `(mem except the interval)`: `E = S - D`; `u_val^2 = u_num^2 + u_input^2 + u_D^2`; the model error lies in `E +- k u_val`, and Fig. 7-3-7 `(src)` shows `E +- 2 u_val` at 95 % probability for Gaussian errors; the V&V 20 summary papers (Eca, Dowding, Roache) confirm `E = S - D` as the interval centre; validation is "not pass/fail" in V&V 20-2009. ASTM D5470 `(mem)`: `theta = A (T_hot - T_cold) / Q`; `theta = R_c1 + R_c2 + BLT/k`; `k_app` from the slope of `theta` against BLT. IPC-2152 against IPC-2221 `(mem)`: the older chart relation `I = k dT^0.44 A^0.725` (A in mil2, k = 0.048 external, 0.024 internal) is the legacy method; IPC-2152 replaces the charts with data that include board thermal effects.

## Part 5: what is still open (as received)

| Item | Open point |
| :-- | :-- |
| Milton book | Read the 2D duality and HS chapters directly from the author's PDF (blocked there) |
| McCormick-Tamstorf primer | Confirm byline |
| Gerber spec | Download from the Downloads page; confirm the revision printed on the cover |
| JESD51-3, JESD51-7 | Not in the listing that could be read; look up by number |
| Lush, May 2004 | Not identified |
| Churchill 1977 (AIChE J. 23(1)) | Read the paper to confirm exponent n and the sign rule for assisting and opposing flows |
| Culham-Yovanovich 1998 | Read to confirm the three averaging schemes |
| Bar-Cohen-Rohsenow 1984 | Confirm `S_opt = 2.714 L / Ra_L^(1/4)` and `Nu_opt` |
| Elenbaas 1942 / Hollands | Confirm page range for Elenbaas; confirm which Hollands paper the program cites |
| Paid standards | Contents not available beyond tables of contents and scopes |

## Sources (pages retrieved, as listed in the compilation)
McCormick multigrid primer (grandmaster.colorado.edu/~stevem/mgprimer.pdf); Ucamco Gerber page and the 2024.05 announcement; Wikipedia, Gerber format; JEDEC JESD51 listing and JESD15-3 page; Electronics Cooling: May 1998 conduction in a PCB, Simons Feb 2002 (`?p=228`), the pixel conductivity map (`?p=4005`), the catalog of Calculation Corner articles; Python `ht` (Churchill-Chu, Hollands), pychemqt, BYU Incropera table; Churchill AIChE 2013 abstract, Churchill-Usagi abstracts; Hashin-Shtrikman 1962 abstract, arXiv:1808.02553, 1105.0954, cond-mat/0310065, cond-mat/0410073, Milton TOC (HEBIS) and publications summary; Bar-Cohen-Rohsenow listing, Elenbaas form in a Gdansk paper, Maya channel page, a plate-fin course note; Culham-Yovanovich citation (Springer) and the IAC-10 PCB conductivity paper; catalogues for Briggs et al., Patankar, Torquato, Carslaw-Jaeger, Incropera; IPC-2152 (GlobalSpec), IPC-4761 preview (ANSI), ASTM D5470-17 (ANSI), DIN Media D5470, ASME V&V 20 contents, the V&V 20 interpretation (Eca, Dowding, Roache).
