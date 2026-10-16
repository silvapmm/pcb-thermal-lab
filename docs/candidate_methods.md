# Candidate Models and Methods Found in the Literature

Compiled on 2026-10-16 from web searches made while designing the new physics core. For each method:
what it is, what it would bring to this project, the effort, and a recommendation. Facts quoted from the
sources are marked with the link; remarks marked *(general knowledge)* come from standard practice and were not
verified in the searches.

Status legend: **Done** = already in `pcbthermal`, **Partly** = a first step exists, **Candidate** = not implemented.

## Summary

| # | Method | What it adds | Status | Effort | Priority |
| :-: | :-- | :-- | :-: | :-: | :-: |
| 1 | Thin-plate fin equation, closed-form (Bessel / cosine series) | exact spreading on uniform boards, fast | **Done** (Analytic model) | - | - |
| 2 | Hollow plated via barrel model | realistic via conductance | **Done** (FVM, Lumped, Analytic) | - | - |
| 3 | Anisotropic FR-4 (in-plane vs through-plane) | lateral heat spreading in the dielectric | **Done** | - | - |
| 4 | Sparse direct / CG solvers, implicit time stepping | exact steady state and stable transients | **Done** | - | - |
| 5 | Lumped thermal networks (LPTN) | fast hot-spot estimates | **Done** (ring networks) | - | - |
| 6 | Junction-to-board resistance of components (JEDEC compact models) | junction temperature per component | **Partly** (`theta_jb`) | S | high |
| 7 | Temperature-dependent h with explicit radiation | no more constant coefficient guess | Candidate | S-M | high |
| 8 | Joule heating of copper traces (IPC-2152 style) | self-heating of tracks, current limits | Candidate | M | medium |
| 9 | Model-order reduction (Krylov) | thousands of fast runs, design sweeps | Candidate | M-L | medium |
| 10 | Multigrid and fast Poisson solvers (DCT, FFT) | very large boards, sub-second solves | Candidate | M | low |
| 11 | 3D finite elements (FEniCSx, Elmer, scikit-fem, FreeFEM) | validation of vias, thick copper, components | Candidate (as reference only) | L | low |
| 12 | Machine-learning surrogates (PINN, physics-driven CNN) | instant layout optimisation | Candidate | L | low |
| 13 | Accurate spreading formulas (Lee, Song, Au, Moran) | closed-form constriction resistance | Candidate (not needed now) | S | low |
| 14 | Explicit finite-difference transients | simple, but conditionally stable | Rejected | - | - |

## 1. Thin-plate fin equation (Done)

A plate thin enough that the two faces have the same temperature obeys a fin equation with the parameter
`α = sqrt(h / (k t))`; the point-source solution uses the modified Bessel functions K0 and K1, and the results
are reported to agree with finite elements within about 1 % in most cases
([Heat Spreading Calculations Using Thermal Circuit Elements](https://www.electronics-cooling.com/?p=390)).
**In this project:** the Analytic model solves the same equation on the rectangle with insulated edges by a double
cosine series, per layer and with vertical coupling. It matches the FVM within 0.05 % on uniform boards.

## 2. Hollow via barrels (Done)

A plated via is a thin copper tube, typically 20 to 35 µm of wall around a hollow core; its conductance is far below
that of a solid rod, and via arrays interact through pad constriction and pitch
([Thermal Modeling and Design Optimization of PCB Vias and Pads](https://tenglong.eng.cam.ac.uk/files/thermalmodelinganddesignoptimizationofpcbviasandpads.pdf);
[thermal via array example](https://dev.to/abc_8b09c7009ee0029b85665/thermal-via-arrays-for-power-electronics-copper-fill-via-in-pad-capping-and-thermal-resistance-3n)).
**In this project:** `A_via = π[(d/2)² − (d/2 − t_p)²]` in all models, with a `filled` option.
**Open:** the pad constriction and pitch interaction of the Cambridge model are not modelled separately; the FVM sees the
constriction only through the copper mesh around the via, which makes Tmax drift by about 1 % with the cell size when via arrays are present.

## 3. Anisotropic FR-4 (Done)

Through-plane conductivity is about 0.29 to 0.34 W/mK and in-plane about 0.8 to 1.06 W/mK
([FR-4 laminates, thermal behaviour](https://researchportal.list.lu/publications/detail/experimental-and-multiscale-numerical-characterization-of-the-temperature-dependent-thermal-behavior-of-fr4-laminates)).
**In this project:** defaults 0.3 and 0.9 W/mK, both editable.

## 4. Matrix solvers and implicit time stepping (Done)

The steady problem is a sparse symmetric positive definite system, so a direct factorisation or conjugate gradients solve it
exactly; implicit schemes are unconditionally stable for any time step, Crank-Nicolson is second order
([Finite volume method for unsteady flow](https://en.wikipedia.org/wiki/Finite_volume_method_for_unsteady_flow)).
**In this project:** `fvm.py` (direct, CG, SOR for comparison; implicit Euler and Crank-Nicolson). Verified against an exact exponential solution.

## 5. Lumped thermal networks (Done)

LPTNs are used for hot-spot approximation in early design; finite elements for verification; researchers developed hybrids that
keep accuracy and speed ([Thermal Modeling of PCB Magnetic Components based on Finite Element 2D Thermal Networks](https://vde-verlag.de/proceedings-en/565822176.html);
[Steady-state temperature calculation tool for multilayer PCBs](https://research.science.eus/documentos/6916ec1dee6cd0098b615763?lang=ca)).
**In this project:** per-heater ring networks aggregated from the real geometry (within about 10 % of the FVM, 1 % on the example board).

## 6. Compact models of components, JEDEC DELPHI (Partly)

Junction-to-ambient resistance depends on the board; the DELPHI compact model (JESD15-4) uses several resistances between nodes
(junction, case top and bottom, leads) and reproduces junction temperatures and fluxes with 1 to 2 % average error
([thermal characterization of active components](https://www.electronics-cooling.com/1999/05/thermal-characterization-of-active-components);
[thermal resistance parameters in datasheets](https://www.diodes.com/tw/design/support/perspective/understanding-thermal-resistance-and-characterization-parameters-in-datasheets)).
**In this project:** a heater has `theta_jb` (K/W); the report adds `T_junction = T_max under the footprint + P · theta_jb`.
**Proposal:** a component library (2R model: θjb and θjc, plus a top-side path), pads as copper contacts, case temperature output.
Effort small, value high for real boards.

## 7. Temperature-dependent h and radiation (Candidate)

A combined coefficient of 10 to 12 W/m²K is standard for natural convection plus radiation, radiation is about 6 W/m²K near 50 °C and comparable to
convection above a ΔT of about 25 °C ([Don't underestimate radiation](https://www.electronics-cooling.com/2001/02/dont-underestimate-radiation-in-electronic-cooling/)).
*(General knowledge)* natural convection scales roughly with ΔT^0.25 and radiation is `ε σ (T⁴ − T∞⁴)`.
**Proposal:** per-cell `h(T)` with a Picard iteration on the existing matrices (each iteration is one sparse solve) and an emissivity per surface.
It makes high-power boards more accurate, with no new solver needed.

## 8. Joule heating of traces (Candidate)

*(General knowledge, not searched)* IPC-2152 gives the temperature rise of a trace versus current, width and copper weight. Heating `I²R(T)` with the
copper resistivity rising with temperature (about +0.39 %/K) couples electrical and thermal problems.
**Proposal:** a "trace" element (polyline, width, current) that becomes a distributed heat source with a few Picard iterations.

## 9. Model-order reduction (Candidate)

Krylov-subspace reduction cuts the cost of PCB thermal simulation, and 3D thermal circuits can be reduced to 2D compact equivalent circuits that run in SPICE
([model reduction for PCB thermal simulation](https://www.tandfonline.com/doi/abs/10.1080/02533839.2000.9670594);
[interconnect model reduction with parameter variation](https://arxiv.org/pdf/2112.03023)).
**Proposal:** a reduced model of the FVM with heater powers and `h` as parameters, for design sweeps and real-time sliders in the GUI.

## 10. Multigrid and fast Poisson solvers (Candidate)

Multigrid solves the Poisson equation in O(N) work ([multigrid on diagonally oriented grids](https://arxiv.org/pdf/math/9907190)); the finite-difference Poisson problem is also solvable
by the discrete cosine transform ([DCT Poisson solver](https://www.mathworks.com/matlabcentral/fileexchange/74162-fast-poisson-equation-solver-using-dct)).
**In this project:** a sparse LU already solves 320 000 cells in 4.6 s and CG in 3.3 s, so multigrid (for example `pyamg`) only pays off beyond about 10⁶ cells.
The DCT idea is what the Analytic model already exploits in the continuous form.

## 11. 3D finite elements as an independent reference (Candidate)

Open-source FEM stacks: FEniCSx (with PETSc and Gmsh), Firedrake, Elmer FEM, FreeFEM and scikit-fem.
**Proposal:** use one of them offline to validate the FVM on thick copper, via fields and components in 3D; not to be shipped with the application.
Related open tools for comparison: [TemperatureFDM](https://github.com/slehmann1/TemperatureFDM) (2D explicit FDM), [pcb-sim-toolkit](https://github.com/mgburr/pcb-sim-toolkit) (2D steady finite differences),
[Thermca](https://github.com/steffenschroe/Thermca) (thermal networks in Python), [PACT](https://github.com/peaclab/PACT) (compact thermal simulator), [TCCbuilder](https://pmc.ncbi.nlm.nih.gov/articles/PMC11700648/).

## 12. Machine-learning surrogates (Candidate)

Physics-informed CNNs learn the map from heat-source layout to the steady temperature field without labelled data
([PI-CNN](https://arxiv.org/pdf/2109.12482)); physics-driven CNNs were used for layout optimisation of heat-conduction plates with particle swarm optimisation
([PD-CNN](https://ar5iv.labs.arxiv.org/html/2201.10002)); physics-informed networks model the transient behaviour of PCBs
([PINN for space systems](https://oa.upm.es/id/eprint/89946)). Thermal neural networks learn lumped-parameter models from data
([Thermal Neural Networks](https://arxiv.org/pdf/2103.16323)).
**Proposal:** only after the FVM can generate thousands of labelled cases quickly (it can); useful for automatic component placement.

## 13. Spreading-resistance formulas of Lee, Song, Au and Moran (Candidate, low value now)

Closed-form constriction/spreading resistance for a source on a plate with convective cooling, reported within -1.2 % to +3.9 % of the exact solution for square geometries
([Simple formulas for estimating thermal spreading resistance](https://www.electronics-cooling.com/2004/05/simple-formulas-for-estimating-thermal-spreading-resistance/)).
The exact coefficients could not be obtained from the searches, and the cosine-series Analytic model already gives the exact solution for the same problem, so this was not implemented.

## 14. Explicit finite-difference transients (Rejected)

Explicit schemes have a stability limit on the time step tied to the cell size and diffusivity, so fine meshes force tiny steps
([same source as item 4](https://en.wikipedia.org/wiki/Finite_volume_method_for_unsteady_flow)). Implicit stepping on the existing matrices is both simpler and unconditionally stable.

## Suggested order

1. Component compact models (item 6) and temperature-dependent `h` with radiation (item 7): small, immediate accuracy for real boards.
2. Transient inputs in the GUI (pulses, duty cycles) on top of the existing implicit solver.
3. Trace Joule heating (item 8).
4. Model-order reduction (item 9) for interactive sweeps, then a surrogate (item 12) if layout optimisation becomes a goal.
