# Literature status for the copper mapping (phase 2)

An honest record of what was read, how, and what is still open.

## How the articles were obtained

The environment's network policy denies `www.electronics-cooling.com` (HTTP 403; `www.ucamco.com` too, `research/gerber-import/docs/literature.md`), so the assistant could not open them. **The maintainer pasted a converted text of the three Electronics Cooling articles** into the conversation. Limits of that text, as its own note says: the equations of article 1, the tables of articles 1 and 2 and all figures were images on the pages; the equations of article 1 were reconstructed by the converter from the surrounding text and the numbers (the numbers below were recomputed here, see the test `test_published_parallel_and_series_example`); tables and figures are known only through captions and the discussion. **These are notes in our own words with the facts and numbers we use, not a copy of the articles** (copyright stays with the publisher; read the originals through the links). Nothing here was checked against the pages themselves.

## 1. Sampson, R. L., "The Problem with Effective Thermal Conductivity", Electronics Cooling, 28 April 2017
https://www.electronics-cooling.com/2017/04/problem-effective-thermal-conductivity/ (the method is from his ASME IPACK2005-73013, 2005)

* **Claim.** The volume-weighted ("smeared") conductivity k_vw = (Vt kt + Vb kb) / V is right only when the traces run along the heat flow; across it the series value applies. Example: 10 % copper (391 W/m K), 90 % board (0.59 W/m K): k_vw about 40 W/m K, series value 0.65 W/m K (we reproduce 39.6 and 0.655 exactly).
* **Why a detailed model is not used:** 400 nodes per side for 0.25 mm traces on 100 mm, about 160 000 nodes per layer, about 1 000 000 for 6 layers.
* **The method, which is what we call the flow-based faces.** Bitmaps of every layer from the CAD files (about 200 ppi, 0.127 mm pixels; 0 = board, 1 = trace); every pixel is a micro-node with a micro-conductance; for each pair of neighbouring macro-nodes i and j, set temperature 1 on the centreline of i and 0 on the centreline of j, solve the micro-network between the two centrelines, take the heat flow, and G_ij = Q_ij / (T_i - T_j); repeat for every pair and every layer and use the conductances in a finite-difference model. **This is the same construction as our `dual_faces` (a local window from cell centre to cell centre); it is prior art from 2005, not our invention.** Our additions are the tests against the pixel-resolved solution on real boards, the 2D patterns, the comparison with simpler mappings, and the program-in-the-loop check.
* **Second procedure.** Fit one k_eff in an FEM model to reproduce the FDM result (minimise the maximum or the RMS difference), then use FEM for parametric studies. k_eff depends on the boundary conditions; k_vw does not, "an obvious weakness".
* **Numbers (post-mounted board, 6 layers, 100 x 125 mm, 4 corner posts, 1 W, traces do not reach the posts for electrical isolation):** without convection and radiation the correct maximum rise is 236 °C and k_vw = 38 W/m K gives 9 °C (error 227 °C); with convection and radiation 19 °C against 7 °C. The k_eff that reproduces the correct result is 1.5 W/m K (no convection) and 11 W/m K (with), against 38.
* **Relevance to us.** Confirms the claim that the volume-weighted fraction is biased and that conductances between neighbouring nodes computed from the bitmap are the remedy; the board-edge case (copper stopping before the posts) is a good future validation scenario. Our result "the fill fraction is 10 to 18 % too cool on real copper" is the same effect at a smaller scale (the article's errors are large because the boundary conditions make heat cross copper-free regions).

## 2. Guenin, B., "Strategies for the Thermal Modeling of Metal Traces on Printed Circuit Boards", Electronics Cooling, 20 March 2015
https://www.electronics-cooling.com/2015/03/strategies-for-the-thermal-modeling-of-metal-traces-on-printed-circuit-boards/

* **Scope.** Heat from the traces into the inner planes of a JEDEC 6-layer BGA test board (101 mm square, 1.54 mm, 35 µm planes, 35 or 70 µm traces, FR-4 0.25 W/m K, 27 mm cutout, 1 W injected into the trace cross-sections, h = 10 W/m²K both faces), FEA with explicit traces as the reference.
* **Findings.** Heat enters the dielectric under the traces, not uniformly; the trace temperature approaches the plane's after about 10 dielectric thicknesses, so the copper **near the package** matters most. Three smeared-plane methods: (1) copper fraction of the whole board: error above 40 % even at high copper and above 100 % at the lowest; (2) the fraction near the package where the traces are parallel: average error -9 %; (3) as (2) and the dielectric between trace layer and plane derated by trace width / pitch: average error +1 %.
* **Relevance.** Two points for the program, not yet tested: (a) the vertical link of a smeared copper layer through the dielectric should carry the *local copper overlap*, not the whole cell area (our layered model uses the whole cell); a test against the 3D solid on a trace over a plane would show it; (b) the 10-thickness length scale is an entrance length that sets the cell size at which a trace can be smeared.

## 3. Blackmore, B., "Creating PCB Thermal Conductivity Maps Using Image Processing", Electronics Cooling, 13 September 2010 (Mentor Graphics)
https://www.electronics-cooling.com/2010/09/creating-pcb-thermal-conductivity-maps-using-image-processing/ (validation in Blackmore, SEMI-THERM 2009, pp. 76-86)

* **Method.** Monotone image per layer (black = copper, white = dielectric), tiles, and per tile an orthotropic conductivity by pixel counting: k_z = area-weighted mean of the two conductivities (parallel); k_x = rows in parallel, each row a series chain of its pixels; k_y the same with columns. Tiles are sorted into %Cu bands.
* **This is our `lam 0` (`low`) bound** for k_x, k_y and the arithmetic fill fraction for k_z (checked by `test_blackmore_tile_formulas_are_the_lower_bound_and_the_arithmetic_mean`). In our single-layer windows `low` alone is 2.6 / 4.5 / 9.5 % too hot at 0.6 / 1.0 / 2.0 mm cells (README 4.4); the geometric mean of `low` and `up` (lambda 0.5) is 1.0 / 1.3 / 3.2 %.
* **His validation.** Against explicit simulation of single-layer boards with traces in typical orientations (10 x 10 tiles): average 3.3 %, maximum 15.3 %. Against an automotive board with 2-R component models (natural convection and radiation): average 5.7 %. Settings 75 tiles on the longest side and 256 %Cu bands. A design of experiments (resolution 1 to 75, bands 256 to 17) found that 25 to 50 tiles on the longest side (tiles of 6.8 to 13.6 mm) kept the case temperatures within 5 % for metallic layers; the number of bands mattered little there; vias need many bands (256) more than resolution (5 to 10).
* **Relevance.** His tiles (7 to 14 mm) are far coarser than ours (0.6 to 1 mm) because his heat sources are packages; we find the small heater (1 to 3 mm) is the hard case. Two ideas to try: %Cu banding of the mapping (a lookup from the fine mask), and treating vias with many bands.

## 4. Effective-medium formulas (search summaries and memory)

* Confirmed by a search summary: duality for 2D two-phase conductivity (Keller 1964; Dykhne 1970): the effective conductivity at swapped phases is related; at equal fractions and an isotropic self-dual microstructure it is sqrt(k1 k2); the effective conductivity lies between the Neumann and Dirichlet values; Hashin and Shtrikman gave optimal bounds for isotropic composites. Seen: arXiv:1105.0954, cond-mat/0410073, a 2017 note in Comptes Rendus Mécanique.
* **Not confirmed by any text read:** the explicit 2D Hashin-Shtrikman bounds and the 2D Bruggeman equation k² - (a - b)(2f - 1)k - ab = 0 used in `conduction.py`. They match the limits in `tests/test_conduction.py` (f = 0 and 1, equal phases, sqrt(ab) at f = 1/2, bounds ordering). Milton, *The Theory of Composites*, and Torquato, *Random Heterogeneous Materials*, are the places to check them.

## 5. Ucamco (the owner of the Gerber format)

The Ucamco format page, the specification and what they confirm for the reader are recorded once, in `research/gerber-import/docs/literature.md` ("Ucamco"); nothing in the copper mapping depends on them beyond the masks.

## 6. What would close the gaps

1. Read the three Electronics Cooling pages and Sampson's IPACK2005-73013 directly (the images: equations, tables).
2. Culham and Yovanovich, "Factors Effecting the Calculation of Effective Conductivity in Printed Circuit Boards", ITHERM 1998 (cited by Blackmore), and Lush, "Modeling Heat Conduction in Printed Circuit Boards Using Finite Element Analysis", Electronics Cooling, May 2004 (cited by Blackmore and Sampson).
3. Milton or Torquato for the 2D closed forms (the Ucamco specification and its test files belong to the reader: `research/gerber-import/docs/literature.md`).
4. Two tests suggested by the articles: copper stopping before the mounting posts (Sampson's case) against the program's FVM; the vertical link of a smeared layer against the 3D solid (Guenin).
