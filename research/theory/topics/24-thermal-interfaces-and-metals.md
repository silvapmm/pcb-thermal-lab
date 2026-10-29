# 24. Thermal interfaces and metals: paste, pads and what "perfect contact" means

![Block, metal and interface](../../component-heatsink/figures/fig_04_block_metal_and_interface.png)

*Figure 4 of `research/component-heatsink` (`research/component-heatsink/figures/fig_04_block_metal_and_interface.png`): the block, its metal and its interface; the interface is one sheet with its own material and thickness.*

The same figures that show the part and the top path: `research/component-heatsink/figures/fig_05_part_and_top_path_schematic.png` and `fig_01_parts_with_and_without_top_path.png`. Investigation: `research/component-heatsink/README.md` and `NOTES.md` (R2); text in `docs/research.md` R2 and `docs/models.md` sections 15 and 16. **Status: implemented** (presets of metals and interfaces, `pad_thickness`, `pad_k`, contact area); the values are *assumed typical values inside the ranges read*, always editable.

## 1. What it is

Between a heatsink (or a block) and the board or the package there is a layer: paste, grease, a gap pad, an adhesive. The program models it as **one dielectric sheet with its own material and thickness**, hence a resistance per area `R'' = t / k` (K m2/W, quoted as K cm2/W). On a package of area `A` the resistance is `R'' / A` in K/W: 0.5 K cm2/W over 3.3 x 3.3 mm is 4.6 K/W.

## 2. The joint

    R_joint = BLT / (k A) + (R''_c1 + R''_c2) / A

the bond line thickness over the bulk conductivity plus a contact resistance at each face (ASTM D5470 fits both from measurements at several thicknesses). The **apparent** conductivity (thickness over measured resistance) is well below the bulk value of the data sheet. Measured totals (round robin of 2014): a paste 0.32 K cm2/W at 300 kPa, a ceramic paste 0.41, a 1.575 mm gap pad 12.1 K cm2/W at 690 kPa.

## 3. The presets (resistance per area, with the apparent `k`)

| Preset | k x t | K cm2/W |
| :-- | :-- | --: |
| good paste | 1.5 W/mK x 50 um | 0.33 |
| **paste, default when unknown** | 2 W/mK x 100 um | 0.5 |
| soft gap pad | 3 x 0.5 mm | 1.7 |
| gap pad | 1 x 0.5 mm | 5 |
| hard gap pad | 1 x 1 mm | 10 |

Metals (typical): aluminium 204 W/mK, copper 386, brass 111, stainless 304 about 14, carbon steel 54 (and the heat capacity for the time simulation).

## 4. What matters and what does not

* **On top of a small package the interface matters** (MOSFET of 2 W with a 12 K/W clip-on heatsink: 68 C with a good paste against 88 C with a hard pad: 10 K cm2/W over 11 mm2 is 92 K/W, far more than the heatsink). The default paste costs 0.1 to 0.6 K against a good paste on the four parts (`research/component-heatsink/README.md` 4.5, table E; `docs/research.md` R2 says 0.6 to 1 K); a gap pad should be typed.
* **Under the board the metal and the interface hardly matter**: aluminium and copper differ by 0.1 K, stainless is 1 K worse, a hard pad 2 K worse; what matters is the block thickness and area and the cooling of its surface (with fins, 1 mm 76.4, 3 mm 73.8, 6 mm 71.2 C, printed by `research/component-heatsink/scripts/study_notes_r2.py`; the 76.8, 74.3, 71.7 C of `docs/research.md` R2 were about 0.5 K high and printed by no script), because the board has spread the heat before the block sees it.
* **Perfect contact** is `R'' = 0.01 K cm2/W` (1e-6 m2K/W): it changes the result by 0.05 K against an ideal zero and is 30 times better than the best measured paste; below 0.003 nothing changes.

## 5. When the datasheet gives only `theta_JB` or `psi_JB`

Three ways, from the least to the most pessimistic (LDO of 1.5 W on a 25 mm pad, true 87.4 C): `psi_JB` with the board temperature of a ring 0.5 to 1.5 mm outside the body, 93.7 C (+6 K); `theta_JB` as the junction-to-pad resistance with the pad and vias drawn, 102.7 C (+15 K), pessimistic because the datasheet's board spreading is counted twice; the same with no copper drawn, where `theta_JB` is the better number. See topic 09.

## 6. Limits

The values come from catalogues and a round robin, not from measurements of this program. Pump-out and ageing of grease are not modelled. The presets are indicative.

## 7. Related topics

09 (the top path), 11 (the block), 13, 25 (contact area and gap), 26.

## 8. Sources

* Metal tables and typical grease and pad values (read by the notes, addresses not recorded): [MetalTables], [GreaseValues]. The joint formula and the measured totals: [ECD5470RoundRobin] (Electronics Cooling, 2014), standard [ASTMD5470] (not read).
* Datasheet routes for `theta_JB`, `psi_JB`: [TI-SPRA953B], [RichtekAN061].
* Own computation: [L-parts].

*What was read and what was not verified:* from `docs/research.md` R2 (read in full); the sources were read by the earlier work, addresses were not recorded.
