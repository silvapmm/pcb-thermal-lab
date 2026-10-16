# Roadmap and Design Notes (next version: 2.1.0)

Status 2026-10-16: version 2.0.0 is released. Work for 2.1.0 happens on `feature/more-models`. This file records the design discussions, the
evidence gathered and the decisions taken, so that implementation can start from here. Items are in the agreed order.
References are listed at the end; claims taken from the literature are marked with the source number, the rest are our own derivations or measurements.

## 1. Variable power: profiles, PWM, pulses (next to implement)

### 1.1 Why it matters (measured)

Same average power, same board (example board, 4 W + 1.5 W scaled together; 10× power for 10 % of every 10 s):

| Quantity | Value |
| :-- | --: |
| Steady state with the average power | 85.8 °C |
| Steady state if the pulse power were continuous (upper bound) | 633.1 °C |
| Periodic-steady-state peak at the end of a pulse (simulated) | 262.7 °C |

The steady-state models alone would call this board safe at 86 °C while it peaks near 263 °C.

### 1.2 Peak-temperature formulas (verified against our solver)

Linear time-invariant response: with `Z(t)` the step response of the hottest point (K/W of total power), `Rth = Z(∞)`, period `T`, pulse width `tp = D·T`
and on-state power `P_on`, the peak at the end of a pulse in periodic steady state is, by superposition,

`ΔT_peak = P_on · Σ_{m=0..∞} [ Z(m·T + tp) − Z(m·T) ]`

The datasheet shortcut used by manufacturers [1, 2, 3] is `ΔT_peak ≈ P_on · [ D·Rth + (1 − D)·Z(tp) ]` (the "normalised effective transient thermal impedance"
`D + (1 − D)·z(tp)`), and the average-power result is `P_on · D · Rth`.

| T [s] | D | P_on / P_nominal | simulated, periodic steady state | exact superposition sum | datasheet shortcut | steady, average power | steady, P_on (bound) |
| --: | --: | --: | --: | --: | --: | --: | --: |
| 10 | 0.10 | 10 | 262.7 °C | 267.3 | 278.0 | 85.8 | 633.1 |
| 2 | 0.25 | 4 | 123.9 | 127.6 | 134.7 | 85.8 | 268.3 |
| 60 | 0.50 | 2 | 124.3 | 124.2 | 127.3 | 85.8 | 146.6 |
| 1 | 0.10 | 10 | 117.9 | 118.7 | 131.5 | 85.8 | 633.1 |

Reading: the exact sum agrees with the simulation within 0.1 to 3 % (the remaining difference is time discretisation of the check); the datasheet shortcut is
**conservative by 4 to 11 %**. A cold start overestimates the first cycle (273.5 °C against 262.7 °C converged). Starting from the **steady state of the average power**
the periodic regime is reached in about 5 to 12 cycles, because only the ripple has to settle.
(The exact superposition expressions in the sources [1, 2] could not be read from the PDFs; the sum above was derived and verified numerically here.)

### 1.3 Design (agreed direction)

- **Which models:** all three, because with constant `h` the problem is linear.
  FVM: implicit time stepping (exists, validated). Lumped: the same stepping on each heater's small dense network (capacities from the real cells), heaters superposed.
  Analytic: every cosine mode decays exponentially, so piecewise-constant power has a closed form; vias and sinks are smeared in the transient (documented limit).
  Because the response is linear, one step response (Zth) per heater plus convolution gives any profile quickly (sweeps of duty cycle and frequency).
  With temperature-dependent `h` (section 2) superposition no longer holds: only time stepping.
- **Steady-state models and power:** selectable per run: **average** (default, physical for fast PWM), **peak** (`P_on`, worst-case bound) and, when a step response is available, the **periodic peak** (formula above).
  Results show all three numbers side by side so the bracket is visible.
- **Initial state (selectable):** cold (ambient), uniform temperature `T0` (for example an enclosure at 60 °C), steady state of a chosen baseline power (standby), or the periodic steady state
  (start from the steady state of the average power and iterate cycles until the change per cycle is below a tolerance).
- **PWM simulator tab:** frequency (or period), duty cycle, on-state power `P_on`, off-state power `P_off` (default 0), delay, rise and fall times. It shows the waveform and the derived
  average power `P_off + D (P_on − P_off)`, peak power, energy per period and a **regime indicator** comparing the period with the footprint's thermal time constant:
  period much shorter than the time constant → the board sees the average and time stepping is not needed (ripple estimate shown);
  comparable or longer → the pulses are resolved. Later: CSV import of a measured profile; a segment table ("power for X seconds, repeat N times").
- **What power is stored (open point, proposal):** store the **physical on-state power `P_on` and the duty** (a MOSFET's conduction loss or an LED's electrical input in the on-state do not
  change when the duty changes), and *derive* the average. A toggle lets the user enter the average instead (then `P_on = P_off + (P_avg − P_off)/D`), with a lock
  "keep `P_on` fixed / keep average fixed" for when the duty is edited. A heater without profile is a constant source (`D = 1`), so existing projects do not change.
  Switching losses of a converter are naturally an *average* contribution (extra average loss field), not part of `P_on`.
- **Limit to document:** switching at kHz to MHz is not resolved; the board responds to variations on the scale of its thermal time constants (hot spot about 19 s on the example board,
  milliseconds only very locally). Microsecond to millisecond events belong to the transient thermal impedance of the part [1, 2, 6].
- **Outputs:** Tmax(t) per heater, peak, minimum, ripple, time above a limit, Zth(t) curve (with mutual curves between heaters), **peak-envelope map** (maximum over time at every cell), animation.
- **Validation plan:** square wave on the uniform slab against the exact RC solution; periodic peak against the superposition sum; energy balance; steady-state models reproduce the average-power result.

## 2. Computed convection and radiation (`h` not typed by the user)

### 2.1 Idea and evidence

The user keeps the option of typing `h` (manual) and gains a **computed** option. `h` depends on the surface temperature, orientation, size, emissivity and air speed, so it is computed per cell from the
current temperature and iterated (Picard) on the same matrices. Prototype on the example board: `h` top 14.1 W/m²K at the hot spot, 11.7 average; bottom 9.1 (against 15 typed);
the temperature rise changed by **+6 %** (89.4 °C against 85.8 °C).

### 2.2 Correlations (isothermal plates, air)

- Rayleigh number `Ra = g β ΔT L³ / (ν α)`, `β = 1/T_film`, air properties at `T_film = (T_s + T_amb)/2`, `L = A/P` (area over perimeter) for horizontal plates [4, 5].
- Hot surface facing up: `Nu = 0.54 Ra^(1/4)` for 10⁴ ≤ Ra ≤ 10⁷, `Nu = 0.15 Ra^(1/3)` for 10⁷ ≤ Ra ≤ 10¹¹; facing down: `Nu = 0.27 Ra^(1/4)` for 10⁵ ≤ Ra ≤ 10¹⁰ [4, 5].
- Vertical plate (Churchill-Chu, laminar): `Nu = 0.68 + 0.670 Ra^(1/4) / [1 + (0.492/Pr)^(9/16)]^(4/9)` for Ra ≤ 10⁹, and the full-range form [4].
- Forced flow over a flat plate: laminar `Nu_L = 0.664 Re_L^(1/2) Pr^(1/3)` [4]; mixed laminar-turbulent and the combination of natural and forced `h` (general textbook practice, to be checked against the source before implementing).
- Radiation, linearised: `h_r = ε σ (T_s² + T_a²)(T_s + T_a)`; about 6 W/m²K near 50 °C, comparable with natural convection [7]. Typical emissivity of solder mask about 0.9 (to be sourced before shipping a default).
- Honest limit: these are isothermal-plate correlations; on a board with a hot spot the local `h` is uncertain by about ±20 to 30 %, so a **calibration multiplier** (fit to a measurement) is part of the design.
- Cooling selector: *manual h* · *still air (computed)* with orientation and emissivity · *forced air at v m/s*. The same model gives `h` for component bodies and heatsinks (section 3).

## 3. Component models (future; the heat source stays a heater for now)

### 3.1 What the current models do and what a part really does

Today a part is a heater: all of its power enters the board under the footprint, and `theta_jb` only adds an offset to the reported junction temperature afterwards.
A real part has the junction (the die) generating the heat, which leaves by **two parallel paths**: downwards through the package pad and solder into the board (resistance junction-to-board, `θJB`), and
upwards through the package top (junction-to-case, `θJC,top`) into the air or a heatsink. The JEDEC two-resistor model (JESD15-3) is exactly this pair of resistances, for single-die packages [8, 9].
The current models cannot represent the top path: they send too much heat into the board (hotter board, hotter junction) and cannot represent a heatsink on the part itself
(a "sink" element only raises `h` on the board surface). Estimate with the reference board (5 W, board resistance 13 K/W, `θJB` 6 K/W):
board only: junction rise 5 × (13 + 6) = 95 K; with a top path of 25 K/W (θJC plus heatsink) the heat splits 57 % board / 43 % top and the junction rises about 54 K (series-parallel estimate, not a measurement).
Limits of the 2R model (one-dimensional heat flow, lowest accuracy of the JEDEC models, DELPHI recommended for higher fidelity) are stated in [8, 9].

### 3.2 Implementation sketch

- **Element `Component`** (fidelity levels, names to be decided, working names *Source* = today's heater, *Pad* = θJB only, *Duo* = θJB + top path, *Duo + Sink*): layer, pad/footprint polygon, power or profile,
  `θJB` (K/W), `θJC,top` (K/W), top cooling (none, a heatsink resistance in K/W, or a surface area exposed to the computed `h`), optional heat capacities and, later, a Foster RC chain of the
  junction-to-case transient impedance (as published by manufacturers [6, 10]) so that package-level pulses are captured. Values are entered by the user; no datasheet numbers are invented.
- **FVM:** one extra unknown `T_j` per component (a dense row over the footprint cells). The footprint cells couple to `T_j` with `G_i = w_i / θJB` (`w_i` coverage weights, `Σ w_i = 1`), `T_j` couples to ambient with
  `G_top = 1 / (θJC,top + R_top)`, and the power is injected at `T_j`. The augmented matrix stays symmetric positive definite. Outputs: `T_j`, `T_case`, power into the board and through the top.
- **Lumped:** `T_j` is a node attached to ring 0 of the heater layer (conductance `1/θJB`) and to ambient (`G_top`); power enters `T_j`.
- **Analytic:** a scalar Woodbury update using the footprint-average modal response already available from the tile machinery: `θ̄_fp = θ̄_0 + g_ff f`, `f = G_b (T_j − θ̄_fp)`, `T_j = (P + G_b θ̄_fp)/(G_b + G_top)`.
- **Backward compatibility:** a heater is the special case `θJB = 0`, `G_top = 0`. The old `theta_jb` post-processing field is superseded.
- **Validation:** limits (θJB → 0 reproduces the heater; G_top → 0 gives heater + offset), exact series-parallel solution on the uniform board, energy balance, power split.
- **Timing:** implement after power profiles and the computed `h` (the `h` model feeds the top surface; the profile model defines the component's power input). Suggested stages:
  (1) Pad and Duo, static, in the three models; (2) top surface and heatsink from the computed `h`; (3) Foster chain for package transients.

## 4. Multigrid solver (optional, low priority)

Measured on the example board (4 layers), seconds per steady solve:

| Unknowns | Sparse direct (current default) | CG, Jacobi | CG, algebraic multigrid (`pyamg`) |
| --: | --: | --: | --: |
| 32 000 | 0.24 | 0.08 | 0.12 |
| 128 000 | 2.3 | 0.6 | 0.7 |
| 262 000 | 4.6 | 2.3 | 2.1 |
| 512 000 | 16.2 | 6.5 | 4.2 |
| 987 000 | not run (memory) | 12.8 | 8.0 |

All agree to 1e-8 K. The gain only appears above about 500 000 unknowns, where the direct solver slows down and needs a lot of memory and multigrid scales almost linearly (`pyamg` stays an optional dependency,
chosen automatically above a threshold). Plain CG already captures most of the benefit for moderate sizes.

## 5. 3D finite elements as an independent validation (not a product feature)

Offline script with `scikit-fem` (installed in the virtual environment for experiments, not in `requirements.txt`): structured hexahedral mesh of the board with graded layers (35 µm copper slabs between FR-4 layers),
anisotropic FR-4, convection on the faces. Compare with the FVM on three reference boards to quantify the error of treating copper as a 2D sheet; validate vias separately with one via on a fine mesh. Output: a short validation report in `docs/`.

## 6. Deferred

Neural-network surrogates (not now); trace Joule heating (IPC-2152 style); reduced-order models (only if transients become too slow); naming of the models (working names Mesh / Network / Fin for FVM / Lumped / Analytic, and Source / Pad / Duo for components, to be decided).

## References

1. Texas Instruments, *Using MOSFET Transient Thermal Impedance Curves in Your Design*, SLUAAT8, https://www.ti.com/lit/pdf/sluaat8 (repetitive pulses, effective normalised impedance `D + (1 − D) z(t)`).
2. Vishay, *Current Rating of Power Semiconductors*, https://www.vishay.com/docs/91419/appnote9.pdf.
3. Infineon, *Dynamic thermal behavior of MOSFETs*, https://www.infineon.com/assets/row/public/documents/24/42/infineon-application-note-dynamic-thermal-behavior-of-mosfets-applicationnotes-en.pdf.
4. Nusselt number correlations (natural convection vertical and horizontal plates, flat-plate forced convection), https://en.wikipedia.org/wiki/Nusselt_number (secondary source quoting the standard textbook correlations).
5. Natural convection from an isothermal plate (MIT DSpace), https://dspace.mit.edu/bitstream/handle/1721.1/148015/thermo-03-00010-v2.pdf.
6. Nexperia, AN11261, *Using RC thermal models* (Foster and Cauer networks), https://mouser.com/pdfDocs/AN11261-3.pdf.
7. Electronics Cooling, *Don't underestimate radiation in electronics cooling*, https://www.electronics-cooling.com/2001/02/dont-underestimate-radiation-in-electronic-cooling/.
8. JEDEC JESD15-3, *Two-Resistor Compact Thermal Model Guideline* (2008), https://www.jedec.org/standards-documents/docs/jesd-15-3 (page not readable by the fetch tool; scope taken from the search summary).
9. ROHM, *Two-resistor model for thermal simulation*, https://fscdn.rohm.com/en/products/databook/applinote/common/two_resistor_model_for_thermal_simulation-e.pdf.
10. Infineon, *Application Note AN 2012-03 (OptiMOS datasheet explanation)*, https://www.infineon.com/assets/row/public/documents/24/42/infineon-mosfet-optimos-datasheet-explanation-applicationnote-en.pdf.
