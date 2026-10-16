# Thermal Models: Description, Formulas and Review (legacy `core/` solvers)

> This document describes the **legacy** solvers in `core/` and why they were replaced. The new
> physics package is documented in [`physics_core.md`](physics_core.md).

Reference document for the three solvers of the PCB Thermal Simulator Tool
(`core/analytic_solver.py`, `core/lumped_solver.py`, `core/fdm_solver.py`).

- Status: describes the code **as implemented** on branch `develop`, commit `904f625`
  (2026-10-16). Section 6 and 7 record what is wrong or questionable.
- Math is written in GitHub LaTeX (`$...$`). Units are given in brackets.
- File and function names refer to the repository; line numbers are not quoted
  because they change.

## Table of contents

1. [Common inputs and conventions](#1-common-inputs-and-conventions)
2. [Analytic model](#2-analytic-model)
3. [Lumped (LPTN) model](#3-lumped-lptn-model)
4. [FDM model](#4-fdm-model)
5. [Results returned by each solver](#5-results-returned-by-each-solver)
6. [Validation experiments](#6-validation-experiments)
7. [Review findings and what is correct](#7-review-findings-and-what-is-correct)
8. [Literature and external references](#8-literature-and-external-references)
9. [Proposed direction](#9-proposed-direction)

---

## 1. Common inputs and conventions

### 1.1 The `json_config` dictionary

The editor (`ui/editor.py`, `run_simulation`) builds one dictionary and hands it to
`ThermalSolver.run_simulation`, which validates it and dispatches by `solver_mode`
(`'analytic'`, `'lumped'`, `'fdm'`).

```
json_config = {
  'solver_mode': 'Analytic' | 'Lumped' | 'FDM',
  'pcb_params':  { ...see table below... },
  'elements':    [ {type, id, points, ...}, ... ],
}
```

`ThermalSolver.validate_config` requires these `pcb_params` keys: `width`, `height`,
`thickness`, `layers`, `copper_thickness`, `copper_conductivity`, `fr4_conductivity`,
`ambient_temp_global`, `convection_h_global`, `convection_h_top`,
`convection_h_bottom`; FDM additionally requires `grid_dx` and `grid_dy`.

| Key | Meaning | Unit | Default (`config.py`) |
| :-- | :-- | :-- | :-- |
| `width`, `height` | board size | mm | 100, 100 |
| `thickness` | total board thickness | mm | 1.6 |
| `layers` | number of copper layers | - | 2 (max 8) |
| `copper_thickness` | copper thickness **per layer** | mm | 0.035 |
| `copper_conductivity` | $k_{Cu}$ | W/(m K) | 385 |
| `fr4_conductivity` | $k_{FR4}$ | W/(m K) | 0.3 |
| `ambient_temp_global` | $T_{amb}$ | °C | 25 |
| `convection_h_global` | $h$ (used by Analytic, Lumped, FDM sides) | W/(m² K) | 10 |
| `convection_h_top`, `convection_h_bottom` | $h_{top}$, $h_{bot}$ (used by FDM only) | W/(m² K) | 10, 15 |
| `grid_dx`, `grid_dy` | FDM grid spacing | mm | 10 |
| `tolerance` | SOR stop threshold on max change per sweep | K | 0.01 |
| `max_iterations` | SOR sweep limit | - | 50000 |
| `over_relaxation_factor` | SOR factor $\omega$ (UI accepts 0 to 2) | - | 1.5 |
| `model_mode` | `Basic` / `Advanced` (Analytic and Lumped only) | - | Basic |
| `boundary_mode` | `Convective` / `Insulated` side faces (FDM only) | - | Convective |
| `hotspot_threshold` | FDM hotspot limit | °C | solver fallback 85, config 100 |
| `pcb_corners` | `[[x_min, y_min], [x_max, y_max]]` of the board in canvas pixels | px | set by the editor |

### 1.2 Elements

| `type` | Fields used | Meaning |
| :-- | :-- | :-- |
| `Zone` | `points`, `layer`, `id` | copper area on one layer |
| `Heater` | `points`, `layer`, `power` [W] | heat source spread uniformly over its polygon |
| `Via` | `points[0]`, `diameter` [mm] | through via, all layers |
| `Sink` | `points`, `layer`, `htc_extra` [W/(m² K)] | extra convection over a polygon |

`points` are canvas pixels. The editor only allows `Sink` on the top or bottom layer.

### 1.3 Pixel to millimetre conversion

With $x_{min}, x_{max}$ from `pcb_corners` and board width $W$ [mm]:

- Analytic and Lumped only use a single scale factor
  $s = W / |x_{max}-x_{min}|$ [mm/px] and take polygon coordinates
  $(x-x_{min})\,s$, $(y-y_{min})\,s$. The y axis is not flipped (irrelevant for areas).
- FDM (`_pixel_to_mm`) scales each axis separately and flips y so $y=0$ is the bottom:

$$
x_{mm} = \frac{p_x-x_{min}}{x_{max}-x_{min}}\,W, \qquad
y_{mm} = H - \frac{p_y-y_{min}}{y_{max}-y_{min}}\,H
$$

### 1.4 Polygon area (shoelace)

Used for heater (and in FDM for heater power density):

$$
A = \tfrac12 \left| \sum_{i=0}^{n-1} \left(x_i\,y_{i+1} - x_{i+1}\,y_i\right) \right|, \quad i+1 \bmod n
$$

Analytic and Lumped sum the areas of all heaters (overlaps are counted twice).

### 1.5 Quantities every solver reports

- $P = \sum P_{heater}$ [W].
- $\Delta T = T_{max} - T_{amb}$ [K].
- Effective thermal resistance $R_{\theta} = \Delta T / P$ [K/W] (FDM), or the
  resistance used in the formula (Analytic, Lumped).

---

## 2. Analytic model

File: `core/analytic_solver.py`, `AnalyticSolver.simulate`.
Idea: the board is a single lump that conducts heat sideways through its copper
(one resistance) and then loses it by convection (another resistance), in series.

### 2.1 Effective area

$$
A_{pcb} = \frac{W}{1000}\,\frac{H}{1000} \; [\mathrm{m^2}], \qquad
A_{eff} =
\begin{cases}
A_{pcb} & \text{Basic}\\
A_{heater} \text{ (or } A_{pcb} \text{ if no heater polygon)} & \text{Advanced}
\end{cases}
$$

with $A_{heater}=\sum_k A_k\cdot 10^{-6}$ from the shoelace areas in mm².

### 2.2 Resistances

Convection (one surface, uses `convection_h_global` $h$):

$$
R_{conv} = \frac{1}{h\,A_{eff}} \quad [\mathrm{K/W}]
$$

Conduction through copper:

$$
L = \frac{\min(W,H)}{2000}\ [\mathrm m], \qquad
t = \frac{t_{Cu}}{1000}\,N_{layers}\ [\mathrm m], \qquad
R_{cond} = \frac{L}{k_{Cu}\,A_{eff}\,t}
$$

where $t_{Cu}$ is the copper thickness per layer in mm and $N_{layers}$ the layer count.
$L$ is half the shorter board side, taken as the average conduction path.

Series total:

$$
R_{tot} = R_{conv} + R_{cond}
$$

### 2.3 Temperatures

$$
T_{max} = T_{amb} + P\,R_{tot}, \qquad
T_{avg} = T_{amb} + \tfrac12\,P\,R_{tot}, \qquad
\Delta T = P\,R_{tot}
$$

$T_{avg}$ is simply the midpoint between ambient and maximum; there is no spatial model.

### 2.4 Worked example (reference case)

100x100 mm, 2 layers, $t_{Cu}$=0.035 mm, $h$=10, $P$=5 W, Basic mode.

- $A_{eff}=0.01$ m², $R_{conv}=1/(10\cdot0.01)=10$ K/W
- $L=0.05$ m, $t=7\cdot10^{-5}$ m, $R_{cond}=0.05/(385\cdot0.01\cdot7\cdot10^{-5})=185.5$
- $R_{tot}=195.5$ K/W, $T_{max}=25+5\cdot195.5=1002.6$ °C

For comparison the FDM solution of the same board is about 92 °C. See section 7.1
for why the conduction term is wrong.

### 2.5 Assumptions and limits

- No spatial resolution, no layer detail, no vias, no sinks, no `h_top`/`h_bottom`.
- Radiation is only present through the user's combined $h$.
- Heater position and shape do not matter in Basic mode; in Advanced mode only its area does.

---

## 3. Lumped (LPTN) model

File: `core/lumped_solver.py`, `LumpedSolver.simulate`.
Idea: build a short chain of thermal resistances (copper, FR4, convection, vias) and
read temperatures at a few characteristic points.

### 3.1 Effective area

$$
A_{eff} =
\begin{cases}
A_{pcb} & \text{Basic}\\
A_{heater}+A_{vias} \text{ (or } A_{pcb} \text{ if it is zero)} & \text{Advanced}
\end{cases}
\qquad
A_{vias}=\sum_v \pi \left(\frac{d_v}{2000}\right)^2 \ [\mathrm{m^2}]
$$

Default via diameter is 0.6 mm when the element has none.

### 3.2 Resistances

With $t_{pcb}$ the total board thickness in metres and $N$ the number of layers:

$$
R_{Cu,layer} = \frac{t_{pcb}}{k_{Cu}\,A_{eff}}, \qquad
R_{Cu,eff} = \frac{R_{Cu,layer}}{N} \quad\text{(layers in parallel)}
$$

$$
R_{FR4} = \frac{t_{pcb}}{k_{FR4}\,A_{eff}}, \qquad
R_{conv} = \frac{1}{h\,A_{eff}}
$$

Vias ($n_v$ vias, average via area $\bar A_v = A_{vias}/n_v$):

$$
R_{via} = \frac{t_{pcb}}{k_{Cu}\,\bar A_v}, \qquad
R_{vias,eff} = \frac{R_{via}}{n_v} \quad (=\infty \text{ if } n_v=0)
$$

### 3.3 Total resistance (as implemented)

$$
R_{tot} = \frac{R_{Cu,eff} + R_{FR4} + R_{conv}}{1 + n_v}
$$

Note that $R_{vias,eff}$ is computed and reported but **not used** in $R_{tot}$.
The division by $(1+n_v)$ is an empirical simplification, not a network law.

### 3.4 Temperatures

$$
\begin{aligned}
T_{max} &= T_{amb} + P\,R_{tot}\\
T_{bottom} &= T_{amb} + P\,R_{conv}\\
T_{top} &= T_{amb} + P\,(R_{Cu,eff}+R_{conv})\\
T_{avg} &= T_{amb} + P\,(R_{FR4}+R_{conv})\\
T_{inner} &=
\begin{cases}
T_{amb} + P\,(R_{FR4}+R_{conv})/N & N>2\\
T_{avg} & N\le 2
\end{cases}
\end{aligned}
$$

and heat flux $q = P / A_{eff}$ [W/m²], $\Delta T = T_{max}-T_{amb}$.

### 3.5 Worked example (reference case, Basic)

$A_{eff}=0.01$ m², $t_{pcb}=0.0016$ m, $N=2$, $n_v=0$.

- $R_{Cu,layer}=0.0016/(385\cdot0.01)=4.16\cdot10^{-4}$, $R_{Cu,eff}=2.08\cdot10^{-4}$ K/W
- $R_{FR4}=0.0016/(0.3\cdot0.01)=0.533$ K/W, $R_{conv}=10$ K/W
- $R_{tot}=10.53$ K/W, $T_{max}=25+5\cdot10.53=77.7$ °C
- $T_{top}=T_{bottom}=75.0$ °C (the copper term is negligible)

In Advanced mode the same board gives 1342 °C because $A_{eff}$ shrinks to the
heater plus via area (see 7.2).

### 3.6 Assumptions and limits

- Vertical heat path through the full board thickness; no lateral spreading.
- Convection on a single surface ($h$ global); `h_top`/`h_bottom` unused.
- Only one FR4 resistance regardless of the number of layers.
- No sinks, no positions, no heater layer.

---

## 4. FDM model

File: `core/fdm_solver.py`, `FDMSolver.simulate` and the Numba kernel `sor_update`.
Idea: a 3D thermal network. Each copper layer is a 2D sheet of nodes; nodes are linked
laterally by copper sheet conductances, vertically by FR4 (plus vias), and each node
loses heat to ambient by convection. The steady-state heat balance of every node
is solved iteratively with Successive Over-Relaxation (SOR).

All lengths are in **mm** inside the solver, conductivities in **W/(mm K)**, heat
transfer coefficients in **W/(mm² K)** ($h_{W/mm^2K} = h_{W/m^2K}/10^6$).

### 4.1 Grid

$$
n_x = \lfloor W/\Delta x \rfloor + 1, \quad n_y = \lfloor H/\Delta y \rfloor + 1, \quad
\text{node } (l,i,j) \text{ at } x=j\,\Delta x,\ y=i\,\Delta y
$$

Layers $l=0\ldots N-1$ (layer 0 is the top). The layers are equally spaced:

$$
\Delta z = \frac{t_{pcb}}{N-1} \quad (N>1)
$$

The grid is node-centred and each node represents a full $\Delta x\,\Delta y$ cell, including
nodes on the border (see 7.4).

### 4.2 Element rasterisation (`_process_elements`)

For each grid node, a ray-casting test decides whether $(x,y)$ is inside a polygon.

- **Zone**: `copper_masks[layer, i, j] = True`.
- **Heater** (power $P_h$, polygon area $A_h$ in mm²): power density $p=P_h/A_h$
  [W/mm²], and each node inside receives

$$
Q_{l,i,j} \mathrel{+}= p\,\Delta x\,\Delta y \quad [\mathrm W]
$$

- **Sink**: `h_extras[layer, i, j] += htc_extra`.
- **Via**: stored as $(x_{mm}, y_{mm}, d)$; applied in 4.3.

The element `layer` is 1-based in the JSON and 0-based in the arrays.

### 4.3 Conductances (`_precompute_conductances`)

Copper sheet conduction between neighbouring nodes exists only if **both** nodes are
copper on that layer (thickness $t_{Cu}$ in mm, $k_{Cu}$ in W/(mm K)):

$$
G_x = \frac{k_{Cu}\,t_{Cu}\,\Delta y}{\Delta x}, \qquad
G_y = \frac{k_{Cu}\,t_{Cu}\,\Delta x}{\Delta y} \quad [\mathrm{W/K}]
$$

Vertical conduction between adjacent layers is through FR4 at every node:

$$
G_z = \frac{k_{FR4}\,\Delta x\,\Delta y}{\Delta z}
$$

A via at $(x,y)$ is snapped to the nearest node $(i,j)=(\mathrm{round}(y/\Delta y),\mathrm{round}(x/\Delta x))$
and adds, for every pair of adjacent layers, the conductance of a **solid** copper rod:

$$
G_{via} = \frac{k_{Cu}\,\pi (d/2)^2}{\Delta z}
$$

Convection to ambient per node (area $\Delta x\,\Delta y$):

$$
G_{conv,l,i,j} = h_{l,i,j}\,\Delta x\,\Delta y, \qquad
h_{0}=h_{top},\ h_{N-1}=h_{bot},\ h_{inner}=0
$$

For a single-layer board both faces count: $h_0 = h_{top}+h_{bot}$. Sink extras are
added to layer 0 and layer $N-1$ only (a sink on any other layer has no effect).

Side faces (only if `boundary_mode = Convective`) with $h_{side}=$ `convection_h_global`
and effective thickness $t_{Cu}$:

$$
G_{side,\,j\in\{0,n_x-1\}} \mathrel{+}= h_{side}\,\Delta y\,t_{Cu}, \qquad
G_{side,\,i\in\{0,n_y-1\}} \mathrel{+}= h_{side}\,\Delta x\,t_{Cu}
$$

Corner nodes get both terms. In `Insulated` mode the sides are adiabatic.

### 4.4 Governing equation

Steady-state energy balance at node $(l,i,j)$ with neighbours $m$:

$$
\sum_{m} G_{m}\,(T_{l,i,j} - T_m)\; +\; G_{conv}\,(T_{l,i,j}-T_{amb})\; +\; G_{side}\,(T_{l,i,j}-T_{amb})\;=\; Q_{l,i,j}
$$

In matrix form $\mathbf{A}\,\mathbf{T}=\mathbf{b}$, with $\mathbf A$ sparse, symmetric and
positive definite whenever at least one node has $G_{conv}>0$ or $G_{side}>0$
(it is weakly diagonally dominant). That is what makes SOR, Conjugate Gradients or a
direct sparse factorisation all valid.

### 4.5 SOR iteration (`sor_update`)

Sweep order: layer, then row $i$, then column $j$, updating **in place** (Gauss-Seidel
ordering). For each node:

$$
T^{*}_{l,i,j} = \frac{\sum_m G_m T_m + (G_{conv}+G_{side})\,T_{amb} + Q_{l,i,j}}
{\sum_m G_m + G_{conv}+G_{side}}
$$

$$
\delta = T^{*} - T_{l,i,j}, \qquad T_{l,i,j} \leftarrow T_{l,i,j} + \omega\,\delta
$$

- $\omega=1$ is Gauss-Seidel, $1<\omega<2$ is over-relaxation.
- The stopping rule is $\max|\delta| < \texttt{tolerance}$ over one full sweep, or
  `max_iterations` reached. **This is a step-size test, not a residual test** (7.1).
- Initial guess: $T=T_{amb}$ everywhere.
- Every `DEFAULT_EVOLUTION_CAPTURE_STEP` sweeps (default 10) the top layer is copied to a
  history buffer, used for the "evolution" GIF. This is iteration history, not time.
- Numba (`@njit`) is optional; without it the file currently fails to import (7.3).

For reference, the optimal $\omega$ of the model Poisson problem on an $n\times n$ grid is
$\omega_{opt}=2/(1+\sin(\pi/(n+1)))$, which tends to 2 as the grid is refined. The fixed
default 1.5 is therefore far from optimal on fine grids.

### 4.6 Post-processing

| Function | What it computes |
| :-- | :-- |
| `_analyze_hotspots` | nodes with $T>T_{hotspot}$ per layer; lists the first 5 |
| `_analyze_gradients` | $\lvert\nabla T\rvert=\sqrt{(\partial_x T)^2+(\partial_y T)^2}$ (via `np.gradient`) per layer, and vertical $\lvert T_l-T_{l+1}\rvert/\Delta z$ |
| `_analyze_heat_flow` | input $\sum Q$ vs. dissipated $\sum h A (T-T_{amb})$ + side losses. Logged only, **not used** for convergence |
| `_analyze_zone_temps` | mean $T$ of the nodes inside each zone polygon |

Final metrics:

$$
R_\theta = \frac{T_{max}-T_{amb}}{P}, \qquad q=\frac{P}{W H\cdot10^{-6}}\ [\mathrm{W/m^2}]
$$

with $P=\sum Q_{l,i,j}$ (the power actually inserted in the grid, which can differ from the
requested heater power, 7.1). `t_top` and `t_bottom` are the **layer averages**, and
`t_inner` is the mean of the inner-layer averages when $N>2$.

### 4.7 Assumptions and limits

- 3D thermal network, steady state only.
- Lateral heat flows only through copper nodes; FR4 conducts only vertically.
- Copper thickness is the same on every layer and fully solid inside a Zone.
- Thermal vias are solid copper rods snapped to a node.
- Convection is applied to the whole board surface, not only to copper.
- Components, enclosures and radiation are not modelled explicitly.

---

## 5. Results returned by each solver

| Key | Analytic | Lumped | FDM |
| :-- | :-: | :-: | :-: |
| `max_temp`, `avg_temp`, `delta_t` | yes | yes | yes |
| `effective_r_th`, `total_power`, `effective_area` | yes | yes | yes |
| `t_top`, `t_bottom`, `t_inner` | - | formula | layer averages |
| `r_th_copper_eff`, `r_th_vias_eff`, `heat_flux` | - | yes | - |
| `T_grid`, `T_history`, `zone_polys`, `iterations`, `converged` | - | - | yes |
| `avg_temp_per_layer`, `dx`, `dy`, `width`, `height` | - | - | yes |

---

## 6. Validation experiments

Date 2026-10-16. Board 100x100 mm, 2 layers with a full copper plane on each,
$t_{pcb}$=1.6 mm, 35 µm copper, $k_{Cu}$=385, $k_{FR4}$=0.3, $T_{amb}$=25 °C, $h_{top}$=10,
$h_{bot}$=15, $h$=10 W/m²K, 5 W heater of 20x20 mm in the centre of layer 1.

The reference ("direct") is a sparse direct solve (`scipy.sparse.linalg.spsolve`) of the
**same** linear system the SOR iterates on, built from the solver's own conductance
arrays. It isolates numerical error from modelling error.

### 6.1 Solver comparison

| Model | $T_{max}$ [°C] | $R_\theta$ [K/W] |
| :-- | --: | --: |
| Analytic, Basic | 1002.6 | 195.5 |
| Analytic, Advanced | 24466.1 | 4888.2 |
| Lumped, Basic | 77.7 | 10.5 |
| Lumped, Advanced | 1341.7 | 263.3 |
| FDM, dx = 2 mm (SOR, tol 0.01) | 90.0 | 13.0 |
| FDM, direct solve of the same system | 92.4 | 13.5 |

Physical sanity bound: even with perfect spreading the board would rise by
$P/((h_{top}+h_{bot})A)=5/(25\cdot0.01)=20$ K, so $T_{max}\ge45$ °C. Anything near 1000 °C
for 5 W on a 100x100 mm board is not credible.

### 6.2 SOR convergence versus direct solve (FDM, dx = 2 mm)

| tolerance | omega | iterations | SOR $T_{max}$ | direct $T_{max}$ | max error [K] | heat out / in |
| --: | --: | --: | --: | --: | --: | --: |
| 0.01 | 1.5 | 386 | 90.04 | 92.40 | 2.66 | 0.883 |
| 0.01 | 1.9 | 118 | 92.26 | 92.40 | 0.41 | 0.992 |
| 0.001 | 1.5 | 796 | 92.16 | 92.40 | 0.27 | 0.988 |
| 0.001 | 1.9 | 170 | 92.39 | 92.40 | 0.04 | 0.999 |

Weak coupling case (200x200 mm board, $h_{top}=h_{bot}=h=2$, 1 W, dx = 2, tol 0.01,
omega 1.5): the solver reports `converged=True` after 183 sweeps, with
$T_{max}=39.39$ °C against 46.48 °C from the direct solve (error 7.1 K) and only
**15 %** of the input power leaving through convection.

### 6.3 Heater power versus grid (FDM, 20x20 mm heater, 5 W requested)

| dx [mm] | power inserted [W] | $T_{max}$ [°C] |
| --: | --: | --: |
| 10 | 1.385 | 58.6 |
| 5 | 3.116 | 76.3 |
| 2.5 | 4.242 | 86.1 |
| 2 | 4.488 | 87.6 |
| 1 | 5.000 | 85.2 |

A 4x4 mm, 5 W heater at dx = 10 mm contains no node: inserted power 0 W, $T_{max}=T_{amb}$.

### 6.4 Missing copper

Same board with no Zone drawn: $T_{max}=548$ °C (heat can only leave through the heater's
own node and the vertical FR4 path).

---

## 7. Review findings and what is correct

### 7.1 FDM numerical issues

1. **Premature convergence.** The criterion is $\max|\delta|<tol$ per sweep. For SOR the
   remaining error is roughly $\max|\delta|/(1-\rho)$, where $\rho$ is the spectral radius
   of the iteration. When the board is weakly coupled to ambient ($G_{conv}\ll G_{lateral}$
   by a factor of 1000 or more, as here) $\rho\to1$ and a small step hides a large error
   (table 6.2). Use the residual $\lVert \mathbf{A}\mathbf T-\mathbf b\rVert$, the global
   power balance, or a direct/CG solver.
2. **Non-conserved heater power** (6.3): nodes are counted, the heater area is not
   integrated exactly. Fix by distributing the requested $P_h$ over the covered nodes
   (weights proportional to node count or to overlapped area).
3. **Fallback import error** (7.3).

### 7.2 Analytic and Lumped modelling issues

1. **Analytic conduction term is dimensionally inconsistent.**
   $R=L/(k\,A_{eff}\,t)$ has units K/(W m). For lateral conduction through a copper sheet the
   cross-section is thickness times width: $R=L/(k\,t\,w)$. Using it makes $R_{cond}$ about 185 K/W
   here, which dominates the result.
2. **Advanced modes use the heater (or heater + via) footprint as the convective area.**
   Heat does not stay under the heater; it spreads. This makes the area, and hence the
   convection resistance, tiny and the temperature enormous. A correct treatment
   would use a spreading resistance (section 8) plus convection over the whole board.
3. **Lumped network structure.** Series elements are summed and divided by $(1+n_v)$; the
   via resistance $R_{via}$ is not in the network; the copper resistance uses the whole
   board thickness with $k_{Cu}$ (copper is 35 µm thick and conducts laterally); one FR4
   resistance is used for any number of layers; and $T_{top}$ may exceed $T_{max}$.
4. **Temperatures** $T_{avg}$ (Analytic: midpoint) and $T_{inner}$ (Lumped: $/N$) are heuristics
   without a derivation.
5. **Both models ignore `h_top`/`h_bottom`**, and neither can see heater position, layer
   or sinks.

### 7.3 Software issues

- `core/fdm_solver.py` cannot be imported without Numba: the annotations
  `float64[:,:,:]` are evaluated when the function is defined, raising `NameError`.
  The pure-Python fallback is therefore unreachable, and `use_numba` branches in
  `_run_sor_simulation` are identical.
- Solvers call `print()` and import `wx` and `matplotlib` for result dialogs, so numerics cannot be
  tested headless without stubbing those modules.
- Rasterisation (`_process_elements`, `_analyze_zone_temps`) uses nested Python loops over
  nodes and polygons: $O(n_x n_y \cdot \text{elements} \cdot \text{vertices})$.
- `hotspot_threshold` default differs between solver (85) and `config.py` (100).

### 7.4 FDM modelling simplifications

- Border nodes carry a full cell for convection, power and conduction; a node-centred
  scheme should give border nodes half a cell (corners a quarter). Total convective
  area becomes $(W+\Delta x)(H+\Delta y)$ instead of $W H$.
- No lateral conduction through FR4. Typical values: copper layer
  $k_{Cu}t_{Cu}=385\cdot35\,\mu\mathrm m\approx0.0135$ W/K per square; FR4 core
  $k_{FR4}t=0.3\cdot1.6\,\mathrm{mm}\approx0.00048$ W/K per square. The FR4 sheet is about 28 times
  weaker but not zero, and matters wherever copper is absent.
- All layers use the same copper thickness (real boards: outer 35 µm, inner 17.5 µm or other).
- Vias are solid rods. A plated via is a hollow tube; with a plating thickness $t_p$:

$$
A_{via} = \pi\left[\left(\tfrac d2\right)^2-\left(\tfrac d2 - t_p\right)^2\right]
\quad\text{e.g. } d=0.3,\ t_p=0.025 \Rightarrow 0.0215\ \mathrm{mm^2}
$$

  versus the solid area 0.0707 mm² used now. The config already defines
  `DEFAULT_VIA_PLATING_THICKNESS` = 0.025 mm but the solver never reads it.
- Sinks on inner layers are silently ignored.
- The "time evolution" GIF is the SOR iteration history, not physical time (7.5).

### 7.5 What is correct

- Using a 2D copper sheet per layer with vertical dielectric links is the standard
  approach (Electronics Cooling, PLOS One four-layer model).
- The copper sheet conductances $k\,t\,\Delta y/\Delta x$ and the FR4 link $k\,A/\Delta z$ are the right finite-difference
  expressions; the node equation is the right energy balance; the matrix is SPD.
- SOR with in-place sweeps is a valid algorithm; the issues are the stop rule and the
  fixed $\omega$.
- The default combined $h=10$ to $15$ W/(m² K) is in the usual range (natural
  convection plus radiation, 10 to 12 W/(m² K)).
- Reporting $R_\theta=\Delta T_{max}/P$ for FDM follows the common definition.
- Shoelace areas, ray casting, and unit conversions are implemented correctly.

---

## 8. Literature and external references

| Topic | Source | Use for this project |
| :-- | :-- | :-- |
| Copper layers as 2D meshes with dielectric links and via resistors | [Modeling Heat Conduction in PCBs Using FEA](https://www.electronics-cooling.com/2004/05/modeling-heat-conduction-in-printed-circuit-boards-using-finite-element-analysis/) | confirms the FDM architecture |
| Limits of volume-weighted effective conductivity | [The Problem with Effective Thermal Conductivity](https://www.electronics-cooling.com/2017/04/problem-effective-thermal-conductivity/) | why Analytic/Lumped averages are not reliable; recommends bitmap conductance and FDM as reference |
| Four-layer PCB steady-state model, 1.8 to 2.5 % vs COMSOL, 4 to 5 % vs experiment | [PLOS One 2024](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0310237) | benchmark for validating FDM; $h$=10 W/m²K assumed |
| Spreading resistance closed form (Lee, Song, Au, Moran), -1.2 to +3.9 % for square geometry | [Simple formulas for spreading resistance](https://www.electronics-cooling.com/2004/05/simple-formulas-for-estimating-thermal-spreading-resistance/) | replacement for the Analytic model |
| Via thermal resistance, hollow tube, pad constriction, pitch interaction | [Thermal Modeling of PCB Vias and Pads (Cambridge)](https://tenglong.eng.cam.ac.uk/files/thermalmodelinganddesignoptimizationofpcbviasandpads.pdf) | improved via model for Lumped and FDM |
| Radiation share of PCB cooling | [Don't underestimate radiation](https://www.electronics-cooling.com/2001/02/dont-underestimate-radiation-in-electronic-cooling/) | radiative $h_r\approx6$ W/(m² K) near 50 °C, comparable to natural convection |
| SOR optimal factor and error estimate from step size | Young's theorem; $\lVert x-x_k\rVert\le\frac{\rho}{1-\rho}\lVert x_k-x_{k-1}\rVert$ | stop rule and $\omega$ choice |
| Open-source similar tools | [TemperatureFDM](https://github.com/slehmann1/TemperatureFDM), [pcb-sim-toolkit](https://github.com/mgburr/pcb-sim-toolkit) | 2D explicit FDM / steady-state toolkits for comparison |

Formulas worth remembering for future work:

- Hollow via tube area (above) and through-plane array resistance
  $R_{via\ array}\approx L/(k_{Cu}\,A_{Cu}\,N)$.
- Optimal SOR factor for the Poisson model problem
  $\omega_{opt}=2/(1+\sin(\pi/(n+1)))$.
- Sheet conductance of a copper layer $k_{Cu}t_{Cu}$ [W/K per square] versus FR4 core $k_{FR4}t_{core}$.
- Radiation coefficient $h_r\approx4\varepsilon\sigma T_m^3$ with $T_m$ in kelvin;
  with $\varepsilon\approx0.9$, $T_m=320$ K gives about 6 W/(m² K).

---

## 9. Proposed direction

1. **FDM first** (it is the reference solver): residual/power-balance stop rule or a
   sparse solver; exact heater power; half-cell borders; FR4 lateral conduction;
   plated via area; fix the import; vectorise rasterisation.
2. **Lumped**: rebuild as a real resistor network (per-layer copper, per-interface FR4,
   vias in parallel with FR4, convection top and bottom).
3. **Analytic**: spreading resistance plus convection over the whole board.
4. **Tests**: this document's board as a regression benchmark, checks on power balance
   (out/in = 1.000 within tolerance), grid refinement, and symmetry.
5. **Transient** (later): add $\rho c_p$ per node and implicit time stepping; only then
   show a physical-time animation.

Update this file whenever a model changes (see `CLAUDE.md`).
