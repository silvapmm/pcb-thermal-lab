# Unit of a temperature difference: K or degC

Question: in the program, is a temperature difference or rise (dT, margin, rise above ambient, gradient, oscillation) written in K or in degC? Absolute temperatures stay in degC.

Status of the sources: R = opened and read here, S = summary only, M = from memory, N = not obtained.

## 1. Conclusion

**K is the SI-preferred unit for a temperature difference; degC is also accepted and is numerically identical.** Both are correct; the SI brochure states no obligation. The engineering literature is mixed: the older electronics-cooling papers and the datasheets/application notes print degC/W, the newer textbook and papers print K and K/W. The decisive argument for one rule is not authority but ambiguity: "5 degC" can be read as a temperature, "5 K" cannot.

## 2. The standards

| Source (status) | Where | Exact words |
| :-- | :-- | :-- |
| BIPM, *The International System of Units (SI Brochure)*, 9th edition (R: PDF opened, text extracted) | section 2.3.1 "Base units", kelvin, printed p. 129 | "The unit of Celsius temperature is the degree Celsius, symbol degC, which is by definition equal in magnitude to the unit kelvin. A difference or interval of temperature may be expressed in kelvins or in degrees Celsius, the numerical value of the temperature difference being the same in either case. However, the numerical value of a Celsius temperature expressed in degrees Celsius is related to the numerical value of the thermodynamic temperature expressed in kelvins by the relation t/degC = T/K - 273.15" |
| same | Table 4, note (f), printed p. 134 | "The degree Celsius is used to express Celsius temperatures. The numerical value of a temperature difference or temperature interval is the same when expressed in either degrees Celsius or in kelvins." |
| same | section 2.3.4 end, printed p. 136 | "Special care must be taken when expressing temperatures or temperature differences, respectively. A temperature difference of 1 K equals that of 1 degC, but for an absolute temperature the difference of 273.15 K must be taken into account. The unit degree Celsius is only coherent when expressing temperature differences." |
| NIST SP 811 (Thompson and Taylor), chapter 4 (S: page text through a fetch summary; the quotes are the summary's quotation) | 4.1, 4.2.1.1, Table 3 note (f) | "The kelvin and its symbol K are also used to express the value of a temperature interval or a temperature difference"; "An interval or difference of Celsius temperature, however, can be expressed in the unit kelvin"; the numerical value of a temperature difference or interval "is the same" in either unit. |
| 13th CGPM 1967, Resolution 3 (S: quoted in the brochure's history, which was read) | brochure appendix | the unit of thermodynamic temperature and of temperature interval are one and the same; "a temperature interval may also be expressed in degrees Celsius". |
| ISO 80000-5 / ISO 80000-1, IEC 60027, NIST SP 330 (M, N) | not opened (paid or not fetched) | From memory, same content (kelvin for intervals, degC accepted); not relied on. |

The standards therefore give no rule of "must": they allow both and note the numerical value is the same. The only strict point is that degC for a difference is "only coherent" for differences (brochure p. 136), and that a difference should not be read as a temperature.

## 3. Practice in the engineering sources (papers library, `papers/md-final/`, line numbers of the extracted text; page numbers of the print not mapped by the extraction unless stated)

| Source (status R: text read at the lines cited, not the whole work) | Place | Rth / theta | Difference |
| :-- | :-- | :-- | :-- |
| Lienhard, *A Heat Transfer Textbook* 2024 (Lienhard2024) | l. 2743 (section 2.2, "Rt has the dimensions of (K/W)"); Example 1.3, l. 1021 | K/W | `Delta T = ... = 16.67 K`; the temperatures given in degC |
| Muzychka, Yovanovich et al. 2003 to 2006 (Muzychka2003 Part 1, Part 2, 2004 Orthotropic, 2006 EdgeCooling; nomenclature) | l. 74 to 79 | K/W | not printed as a number |
| Teertstra, Yovanovich et al. 1995, 2004, 2006; Yovanovich 2003; Yovanovich, Muzychka, Culham 1999 | nomenclature | K/W | |
| Culham 2007, plate-fin spreading (Culham2007PlateFinSpreading) | Table 4, l. 372; nomenclature l. 432 | K/W | column "theta (K)" |
| Fish 2017 | l. 270, l. 372 | K/W | `Delta T` as a symbol; no degC |
| Soleymani Koohbanani 2016 | l. 264 | K/W | |
| Infineon AN 2012-03 | l. 182 | K/W | `(175-25) K / 1.1 K/W = 136 W`: the difference of two degC temperatures is written in K |
| Culham, Yovanovich 1998 and Yovanovich, Culham, Teertstra 1998 | nomenclature l. 55 | degC/W | |
| Culham, Fourier-series PCB 2000 (CulhamFourier2000) | l. 392 to 393, l. 366, l. 425 | degC/W | table column "Delta T (degC)" |
| Lemczyk 1992; Lee, Lemczyk, Yovanovich 1992 | l. 162, l. 271 | degC/W | |
| Shen and Wang 2019 (vias) | nomenclature l. 124 | degC/W (33 times) and K/W (9) | mixed inside one paper |
| Mondragon 2025; Rodero 2025 (multilayer PCB) | Mondragon l. 252; Rodero l. 878 to 880, table l. 1027 | degC/W | Rodero: "Delta T [degC]" |
| ROHM 65AN114E | l. 100, l. 139 | degC/W | `Delta T_J = ... [degC]` (eq. 2) |
| TI SPRA953B, SLUAAT8, AN2020 | SPRA953B l. 141; AN2020 l. 210 to 212 | degC/W (RthetaJA 40 degC/W) | |
| JEDEC JESD51 series (JESD51-1, -2A, -12; M, N: the standards were not opened) | | From memory the series prints degC/W and "K/W" both; the RthetaJA definition is (Tj - Ta)/P | not relied on |
| Incropera and DeWitt (M, N: not in the library) | | From memory: K for differences and for R_t (K/W), degC for temperatures | not relied on |

Reading: of the 31 sources of the library with a resistance unit, 17 print K/W and 12 print degC/W (Shen and Wang both). The split follows the field and the era: the electronics-cooling group of Yovanovich printed degC/W up to 2000 and K/W from 2003 (Culham 2000 degC/W, Culham 2007 K/W: the same author, both units); the datasheet world (TI, ROHM) prints degC/W; Lienhard and Infineon print K/W. No source prints a gradient in degC/mm in the library (not searched exhaustively).

## 4. What the program writes today (tree: development at 6c225276)

Already in K: every resistance (K/W: `Rtheta`, theta, psi, `r_top`, `stackimpedance`, the model table), m2K/W, W/mK, %/K; the margin (`margin_k`, "margin 3.2 K", warnings "x K above its limit"); the gradient (K/mm, `results_view.py:484`, `display.py`); the contour step (K); the surface/column differences (`signed_fixed(d, 3) K`); the ripple of the heaters in the profile result (`profile_results.py:150`, K); the warnings of `checks.py` ("up to 4 K", "11 K"); `docs/theory.md` 49 (`theta` in "K, degC"), 5 ("theta = T - T_amb is the rise above the ambient").

Written in degC although they are differences:

| Place | Text | Kind |
| :-- | :-- | :-- |
| `pcbthermal/gui/results_view.py:536` | Summary header `"ΔT °C"`  | Tmax minus ambient |
| `pcbthermal/api.py:276` | report table header `ΔT [°C]` | same |
| `pcbthermal/api.py:331` | text table header `dT C` | same |
| `pcbthermal/gui/tips.py:42` | tip of the model table, "dT = Tmax - ambient" (units not printed; the header carries them) | |
| `pcbthermal/api.py:297` and `:306` | profile tables `Oscillation [°C]` | swing (max - min) |
| `pcbthermal/gui/profile_page.py:182` | column `"Osc. °C"` | swing |
| `pcbthermal/gui/profile_page.py:138` and tooltip l. 139 | the threshold spin box " °C" and "Swing, °C, ..." | swing threshold |
| `pcbthermal/gui/profile_results.py:144` and `plots.py:1117` | "oscillation 12.3 °C" (the same line also has "Peak ... °C" as absolute) | swing |
| `pcbthermal/help/index.html:319` | "threshold, default 1 °C" | swing threshold |
| `pcbthermal/profiles.py:93, 148, 149, 158, 206, 301`; `pcbthermal/fvm.py:1149-1150` | comments and docstrings: `threshold_c` "(degC)", "degC/W" for step response and Rth (the printed K/W of the model table is the same quantity) | docstrings |
| `docs/version-comparison.md:2963` | "temperature differences shown in °C" (record of an older version) | history, leave |

Absolute temperatures in degC (correct, no change): Tmax, Tmean, ambient, Tj, Tj max, hotspot limit, `Tj - 25 degC` in the power coefficient formula (a reference temperature), colour bars and axes.

Two small inconsistencies inside the same lines: `api.py:196` prints "column ... peaks at x degC; the surface is +0.003 K" (absolute in degC, difference in K: already the rule below), but the Summary of the same window prints the rise in degC.

## 5. Recommendation for this program (one rule)

**Every temperature difference, rise, margin, swing and gradient is written in K (K/mm, K/W for resistances); every absolute temperature is written in degC.** Reasons: it is the SI-preferred form (brochure p. 129, 134 and 136), the program already does it in the great majority of places (resistances, margins, gradients, warnings, the surface/column differences), it removes the "5 degC: a temperature or a difference" ambiguity that the program's own table has (Tmax degC next to dT degC), and it matches `docs/theory.md`.

Concrete changes (not made: no program edit from this branch):
1. Summary header "ΔT °C" to "ΔT K" (`results_view.py:536`, `api.py:276` as `ΔT [K]`, `api.py:331` as `dT K`). Thus the table reads Tmax degC, Tmean degC, dT K, R K/W.
2. Oscillation, `Osc. °C`, the threshold spin box and its tooltip, "oscillation x degC" in the profile result and in the figure title, the user guide line 319: K. The saved JSON field `threshold_c` keeps its name (a file format; renaming would break files), and the preferences label that names it in a way the user sees changes to K.
3. Docstrings degC/W to K/W in `profiles.py` and `fvm.py`.
4. Tests that match these strings (`tests/test_help.py`, the tests of the report columns, if any) move with the change; the frozen numbers are not touched (a header, not a number).
5. Not a unit problem, no change: "Tj - 25 degC" in the power-coefficient text and every absolute temperature.

The rule in one sentence for the guide: "Temperatures are in degC; differences between temperatures (rise above ambient, margin, swing, gradient) are in K, and a resistance is in K/W; the size of the two units is the same."

## 6. How sure

- That K is SI-preferred and degC is accepted for a difference: sure (brochure read, three passages). The NIST wording is from a summary of the page (S).
- That engineering practice is mixed: sure (31 sources of the library counted by a text search of the extracted files; counts are of occurrences, not of a reading of each paper; the JEDEC standards, Incropera, ISO 80000, IEC were not opened).
- The recommendation (K for differences) is a choice of consistency, not a requirement of any standard; degC for a difference would be equally conformant.

## What was read and what was not verified

R: BIPM SI Brochure 9th edition (the three passages above, text extracted from the PDF; page numbers printed = PDF page minus 2). S: NIST SP 811 chapter 4 (through a summary). R at the cited lines only: the papers of section 3 (library text, counted by search; not each read in full for this question). M: ISO 80000-1/-5, JEDEC JESD51, Incropera, IEC 60027. N: NIST SP 330, IEC 60747. The program places of section 4 come from a text search of `pcbthermal/`, `docs/`, `README.md` on the tree named; places that build a string in a way the search did not match (for example a unit passed through a variable) may be missing.
