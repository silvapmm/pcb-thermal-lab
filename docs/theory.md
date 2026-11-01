# Theory: the mathematics and physics of every model

This document states **every equation the program solves**, how each model discretises it, which approximations are made and where the code does it, **as implemented**. What earlier versions did is in [`versions.md`](versions.md); every number that tests a statement below (errors, timings, case counts) is in [`validation.md`](validation.md); [`models.md`](models.md) is the guide to choosing a model.
Sources are cited by key; section 12 gives the reading status of each (**R** read, **S** seen as a summary, **M** from memory, **N** not obtained, **L** own derivation checked in the repository). A citation of a source not read is followed by its letter, for example [Peaceman1978] (S).
Units: SI inside the package (m, s, W, K, W/mK, W/m²K, J/m³K); temperatures in the interface are °C and `θ = T − T_amb` is the rise above the ambient. Millimetres and K·cm²/W appear only at the user boundary.

![The map of the document](images/fig_38_document_map.png)

*Figure 38 (`images/fig_38_document_map.png`): the board of the Problem is idealised in layers (section 1.2) for the FVM, FDM, Lumped and Analytic models; the 3D solid builds real slabs from the same board. Underneath, the pieces that the models share (metal blocks, vias (section 1.5), the heat transfer coefficients and their loop, parts, profiles) and the verification (section 11). Schematic, no numbers.*

**Where each part lives in the code, and where it is checked**

| Section | Module | Investigation (`research/`) | `models.md` | `validation.md` |
| :-- | :-- | :-- | :-- | :-- |
| 1 description, geometry, laminate, via | `model.py`, `geometry.py`, `laminate.py`, `viaconstriction.py` | `effective-conductivity`, `laminate-nodes`, `bare-spot-under-source`, `rotated-square-3d`, `outline`, `stackup`, `lumped-analytic-vias` | 1, 2.4.1, 9, 12 | 3, 12, 14, 18, 21, 22, 23 |
| 2 FVM (and the via on the grid) | `fvm.py`, `viawell.py` | `point-via-convergence`, `sor-with-via-couplings`, `young-omega-tiles`, `models-comparison` | 2.1 | 2, 5, 7, 18 |
| 3 FDM | `fdm.py` | `models-comparison`, `point-via-convergence` | 2.2 | 2, 18 |
| 4 3D solid | `solid3d.py` | `solid3d-verification` | 2.7 | 3, 16 |
| 5 Lumped | `lumped.py`, `viaconstriction.py` | `lumped-analytic-vias`, `lumped-via-groups`, `lumped-zones-adoption` | 2.3 | 3, 17, 18.1, 18.2, 21 |
| 6 Analytic | `analytic.py`, `viaconstriction.py` | `analytic-partial-copper`, `lumped-analytic-vias`, `young-omega-tiles` | 2.4 | 3, 4, 13, 18.1 |
| 7 metal blocks | `blocks.py`, `checks.py` (used by `fvm.py`, `fdm.py`, `solid3d.py`, `lumped.py`, `analytic.py`) | `block-and-fins`, `fin-channel`, `fin-channel-sources`, `effective-conductivity` | 2.6, 4b, 15 | 12 D, 15, 17, 22, 24 |
| 8 heat transfer coefficients | `convection.py`, `api.py` (fixed-point loop) | `horizontal-plate-h`, `plate-h-level`, `effective-conductivity` | 5, 18 | 8, 22 |
| 9 parts | `analysis.py` (`heater_stats`, `part_split`), `api.py` (power coefficient, top-path split) | `component-heatsink` | 6, 13 | 9, 19 |
| 10 power profiles | `profiles.py`, `profile_io.py` | | 4 | 7 |
| 11 verification | `tests/`, `research/` | `theory`, `models-comparison` | | all |

## 0. Symbols

Only the symbols used in more than one section are listed; the others are defined where they appear. One letter has one meaning in the whole document.

| Symbol | Meaning | Unit |
| :-- | :-- | :-- |
| `W, H_b, t_pcb` | board width, height and total thickness | m |
| `N_L` | number of copper layers (layer 1 = top) | – |
| `t_cu,l`, `slab_l` | copper thickness of layer `l`; thickness represented by its node (`t_pcb/N_L` in the simple stack-up) | m |
| `d`, `d_j` | thickness of a dielectric gap (gap `j` in the advanced stack-up) | m |
| `f` | copper fill: area fraction of a cell that is copper | – |
| `k_cu, k_ip, k_th` | conductivity of copper, of FR-4 in the plane and through the thickness (385, 0.9, 0.3 W/mK by default) | W/mK |
| `ρc` | volumetric heat capacity | J/m³K |
| `Δx, Δy` | cell size | m |
| `c`, `c_b` | cover of a cell by a polygon (zone, heatsink, block); by the board | – |
| `S` | sheet (in-plane) conductance of a layer: the conductance of a square | W/K |
| `g` | conductance per area between two adjacent layers, `k_th/d` | W/m²K |
| `G` | conductance between two nodes | W/K |
| `A_via`, `G_via` | copper cross-section of a via barrel; its conductance across one gap, `k_cu A_via/d` | m², W/K |
| `h`, `h_top`, `h_bottom`, `h_side`, `h_extra` | heat transfer coefficient of a face (convection plus radiation); top, bottom and edge faces; extra coefficient under a plain heatsink | W/m²K |
| `R''` | interface resistance per area (`t/k` of a paste or pad) | m²K/W |
| `P, Q, q` | power of a heater (W), source vector (W per node), power density (W/m²) | |
| `θ`, `T`, `T_amb` | temperature rise, temperature, ambient | K, °C |
| `K`, `C` | conductance matrix (W/K) and heat capacity vector (J/K) of a network | |
| `ϑ` | parameter of the theta method | – |
| `λ_l` | fin length of layer `l`, `√(S_l/g_loss)` | m |
| `Θ_part`, `Tj` | junction-to-pad resistance of a part (K/W) and junction temperature (°C) | |
| `r_v`, `r_t`, `a` | drill radius of a via; target radius `r_t = e^(−1/4) r_v` of its sink (also written `a`) | m |
| `R_K` | constriction (Krogh-cell) resistance of a via on a plane, eq. (1.8) | K/W |
| `I₀, I₁, K₀` | modified Bessel functions (always with their index) | |

## 1. The physical description

![The continuum problem](images/fig_20_continuum.png)

*Figure 20 (`images/fig_20_continuum.png`): the board (and any block) as a solid with the heater as a power over a footprint, the exchange with the air on every face, the edges and the equation.*

### 1.1 The continuum problem

Heat conduction in the board (and in any metal block) is

    ρc ∂T/∂t = ∇·(k ∇T) + q                                                      (1.1)

with `k` a tensor (diagonal: `k_ip, k_ip, k_th` for FR-4, `k_cu` for copper, `k` for a metal block). Every outer face exchanges heat with the air, `−k ∂T/∂n = h (T − T_amb)` with `h = h_conv + h_rad`; the board edges use `h_side` (or are insulated). The sources are the heaters: a power `P` spread **uniformly over a footprint** (a polygon on one layer). In steady state `∂T/∂t = 0`. Section 4 (the 3D solid) solves this problem directly; sections 2, 3, 5 and 6 solve its layered idealisation.

### 1.2 The layered idealisation (FVM, FDM, Lumped, Analytic)

![The layered idealisation](images/fig_01_layered_idealisation.png)

*Figure 1 (`images/fig_01_layered_idealisation.png`): a section of the board as the layered models see it. Each copper layer is one node (one temperature per plan position) with a sheet conductance; the dielectric gap between two layers is a one-dimensional resistance `d/k_th` (cut into laminate nodes where copper is absent, section 1.4); the outer layers exchange heat with the air through `h_top` and `h_bottom`.*

A PCB is a stack of very thin, highly conducting copper layers separated by poorly conducting dielectric. Across the 35 µm of copper the Biot number is `h t_cu / k_cu ≈ 10⁻⁷` and the conduction resistance `t_cu/k_cu ≈ 10⁻⁷ m²K/W` is four orders of magnitude below that of a dielectric gap (`d/k_th ≈ 5·10⁻⁴ m²K/W`), so each copper layer is **isothermal across its thickness**. The model therefore keeps **one temperature per layer and plan position**, `θ_l(x, y)`:

* **In-plane (lateral) conduction** of layer `l` is carried by copper and by the FR-4 in the same slab, in parallel:

      S_l(x,y) = f · k_cu · t_cu,l + k_ip · (slab_l − f · t_cu,l)                  [W/K]       (1.2)

  (`slab_l − f t_cu,l` is the FR-4 left in the slab of the layer). The heat flux per unit length is `−S ∇θ`.
* **Vertical conduction** between layers `l` and `l+1` acts through the dielectric gap, a one-dimensional resistance, `g = k_th / d` [W/m²K] (1.3). Where a via crosses the gap the barrel acts in parallel (a via connects **all** layers):

      G_via = k_cu · A_via / d        A_via = π[(D/2)² − (D/2 − t_plating)²] + (k_fill/k_cu) π (D/2 − t_plating)²      (1.4)

  with `D` the **drill** diameter; the fill is an open barrel (`k_fill = 0`), epoxy resin (0.3 W/mK), conductive paste (8) or electroplated copper, for which `A_via = π(D/2)²`. How the barrel couples to the plane temperatures is section 1.5.
* **Ambient exchange**: the top layer loses `h_top` and the bottom layer `h_bottom` per unit area (a one-layer board: `h_bottom` on its last laminate node, section 1.4); a plain heatsink adds `h_extra` over its polygon; an edge cell of a layer loses `h_side · (edge length) · slab` through the board edge.
* **Heat capacity per area** of a layer: `c_l = f ρc_cu t_cu,l + (slab_l − f t_cu,l) ρc_fr4`.

The layer equation (steady) is the **multilayer fin equation**

    ∇·(S_l ∇θ_l) − h_l θ_l − Σ_{n = l±1} g (θ_l − θ_n) = −q_l                       (1)

with `h_l` nonzero only on the outer layers and `q_l` the heater power density on its layer. Transient: add `c_l ∂θ_l/∂t` on the left.

**1.2.1 The advanced stack-up** (`Board.dielectrics`, one entry per gap). Gap `j`, between layers `j` and `j+1`, has its own `d_j`, `k_th,j`, `k_ip,j` and `ρc_j`, and `g_j = k_th,j / d_j`.
* The node of layer `l` stands for its copper plus half of each adjacent gap, `slab_l = t_cu,l + d_{l−1}/2 + d_l/2`, so the slabs add up to the board thickness; its laminate takes the thickness-weighted `k_ip` and `ρc` of the two half gaps.
* A gap of several sheets (`combine_sheets`) is one gap: `k_th = Σt_i / Σ(t_i/k_th,i)` (in series through it), `k_ip = Σ t_i k_ip,i / Σ t_i` (side by side along it).
* The simple stack-up (`dielectrics = None`) has `slab = t_pcb/N_L` and equal gaps. A heavier inner copper keeps every `d_j`, so the board grows by `Σ (t_cu,l' − t_cu,l)` (`models.md` 12).

![The advanced stack-up](images/fig_39_stackup_slabs.png)

*Figure 39 (`images/fig_39_stackup_slabs.png`): left, three copper layers and two gaps of different thickness (illustrative): the node of a layer represents its copper plus half of each adjacent gap, so the slabs add up to the board thickness; middle, the network the nodes make, with `g_j = k_th,j / d_j` per gap; right, a gap made of several sheets: in series through the gap, side by side along it (`combine_sheets`).*

**Energy balance**: integrating (1) over the board (all internal exchanges cancel) gives `Σ h_l ∫θ_l dA + ∫ edge losses = Σ P`: the heat leaving by every path equals the power injected. Every result reports this balance.

**Limits of the idealisation.** The 3D solid (section 4) measures their sum, the **model error**, on any board.
* A layer has no gradient through its thickness: its one temperature is the mean, and the face under a source is hotter by at most `q'' t / (2 k)`, negligible for copper (section 7.5 for thick plates).
* A gap is a 1D resistance, with no spreading inside it.
* The film acts on the outer node itself; the half copper layer in between, `t_cu/(2k)`, is 5·10⁻⁷ of `1/h` for 35 µm at 10 W/m²K and is neglected (over bare laminate, 6·10⁻⁴, section 1.4 adds it).
* The stack is **not** replaced by an averaged conductivity: any such mean (series, parallel, geometric, harmonic) can be 70 % to 300 % off, through spreading and the order of the layers [CulhamYovanovich1998].
**Where it is checked**: `validation.md` 3 (the 3D solid), 12 (advanced against simple stack-up), 14.1 (inner copper), 22.1 (published coupon cases, `research/effective-conductivity/`).

### 1.3 Sources and geometry

![A footprint on the grid](images/fig_21_coverage.png)

*Figure 21 (`images/fig_21_coverage.png`): a triangular footprint on a grid of cells; each cell is sampled on an 8 x 8 lattice and its coverage is the fraction of samples inside the polygon (computed here); the sum of the coverages equals the area of the triangle, so the power shared in proportion is exact.*

#### 1.3.1 Rasterisation

A footprint polygon is rasterised on the grid by **sub-sampling**: every cell is sampled on an `s × s` lattice (`s = 8` for heaters, in all the models that spread a heater over the grid, and for the board outline, 4 for zones, heatsinks and blocks), and the fraction of samples inside the polygon (even-odd ray test) is the **coverage** `c ∈ [0,1]` of the cell. A heater's source vector is

    Q_i = P c_i / Σ c                                                            (1.5)

so the power is **exact** whatever the grid (the weights sum to 1); if the footprint is smaller than a sample, all the power goes to the cell (or node) of the centroid. The copper fill of a cell is the **union of the zones of its layer taken at every sample**: each of the `4 × 4` samples gets the largest `fill` of the zones that contain it, and `f` is the mean over the samples (`geometry.zone_fill`). Overlapping zones are therefore not added, and two zones that meet inside a cell both keep their copper (a maximum per cell would keep only the larger half); a self-intersecting polygon is warned.

#### 1.3.2 A part across the board outline (FVM, FDM and 3D solid; `geometry.part_weights`)

A cell cut by the outline has only a fraction `c_b` of board in it, and a part may cover only some of that board. The part and the outline are tested on the *same* `8 × 8` samples (`geometry.BOARD_SAMPLES`): `n_b` samples of the cell are on the board, `n_pb` are in the part *and* on the board, and `c_b = n_b / 64` is the board cover the model uses. The weight of the cell is

    c_i = (n_pb / n_b) · c_b = n_pb / 64                                          (1.6)

and `Q_i = P c_i / Σ c` as in (1.5), so the power stays exact and the power density on the board part of the cut cell is that of the part in the share `n_pb / n_b` it really covers. Without an outline `c_i` is the plain coverage. Two simpler rules are wrong: the **product** `c_part · c_b` (right only when one of the two covers the whole cell) and an intersection counted on a lattice other than the one that gives `c_b`. The statistics of a result (mean and minimum under a heater or a zone, the ring of `ψJB`) are taken over the cells or nodes on the board only; a cell off the board reads the ambient.

![A cell cut by the outline and by the edge of a part](images/fig_34_part_cut_cell.png)

*Figure 34 (`images/fig_34_part_cut_cell.png`): a cell cut by the board outline (solid blue line) and by the edge of a part (dashed); left, the `8 × 8` samples coloured by what they lie in (orange: part only, blue: board only, green: both); right, the same samples counted as board only, from which the model takes the board cover `c_b`.*

![Weight and power density of a cut cell by three rules](images/fig_35_part_weight_rules.png)

*Figure 35 (`images/fig_35_part_weight_rules.png`): the weight of that cell by the product of the covers, the plain intersection and the intersection normalised to the board cover (left), and the power density each puts on the board part of the cell relative to the density of the part (right; the correct value is 1).*

*Limit.* The cut cell still conducts with its cover (a cell with half the board has half the conductance, whatever the part inside it), so a part over a cut edge reads a little hotter at fine cells than with the edge on the grid lines; treating the cut cell by its real shape is an item of the chapter "Planned" of `versions.md`. **Where it is checked**: `validation.md` 23 (`research/rotated-square-3d`, `research/outline`).

#### 1.3.3 A board with an outline in the Lumped and Analytic models

The FVM, FDM and 3D solid follow the outline with the cell cover `c_b`. The Lumped and Analytic models are rectangular (rings, cosine series), so they run on the rectangle of the same area (`Problem.equivalent_rectangle`): sides `sW` and `sH` with `s = √(A_outline/(W H_b))`, positions scaled `x → s x`, parts at their own size, and the field stretched back by `1/s`. This keeps the area (hence the total `h A`) and the aspect ratio. A part near a cut corner or in a narrow arm has less board to spread into than the rectangle gives, so it reads too cool (warned). No time simulation on an outline for these two models. **Where it is checked**: `validation.md` 13.

### 1.4 A one-layer board and the laminate nodes

![The laminate nodes](images/fig_44_laminate_nodes.png)

*Figure 44 (`images/fig_44_laminate_nodes.png`): left, a section across a copper edge: the gap between two copper nodes is cut into `n` sub-gaps (here `n = 4`) in the cells where copper is absent plus a margin, and is the single link `k_z A / d` elsewhere; middle, the plan of the cells that are cut; right, the rule for `n` and the one-layer board, whose laminate is a gap down to the bottom face. Illustrative proportions.*

**Why a gap is cut.** Where the copper next to a gap is absent, the laminate carries heat sideways inside the gap (under or beside a copper edge), which one link `g = k_th/d` cannot represent. With copper in every cell nothing is cut. A **one-layer board** has copper on the top face only: its laminate, `t_lam = slab − t_cu`, is a gap down to a bottom node that carries `h_bottom`.

**The rule (FVM and FDM, `laminate.py`).** A gap of thickness `d` between two copper nodes is cut into

    n = min(n_max, ⌈d / s_max⌉)      equal sub-gaps s_j = d / n,      s_max = 0.4 mm,  n_max = 4 (defaults)          (1.7)

(1, 2, 4, 4 sub-gaps for gaps of 0.4, 0.8, 1.6, 3.2 mm at the defaults; `s_max` (0.05 to 5 mm) and `n_max` (an integer, 1 to 16; 1 turns the cutting off) are options of the run, `SolverOptions.laminate_s_max_mm` and `laminate_n_max`, applied with `laminate.using()`. A larger `n_max` alone changes nothing when `s_max` already gives `n_max` sub-gaps: 8 sub-gaps of a 1.6 mm gap need `s_max ≤ 0.19 mm`, 16 need `s_max ≤ 0.09 mm`), **only in the cells where the copper fill of either adjacent layer is below 1, plus a margin of `⌈d/Δx⌉ + 1` cells** (Euclidean distance); every other cell keeps the single link `G = k_th A / d` of section 2. The rule is not applied on a board with a metal block (single links; a one-layer board keeps the two nodes of the next paragraph). In a cut cell:

* the copper nodes keep their copper and half of the adjacent sub-gap; the `n − 1` interior nodes hold `(s_j + s_{j+1})/2` of laminate each (lateral conductance `k_ip` and capacity `ρc` times that thickness); consecutive nodes are joined by `G = k_th A / s_j`. In the simple stack-up of three or more layers an inner node holds only `t_pcb/N_L − t_cu`, less than the two half gaps it would give up: its moves are scaled to what it holds, so no capacity or conductance is created;
* the laminate that takes the place of absent copper lengthens the path, `d → d + (1 − f_a) t_a/2 + (1 − f_b) t_b/2`, split between the first and last sub-gap (or whole in the single link of a bare cell outside the mask);
* the error against a resolved 3D solver falls as `1/n`.

**The face value of a part.** A part on an outer layer injects its heat at its node, at mid-thickness of the copper layer. Where the copper is absent, the half layer of laminate between the node and the face adds `Q t_cu/(2 k_th A)` to the peak (scaled by `min(1, (1 − f) Δx/(4 t_cu))` for a bare feature narrower than four copper thicknesses) and the bare share `(1 − f)` of it to the mean (`laminate.face_terms`).

**A one-layer board in the other models.**
* **Lumped**, and FVM/FDM with a **metal block**: two laminate nodes under the copper in every cell (`laminate.LAMINATE_NODES = 2`, gaps `t_lam/2`), one link per gap.
* **Analytic**: one node, with the laminate in series with the bottom film, `h_bottom → 1/(1/h_bottom + t_lam/k_th)` (`laminate.series_bottom_problem`).
* **3D solid**: four FR-4 slabs (section 4); a part reads the centre of its top slab.

For a uniform board heated all over every treatment is exact, `θ = P / (A (h_top + 1/(1/h_bottom + t_lam/k_th)))`; the partial-copper limits of the Lumped and Analytic are in `validation.md` 21.

**Solving the cut network.** The cycle `a(i) − b(i) − b(j) − [n links] − a(j) − a(i)` of the two copper nodes of neighbouring cells has length `n + 3`, odd for every even `n`, so the nodes cannot be two-coloured and the point red-black SOR does not apply; the SOR relaxes each plan column as a block (section 2.3).

**Where it is checked**: `validation.md` 21 and 21.2 (against an independent 3D solver, `research/laminate-nodes`, `research/bare-spot-under-source`, `research/gap-subdivision`; `tests/test_laminate.py`, `tests/test_laminate_rule.py`). **Sources**: [CulhamYovanovich1998]; the rule is derived and checked in the repository (L).

### 1.5 The via (all models)

![A via in section: the paths of the heat to the barrel](images/via_section_and_flux.png)

*Figure (`images/via_section_and_flux.png`): a via in section; the heat of each copper plane flows sideways to the barrel (the constriction) and down the barrel through the gaps.*

**The cause.** A via joins all the copper layers through its barrel, `G_via` per gap (1.4). A model carries one temperature per plane and region (a cell, a ring, a tile), the area mean; the barrel sees the copper at its wall, which is cooler, because the heat of the plane converges on the small disc of the barrel. The difference is the **constriction resistance**, in series with the barrel in every plane; leaving it out overstates the via effect. Where each model puts it:
* FVM and FDM: a footprint of cells with a mean-potential coupling and a Peaceman well (section 2.6);
* Lumped: a well in each ring (section 5.1);
* Analytic: a self-term of its tiles (section 6.1);
* 3D solid: a footprint tuned to the target radius of eq. (1.9) (section 4).

**The Krogh cell.** A sink disc of radius `a` at the centre of a circular cell of radius `R`, a uniform source over the annulus and an insulated rim (the Wigner-Seitz cell of a lattice of vias), on a sheet of conductance `S`. The mean temperature of the annulus above the temperature at the wall, per watt taken by the sink, is

    R_K(S, R, a) = (1/(2 π S)) [ ξ⁴ ln ξ/(ξ² − 1)² − ξ²/(2 (ξ² − 1)) − 1/4 ],        ξ = R/a      (1.8)

which tends to `(ln ξ − 3/4)/(2 π S)` for large `ξ`. The closed form is an own derivation (L) checked numerically against a finite-difference cell solver and an axisymmetric solve; it is the mathematics of the pseudo-steady-state well equation of reservoir engineering [Dietz1965] (S), and the Krogh cylinder [Krogh1919] (M) is the same cell.

![Constriction on a via barrel](images/via_constriction_krogh_cell.png)

*Figure (`images/via_constriction_krogh_cell.png`): left, the plan of one plane: the heat of a cell converges on the barrel; middle, the section: the constriction `R_K` of each plane is in series with the barrel of each gap; right, the profile of the temperature above the wall in the cell (closed form, `S = 1`): the area mean (what a ring or a tile carries) is above the wall by `R_K`.*

**The target radius.** The layered idealisation spreads the barrel uniformly over its disc, and the mean potential of a uniform disc is that of a circle of `e^(−1/4)` times its radius, so the sink radius used everywhere is

    a = r_t = e^(−1/4) r_v = 0.78 r_v                                                    (1.9)

(`viawell.TARGET_RATIO`). It is one value that is close on average against an axisymmetric 3D solve with the barrel drawn, not the radius of a real barrel (`research/point-via-convergence`, `validation.md` 18).

**Limits.** A lone via is the weak case of every reduced model: its effect depends on where it falls in the grid, ring or tile. A published numerical case that tests the closed form itself was not reproduced; the case of [Fish2017] (chapter 6) tests the microspreading of via cells and was reproduced. **Where it is checked**: `validation.md` 18 and 18.1; `research/lumped-analytic-vias`, `research/lumped-via-groups`, `research/young-omega-tiles`, `research/point-via-convergence`.

## 2. FVM: cell-centred finite volumes (the reference)

![The finite-volume cell](images/fig_02_fvm_cell.png)

*Figure 2 (`images/fig_02_fvm_cell.png`): left, the heat balance of one cell through its four faces; middle, one face as two half cells in series, which gives the harmonic mean of the two sheet conductances; right, the row of the matrix that the cell produces (a symmetric M-matrix).*

### 2.1 Unknowns and faces

**Unknown**: the mean temperature rise `θ_{l,i,j}` of the copper layer `l` in the cell `(i, j)` of size `Δx × Δy` (plan grid `nx × ny`, `Δx = W/nx`). The program integrates (1) over each cell and balances the heat through its faces, so the discrete energy balance is **exact in every cell**. The conductances (all in W/K):

* *Lateral*: between two neighbouring cells the heat crosses the two half cells in series, `R = Δx/(2 S₁ Δy) + Δx/(2 S₂ Δy)`, so with `S` of each cell

      G_x = (2 S₁ S₂ /(S₁ + S₂)) · Δy/Δx        G_y = (2 S₁ S₂ /(S₁ + S₂)) · Δx/Δy              (2.1)

  the **harmonic mean** of the two sheet conductances (a copper/FR-4 edge is a series, not an average); zero when both are zero [Patankar1980] (M).
* *Vertical*, between layers `l` and `l+1` in a cell: `G_z = k_th Δx Δy / d` (the dielectric alone; in the cells where copper is absent next to the gap the gap is cut into laminate nodes, section 1.4). The barrel of a via is **not** added here: it is a mean-potential coupling of a footprint of cells (section 2.6).
* *Ambient*: `G_amb = (h_top or h_bottom) Δx Δy` on the outer layers, plus `h_extra Δx Δy c_hs` under a plain heatsink (`c_hs` its coverage), plus `h_side Δ_edge · slab` on edge cells; under a metal block the board coefficient is multiplied by `1 − c` (section 7).
* *Outline* (`geometry.edge_length_on_board`, also used by the FDM and the 3D solid): `Δ_edge` is the length of the outline inside the cell. The outline is sampled at a tenth of a cell and every sample is moved a thousandth of a cell inwards, so a side lying on a grid line belongs to the cell on the board; length that falls in a cell off the board goes to the nearest cell on the board. `Σ Δ_edge` is then the perimeter wherever the polygon falls on the grid. Cells off the board are decoupled and pinned to the ambient by 1 W/K (`g_pin`): this keeps the matrix regular and is not a path to the air.

### 2.2 The system

    K θ = Q,        K = D − N                                                    (2.2)

with `N` the symmetric matrix of the non-negative face conductances and `D` its row sums plus the ambient conductances (the SOR uses the same split). The row sums of `K` are the ambient conductances, hence `Σ G_amb θ = Σ Q` (energy balance).
* Without vias `K` is a symmetric positive definite **M-matrix** (diagonally dominant, strictly where there is an ambient path, and irreducible): the solution exists, is unique and obeys the maximum principle (`θ ≥ 0`).
* The via couplings (2.6) add symmetric positive semidefinite terms with zero row sums, positive off-diagonal entries inside a footprint. Where the face conductances do not cancel them `K` is no longer an M-matrix: it stays symmetric positive definite (unique solution, energy balance), but the maximum principle is not proved (no temperature below the ambient has been seen).

### 2.3 The linear solvers (`fvm.Network.solve_steady`, `solve_sor`)

* **Direct**: sparse LU (SuperLU) with the symmetric minimum-degree ordering (`MMD_AT_PLUS_A`); the relative residual `‖Kθ − Q‖/‖Q‖` is reported.
* **Conjugate gradients** with a Jacobi (diagonal) preconditioner, tolerance 10⁻¹².
* **Red-black SOR**: `θ_new = (Σ G_m θ_m + Q)/D`, `θ ← θ + ω(θ_new − θ)`, stopped on the **residual** (10⁻⁹), not on the change of a sweep (a step criterion can stop far from the solution, `validation.md` 5).

**The relaxation factor** (`fvm.Network.sor_omega`). For a two-colourable network Young's relation gives the optimum

    ω_opt = 2/(1 + √(1 − ρ_J²))                                                  (2.3)

with `ρ_J` the spectral radius of the Jacobi matrix `D⁻¹N` [Saad2003] (Theorem 4.16, equation 4.47; the original is [Young1950] (N)). `ρ_J` is bounded from below by the Rayleigh quotient of the trial vector `D^{1/2}·1`, restricted to the nodes that have a link (the cells off an outline are decoupled and left out):

    ρ_J ≥ 1 − mᵀ K m / mᵀ D m,        ω = min(ω_opt(ρ_J), 1.999)                  (2.4)

one product with the full `K`, vias and footprints included. Being a lower bound, it gives an `ω` at or below the optimum, the safe side: below the optimum the sweeps grow slowly, above it steeply. With via blocks or laminate columns Young's relation does not hold (no two-colour ordering) and the factor is a safe-side heuristic, not a proved optimum. The proofs, the measurements and the comparison with the factor of a plate with fixed edges are in `research/young-omega-tiles` (README); the sweep counts are in `validation.md` 5 and 25.

![Sweeps against omega](images/sor_sweeps_against_omega.png)

*Figure (`images/sor_sweeps_against_omega.png`): sweeps to a residual of 1e-9 against `ω` on a 4-layer 40 × 40 board (an independent red-black SOR, `research/young-omega-tiles`): the factor of a plate with fixed edges (red) is on the slow flank, Young's optimum (green) at the minimum.*

**Block SOR** (`fvm.Network.solve_sor`, `_sor_columns`). Two couplings are not seen by the six-neighbour point update:
* *Vias*: the cells of a footprint are coupled by the dense via blocks of `K`. After the two colours each group of via blocks that `K` does not couple (greedy colouring [Saad2003]) takes the exact solution of its block, `θ_B += ω K_BB⁻¹ (Q_B − K_B θ)`.
* *Laminate columns* (section 1.4): every plan cell is a block of all its nodes, the blocks (merged where a via footprint joins them) are coloured and each colour is solved exactly.

The point and the block SOR of a symmetric positive definite matrix converge for every `0 < ω < 2` ([Saad2003] Theorem 4.10 states the point case; the block case is the same argument for a block splitting). The dense inverse of a block costs about `75 n²` bytes (`memory.sor_block_bytes`: the dense block, its inverse, LAPACK's copy and the sparse form the iterations keep; 5 000 unknowns take about 1.9 GB, not the 200 MB the old comment said). The sum of `75 n²` over **all** the blocks must be at most 25 % of the memory limit of section 2.7 (`memory.sor_block_fits`; the inverses of all the blocks stay alive for the iterations); otherwise the board is solved with the direct solver and the result says so.

### 2.4 Time: the theta method

![The theta method](images/fig_07_theta_method.png)

*Figure 7 (`images/fig_07_theta_method.png`): left, the factor by which one step multiplies a mode of rate `λ`, against `λΔt`, for the exact solution, implicit Euler, Crank-Nicolson and explicit Euler; right, the stages used for the step responses: the step grows geometrically (ratio 3) with four steps per stage, so one factorisation serves each stage. Textbook formulas, no program data.*

    C dθ/dt + K θ = Q(t),        C_i = c_l Δx Δy   (J/K)

The **theta method**

    (C/Δt + ϑK) θ^{n+1} = (C/Δt − (1 − ϑ)K) θ^n + Q^{n+1/2}                       (2.5)

with `ϑ = 1` (implicit Euler, first order, robust) or `ϑ = 1/2` (Crank-Nicolson, second order); both are unconditionally stable for the diffusion equation: each eigenmode of rate `λ` is multiplied by `(1 − (1−ϑ)λΔt)/(1 + ϑλΔt)`, of modulus below 1 for `ϑ ≥ 1/2` [Patankar1980] (M).
One LU factorisation is needed per distinct `Δt`, so the steps grow in stages of `m` equal steps whose sum is `t_end`:
* animation: ten stages, `Δt_j = Δt₀ 2^j`, `Δt₀ = t_end/(m(2¹⁰ − 1))`;
* **step responses**: 18 stages of `m = 4`, `Δt_j = Δt₀ r^j`, `r = 3`, `Δt₀ = t_end(r − 1)/(4(r^{18} − 1))`, `t_end = 10 τ` with `τ = ΣC/ΣG_amb` the uniform-board time constant (`ΣG_amb` without the 1 W/K pins).

The board mean of a transient weights every cell by its board area. The **step response** `Z_i(t)` is the rise of the hottest point of heater `i` per watt, and `R_th,i = Z_i(∞)` its steady value.

### 2.5 Accuracy

Second order in the cell size for smooth fields, first order at features (a via, a copper edge, a thin heater). The layered idealisation of section 1.2 is the model error that the 3D solid measures; the discretisation error is the change with the cell.

### 2.6 The via on the grid (FVM and FDM; `viawell.py`)

The physics of the via, the constriction and the target radius `r_t` are in section 1.5; this section is how the grid models carry them. The 3D solid uses its own footprint rule (section 4). **Footprint rule:** a via whose drill disc has no board under it (the board tested with the centre plus 6 rings of 24 samples, `geometry.discs_board_share`; the outline, or the box of a rectangular board) is left out of every model, not moved to the nearest board cell; the footprint of a via that is partly on the board is the part of the disc on the board.

**Why the barrel is spread.** A source in one cell of the five-point stencil is a point of the lattice whose potential is that of a hole of radius

    r_eq = exp(−(γ + 1.5 ln 2)) Δx = 0.1985 Δx                                  (2.6)

(γ Euler's constant; computed from the lattice Green function; Peaceman's radial argument [Peaceman1978] (S) gives `exp(−π/2) Δx = 0.2079 Δx`). Putting the barrel in the one cell that holds the via centre would be right only at `r_eq = r_t`, that is `Δx = 3.9 r_v`. On coarser cells the resistance `ln(r_eq/r_t)/(2π S)` is missing, and a series *well* supplies it. On finer cells the point is too constricted by `ln(r_t/r_eq)/(2π S)`, which grows as the cell shrinks and no series resistance can remove: the barrel has to be spread over several cells.

![The lattice sink and the Peaceman well](images/via_peaceman_well.png)

*Figure (`images/via_peaceman_well.png`): left, the potential of the nodes of a point sink on the lattice against the continuum holes (the nodes lie on a hole of radius 0.1985 Δx); right, the bookkeeping of resistances: a well is added when `r_eq > r_t`, and the barrel is spread when `r_eq < r_t`.*

**The construction.** Each via has:

* a **footprint**: weights `w_a` (sum 1) on the cells its disc covers (area of the disc in each cell, times the cover of the cell, restricted to the cells on the board and normalised); if the lattice effective radius of the footprint is smaller than `r_t`, the disc is enlarged (centre fixed) until it equals it. The effective radius of a distribution is

      ln(r_eff/Δx) = (π/2)(E_w − κ_a),      E_w = Σ_ab w_a w_b a(a − b)          (2.7)

  with `a(x)` the potential kernel of the stencil (`a(x) → (2/π) ln|x| + κ_a`, `κ_a = (2γ + 3 ln 2)/π = 1.0294`; a single cell gives `r_eq`);
* the **mean temperature of each plane over the footprint**, `T̄_l = Σ_a w_a T_{l,a}`;
* a **well** between `T̄_l` and the barrel node of plane `l`, `G_c = 2π S_l / ln(r_eff/r_t)` (none when `r_eff ≤ r_t`; `S_l` the sheet conductance per unit of board of the footprint cell with the largest weight), the barrel nodes joined by `G_via` per gap (1.4).

![The mean-potential coupling](images/via_mean_potential_coupling.png)

*Figure (`images/via_mean_potential_coupling.png`): the footprint, the mean temperature of each plane, the well and the barrel; after the Kron reduction only the couplings between the plane means remain.*

The barrel nodes are eliminated (Kron reduction [Kron2022] (S)), which leaves couplings `G_lm` between the plane means; the matrix gets `G_lm (e_l ⊗ w − e_m ⊗ w)(e_l ⊗ w − e_m ⊗ w)ᵀ` for each pair of planes: `K` stays symmetric, positive semidefinite with zero row sum from the via, and no unknown is added. The couplings are the same for the steady state and the transient, and the footprint cells are solved as dense blocks by the SOR (section 2.3). The FDM uses the same footprint and well on nodes. The 3D solid has no well (its cells carry the copper area of the barrel) and uses `viawell.tuned_footprint` (section 4): weights whose effective radius equals `r_t` exactly.

**Limits.** The lattice kernel has no image of a board edge, so a via within one cell of the edge is clipped (`checks.check_via_limits`); from a 2 mm cell the via is a fraction of a cell and the answer depends on where its centre falls in it (a warning).
**Where it is checked**: `validation.md` 2.1, 5, 7 and 18 (convergence with the cell, the copper-fill gain of the 3 × 3 board); `research/point-via-convergence`, `research/sor-with-via-couplings`, `research/models-comparison`; `tests/test_sor_omega.py`.

### 2.7 The memory guard (`memory.py`)

![The memory guard](images/fig_46_memory_guard.png)

*Figure 46 (`images/fig_46_memory_guard.png`): left, the chain from the cell to the verdict; right, the law of the estimate against the unknowns for the FVM (`t_eff` = 2 and 6), the FDM (4) and the 3D solid (6), with the coefficients of `memory.CONTINUOUS`, the safety factor included and the base left out, against 60 % of 16 GiB. Illustrative of the shape: the bytes were measured on one machine.*

A sparse direct factorisation needs memory that grows faster than the number of unknowns, and the number is set by the cell the user chooses. The guard estimates the peak memory of a solve **before anything is allocated** from the unknown count that the models already provide (`fvm.unknowns`, `fdm.unknowns`, `solid3d.unknowns`) and refuses a run above a limit.

**The law** (one per model, continuous in the thickness of the graph):

    peak = base + safety · factor · k₁ · t_eff^a · N · (N / N_ref)^(p − 1),      t = N / (n_x n_y),   t_eff = min(t, n_x n_y / t)        (2.8)

with `N` the unknowns, `N_ref = 500 000`, `t` the nodes per plan cell (the thickness of the graph that is factored) and `t_eff` its smaller side, because a board that is very thick in layers is also thin in plan (the smallest separator of the graph is then a horizontal plane, the nested-dissection argument of [George1973] (M), supported by two measured points only). The coefficients (`memory.CONTINUOUS`, bytes at `N_ref` and `t_eff` = 1) are, with the exponents of `N` and of `t_eff` and the safety factor: FVM `k₁` = 1469, `p` = 1.24, `a` = 0.79, safety 1.40; FDM 1228, 1.34, 1.03, 1.24; 3D solid 1063, 1.30, 0.98, 1.30. The safety factor is the largest measured/fitted ratio of the ladder rounded up, so the estimate does not fall below the measurement on the points that were measured. `base` is the resident size of the process when the check is made (not multiplied: it is measured); `factor` is 1 for a steady solve and 2.0 for a time simulation, an animation or a profile run (`memory.TRANSIENT_FACTOR`, `PROFILE_FACTOR`: the transient keeps one factor of the matrix plus the previous stage while the next is built, measured 1.9 after the program was changed to keep one LU factor instead of ten; the profile factor is not measured). The Lumped and the Analytic models are not estimated here (455 bytes per unknown for the Lumped; the Analytic has its own 4 800-unknown guard, section 6.1).

**Cheap lower bound first.** The exact unknown count of the layered models samples the copper of every plan cell (about 300 bytes per plan cell, tens of GB for a 0.5 m board at 0.05 mm), so the guard first takes a lower bound (one node per copper layer and plan cell; the 3D count is already exact and cheap). The estimate grows with `N` at fixed plan cells, so a bound above the limit refuses the run without the exact count, and the message says "at least". Only a bound that fits is counted exactly.

**Verdicts.** The limit is a fraction of the physical memory (read without a dependency: `sysconf`, `sysctl hw.memsize`, `/proc/meminfo`, `GlobalMemoryStatusEx`; the cgroup limit of a container lowers it; the variable `PCBTHERMAL_MEMORY_BYTES` replaces the reading). The default fraction is 0.60 (10 to 95 % allowed), a **machine preference** (`solver.memory_fraction` in Preferences, command line `--memory-fraction`), not a property of a project: it is not saved in the project file and an old file's value is ignored. The verdict is *refuse* above the limit, *slow* when the predicted solve time is above 30 s (a time law per class, measured on a shared machine, so a lower bound), otherwise *ok*. The 3D solid is also refused above an absolute ceiling of 2 million unknowns (it binds only from about 26 GB of memory). A refusal names the cell that fits (grown in steps of 10 %, rounded up to 0.1 mm, up to 50 mm). When the estimate is above the memory **available** now (`vm_stat`, `MemAvailable`, `ullAvailPhys`) the result is a warning, not a refusal: the same project would otherwise run or not depending on the moment. `solid3d.size_limit(n)` (offline studies) is a window: a model is accepted up to `n` unknowns whatever the estimate and refused above it.

**Limits.** The coefficients were fitted on 67 points (layer-major numbering) of one 16 GB machine; the extrapolation beyond the largest measured points (240 000 to 400 000 unknowns for the 3D solid) is trusted to about ±20 %; Windows and containers were not measured; the memory compressor of macOS can make a resident peak read 20 % low on a loaded machine. The program logs the estimate and the measured peak after each run, so another machine can check the law. The count of unknowns by an exact symbolic factorisation (the number of non-zeros of the factor), which would replace the fitted safety factor, is an item of the chapter "Planned" of `versions.md`.
**Where it is checked**: `validation.md` 26 (the memory ladder and the accuracy of the law); `research/memory-guard` (README 5, 9, 10, 14); `tests/test_memory.py`. **Sources**: [George1973] (M), [Davis2006] (M), [LiSuperLU2005] (N), none opened: they only motivate the form of the law, which is fitted and tested on the measurements.

## 3. FDM: node-centred finite differences (the comparison)

![FVM and FDM layouts](images/fig_03_fdm_nodes.png)

*Figure 3 (`images/fig_03_fdm_nodes.png`): the same board with the two layouts of the unknowns. FVM: the unknown is at the cell centre and the board edge is a cell face. FDM: the unknown is at the node, the nodes include the board edge, and each node owns a control volume that is full inside, half on an edge and a quarter at a corner.*

**Unknown**: the temperature at the **nodes** of a grid that includes the board edges (`(nx+1) × (ny+1)` per layer). Each node owns a **control volume** of `Δx_c × Δy_c`, with `Δx_c = Δx` inside and `Δx/2` at the edge nodes (a quarter at a corner), so a convective edge is treated by the standard half-cell balance (equivalent to a ghost node, second order). Written as the balance of a control volume the scheme is conservative too, and gives the same system `K θ = Q` and the same transient (2.5); what differs from the FVM is **where the data live**:

| | FVM (section 2) | FDM |
| :-- | :-- | :-- |
| unknown | mean of the cell, at its centre | value at the node, on a grid that includes the edges |
| sheet conductance `S` | of the cell, from the cover of the cell | **sampled at the nodes**: the coverage of the control volume around the node (`sampling="area"`, the default: the four surrounding cell coverages weighted by the shared area) or the point test (`"point"`) |
| lateral conductance | harmonic mean of the two `S` | mean of the two nodal values, arithmetic `(S₁ + S₂)/2` (default) or harmonic, times the face width over `Δ` (the face width is the control-volume side) |
| vertical | `k_th Δx Δy / d` | `k_th A_c / d`, `A_c` the control area (laminate nodes where copper is absent: section 1.4, on the nodes) |
| via | footprint of cells, mean-potential coupling | the same coupling, on a footprint of **nodes** (weights: area of the disc over the control volumes) |
| ambient and edge | cell areas and edge lengths | control-volume areas and lengths (the outline shifted by half a cell onto the control volumes) |
| source | coverage of the footprint over the cells | coverage shared among the four nodes of each cell (area) or one for each node inside (point), normalised to 1: power exact |

The transient machinery of the FVM is reused unchanged (`fvm.transient_from_network`), because the FDM network exposes the same `K, C, Q`. **Limits**: on coarse cells neither grid model converges monotonically: the answer moves with the way the heaters, the copper edges and the vias fall on the grid (a cell that does not divide the features moves it most), and the FDM, whose copper and source are sampled at the nodes, moves more than the FVM (`validation.md` 2.1). It is a comparison model that checks the FVM, not a second reference.
**Where it is checked**: `validation.md` 2 and 2.1 (the models against each other and against the grid), 18 (the via array); `research/models-comparison`.

## 4. 3D solid: finite volumes in three dimensions

![The 3D solid](images/fig_04_solid3d_slabs.png)

*Figure 4 (`images/fig_04_solid3d_slabs.png`): left, a section of the structured grid: one slab for each copper layer, four slabs for each laminate gap, a via as a rod of the barrel's copper area, a pad slab and metal slabs for a block; right, the conductance of two neighbouring cells as the harmonic mean of the half-cell resistances.*

`solid3d.py` drops the "one node per copper layer" idea. The plan grid is the FVM's; across the thickness the stack is cut into **real slabs** from the top face down:

* a copper slab of thickness `t_cu,l` for each layer, and `n_diel = 4` equal slabs of `d/4` in each dielectric gap (a one-layer board has no gap: its laminate is cut into four FR-4 slabs under the copper, so it spreads heat and the bottom face loses heat through it);
* for a block under (or over) the board a **pad slab** (the interface: thickness `R''·1 W/mK` and conductivity 1 W/mK, so its resistance per area is exactly `R''`) followed by `n = round(thickness/1 mm)` metal slabs (1 to 6).

Every cell of every slab has one unknown: `n_slabs × nx × ny`, counted before the model is built (`solid3d.unknowns`) and checked by the memory guard of section 2.7 (a memory estimate against the limit, and an absolute ceiling of 2 million unknowns; the old fixed limit of 250 000 is gone). The class `Solid` checks its own count in its constructor, so the guard also covers a direct use of the model.

**Cell materials** (volume averages on the structured grid, the tiled-conductivity method of PCB thermal models):

* copper slab with fill `f`: in-plane `k_x = f k_cu + (1 − f) k_ip`; through `k_z = f_eff k_cu + (1 − f_eff) k_th` with `f_eff = min(1, f + a_via)`;
* dielectric slab: `k_x = k_ip`, `k_z = a_via k_cu + (1 − a_via) k_th`;
* `a_via = Σ A_via w / (Δx Δy)`, the **real copper area of the barrel** (1.4) spread in parallel in every slab (the lateral effect of the thin barrel wall is neglected), clipped at 1 per cell (a via whose copper-equivalent area exceeds the cell loses the excess);
* the weights `w` come from `viawell.tuned_footprint`. Having no well, the 3D solid must reach the target radius `r_t` (1.9) exactly: `w` mixes the cell of the centre (share `1 − β`) with the area weights of the disc of radius `r_t` (share `β`), `β` chosen so that the lattice effective radius (2.7) equals `r_t`; the disc is enlarged when even `β = 1` falls short, and the cell of the centre is used alone when `r_t < r_eq` (2.6); the point fallback (a disc smaller than a cell) is the part of the disc on the board, and a via with no board under its disc is left out (2.6);
* block slabs: `k = k_metal · c`, pad slab `k = 1 · c`; cells with no material get `k = 10⁻⁹ W/mK` and a leak of `10⁻⁹ W/K` to the ambient to keep the matrix regular.

**Conductances** (each pair of neighbouring cells, harmonic mean of the half-cell resistances):

    lateral:   G = min(dz₁, dz₂) · Δy · 2 k₁ k₂ / ((k₁ + k₂) Δx)      (x; same for y with Δx ↔ Δy)
    vertical:  G = Δx Δy / (dz₁/(2 k_z1) + dz₂/(2 k_z2))
    face:      G = A / (1/h + dz/(2 k_z))                              (film in series with the half cell)
    edge:      G = 1 / (1/(h_side Δ dz) + (Δ_n/2)/(k_x Δ dz))                      (4.1)

with `Δ` the edge length of the cell face. A block hides the board face under it (factor `1 − c`) and loses heat on its exposed face, `h_exp = h_face·r_fin + h_extra` (section 7), and on the side walls of every block slab, `G = (h_face + h_extra) dz L_edge` (no fin ratio; `L_edge` the block outline inside the cell). The heater power goes to the copper slab of its layer with the weights of section 1.3. The system is solved directly; the result has the layout of the FVM (the copper slab of each layer, plus the block fields).

**What it measures**: the error of the layered idealisation on **your** board.
**Limits**: the barrel is a lumped area; copper is one slab thick; a block contact is perfect over the pad; the cost grows quickly with layers and cells (the fill-in grows with the width of the plan times the slab count, and the guard of section 2.7 limits the estimated memory, not the count); steady state only.
**Where it is checked**: `validation.md` 3 and 16 (against a finite-element solid and Yovanovich's table, convergence in slabs and cells, timings and memory); `research/solid3d-verification`. **Sources**: the flux-tube table of [Yovanovich2003], the grid convergence procedure of [Celik2008], [Roache] (M).

## 5. Lumped: thermal network by rings (LPTN)

![The rings of the Lumped model](images/fig_05_lumped_rings.png)

*Figure 5 (`images/fig_05_lumped_rings.png`): left, the rings of a rectangular footprint (the distance of every cell to the footprint, computed with a distance transform, cut at geometric edges; ring 0 is the footprint); middle, the chain of lateral resistances between the ring means with the vertical and ambient conductances of each ring; right, the superposition of the fields of two heaters. Rings narrower than a cell are merged (`RING_MIN_WIDTH`).*

`lumped.py` reduces the FVM network, per heater, to a few unknowns per layer, using the fact that the temperature field of a heater depends mostly on **distance from its footprint**. A board with an outline is solved on the rectangle of the same area (section 1.3.3).

**Unknowns.** One temperature per layer and ring, `N_L (N_ring + 1)` per heater (ring 0 is the footprint, found with a `4 × 4` sampling of the cells, and gets the whole power), plus one per ring for a metal block layer and, on a one-layer board, one per ring for each of its two laminate nodes (section 1.4). A footprint that holds a dense group of vias is two nodes per layer instead of one (section 5.2).

**Rings (geometry).** The distance `δ(x, y)` of every cell to the footprint is computed (Euclidean distance transform; 0 inside). Ring 0 is the footprint; ring `k = 1..N_ring` holds the cells with `δ ∈ (E_{k−1}, E_k]`, with geometric edges

    E_k = E₁ (E_max/E₁)^{(k−1)/(N_ring−1)},    E₁ = min(max(1.5 min(Δx,Δy), 0.04 E_max), 0.5 E_max),    E_max = max δ        (5.1)

Edges closer than one cell, `max(Δx, Δy)`, are merged (`lumped.ring_edges`: a thinner ring would get a contour length that is too short and a resistance too high); rings with no cell are dropped. Any footprint shape and the real outline are followed. For layer `l` and ring `k` the real cells are aggregated: `S_{l,k}` mean sheet conductance, the sums of `G_amb` by path, of `G_z` (dielectric and vias) and of `C`, the ring **thickness** `Δ_k` (distance span) and its **contour length** `L_k = (N_k Δx Δy)/Δ_k` (`N_k` cells).

**Lateral resistances** between the area-mean temperatures of consecutive rings (the heat crosses the offset contours):

    R_{k,k+1} = Δ_k/(2 S_k L_k) + Δ_{k+1}/(2 S_{k+1} L_{k+1})           (k ≥ 1)                (5.2)

**Inside the footprint** the resistance from its mean temperature to its boundary comes from the logarithmic potential of a uniformly heated region on a sheet: the temperature at a point is `θ = −(Q/(2π S)) φ + const` with `φ_i = mean ln|r_i − r_j|` over the footprint cells `j` (the self term of a square cell is `ln(0.447 √(Δx Δy))`, 0.447 being the geometric mean distance of a square to itself in units of its side). Up to 900 footprint cells the sums run over every cell; above that the source cells are aggregated in `k × k` blocks (weighted centroid, weight sum, self term `ln(0.447 √(area of the block's cells))`, `k` the smallest integer that leaves at most 900 blocks), and the boundary cells and the cells of the nine lowest blocks are read at their own positions against the blocks (distance never below the self term of a block), so that `φ_boundary` and `φ_min` are not taken half a block inside. Against the sum over every cell this is within 0.1 % on `φ_boundary − φ_mean` and 0.15 % on `φ_mean − φ_min` (squares, a disc, an L, a square ring, a footprint cut by the board edge; `tests/test_lumped_footprint.py`). Then

    R_{0,1} = f_R · (φ_boundary − φ_mean)/(2π S₀) + Δ₁/(2 S₁ L₁)                              (5.3)

which is `1/(8π S)` for a disc. When the layer also loses heat vertically under the footprint (loss conductance `g_eff` per area, fin length `λ = √(S/g_eff)` not much larger than the footprint radius `r_f`), the disc solution `θ(r) = q/g_eff + A₀ I₀(r/λ)` (`A₀` a constant) gives the **correction factors** (`x = r_f/λ`; `I₀, I₁` modified Bessel functions)

    f_R = 4 (I₀(x) − 2 I₁(x)/x) / (x I₁(x))          f_P = 4 (2/x² − 1/(x I₁(x)))        (both → 1 as x → 0)          (5.4)

`g_eff` is taken from the solution itself (heat leaving the footprint of the layer towards its neighbours and the ambient, divided by its rise and by the footprint area) and the network is re-solved, three passes. **Vertical and ambient**: `G_z` between layers and the ambient conductances of every ring are added as in the FVM, so vias, heatsinks and edges enter by their real positions.

**Solution.** Each heater gives a small dense system `K_h θ = Q_h` (the unknowns above, `Q` at ring 0 of the heater's layer), solved exactly. Because the problem is linear the board is the **superposition** of the heaters: the field of heater `h` at a cell is its ring profile interpolated at the distance `δ_h` of the cell (constant beyond the ends), and the field is the sum over the heaters, so the mutual heating is the other heater's radial profile read at the distance of the footprint. The **peak** inside a footprint is

    θ_peak = θ_ring0 + Q_lat f_P (φ_mean − φ_min)/(2π S₀)                                   (5.5)

(`Q_lat` the lateral outflow of ring 0, `φ_min` the hottest point), plus the rises of the other heaters at its centroid. **Transient**: `C dθ/dt + K_h θ = Q` per heater network with the ring capacities, solved with the theta method of section 2.4; the profile and animation tools superpose the heaters. **Metal block**: in steady state the block layer of the FVM network (sheet conductance `k t` per cell, the contact, exposed and wall conductances of section 7) is summed over the rings like the board layers, section 7.3; no time simulation with a block.

### 5.1 The via in the rings (`viaconstriction.py`)

The constriction `R_K` and the sink radius `a` are in section 1.5. In a ring that holds `n` vias the plane `l` reaches the barrel through a **well** `R_w(l)` in series with the barrel; for a via that belongs to a group of `N_g` vias

    R_w(l) = R_K(S_l, R_c, a) + N_g R_K(S_l, R_macro, r_cl)       (second term only if N_g > 1 and R_macro > r_cl)       (5.6)

* `R_c = min( √(A_ring/(π n)), d_nn/√π )`: the radius of the cell of one via (the ring area shared among its vias, or the nearest-neighbour distance `d_nn`, whichever is smaller: a lone via in a wide ring does not get the whole ring);
* `r_cl = √N_g R_c`: the disc that the group covers;
* `R_macro`: the radius of the disc of the rings that the group touches, **capped at `0.75 λ_l`** (the cluster draws heat from within a few fin lengths only);
* the **groups** are found by single linkage at twice the larger nearest-neighbour distance of the two vias.

The network of a ring becomes a star: the sheet node of each plane, its well, the barrel node of the plane, the barrel conductance between adjacent barrel nodes. The barrel nodes are eliminated by Schur complement (Kron reduction [Kron2022] (S), `viawell.kron_barrel`), which leaves **couplings between all the planes** of the ring, adjacent or not; the matrix of each heater keeps its size.

![The well in the rings](images/via_constriction_lumped_well.png)

*Figure (`images/via_constriction_lumped_well.png`): left, a lone via outside the footprint sits in one ring, and the ring carries its mean temperature at one radius: the angular gradient of the real field is lost; right, the network: one well `R_w` per plane in series with the barrel.*

**Limits.** The rings have no angular resolution: the effect of a lone via depends on its distance and on the number of rings. For a part over a dense group of vias the footprint is cut into two zones (section 5.2), which removes most of the error of the one-node footprint; what is left, and what the zones do not touch, is: an array that straddles the footprint edge or lies just outside it (the part is read too cool, up to 16 % of its rise with the zones; with the one-node footprint up to 3.2 times the via effect, about 11 K, a quarter of the rise), and an array off the centre or under an elongated footprint (1 to 5 % and 2 to 4 % of the rise with the zones; `checks.lumped_via_cool_warning` warns). A lone via, a row and scattered vias outside every footprint keep the ring network's error (a lone via from 22 % too small to 65 % too large). A copper edge across the footprint, a board corner and a thin heater are the cases where the ring network fails (the input checks warn); round boards and a two-layer board have the via effect 16 to 21 % too small, so the part reads hotter (the safe side); a one-layer board with partial copper has only the two laminate nodes.
**Where it is checked**: `validation.md` 3 (against the 3D solid), 17 (the metal block), 18.1 (vias), 21 (rings and one-layer boards); `research/lumped-analytic-vias`, `research/lumped-via-groups`, `research/models-comparison`. **Sources**: [CarslawJaeger] (M) (logarithmic potential, `I₀`, `I₁`).

### 5.2 The footprint in two zones (`lumped.py`, `viaconstriction.py`)

![A footprint cut into the rest A and the core C](images/lumped_zones_footprint.png)

*Figure (`images/lumped_zones_footprint.png`): a part over a group of vias. The cells within `0.7071 d_nn` of the vias form the core C, the rest of the footprint is A; the vias reach the planes through the wells of section 5.1 at node C, and the heat of A reaches the barrels through the lateral link A-C.*

With one node for the whole footprint the heat generated far from the vias is assumed to reach them at the mean temperature of the footprint, and a part much larger than its via array reads too cool (the one-node footprint is up to 109 % off in the via effect on dense arrays under a large footprint). When the footprint holds a **group of two or more vias** (single linkage, section 5.1) the cells within `CORE_R d_nn = 0.7071 d_nn` of the vias of the group (`d_nn` the mean nearest-neighbour distance of those vias; `0.7071 = 1/√2` covers a square lattice) are the **core** C, and the rest of the footprint is **A**. A and C are two nodes per layer (`lumped._zone_network`); the rings outside are the program's. The sums of sheet conductance, films, dielectric conductance and capacity of each node are sums over its cells, the barrels of the vias in C reach the planes through the micro wells of eq. (5.6) at node C (the cluster-well term is kept in every node, with its cap of `0.75 λ_l`), and the source of the layer is divided between the two nodes in proportion to the covered area, `Q_A = (1 − f_C) Q`, `Q_C = f_C Q` (`f_C` the coverage-weighted share of the footprint in the core).

![The network with two zones](images/lumped_zones_network.png)

*Figure (`images/lumped_zones_network.png`): the network of two layers with the footprint in two zones: each layer has A, C and the rings; the vertical links (dielectric, barrels with their wells) and the lateral links A-C and A to ring 1.*

**The link between A and C.** For a uniform source over A and a uniform sink over C of equal strength `Q` on a lossless sheet of conductance `S`,

    T_A − T_C = Q (2 φ_AC − φ_AA − φ_CC)/(2 π S),        φ_XY = mean of ln|x − y| over x in X, y in Y        (5.7)

taken on the real shapes of A and C with the potential sums of section 5 (zones of more than 700 cells are aggregated in blocks, `_block_points`, `_mutual_potentials`). For concentric discs this is the Krogh resistance of the annulus plus `1/(8π S)` of the core, so the convergence of the heat on the group is not counted a second time by the cluster well that stays at C (confirmed by the run: leaving the cluster well out of the zone nodes or keeping it differs by 0.2 point of mean error; with several groups under one footprint keeping it is better by 3 to 6 points of the effect, which is why it is kept).

**The link between A and ring 1** is the mean-to-outer-wall resistance of the annulus of inner radius `r_c` and outer radius `a`, with a uniform source and the inner side insulated (`viaconstriction.annulus_out_resistance`), plus the half ring of the program (the Bessel factor of eq. 5.4 is not applied to this link):

    R_{A,1} = [ (I₁ − I₂)/((a² − r_c²)/2) ] / (2 S π (a² − r_c²)),
    I₁ = a² (a² − r_c²)/4 − (a⁴ − r_c⁴)/8,     I₂ = r_c² [ a²/4 − (r_c²/2) ln(a/r_c) − r_c²/4 ]        (5.8)

with `r_c` and `a` the radii of the discs of the same area as the core and as the footprint; it tends to `1/(8π S)` as `r_c → 0`, the one-node value of eq. (5.3) for a disc.

**The peak.** The hottest point of the source layer is the largest of three candidates (`lumped._ZonePeak`): (i) the hottest point of A, the field of a uniform generation `Q_in + Q_out` over A with a sink `Q_in` on C and `Q_out` far away, with the `K₀(d/λ)` kernel of the layer; (ii) the core mean plus the **rim of the Krogh cell** of one via above the cell mean (`viaconstriction.rim_minus_mean`), per watt taken by the via,

    ΔT_rim = [ b² ln b/(b² − 1) − 1/2 ]/(2π S) − R_K(S, R_c, a),      b = R_c/a        (5.9)

(the micro peak: the temperature at the rim of the cell exceeds its area mean); (iii) when the core is hotter than A, the core mean plus the rim plus the **bump** of the core above its mean (the footprint formula of eq. 5.5 applied to C). The bump is essential: without it the largest error of the via effect over the 36 family boards went from 9.1 to 20.1 %. The one-node footprint (the fallback) carries no micro peak, so that it is the program's code unchanged.

**The decision: zones or one node.** There is no core, or the footprint is one node, when the core covers more than **92 %** of the footprint counted on the Lumped grid **and** on a 0.1 mm grid (`_fine_core_share`; `will_be_zoned` counts on the fine grid alone, before the grid exists): a core of 94 to 99 % of the footprint leaves a handful of cells for A, and the zone network then reads the part up to 14 % hot, so the threshold protects; the fine count does not jump with the raster (without it the inverted-T example board stepped 2.9 K between 1.0 and 0.5 mm). A board with an outline is decided on the rectangle of the same area, the board the model solves (section 1.3.3). The nine vias of the example board are a core of 98 to 100 % of the footprint of U1, so U1 stays one node and the board is unchanged.

![The raster against the core](images/lumped_zones_raster_against_core.png)

*Figure (`images/lumped_zones_raster_against_core.png`): the core of a via array on the Lumped raster at 1.0 and 0.5 mm: a core a few cells across is badly drawn.*

**The raster.** The core must be a handful of cells across, so a board that has a part that will be zoned runs the Lumped model on a **0.5 mm cell** (`lumped.cell_for`; the other boards keep the 0.5 to 1.0 mm clip of the options). The cell is one per board: the other parts of that board move by the raster too. The Analytic keeps its clip.

**Capacities and time.** The capacity of each zone node is the sum of the capacities of its cells (the sum over the nodes of the footprint equals the footprint capacity of the one-node network), and the transient is `C dθ/dt + K θ = s P` with `s` the source vector (the share of A and C by the covered area); the peak is evaluated at every step with the same operator as in steady state. The cells of the core are painted with the temperature of node C in the temperature map; outside the footprint the radial profile is read from A (`lumped._radial`).

![The profile runner with zones](images/lumped_zones_profile_runner.png)

*Figure (`images/lumped_zones_profile_runner.png`): the square-wave run: the wave, the source split between A and C, the zone network and the peak operator; below, what an adapter that puts the whole power on A does, and what the split changes.*

**The profile runner.** The runner of the power profiles (`_LumpedAdapter.advance`) and the step responses used by the decision average-or-resolve (`lumped.step_responses`) apply the power through the same source vector and read the same zone peak; with the whole power put on A the part would read up to 25 % of its rise too hot (measured on 93 boards).

**Limits.** The core radius `0.7071 d_nn`, the 92 % and the 700-point block aggregation are assumed constants. The model reads the part too cool by up to 16 % of its rise for an array across the edge of the footprint and 1 to 5 % for an off-centre cluster and 2 to 4 % for an elongated footprint (steady state and profile), and up to 6.1 % of the rise too cool when the vias conduct nothing (the cut of the footprint lowers the peak by itself); the one board of the 62 simple boards on which the zones are worse than the one-node footprint by more than 5 points of the via effect reads the part 7 % too hot, on the safe side (the 7 x 7 array at 0.6 mm pitch with a 0.2 mm drill, copper-filled, under 8 mm), and in the square-wave run three of the 93 boards read the peak 6 to 13 % of the rise too hot, partly the same steady offset and partly the overshoot of the peak term at the switching edge. Several groups under one footprint are treated as one core (their union). Irregular groups, a guard ring of vias, a block under the part and an L-shaped footprint were not tested; a footprint whose core covers more than 92 % of it, or that holds no group, is the one-node network. Warnings in `checks.py` (`lumped_via_cool_warning` with the bound of the zoned model, a raster coarser than a tenth of the core, a footprint kept as one node).
**Where it is checked**: `validation.md` 18.2; `tests/test_lumped_zones.py`; `research/lumped-zones-adoption` (README 4, 8, 9 and 10), `research/lumped-via-groups`. **Sources**: the closed forms (5.7) to (5.9) are own derivations checked numerically against the FVM at 0.25 mm and a fine-grid layered solver; Krogh's cell was not opened as a source (section 12); the published case of Shen and others (2020) was read in equations (2) to (5) and its CFD number was not reproduced (`validation.md` 18.2).

## 6. Analytic: multilayer Fourier series

![The Analytic series](images/fig_06_analytic_modes.png)

*Figure 6 (`images/fig_06_analytic_modes.png`): left, four of the cosine modes of a board with insulated edges; middle, the partial sums of the series for a strip source (the shape only: the curves are illustrative); right, the tiles on which the Green-function correction acts: only the tiles with a via or a heatsink.*

**Unknowns.** The amplitudes `a_{l,mn}` of the cosine series of each layer, `N_L` per mode, 300 modes per direction by default; for the corrections, the temperatures of the tiles with a local element.

**Equations.** On a **uniform** board with insulated edges (1) is solved exactly. Expanding each layer in cosines, `θ_l(x, y) = Σ_{m,n ≥ 0} a_{l,mn} cos(mπx/W) cos(nπy/H_b)`, the Laplacian becomes `−κ²_mn`, `κ²_mn = (mπ/W)² + (nπ/H_b)²`, and the layers decouple by mode into a tridiagonal `N_L × N_L` system

    A_mn a_mn = q_mn            A_mn = diag(S_l κ²_mn + h_l) + g · Λ                    (6.1)

where `g · Λ` is the weighted graph Laplacian of the layer chain, with the conductance per area `g_j` of each gap on its link (`(g·Λ)_ll = g_{l−1} + g_l` over the gaps that exist, `(g·Λ)_{l,l+1} = −g_l`; one `g` for every gap in the simple stack-up) and `h_l` the surface coefficient of the layer (zero for inner layers; for a one-layer board `h_bottom` is in series with the laminate, section 1.4). The **mode (0,0)** is the uniform-board limit `P/(h_tot W H_b)`: it integrates each layer exactly, so the heat out of the faces is read from it.
**Source**: the heater is replaced by the axis-aligned rectangle `[x₁,x₂] × [y₁,y₂]` with the same area and centroid (aspect ratio of the bounding box); its cosine coefficients are

    q_mn = P · ε_m ε_n · I_x(m) I_y(n) / (W H_b · area),   ε₀ = 1, ε_{m>0} = 2,   I_x(0) = x₂ − x₁,   I_x(m) = (sin(κ x₂) − sin(κ x₁))/κ,  κ = mπ/W       (6.2)

and `I_y` likewise. The field is `θ_l = cos_y · a_l^T · cos_x^T` evaluated at the cell centres by two matrix products.

**Copper is not uniform.** Each layer gets an **effective copper fill** averaged with the *influence* of the heaters, `f_eff,l = Σ w f_l / Σ w` with `w(x,y) = Σ_i P_i K₀(r_i/λ_l)` (`K₀`, the modified Bessel function of the second kind of order zero, is the Green function of the fin equation) and the **layer's own fin length** `λ_l = √(S_l/(h_surface + n_neighbours g))` for a layer that carries a heater (about 5 mm; the 34 mm of the whole stack would let distant copper count too much). A warning is raised when the fill varies strongly (weighted spread above 0.25).

**Vias and heatsinks are local** and are added back by a Green-function (Woodbury) correction on tiles of size `min(max(λ/4, 2.5 mm), 5 mm)`, `λ = √(Σ_l S_l / h_tot)` the fin length of the whole stack (`h_tot` the sum of the face coefficients). A tile with a via has `G_via` between adjacent layers (1.4); a tile under a heatsink has `g_hs = h_extra Δx Δy c` to the ambient. With `y₀` the tile means of the uniform solution and `G_mod` the modal response of the uniform board between tiles (first 64 modes), the tile temperatures `y` and the heat `φ_loc` that the local elements extract or move satisfy

    (I + G_mod C_loc) y = y₀,        φ_loc = −C_loc y,        a_mn ← a_mn + A_mn⁻¹ (projection of φ_loc)       (6.3)

the exact solution of the board with the local conductances for the tile-lumped model (a dense system of `N_tiles · N_L` unknowns, small), the static condensation of finite-element codes [MFEMStaticCond] (S). `C_loc` is the local conductance matrix of the tiles (via conductances, heatsink conductances and, with a block, the Schur complement of section 7.3).

**Transient.** Each mode obeys `C a' + A_mn a = q(t)` with `C = diag(c_l)`. With `C^{-1/2} A_mn C^{-1/2} = V diag(μ_p) Vᵀ` and `β = Vᵀ C^{1/2} a` the eigenmodes decouple, `β' = −μ β + s` with `s = Vᵀ C^{-1/2} q`, and a constant power over a step has the **exact propagator** `β⁺ = e^{−μΔt} β + (1 − e^{−μΔt}) s/μ`. The local corrections are not used in time: the vias (or the heatsink) are smeared over the board and their conductance is **scaled per heater**, by bisection, until the steady maximum equals that of the corrected model (one scale for the whole board distorts a distant heater). No time simulation with a block or on an outline.

**Limits.** Copper that is not uniform near a heater (a small pad, an edge across the footprint) is represented by the influence-weighted fill, an average; insulated edges are assumed (the default edge coefficient of 10 W/m²K makes the model slightly warm on a uniform board, which is the whole of its difference from the FVM there); the heater is a rectangle of the same area. The checks warn. With partial copper the Analytic model is the better of the two reduced models.
**Where it is checked**: `validation.md` 3 (the 3D solid), 4 (why the FVM and the Analytic model agree on uniform boards: the same layered model; the Analytic is its exact solution on a uniform sheet), 13 (outline), 7 (time); `research/analytic-partial-copper`. **Sources**: [CarslawJaeger] (M), [IncroperaDeWitt] (M), [MFEMStaticCond] (S).

### 6.1 The via in the tiles (`viaconstriction.py`)

The Analytic model carries the mean temperature of a tile of its Green-function mosaic, so the correction (6.3) must read the via at its wall (section 1.5). The tile rules:

* the **tile** is `t = min(1 mm, 0.75 median d_nn)`, at least 0.25 mm and never above the program tile (2.5 to 5 mm without vias), so that the sink has the scale of the barrel; it is enlarged until the active tiles (those with a via, a heatsink or a block) times the layers are at most 4800 unknowns (the dense system is then of the order of a gigabyte; the same guard coarsens the tile when the estimate of active tiles passes 1200);
* a via that is **alone at the scale of a tile** (`d_nn ≥ 0.7 t`, outside a guard of `0.5 t` around a footprint) is spread bilinearly over the four tiles around it, which keeps its first moment, and not put in the one tile that holds its centre;
* the diagonal of `G_mod` gets a **self-term** that makes the tile read the temperature at the wall: for `n ≤ 1` vias per tile `D_self = [ln(R_blk/a) − 1/4]/(2 π S n)`, `R_blk = R_tile/√n`; for `n > 1`, `D_self = ln(R_tile/r_cl)/(2 π S) + R_K(S, R_c, a)/n`; here `R_tile = t/√π`, `R_c = min(R_tile/√n, d_nn/√π)` and `r_cl = √n R_c` (the rules of eq. 5.6 with the tile for the ring and the vias of the tile for the group), `n` the (weighted) number of vias in the tile.

![Tiles over a via array](images/via_constriction_analytic_tiles.png)

*Figure (`images/via_constriction_analytic_tiles.png`): left, the tiles of the program (2.5 to 5 mm) over a 5 x 5 array of 0.3 mm vias at 1.2 mm pitch under a 6 mm source: one tile holds many vias and the tile mean is read; middle, the tiles of 1 mm with the self-term: the via is read at its wall; right, a tile that straddles a copper or source edge averages two different temperatures, which is why the tile must be small.*

**Limits.** A lone via is the weak case (its effect depends on the distance to the heater and the tile); the tile is limited by the unknowns guard (the Analytic keeps the clip of the cell to 0.5 to 1 mm, so 2 mm equals 1 mm; the Lumped model uses 0.5 mm when a part will be zoned, section 5.2, and the Analytic has no zones). The numbers are in `validation.md` 18.1; the formulas are derivations checked numerically against the FVM and an axisymmetric solve (`research/lumped-analytic-vias`, `research/lumped-via-groups`, `research/young-omega-tiles`).

## 7. Metal blocks (FVM, FDM, 3D solid; Lumped and Analytic in steady state)

![The metal block](images/fig_11_metal_block.png)

*Figure 11 (`images/fig_11_metal_block.png`): left, a block on the board through an interface sheet (the heat enters the block where it overlaps copper; over bare laminate it must also cross the FR-4); middle, a plate fin whose heat to the air falls along the fin, `η = tanh(mL)/(mL)`; right, the two equivalents of the Lumped and Analytic models, which keep the block's lateral conduction.*

### 7.1 The plate in the layered models

A heatsink with `thickness > 0` is a plate of metal (conductivity `k`, heat capacity `ρc`, thickness `t`) pressed on the top or bottom face through an interface of resistance per area `R''`. In the layered models it adds **one extra layer of nodes** (one per cell) on that face, with the coverage `c` of the cell by the block:

    lateral sheet conductance   S = k t c                                (joined by the harmonic mean, as the board)
    heat capacity               C = ρc t Δx Δy c
    contact to the board layer  G = c Δx Δy [ f/R'' + (1 − f)/(R'' + r_half) ]
    exposed surface             G = h_exp Δx Δy c,           h_exp = h_face · r_fin + h_extra
    sides of the plate          G = h_wall t L_edge,         h_wall = h_face + h_extra                       (7.1)
    board face under the block  its coefficient is multiplied by (1 − c)

`f` is the copper fill of the board layer there and `r_half` half a layer slab over `k_th`: **the heat enters the block mostly where the block overlaps copper** (the intersection of the two planes) through `R''`; over bare laminate it must also cross the FR-4 (a much larger resistance). The block is an isotropic plate without gradient across its thickness (valid while `h t/k` is small). Cells with no block have `10⁻⁹ W/K` to the ambient.

![The block in section](images/fig_41_block_section.png)

*Figure 41 (`images/fig_41_block_section.png`): left, a metal block on the board in section (illustrative proportions): the heat enters the block through the interface `R''` over copper, and over bare laminate also across half a slab of FR-4; it leaves through the exposed face (fins, `h_exp = h_face r_fin + h_extra`) and the side walls (`h_wall = h_face + h_extra`); the board face under the block loses nothing (factor `1 − c`). Right, the cell network these paths make.*

### 7.2 Plate fins

`r_fin` is the **fin ratio** of the optional plate fins (height `H_f`, thickness `t_f`, pitch `p`, perpendicular to the base, thin fins with an adiabatic tip at the corrected height `H_c = H_f + t_f/2`): per unit of base area

    r_fin = (1 − t_f/p) + 2 H_c η / p,       η = tanh(m H_c)/(m H_c),       m = √(2 h_face/(k t_f))                  (7.2)

(`r_fin = 1` without fins) [IncroperaDeWitt] (M). The fins stand on the exposed face, so only `h_exp` carries `r_fin`; the side walls of the plate keep `h_wall = h_face + h_extra` (7.1), which is not the board edge coefficient `h_side`. Not modelled: the end faces of the fins, their heat capacity (only the plate `ρc t` is in `C`, so a finned block responds too fast in time) and conduction along the fin row.

![Fin efficiency and fin ratio](images/fig_31_fin_efficiency_and_ratio.png)

*Figure 31 (`images/fig_31_fin_efficiency_and_ratio.png`): left, the efficiency `tanh(mL)/(mL)` of a plate fin against `mL` (closed form; the dots are the fins of the right panel at `H_f` = 10, 30 and 60 mm, `h` = 10 W/m²K, 1 mm thick, 5 mm pitch); right, the fin ratio of the program (`pcbthermal.blocks.fin_ratio`) against the fin height for aluminium (204 W/mK), copper (386) and carbon steel (54) of the program's metal library, with the line of fins that conduct perfectly. Computed by `scripts/make_figures.py`.*

### 7.3 Lumped and Analytic: the block in steady state

An equivalent coefficient `h_eq = 1/(R'' + 1/(h_face + h_extra))` (isothermal block) cannot work because the block spreads the heat of the pad centre to the whole pad, which a uniform coefficient does not do; what works is to keep the block's lateral conduction:

* **Lumped**: the block layer of the FVM network (7.1) is summed over the rings like the board layers: one more layer of unknowns per ring, lateral links between rings with the same contour formulas (infinite where the block does not reach), vertical link `g_link` summed per ring to the heater's layer. The board face under the block loses nothing.
* **Analytic**: on the tile grid of the local corrections the same block layer is built with `blocks.extra_layers`; the block temperatures `φ_blk` obey `(K_b + D_amb + D_link) φ_blk = D_link y_b` (`K_b` the lateral conductances between tiles, `D_amb` the exposed and wall conductances, `y_b` the board-layer temperatures of the tiles), so the heat they take from the board is `B y_b` with the Schur complement

      B = D_link − D_link (K_b + D_amb + D_link)⁻¹ D_link                                           (7.3)

  a dense matrix that couples the tiles of the block among themselves. `B` is added to the local conductance matrix `C_loc` of the correction (6.3) (static condensation, or Kron reduction of a network), together with the negative conductance `−h_face·A·c` for the face that the block hides. This is exact for the tile model; the error left is the tile size and the sheet averaging of the uniform problem.

Both are steady state only; the time simulations refuse a block, and SOR does not support blocks.

### 7.4 Close fins: a warning (`checks.check_fin_channels`)

The fin formula assumes one coefficient on every face; between fins closer than a few millimetres the air in the channel is slowed. After the solve the program computes the channel Rayleigh number of every finned block in still air,

    Ra_b = g β θ b_f⁴ Pr / (ν² L),      b_f = p − t_f                                                  (7.4)

(`θ` the mean excess of the block over the air, `L` the longer side of the block, air at ambient + θ/2), and warns when `Ra_b < 90`, that is when the channel keeps less than 90 % of the coefficient of an isolated plate. From the composite of two vertical plates of Bar-Cohen and Rohsenow [BarCohenRohsenow1984] (N; read as printed in [TeertstraReview]), `Nu_b = [(24/Ra_b)² + (0.59 Ra_b^{1/4})^{-2}]^{-1/2}`, the kept fraction is, by own algebra (L),

    ϕ_ch = [1 + (14.16 / Ra_b^{3/4})²]^{-1/2}                                                              (7.5)

(0.9 at `Ra_b` = 90, 0.75 at 40.5, 0.5 at 16.5). The result is never changed. The text of the warning, its limits (vertical channels, below `Ra_b = 14` the loss is an upper bound, no radiation, forced air not checked) and the numbers are in `models.md` 15 and `validation.md` 24; evidence `research/fin-channel`, `research/fin-channel-sources`. **Sources**: [ElenbaasBCR] (N), [BarCohenRohsenow1984] (N), [TeertstraReview].

### 7.5 The thickness of a plate: a bound (`checks.check_thick_plates`)

![The through-thickness correction](images/fig_33_thick_plate_correction.png)

*Figure 33 (`images/fig_33_thick_plate_correction.png`): the through-thickness correction `q'' t / (2 k)` against the thickness of the plate for copper (385 W/mK), aluminium (204), carbon steel (54) and FR-4 (0.3 through the thickness), for the flux of U1 of the example board (4 W over 100 mm², 40 kW/m²), with the 5 % limit of the check (`checks.THICK_PLATE_LIMIT`) of the rise of the hottest point of the board (FVM, 0.5 mm). Computed by `scripts/make_figures.py`.*

A copper layer and a block are one node through their thickness, the mean temperature. Where a flux `q''` enters one face of a plate of thickness `t` and conductivity `k` and leaves by the other, the entering face is hotter than the mean by

    Δθ_t = q'' t / (2 k)                                                                                    (7.6)

(a flux falling linearly to zero with depth gives `q'' t/(3k)`). After a run the program compares it with the rise of every heater and warns above 5 %; it is never added to the result. How `q''` is taken (the copper layer, the block, the auxiliary run) and the numbers are in `models.md` 4b and `validation.md` 22. **Published cases**: the plate model reproduces the spreading resistance of a small source on a plate, Seri Lee [EC1998Spreading], and the cross of five sources of [Muzychka2003] (`validation.md` 22.1, `research/effective-conductivity/`).

## 8. Heat transfer coefficients: convection and radiation

![Convection and radiation](images/fig_08_heat_transfer.png)

*Figure 8 (`images/fig_08_heat_transfer.png`): left, a board face that loses heat by convection and by radiation, `h = h_c + h_r`; middle, how both grow with the temperature of the face (illustrative values: a constant `h` overestimates the rise at high power and underestimates it at low power); right, the fixed-point loop that finds them, outside the models. The curve is the general form of Churchill and Chu; the laminar form is an option (`Board.natural_form`).*

In "computed" mode each outer face gets `h = h_c + h_r` (`convection.py`, mean face temperature `T_s`, air at the film temperature `(T_s + T_a)/2`):

* **Air** (dry, 1 atm, Sutherland-type fits, 250 to 450 K): `μ_air = 1.458·10⁻⁶ T^{3/2}/(T + 110.4)`, `k_air = 2.648·10⁻³ T^{3/2}/(T + 245.4·10^{−12/T})`, `ρ = p/(R T)`, `ν = μ_air/ρ`, `α = k_air/(ρ c_p)`, `Pr = μ_air c_p/k_air`, `β = 1/T`.
* **Rayleigh number**: `Ra = g β |ΔT| L³/(ν α)`, with `L = area/perimeter` for a horizontal plate and the height for a vertical one.
* **Natural convection, horizontal plate**: hot face up `Nu = 0.54 Ra^{1/4}` (`Ra ≤ 10⁷`), `0.15 Ra^{1/3}` above; hot face down `Nu = 0.27 Ra^{1/4}` (the roles swap for a face colder than the air) [IncroperaDeWitt] (M; the same forms are read in [Lienhard2024]).
* **Natural convection, vertical plate** (Churchill and Chu [ChurchillChu1975], equations 8.13a and 8.13b of [Lienhard2024]). The general form for all `Ra`

      Nu = (0.825 + 0.387 Ra^{1/6}/[1 + (0.492/Pr)^{9/16}]^{8/27})²                                  (8.1)

  and the laminar form for `Ra < 10⁹`

      Nu = 0.68 + 0.670 Ra^{1/4}/[1 + (0.492/Pr)^{9/16}]^{4/9}                                       (8.2)

  `h_n = Nu k_air/L`. The choice is `Board.natural_form` (`"general"`, the default, or `"laminar"`; the laminar form warns above `Ra = 10⁹`). The general form reproduces the worked example of [Lienhard2024] (Example 8.1, `Nu` 47.33); the laminar form is checked against the laminar boundary-layer solution of an isothermal vertical plate, `4/3 (Gr/4)^{1/4} g(Pr)` with LeFevre's `g(Pr) = 0.75 Pr^{1/2}/(0.609 + 1.221 Pr^{1/2} + 1.238 Pr)^{1/4}` [LeFevre1956] (M) (`validation.md` 22).
* **Forced convection**, flat plate along the flow: `Nu = 0.664 Re^{1/2} Pr^{1/3}` (`Re < 5·10⁵`), `(0.037 Re^{4/5} − 871) Pr^{1/3}` above, `Re = u L/ν` with `L` the board width (the flow runs along `x`), `h_f = Nu k_air/L` [IncroperaDeWitt] (M).
* **Mixed**: `h_c = C_cal (h_n³ + h_f³)^{1/3}` (Churchill's rule [ChurchillBlend]: the paper N, the rule S), `C_cal` the calibration multiplier of the convection.
* **Radiation** to surroundings at the air temperature, linearised: `h_r = ε σ (T_s² + T_a²)(T_s + T_a)` (absolute temperatures, view factor 1).

![Board orientation](images/fig_23_orientation.png)

*Figure 23 (`images/fig_23_orientation.png`): the two orientations of the Board panel (horizontal with layer 1 facing up, and vertical) and the three natural-convection laws against the Rayleigh number; at the same Rayleigh number the facing-down coefficient is half the facing-up one up to `Ra` 10⁷ (above it the facing-up law turns to `0.15 Ra^{1/3}` and the ratio falls). Constant air properties (`Pr` 0.71) for the vertical law; the vertical curve is the general form.*

**The loop.** Because `h` depends on the face temperature the program **iterates**: solve with the current `h`, take the mean temperature of each face, recompute `h`; it stops when both change by less than 0.01 W/m²K (a Picard fixed-point loop, outside the models, in `api._solve_computed_h`). The time simulation and the animation use the steady-state coefficients. `calibrate_convection` finds `C_cal` by bisection on `ln C_cal` so that the model reproduces one measured temperature.
**Limits**: correlations of isothermal plates (a board with hot spots departs from them), edge coefficient typed, no enclosure view factors.
**Where it is checked**: `validation.md` 8 (the loop) and 22 (the laminar form, the natural-convection forms); `research/horizontal-plate-h`, `research/plate-h-level`, `research/effective-conductivity`. **Sources**: [IncroperaDeWitt] (M), [ChurchillChu1975] (through [Lienhard2024]), [Lienhard2024], [LeFevre1956] (M), [ChurchillBlend] (S).

## 9. Parts: the junction temperature

![A part and the power coefficient](images/fig_09_part_runaway.png)

*Figure 9 (`images/fig_09_part_runaway.png`): left, the worst case: all the power enters the board and the junction sits a series resistance `Θ_part` above the hottest pad point; middle and right, the power that grows with temperature, `P(Tj) = P₀ [1 + α (Tj − 25)]`, against what the board removes, `(Tj − T_amb)/R`: they cross at the fixed point (stable, `α R P₀ < 1`) or never cross (thermal runaway, `α R P₀ ≥ 1`). The numbers of the curves are illustrative.*

A **part** is a heater with a junction-to-pad resistance `Θ_part`. In the worst case all the power enters the board (no heat through the package top): the board is solved with `P` unchanged and the junction is

    Tj = T_max,footprint + P Θ_part                (series resistance between the junction and the pad)          (9.1)

(the hottest board point under the footprint is the pad temperature). Derived quantities, for the same board response `R = (Tj − T_amb)/P` (linear for constant coefficients):

    margin = Tj,max − Tj          power limit P_lim = (Tj,max − T_amb)/R = P (Tj,max − T_amb)/(Tj − T_amb)
    ψJB estimate:  Tj = T_ring + ψJB P,   T_ring = mean board temperature in the ring 0.5 to 1.5 mm outside the outline (bounding box) of the footprint

`T_ring` is a board temperature away from the source: it does not include the face value of a part (section 1.4, `laminate.face_terms`), which (9.1) includes through `T_max` when the copper under the part is absent; `ψJB` is measured by JEDEC on the board beside the package, so the ring estimate is meant without it.

**Power that depends on temperature**: `P(Tj) = P₀ [1 + α (Tj − 25 °C)]`. The program iterates `P_{k+1} = P₀[1 + α(Tj(P_k) − 25)]` around the board solve until the powers change by less than 10⁻⁵ (relative). For a linear board (constant `R`, ambient 25 °C) the fixed point is

    ΔT = P₀ R/(1 − α P₀ R)                                                                                        (9.2)

the iteration converges when `α P₀ R < 1` and **thermal runaway** (no stable point) is reported when the device passes 1500 °C or the power grows 50 times. In general `ΔT = R P₀ [1 + α(T_amb − 25)]/(1 − α R P₀)`. A loop that does not settle warns.

### 9.1 The top path as a root (`analysis.part_split`, `api._top_path_split`)

![The top-path split](images/fig_42_top_path_split.png)

*Figure 42 (`images/fig_42_top_path_split.png`): left, a part with a top path: the junction joins the ambient through `R_top` and the board through `Θ_part` and `R_b`; middle, the residual `g(P_b) = P_b − P + p_top` of the split, computed with `pcbthermal.analysis.part_split` for a board resistance below (A) and above (B) the top resistance (illustrative values `P` = 2 W, `Θ_part` = 5 K/W, `R_top` = 20 K/W, `R_b` = 8 and 40 K/W): monotone, one root, a kink where the top heat is clipped at `P` (case B); right, the plain fixed point `P_b ← P − p_top(T_max(P_b))` on case B, slope −1.6: it jumps between 0 and 1.6 W and is not used. Computed by `scripts/make_figures.py`.*

With a heatsink on the package (`theta_jc_top`, `interface`, `theta_sa`) the part is a junction node joined to the board by `Θ_part` and to the ambient by `R_top = θJC(top) + R''/A + θSA` (`A` the contact area, or the footprint). With `P_b` the heat into the board and `T_max(P_b)` the hottest board point under the footprint,

    Tj − T_amb = (T_max − T_amb) + P_b Θ_part,     P_b = P − (Tj − T_amb)/R_top
        ⇒   Tj − T_amb = (T_max − T_amb + P Θ_part)/(1 + Θ_part/R_top)                                            (9.3)

(`analysis.part_split`; the top heat is limited to `[0, P]`, a heat that cannot be negative or exceed the part's power: the board never feeds the part through its top, which is conservative and is the reason for the kink of `g` at `P_b = P`). `T_max` depends on `P_b`, so the operating point is the root of the scalar equation of each part

    g(P_b) = P_b − P + p_top(T_max(P_b)) = 0,         g' = 1 + R_b/(R_top + Θ_part) ≥ 1,   g(0) ≤ 0 ≤ g(P)       (9.4)

with `R_b = dT_max/dP_b` the board's resistance under the part (the slope is 1 where the top heat is clipped at `P`; monotone, so the root is bracketed by `[0, P]`). **A fixed-point iteration `P_b ← P − p_top(T_max(P_b))` is not used**: its slope is `−R_b/(R_top + Θ_part)`, it converges only when the board under the part resists less than `R_top + Θ_part` and oscillates with a growing amplitude above that, which is the case on a small pad. The algorithm (`api._top_path_split`):

* **one part**: regula falsi with the Illinois rule on `[0, P]`; with constant face coefficients the board is affine in `P_b`, so the secant between the two ends is exact and three board solves give the root, unless the top heat is already clipped at `P_b = P` (small pads, a kink in `g`); with computed coefficients the Picard loop of section 8 is inside every solve;
* **several parts**, whose splits interact through the board: a Broyden quasi-Newton iteration on the vector `P_b`, started from the finite-difference Jacobian with the wide steps `P_b,j → 0` (exact for an affine board only when no top heat is clipped and the hottest cells under the footprints do not move), projected on `[0, P]` and with step halving;
* it stops when every `|g_i|/P_i ≤ 10⁻⁵` (at most 40 steps); the best iterate is kept, and when its residual is above `10⁻⁴` the result carries the warning "the top-path split did not converge".

The power temperature coefficient is the other loop: it stays a fixed point around the whole solve (its slope `α P₀ R` is the physical runaway condition), and with both the power loop goes around the top-path solve; every pass of it repeats the split.
**Why `Θ_part` must be a junction-to-pad number**: `θJA` contains the manufacturer's board and air, and `θJB` the spreading in the manufacturer's board; the program computes the spreading in your board, so either would count it twice (`models.md` 6).
**Limits**: worst-case convention (the hottest point under the footprint); steady state only for the top path; no Foster chain; the share of the power into the board is not checked against a manufacturer's value.
**Where it is checked**: `validation.md` 9 and 19 (parts, the top of the package; solve counts and the small-pad cases); `research/component-heatsink`; `tests/test_top_path.py`. **Sources**: [JESD15-3] (R through a mirror; the two-resistor model), [JESD51family] (N), the datasheets of `models.md` 6.

## 10. Power profiles in time

![The decision average or resolve](images/fig_10_profile_decision.png)

*Figure 10 (`images/fig_10_profile_decision.png`): left, a square wave and the response of the hottest point (first-order response, illustrative): the temperature oscillates around the value of the average power; middle, the average-or-resolve decision: heaters sorted by oscillation, averaged while the cumulative oscillation stays under the shared threshold (illustrative oscillations); right, the window is the least common multiple of the periods.*

A heater may carry a repeating profile (`SquareWave`, `TableProfile`) or a one-shot table. With the unit **step response** `Z(t)` of the heater's own hottest point (section 2.4) the response to a piecewise-constant periodic power `P(t)` of period `T` is, by superposition of delayed steps,

    T(u) = Σ_j P_j [ G_p(σ₂,j) − G_p(σ₁,j) ]          G_p(σ) = Σ_{m≥0} [ Z(σ + mT) − Z(mT) ] + (σ/T)(R_th − Z(MT))         (10.1)

(`[σ₁, σ₂]` the part of the period whose impulse falls on stretch `j`; the tail beyond `M` exact terms is the remaining response taken flat; `G_p(T) = R_th`; `G_p` is a name of this section, not a conductance). For a square wave `peak = P_off R_th + ΔP G_p(t_p)`. The **oscillation** peak − valley is in °C.
**Decision**: heaters are sorted by oscillation and *averaged* (smallest first) while their cumulative oscillation stays within the threshold (default 1 °C, a shared error budget); the others are *resolved*; one-shot tables are always resolved.
**Run**: one time-stepping run with all heaters (the problem is linear), step `Δt` a tenth of the shortest stretch, the power of a step is the **exact mean** of the profile over the step `(1/Δt)∫P dt`, the window is the least common multiple of the periods, and windows repeat until peak and valley change by less than 0.1 °C. Start: the steady state of the average power. The Analytic model smears vias and heatsinks in time (warned) and none of the models runs a time simulation with a block.
**The face of a part over absent copper (FVM and FDM).** A part over bare laminate is read at its face, the copper node plus the drop over the half layer of laminate under it (section 1.4). In the resolved run the curve of a heater adds the quasi-static face term of the power of each step, `Q t_cu/(2 k_z A)` (`laminate.face_terms`), a first-order model of the half copper layer, whose time constant is `τ₁ = 4 (t/2)² /(π² α)` = 0.69, 2.8 and 11 ms for 35, 70 and 140 µm of copper (FR-4 `α` = 1.8·10⁻⁷ m²/s). Below about `10 τ₁` the curve follows the power with no lag and overstates the swing of the face (the peak on the hot side, the minimum on the cool side). The decision adds the swing of the face to the oscillation of the node, `Δ = Δ_node + (P_peak − P_low) R_face,max`, with `R_face,max` the largest face term of the part per watt of its own power (`profiles.face_resistances`), and does **not** attenuate it with a `tanh` of `P/(4τ₁)`: it stays on the safe side, a resolved run costing windows of one period. Without a face term the decision is the node's, bit for bit. Example (6 mm part on bare laminate, 0 to 2 W at 10 ms, threshold 1 K): averaged by the node (0.36 K), resolved with the face (3.6 K); peak 187.60 → 189.58 °C.

**Where it is checked**: `validation.md` 7 (time-dependent results); `tests/test_profiles.py`. **Sources**: superposition and the theta method as in section 2.4; no external source.

## 11. Verification summary

![The verification ladder](images/fig_22_verification_ladder.png)

*Figure 22 (`images/fig_22_verification_ladder.png`): the checks in order of independence, from exact solutions to the comparison between models, with the results of this section (their evidence is in `validation.md`), and the rung that is still missing: a physical board.*

| Piece | How it is checked | Result (evidence in `validation.md`) |
| :-- | :-- | :-- |
| Energy balance of every model | `power_out` against the injected power on every test board | 10⁻¹² to 10⁻⁹ |
| Linear solvers | direct, CG and SOR on five boards | agree to 2·10⁻⁸ K (5) |
| Time stepping | exact RC solution of a uniform board | Euler first order, Crank-Nicolson second order (7) |
| Stack-up | exact series circuit of a uniform board with three different gaps | 10⁻⁶ K on every layer (12) |
| Layered idealisation | the 3D solid and an independent finite-element solid | 0.1 to 0.7 % (FVM; up to 2.9 % on a one-sided pad no larger than the heater) (3) |
| Layered models | the independent 3D solver of the tests on a Cu / FR-4 / Cu coupon | FVM, 3D solid and Analytic within 0.2 %, FDM within 1.2 % (22) |
| 3D solid | Yovanovich's Table 3 (isoflux source on a flux tube) | +0.7 to +0.8 % at `ε` 0.2 and 0.3, 2 % at `ε` 0.1 where the source has three cells (16; `research/solid3d-verification`) |
| 3D solid | finite-element solid, convergence in slabs and cells | 0.2 % on three boards, ±4 % on a heater-sized pad (16) |
| Plate (block) model | published spreading resistance (Seri Lee) | +0.6 % centre, −0.8 % edge, −4.6 % corner (22.1) |
| Convection correlations | textbook air properties, closed forms | 1 to 3 % (8) |
| Parts | closed form `ΔT = P₀R/(1 − αP₀R)` | 0.05 K (9) |
| Mesh and model comparison | the 19 scenarios of `validation.md` 2 (and the example board), four models and the 3D solid | the Lumped and Analytic models fail in known cases, which the input checks warn (2) |

The models have **not** been compared with measurements of a physical board in this project; `calibrate_convection` is the tool to fit one measurement.

## 12. References

The reading status: **R** read in full or in the pages that matter; **S** seen as a summary, abstract or a search result; **M** known from memory; **N** not obtained; **L** own derivation checked in the repository. The full records (what was opened, pages, what was reproduced) are in `research/theory/BIBLIOGRAPHY.md` (section 20 is the table of this document). A statement that rests on a source with status N, M or S is marked where it is made.

| Key | Citation | Status | Where used |
| :-- | :-- | :-- | :-- |
| [Patankar1980] | S. V. Patankar, *Numerical Heat Transfer and Fluid Flow*, Hemisphere (McGraw-Hill), 1980 | M content, S citation | 2.1, 2.4 (finite volumes, harmonic mean, theta method; derived in the text) |
| [Peaceman1978] | D. W. Peaceman, *Interpretation of well-block pressures in numerical reservoir simulation*, SPE J. 18 (3) (1978) 183-194 | S (abstract only) | 2.6 (well radius of a point sink; the constant 0.1985 is computed) |
| [Saad2003] | Y. Saad, *Iterative Methods for Sparse Linear Systems*, 2nd ed., SIAM, 2003 (open copy) | R (sections 3.3, 4.1, 4.2, 10.2) | 2.3 (Theorem 4.16, equation 4.47, pages 126 and 127; multicolouring; block relaxation) |
| [Young1950] | D. M. Young, PhD thesis, Harvard, 1950 (Trans. AMS 76 (1954) 92-111, from memory) | N | 2.3 (consistent orderings, the optimum `ω`; quoted through [Saad2003]) |
| [Young1971] | D. M. Young, *Iterative Solution of Large Linear Systems*, Academic Press, 1971 | N | 2.3 (same) |
| [Krogh1919] | A. Krogh, J. Physiology 52 (1919) 409-415 (from memory) | M; the formula (1.8) is L | 1.5 (the Krogh cell) |
| [Dietz1965] | D. N. Dietz, J. Petroleum Technology (1965), SPE-1156-PA | S equation, M shape factors | 1.5 (the same mathematics in well testing) |
| [IncroperaDeWitt] | F. P. Incropera, D. P. DeWitt, *Fundamentals of Heat and Mass Transfer*, Wiley (edition not recorded) | M content, S citations | 1.2, 6, 7.2, 8 (fin and sheet equations, correlations, radiation) |
| [CarslawJaeger] | H. S. Carslaw, J. C. Jaeger, *Conduction of Heat in Solids*, 2nd ed., Oxford, 1959 | M content, S citation | 5, 6 (Fourier series, `K₀` Green function, disc sources, `I₀`, `I₁`) |
| [CulhamYovanovich1998] | J. R. Culham, M. M. Yovanovich, *Factors affecting the calculation of effective conductivity in printed circuit boards*, ITherm'98, pp. 460-467 (1998) | R (pages 460 to 466, scan) | 1.2 (no homogenised conductivity) |
| [Lemczyk1992] | T. F. Lemczyk, B. L. Mack, J. R. Culham, M. M. Yovanovich, *PCB trace thermal analysis and effective conductivity*, J. Electronic Packaging 114 (4) (1992) 413-419 | R (pages 414 to 417 as images; Tables 1 to 3 reproduced with an independent 2D solver) | 1.2 (context; coupon cases reproduced in `validation.md` 22.1) |
| [EC1998Spreading] | Seri Lee, *Calculating spreading resistance in heat sinks*, Electronics Cooling, January 1998 | R (equations 1 and 2 as images, the worked example reproduced) | 7.5 (the plate check). The paper of Lee, Song, Au and Moran (1995) [Lee1995] cited by earlier documents was not located (N) and is not cited |
| [Muzychka2003] | Y. S. Muzychka, J. R. Culham, M. M. Yovanovich, *Thermal spreading resistance of eccentric heat sources on rectangular flux channels*, J. Electronic Packaging 125 (2) (2003) 178-185 | R | 7.5 (cross of five sources reproduced) |
| [Yovanovich2003] | M. M. Yovanovich, *Thermal resistances of circular source on finite circular cylinder with side and end cooling*, J. Electronic Packaging 125 (2003) 169-177 | R (Table 3) | 4 (flux-tube check of the 3D solid) |
| [ChurchillChu1975] | S. W. Churchill, H. H. S. Chu, Int. J. Heat Mass Transfer 18 (1975) | N for the paper; equations R through [Lienhard2024] | 8 (equations 8.1, 8.2) |
| [ChurchillBlend] | S. W. Churchill (1977), mixed convection rule | N for the paper; the rule S | 8 |
| [LeFevre1956] | E. J. LeFevre, Ninth Int. Congress of Applied Mechanics, Brussels, 1956, vol. 4, p. 168 (from memory) | M | 8 (check of the laminar form only; own computation) |
| [Lienhard2024] | J. H. Lienhard IV, J. H. Lienhard V, *A Heat Transfer Textbook*, 6th ed. (open) | R (pages 311, 419 to 421, 435 to 437) | 8 (equations 8.13a, 8.13b, Example 8.1) |
| [BarCohenRohsenow1984] | A. Bar-Cohen, W. M. Rohsenow, J. Heat Transfer 106 (1) (1984) 116-123 | N for the paper; the composite R as printed in [TeertstraReview] and in Bar-Cohen, Iyengar, Kraus (2003) | 7.4 (`ϕ_ch` is own algebra, L) |
| [ElenbaasBCR] | W. Elenbaas, Physica 9 (1942) 1-28 (pages from memory) | N | 7.4 |
| [TeertstraReview] | P. Teertstra, J. R. Culham, M. M. Yovanovich, *Comprehensive review of natural and mixed convection heat transfer models for circuit board arrays*, Univ. of Waterloo report | R (equations as images) | 7.4 (equations 8, 20, 21, 22) |
| [JESD15-3] | JEDEC JESD15-3, *Two-resistor compact thermal model guideline* (2008) | R (through a mirror) | 9 |
| [JESD51family] | JEDEC JESD51 family (θJA, θJB, θJC, ψ definitions) | N | 9 |
| [George1973] | A. George, *Nested dissection of a regular finite element mesh*, SIAM J. Numer. Anal. 10 (1973) 345-363 | M | 2.7 (the exponent and the thin-in-plan board; a hypothesis the measurements test) |
| [Davis2006] | T. A. Davis, *Direct Methods for Sparse Linear Systems*, SIAM, 2006 | M | 2.7 (fill of sparse factors) |
| [LiSuperLU2005] | X. S. Li, *An overview of SuperLU*, ACM Trans. Math. Softw. 31 (2005) 302-325 | N | 2.7 (the memory of the factor) |
| [Celik2008] | I. B. Celik, U. Ghia, P. J. Roache, C. J. Freitas, J. Fluids Engineering 130 (7) (2008) 078001 | R (pages 4 to 9; Table 1 reproduced) | 4 (grid convergence index) |
| [Roache] | P. J. Roache, verification and validation in computational science and engineering | M (summaries S) | 4 (cite [Celik2008] for the procedure) |
| [Fish2017] | M. C. Fish, PhD dissertation, University of Maryland (2017) | R chapter 6 (reproduced; chapters 5 and 7 not read) | 1.5 (microspreading of via cells) |
| [Kron2022] | Kron reduction of a network, arXiv 2204.05554 (authors and title not recorded) | S | 2.6, 5.1 |
| [MFEMStaticCond] | MFEM documentation, static condensation | S | 6, 7.3 |

