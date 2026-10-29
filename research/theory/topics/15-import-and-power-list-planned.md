# 15. Planned: board and power-list import, passive areas, a component library

![Import and power list](../figures/fig_15_import_to_power_planned.png)

*Figure 15 (`figures/fig_15_import_to_power_planned.png`): left, a KiCad board file and a power list (a BOM or CSV with reference, power, theta, tj_max) matched by designator into the problem: board, copper per layer, vias, parts with power; right, passive areas as component types: a cooled area (extra `h`), a contact held at a fixed temperature, a material patch. The component library by part number is planned; a typical theta by package family is already a library of the program (`package_theta`, Preferences).*

The reader that exists on the research branch, and the full chain from the Gerber files to the temperature: `research/gerber-import/figures/fig_17_nets_from_files.png` (nets), `fig_16_outline_how.png` (outline), `research/gerber-models/figures/fig_10_pipeline.png` (the whole chain); the copper mapping is topic 17.

**Status: planned** (`docs/versions.md` "Planned", "Import of copper and parts"); the Gerber reader and the mappings are researched, not in the program.

## 1. KiCad import

`.kicad_pcb` is text (s-expressions): outline, copper zones and tracks per layer, vias with drills, the stack-up table, footprints with reference, position and size. A pure-Python parser needs no KiCad installation. The research branch already reads the file for the nets check (`research/gerber-import/lib/kicad_pcb.py`).

## 2. Gerber and Excellon import

Rasterise the copper per layer on a fine grid and store the copper fill fraction per cell, which is what the FVM already uses; drills with plating become vias; the profile layer gives the outline (topic 20). Limits to state: the fill fraction hides how the copper is connected (topic 17); the layer assignment needs a step in the GUI and a validation against a board also drawn by hand.

## 3. Power list

A CSV or BOM (`reference, power_w, theta, tj_max`) applied to footprints by designator; the power may come from a circuit simulation or a regulator model (`P_out (1/eta - 1)` for a switching converter, `(V_in - V_out) I_out` for an LDO). Parameters in the CAD fields with a **sidecar file** for our settings, so the CAD files are never modified.

## 4. Passive areas and a component library

Component types for a **cooled area** (extra `h`), a **contact to a fixed temperature**, a **material patch**; a library of typical `theta_JC`, `theta_JB`, `psi_JB`, size and mass by family or part number (presets for processors with lid and paste). Probes and tables, export for ParaView or an external 3D check, pass/fail checks with an exit code and a result cache are further ideas of the same section of `docs/versions.md` "Planned".

## 5. Licence rule

FYPA, padne and altium_monkey are AGPL-3.0; the project is MIT. Their ideas and the public file formats are used; **no code is copied** and any import is written independently.

## 6. Related topics

17 (copper to cells), 19 (nets and the current of a net), 20 (outline), 21 (vias), 22 (stack-up), 23 (the calculator).

## 7. Sources

* The ideas and the tools read as summaries: [OpenToolsIdeas]. KiCad format: [KiCadFormat]. Gerber specification (revision 2024.05, read in part by the reviews of `research/gerber-import`: the passages named in its README section 7 and `docs/literature.md`) and the format page: [UcamcoGerber]. Reader and comparison tools: [Gerbonara], [GerberTools].
* Datasheet values and families for the library: [Datasheets], [Microchip-Thermal].
* Own computation: [L-gerber].

*What was read and what was not verified:* the ideas come from web summaries (repositories were not cloned or run); nothing of this is in the program.
