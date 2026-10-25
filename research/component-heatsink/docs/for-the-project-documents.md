# Text for the project documents (review of 2026-10-25)

The review of `research/component-heatsink/` (README section 7) found statements in the program's documents that are stale, contradicted by the tables of the studies or missing. The project documents are not edited on a research branch; this is the text to fold in on the next documents branch off `develop`.

## 1. `docs/theory.md`, section 9: the top path is not described

Add after the power coefficient paragraph:

> **Top path** (a heatsink on the package; `theta_jc_top`, `interface`, `theta_sa`): the part is a junction node joined to the board by `θ` and to the ambient by `R_top = θJC(top) + R''/A + θSA` (`A` the contact area, or the footprint). With `P_b` the heat into the board and `T_max(P_b)` the hottest board point under the footprint,
>
>     Tj − T_amb = (T_max − T_amb) + P_b θ,     P_b = P − (Tj − T_amb)/R_top   ⇒   Tj − T_amb = (T_max − T_amb + P θ)/(1 + θ/R_top)
>
> (`analysis.part_split`; the top heat is limited to `[0, P]`). `T_max` depends on `P_b`, so the board is solved again with the new `P_b` (`api._solve_with_tc`, together with the power coefficient). Linearising `T_max − T_amb = R_b P_b`, the plain iteration has the slope `−R_b/(R_top + θ)`: it converges only when the board's resistance under the part is below `R_top + θ`. On small pads it does not (README 4.11 of the research folder: 17 to 58 K too low on 8 mm pads); until the loop is replaced by a root finder, a result with a top path is not reliable when the board rise under the part per watt exceeds `R_top + θ` (measured: 8 mm pads, ratio 1.3 to 2.4).

(Drop the last sentence once the correction of `research/component-heatsink/INTEGRATION.md` is in the program.)

In the same section, "a junction node joined by a uniform conductance would be 3 K lower" -> "would be 1.3 to 3.4 K lower on the chips of the study (0.2 K on a 0603 resistor)".

## 2. `docs/validation.md`, section 9

* "the FVM, FDM, Lumped and Analytic models agree on `Tj` within 10 % of its rise" -> "the FVM, FDM, Lumped, Analytic and 3D solid models agree on `Tj` within 1.4 % of its rise (`top_path_study.py`; the test asks for 10 %)".
* "(about 3 K above a junction node with a uniform conductance ...)" -> "(1.3 to 3.4 K above a junction node with a uniform conductance on the chips, 0.2 K on the resistor ...)".
* Add a bullet under **Top path**: "The rows hold on a 25 mm pad. On an 8 mm pad the fixed-point loop does not converge (the board under the part resists more than the top path) and reports the junction 17 to 58 K too low with a 'thermal runaway' warning (`research/component-heatsink/scripts/study_top_path_convergence.py`); the LDO row also stopped at 80 iterations, within 0.1 K of the exact root."
* The ψJB route numbers (93.7, 65.1, 102.7 °C) are now printed by `component_study.py` (table E); no change of numbers.

## 3. `docs/research.md` (the same text is in `research/component-heatsink/NOTES.md`, corrected there)

* "A bare mould carries about 1 % of the heat (2 to 4 K); a heatsink takes 41 to 51 % and lowers `Tj` by 16 to 40 K" -> "A bare mould carries about 1 % of the heat (0.4 to 0.8 K against the same junction node without a top path); a heatsink takes 41 to 51 % and lowers `Tj` by 14 to 38 K".
* R2: "The default paste costs only 0.6 to 1 K against a good paste" -> "0.1 to 0.6 K".
* R2: the fin and block-thickness numbers ("71.7 to 72.2 °C", "1 mm 76.8, 3 mm 74.3, 6 mm 71.7 °C with fins") -> "71.2 to 71.8 °C" and "1 mm 76.4, 3 mm 73.8, 6 mm 71.2 °C" (`study_notes_r2.py`); the "perfect contact" table is reproduced unchanged by the same script.
* R5: "the same change on top moves it by 10 to 20 K" -> "by 2.4 to 12 K".
* R6: "(+2.3 K, +4 K at 4 W the other way: 113.9 against 111.1); the same heatsink at 1, 2.5 and 5 m/s gives 65.7, 64.5 and 63.6 °C. The scenarios change `Tj` by 2 to 7 K" -> "(+2.3 K; +2.8 K at 4 W: 113.9 against 111.1); the same heatsink at 1, 2.5 and 5 m/s (catalogue value times the factor, held fixed) gives 64.1, 63.3 and 62.8 °C. The scenarios change `Tj` by 2 to 8 K" (the study scaled the forced values with the rise as in natural convection; corrected).
* R8 table: replace with the values of `research/component-heatsink/README.md` 4.7 (aluminium 1 mm 1.73, 3 mm 0.87; copper 3 mm 0.46; steel 1 mm 6.46, 3 mm 3.28 K/W for the 3.3 mm source; the old values read the first cell centre, up to 30 % low on thick bases), "5 to 13 %" -> "5 to 14 %".
* Two sections are numbered R3 (air flow; a heatsink larger than its contact); renumber one.

## 4. `docs/models.md`, section 6

* "±30 % in θ moves `Tj` by 1 to 3 K for chips" -> "by 0.8 to 3 K for chips" (LDO ±0.8 K).
* In "The top path" paragraph, add: "On a pad much smaller than the heatsink's path (the board under the part resisting more than `R_top + θ`) the current fixed-point loop does not converge; see `theory.md` section 9."

## 5. Library `package_theta` (`pcbthermal/data/defaults.json`)

No change needed: "QFN / exposed pad" keeps `tj_max_c` 150 as a family value; the TPS7A47 itself is rated 125 °C in operation (SBVS204G), which is a datasheet value to type, not a family default. The SMA entry (θ 20 K/W, Tj max 125 °C) follows the SX Semiconductor sheet; the Vishay SS12 gives RθJL 28 K/W and 150 °C: the note could say that the junction-to-terminal value is maker-dependent (20 to 28 K/W).

**Proposal for the `defaults.json` note of the SMA entry** (`package_theta`): "The junction-to-lead resistance of an SMA diode depends on the manufacturer: the SX Semiconductor sheet used here gives 20 K/W, the Vishay SS12 (document 88746) gives RthJL 28 K/W. Take the typical value as a range of 20 to 28 K/W and type the value of your datasheet." The program is not edited here.
