# Calculators

The auxiliary tools of the program that answer a question with a few numbers instead of a simulation of a whole board. Today there is one, the **Power calculator** (Simulation menu); this file documents what it does, which formulas and parameters it uses, how it was validated, what it cannot do, and the sources. A new calculator gets its own section here.

## 1. Power calculator: the watts a part dissipates, from a temperature you measured

**The question.** You measured a temperature on a board (a thermocouple next to a part, a sense diode in it, an infrared reading of its top) and you want to know how many watts that part dissipates. It is the simulation run backwards. Code: `pcbthermal/inverse.py` (the maths), `pcbthermal/gui/calculator.py` (the window), `pcbthermal/jobs.py` (the calculation runs in the separate process, so the window never freezes).

### 1.1 Route 1: from the drawn board

**Idea.** For fixed heat transfer coefficients the board problem is linear: the temperature of any point is `T(P) = T(0) + R·P`, where `T(0)` is the temperature caused by the *other* heaters and `R` (kelvin per watt) is the **board resistance seen by that point**. So the power that reproduces your measurement is

```
P = (T_measured − T(0)) / R          R = (T(P_run) − T(0)) / P_run
```

and two model runs (the part at 0 W and at any `P_run`) give `T(0)` and `R`; a third run checks the answer. With computed convection (the coefficients grow with temperature) the relation is not linear and a secant iteration finishes it (a few more runs). One last run reports what the model reads at the power found.

**What the copper does.** The program does not "see" the heat in the copper. The copper, the vias, the stack-up and the air decide `R`, how many kelvin each watt raises at the point you measured: a plane under the part spreads the heat, `R` is small and the same temperature means more watts; a bare board has a large `R` and the same temperature means fewer watts. That is why the board you draw must be the real one, and why the result window shows `R`.

**Where the measurement is taken** (the *Measured at* list; each option has a hint in the window):

| Point | What it is | Needs | Typical use |
| :-- | :-- | :-- | :-- |
| Board ring (1 mm around the part) | board temperature 0.5 to 1.5 mm outside the package: the point where the datasheet's ψJB takes the board temperature | nothing from the datasheet | thermocouple taped on the copper next to the part |
| Hottest board point under the part | maximum board temperature under the footprint | nothing | a probe under the package |
| Mean board temperature under the part | average under the footprint | nothing | comparison with the model's mean |
| Junction | `Tj = T_board,max + θ·P` | θ of the part | a sense diode or the part's own sensor |
| Top of the package | `T_top = Tj − ψJT·P = T_board,max + (θ − ψJT)·P` | θ and ψJT | thermocouple or infrared reading of the case |

**The parameters and where they are.** They are entered in the calculator itself, not elsewhere, and only the ones the chosen point needs appear:
* **θ junction-to-pad** (K/W): the datasheet's junction-to-case (bottom or exposed pad), junction-to-lead or junction-to-solder-point resistance; never θJA. It starts at the value in the part's Properties and the number typed in the calculator is used for that calculation only. The convention is the program's worst case: all the power enters the board, and the junction is `θ·P` above the hottest board point under the part.
* **ψJT** (K/W): the datasheet's junction-to-top characterisation parameter, `Tj − Ttop = ψJT·P`. It is not a resistance (only part of the heat flows through the top) and belongs to the datasheet's test board.
* **Ambient**: the air temperature at the time of the measurement.

The result window gives the power, the temperatures the model reads at that power (hottest board point, ring, junction, top), and the board resistance `R` at the measured point. *Use as the power of this part* writes the power into the heater.

### 1.2 Route 2: from a datasheet parameter

`P = (Tj − T_reference) / parameter`, for a known junction temperature, with the reference point and the parameter of the same definition: ψJB (board 1 mm from the package), ψJT (top of the case) or θ. It uses no board model, so it is exact only on the datasheet's own board.

### 1.3 The shortcut that is not offered

From the definitions `Tj − Ta = θJA·P` and `Tj − Ttop = ψJT·P` follows `P = (Ttop − Ta)/(θJA − ψJT)`. It was not found stated in any datasheet read, its denominator is a difference of two similar numbers, and θJA belongs to the JEDEC board, not to yours. With a θJA 30 % below or above the real board's it gives +50 % or −25 % (table 2.2), so it is not offered.

## 2. Validation

### 2.1 Against datasheets (`examples/calculator_validation.py`, `tests/test_calculator_validation.py`)

A datasheet gives RθJA for a *stated* board. Built in the program, that board must return the datasheet's thermal resistance: the calculator must give 1 W when the junction is `RθJA` above ambient. Computed natural convection and radiation, horizontal board, still air.

| Case | datasheet RθJA (K/W) | model RθJA (K/W) | power returned for 1 W | error |
| :-- | --: | --: | --: | --: |
| TI CSD17308Q3 on its datasheet board (38.1 × 38.1 mm, 1.52 mm FR-4, 71 µm copper, 1 in² pad), RθJA typical | 46 | 46.8 | 0.983 W | −1.7 % |
| JESD51-7 2s2p board, exposed-pad QFN with 9 thermal vias (TPS7A47-like, **package data assumed**) | 32.5 | 31.6 | 1.030 W | +3.0 % |
| the same, measured on the top with ψJT 0.3 K/W | 32.5 | 31.5 | 1.030 W | +3.0 % |
| the same JEDEC board **without** the thermal vias | - | 67.4 | (0.48 W) | the exposed pad needs the vias (JESD51-5) |

* The CSD17308Q3 datasheet also gives 58 K/W as a *maximum* and 165 K/W for the minimum pad (also a maximum). A maximum covers the spread of parts and boards, not this board, so it is not a target (the model gives 45.7 K/W when the junction is 58 K above ambient because the computed convection improves with temperature). The pad of the minimum-pad case is not stated, so that case cannot be built.
* The JEDEC 2s2p board follows ROHM application note 64AN113E (JESD51-3/5/7/9/10): 114.3 × 76.2 × 1.6 mm, 70 µm top and bottom traces, two 74.2 × 74.2 mm planes of 35 µm, thermal vias Ø0.30 mm at 1.2 mm pitch. The traces are not drawn. The TPS7A47 values used (RθJA 32.5, θJC(bot) 1.7, ψJT 0.3 K/W) are from its datasheet; the 5 × 5 mm body, the 3.15 mm pad and the 3 × 3 via array are assumptions, so this row is an indication (−3 %), not a proof.
* The ψJT row only checks that the top-of-package point is consistent with the junction point; the model has no top path in the JEDEC case, so ψJT cannot be predicted (that needs the junction node of the roadmap).
* Tests: the three rows above with tolerances of 3 % (CSD17308Q3) and 5 % (JEDEC), and the factor of about two for the missing vias.

### 2.2 Sensitivity to the board and to the data (`examples/power_from_top_study.py`, `docs/validation.md` section 19)

Part of 2 W, θ = 6 K/W, ψJT = 2 K/W on the example board; the top reading is made on the real board and the power is recovered on a drawn board that differs:

| What differs between the drawn board and the real one | recovered power (W) | error |
| :-- | --: | --: |
| nothing | 2.000 | 0.0 % |
| top copper half filled (hatched) | 1.735 | −13.2 % |
| copper 17.5 µm instead of 35 µm | 1.519 | −24.1 % |
| no inner planes | 1.312 | −34.4 % |
| no top copper pad | 1.100 | −45.0 % |
| no vias under the part | 1.780 | −11.0 % |
| heat transfer coefficients +30 % / −30 % | 2.126 / 1.818 | +6.3 % / −9.1 % |
| θ +20 % / −20 % | 1.873 / 2.145 | −6.3 % / +7.3 % |
| ψJT 1 / 3 K/W instead of 2 | 1.893 / 2.119 | −5.3 % / +6.0 % |
| measured top temperature 3 K low / high | 1.831 / 2.169 | −8.5 % / +8.5 % |
| datasheet shortcut with θJA 30 % below / above the board's (19.7 K/W) | 3.002 / 1.499 | +50.1 % / −25.0 % |

**Reading it.** On the datasheet's own board the calculator is within 2 to 3 % (table 2.1); the large deltas appear only when the drawn board is not the real one. The copper dominates (11 to 45 % for a wrong copper, planes or vias), the heat transfer, θ, ψJT and a 3 K measurement error each move the answer by 5 to 9 %.

### 2.3 Self-consistency (`tests/test_inverse.py`)

On a known board the model's own temperature at every point (max, mean, ring, junction, top) gives back the power within 0.1 %, with constant and with computed heat transfer coefficients; a part without θ is refused for the junction and the top; a board with less copper gives a lower power for the same top temperature; a larger ψJT gives a larger power.

## 3. Limits

* It is only as good as the drawn board (copper, vias, stack-up, air) and the measurement: a thermocouple that touches the board cools it a little and an infrared spot is too large for a small part; the emissivity of a package top is about 0.9 and of bare copper 0.05 to 0.1.
* The board is solved in steady state with constant power; a time-varying part is not covered.
* The top of the package is taken as `Tj − ψJT·P`; the program has no top path model in this calculator (the heat is assumed to go into the board), so with a heatsink on the package use the part's θSA fields and the simulation, not this route.
* ψJT, ψJB and θ come from the datasheet's board and are estimates on yours (ψJB within about 15 % of θJB).

## 4. Reproduce

```sh
.venv/bin/python examples/calculator_validation.py     # table 2.1
.venv/bin/python examples/power_from_top_study.py       # table 2.2
.venv/bin/python -m pytest -q tests/test_calculator_validation.py tests/test_inverse.py
```

## 5. Sources

1. Texas Instruments, *Semiconductor and IC Package Thermal Metrics*, SPRA953B, https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/171/4745.TI_5F00_PackageThermalMetrics_5F00_spra953b.pdf (definitions of θJC, θJB, ψJT, ψJB; ψJT to get Tj from a measured case temperature).
2. Renesas, *Thermal Characterization of Packaged Semiconductor Devices*, https://www.renesas.com/en/document/whp/thermal-characterization-packaged-semiconductor-devices; Richtek, AN061, https://www.richtek.com/Design%20Support/Technical%20Document/AN061?sc_lang=en (the ψJB and ψJT estimates and their measured check).
3. ROHM, *Thermal resistance and thermal characterization parameter*, 64AN113E, https://fscdn.rohm.com/en/products/databook/applinote/ic/power/switching_regulator/thermal_resistance_appli-e.pdf (JEDEC test boards: 114.3 × 76.2 mm, 70 µm traces, 74.2 mm planes of 35 µm, thermal vias Ø0.30 mm at 1.2 mm pitch); ROHM, *θJA and ψJT*, 65AN114E, https://fscdn.rohm.com/en/products/databook/applinote/common/theta_ja_and_psi_jt_an-e.pdf (why θJA and ψJT change in other applications).
4. Texas Instruments, CSD17308Q3 datasheet (SLPS262C), https://www.ti.com/lit/ds/symlink/csd17308q3.pdf (RθJC 4.5, RθJA 46 typical and 58 maximum on 1 in² of 2 oz copper); TPS7A47 datasheet, https://www.ti.com/lit/ds/symlink/tps7a47.pdf (RθJA 32.5, θJC(bot) 1.7, ψJT 0.3, ψJB 11.9 K/W).
5. JEDEC JESD51 family (JESD51-2A still air, -3 low-k board, -5 thermal vias, -7 high-k 2s2p board, -9, -10, -12): as summarised in Electronics Cooling, *JEDEC Thermal Standards: Developing a Common Understanding* (2019), https://www.electronics-cooling.com/2019/11/jedec-thermal-standards-developing-a-common-understanding/ (the standards themselves were not read).
6. Microchip, *Thermal parameters of an IC*, https://support.microchip.com/s/article/Thermal-parameters-of-an-IC; Texas Instruments, SLRR012 one-page thermal reference, http://www.ti.com/lit/pdf/SLRR012.
