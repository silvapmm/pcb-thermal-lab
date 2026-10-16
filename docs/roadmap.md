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

### 1.3 Design (agreed 2026-10-16)

- **Which models:** all three, because with constant `h` the problem is linear.
  FVM: implicit time stepping (exists, validated). Lumped: the same stepping on each heater's small dense network (capacities from the real cells), heaters superposed.
  Analytic: every cosine mode decays exponentially, so piecewise-constant power has a closed form; vias and sinks are smeared in the transient (documented limit).
  Because the response is linear, one step response (Zth) per heater plus convolution gives any profile quickly (sweeps of duty cycle and frequency).
  With temperature-dependent `h` (section 2) superposition no longer holds: only time stepping.
- **Steady-state models and power:** selectable per run: **average** (default, physical for fast PWM), **peak** (`P_on`, worst-case bound) and, when a step response is available, the **periodic peak** (formula above).
  Results show all three numbers side by side so the bracket is visible.
- **Initial state (selectable):** cold (ambient), uniform temperature `T0` (for example an enclosure at 60 °C), steady state of a chosen baseline power (standby), or the periodic steady state
  (start from the steady state of the average power and iterate cycles until the change per cycle is below a tolerance).
- **Power profile tab** (not "PWM"; simplified in 1.4): a square wave (frequency or period, duty, `P_on`, `P_off`) with the derived average power and an automatic regime decision based on the
  estimated oscillation of the hottest point. Later: a segment table and CSV import.
- **What power is stored (open point, proposal):** store the **physical on-state power `P_on` and the duty** (a MOSFET's conduction loss or an LED's electrical input in the on-state do not
  change when the duty changes), and *derive* the average. A toggle lets the user enter the average instead (then `P_on = P_off + (P_avg − P_off)/D`), with a lock
  "keep `P_on` fixed / keep average fixed" for when the duty is edited. A heater without profile is a constant source (`D = 1`), so existing projects do not change.
  Switching losses of a converter are naturally an *average* contribution (extra average loss field), not part of `P_on`.
- **Limit to document:** switching at kHz to MHz is not resolved; the board responds to variations on the scale of its thermal time constants (hot spot about 19 s on the example board,
  milliseconds only very locally). Microsecond to millisecond events belong to the transient thermal impedance of the part [1, 2, 6].
- **Outputs:** Tmax(t) per heater, peak, minimum, oscillation, time above a limit, Zth(t) curve (with mutual curves between heaters), **peak-envelope map** (maximum over time at every cell), animation.
- **Validation plan:** square wave on the uniform slab against the exact RC solution; periodic peak against the superposition sum; energy balance; steady-state models reproduce the average-power result.

### 1.4 Time scales and the profile editor (refined 2026-10-16)

**Two situations that look alike, and the board treats them differently.** A switching waveform at kHz to MHz (MOSFET, LED PWM dimming at 100 Hz to a few kHz) is far faster than the
board can follow: the board only feels its **average power**. A slow duty cycle (seconds to hours: a fan on 30 s / off 70 s, a motor accelerating and holding, a radio transmitting in
bursts, a charger) is slow enough for the temperature to rise and fall: it must be **resolved in time**. Both are "power versus time" and use the same description (period, duty, on-state power,
off-state power); what differs is what the simulator does with it. So the feature is **not called PWM**: it is a **Power profile**, with an automatic regime decision.

**How fast is "fast" on our board** (example board, hottest point, from the FVM step response):

| t [s] | 1e-4 | 1e-3 | 1e-2 | 0.1 | 1 | 10 | 100 | 1000 |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: |
| Z(t) [K/W] | 0.001 | 0.010 | 0.104 | 0.93 | 3.87 | 6.34 | 9.31 | 11.06 |
| share of Rθ | 0.0 % | 0.1 % | 0.9 % | 8.4 % | 35 % | 57 % | 84 % | 100 % |

Square wave with 10× the nominal power at 10 % duty (average rise 60.8 K), exact periodic response by superposition of `Z(t)`:

| Frequency | Period | Peak rise | Valley rise | Ripple (peak-to-peak) | Ripple / average rise | Decision (tolerance 1 K or 2 %) |
| --: | --: | --: | --: | --: | --: | :-- |
| 100 kHz | 10 µs | 60.81 K | 60.81 | 0.001 K | 0.00 % | average |
| 1 kHz | 1 ms | 60.83 | 60.79 | 0.05 | 0.08 % | average |
| 100 Hz | 10 ms | 61.1 | 61.2 | below the 0.06 K noise floor of this check | about 0 % | average |
| 50 Hz | 20 ms | 62.71 | 61.51 | 1.2 | 2.0 % | average (boundary) |
| 30 Hz | 33 ms | 63.57 | 60.06 | 3.5 | 5.8 % | resolve in time |
| 10 Hz | 0.1 s | 63.5 | 44.95 | 18.6 | 30.5 % | resolve in time |
| 1 Hz | 1 s | 93.4 | 43.7 | 49.7 | 82 % | resolve in time |
| 0.1 Hz | 10 s | 242.1 | 29.8 | 212 | 349 % | resolve in time |
| 0.01 Hz | 100 s | 363.2 | 15.9 | 347 | 571 % | resolve in time |

On this board the boundary is near 50 Hz. It depends on the board (heater size, copper), so the **simulator computes it for the board at hand**: the ripple is obtained from the step response `Z(t)` of
the selected reference model (peak and valley sums as in 1.2, with the tail `D (Rθ − Z(M T))`). The decision rule is *ripple below a tolerance → use the average* (default tolerance: 1 K or 2 % of the average
rise, whichever is larger, user-adjustable).

**Profile editor: simple on purpose (decided 2026-10-16: no waveform designer).** Two kinds of profile in 2.1:

1. **Constant** (default, the present behaviour).
2. **Square wave**, nothing else: frequency or period (unit selector Hz, kHz, ms, s, min), duty (%), power while on `P_on`, power while off `P_off` (default 0).
   Read-only derived values: on-time, average power `P_off + D (P_on − P_off)`, and the **decision text**
   ("Fast: the board only sees the average, oscillation 0.05 °C, using 12.4 W" or "Slow: resolved in time, about N steps, about X s").
   No delay, no rise and fall times, no extra-loss field: edges of milliseconds are invisible to the board (section 1.4 table), a delay is just a different start state, and any
   extra average loss can be added to `P_on` or `P_off` by the user.

Later and only if needed: a table of steps ("power for X seconds", repeated) and CSV import of a measured profile.

Typical uses: LED dimmed at 1 kHz and 30 %, MOSFET at 100 kHz: **fast, average**; fan or heater on/off every few seconds or minutes, motor start-hold-stop, communication bursts: **slow, resolved**.
A short single pulse (microseconds to a few milliseconds) heats the **die**, not the board: that belongs to the component's own transient thermal impedance (section 3), and the tab says so.

**The oscillation threshold.** One setting, in °C: *ignore oscillations smaller than* (default **1.0 °C**). The simulator estimates the peak-to-peak oscillation of the hottest point
(from the step response, section 1.2). If it is below the threshold the waveform is replaced by its average (exact to within that error, and instant); otherwise the cycle is simulated in time.
No percentages: the threshold is a temperature the user cares about. Temperatures and temperature differences are shown in **°C** everywhere in the application and the reports; thermal resistance is shown in **°C/W** (identical to K/W).

**Per heater:** every heater has its own profile (different periods are fine: the response is the sum of each heater's contribution). The steady-state models use, per run, the average (default), the peak `P_on`
(worst-case bound) or the periodic peak (from `Z(t)`).

### 1.5 Duration, start state and cost

Two different "how long" questions:

**Simulated time (how much of the profile is simulated).** Setting *Duration*, derived from the profile and the board, three choices:
- **Until stable** (default for a square wave): cycle after cycle until the peak temperature changes by less than 0.1 °C between two consecutive cycles (cap: 100 cycles).
  Starting from the steady state of the average power this takes about 5 to 12 cycles (measured), because the mean of a periodic response equals the average-power steady state and only the oscillating part has to settle.
- **N cycles**: a fixed number of periods.
- **Fixed time**: seconds (the choice for heat-up from cold, where the board needs several of its time constants, hundreds of seconds on the example board).

**Computing time (how long the run takes).** The time step is automatic: about one tenth of the shorter of the on-time and the off-time (the implicit Crank-Nicolson scheme is stable at any step, so the step
only has to resolve the waveform), with one matrix factorisation per run. Measured on the example board (FVM, one step of the 4-layer board):

| Cell size | Unknowns | Factorise once | One step | Steps per second |
| --: | --: | --: | --: | --: |
| 2 mm | 8 000 | 0.03 s | 0.8 ms | 1 300 |
| 1 mm | 32 000 | 0.23 s | 5.7 ms | 176 |
| 0.5 mm | 128 000 | 2.0 s | 29.6 ms | 34 |

Examples at 1 mm cells: period 10 s, duty 10 %, 12 cycles (120 s simulated, step 0.1 s, 1 200 steps): about 7 s; period 60 s, duty 50 %, 6 cycles (step 3 s, 120 steps): about 1 s;
50 Hz, 12 cycles (0.24 s, step 2 ms, 120 steps): about 1 s. The Lumped model needs milliseconds and the Analytic model microseconds per evaluation. The editor shows the estimated number of steps and time before running and
refuses runs above a cap (default 200 000 steps), suggesting the average instead.

**Start state (setting *Start from*):** *average steady state* (default for a square wave), *ambient* (cold start), *a fixed temperature T0 in °C* (for example an enclosure at 60 °C), or *the steady state of a chosen power* (standby).
Results report the last cycle (peak, minimum, oscillation) and, when starting from cold, the heat-up curve; the animation shows the last cycles.

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
