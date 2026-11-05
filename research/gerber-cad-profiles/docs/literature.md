# Literature status of `gerber-cad-profiles`

| Source | Status | What was read |
| :-- | :-- | :-- |
| Ucamco, *The Gerber Layer Format Specification*, revision 2026.05 | R (the passages cited) | `.GenerationSoftware` (page 149), the revision history lines on its version field (revision 2023.08), the attribute grammar, section 3.4.5 "Names" (page 37, read by the review); the rest S |
| Ucamco, *The XNC Format Specification*, 2021 | R (sections 2.4 to 2.8, 3.1 to 3.5 and 4) | attributes written as standard comments `; #@!`; the review read the command overview (no `G93`, no `M71`/`M72`), `M48` on the first header line and the unit command |
| gerbonara `tests/resources` (sparse clone) | R for the files, L for the licences | headers of every file, the README, LICENSE and the three scripts of `zuken-emulated` |
| gerbonara `layer_rules.py`, `layers.py` (installed package) | R | the generator guess by names and header regexes, used by the review as an independent reference (README 10.2) |
| 48 public repositories (`scripts/fetch_manifest.py`) | R for the files read | headers of every file; licences from the GitHub API |
| ODB++ specification | **N** (confidential; not copied) | only the fields of a real KiCad 9.0.3 `misc/info` and `matrix/matrix` |
| IPC-2581, IPC-D-356 | N for IPC-2581; IPC-D-356 headers of Allegro and UcamX files seen | no IPC-2581 file obtained |
| Vendor documentation (Siemens, Zuken, Altium, Cadence, Autodesk, Labcenter, Pulsonix, DipTrace) | **N** | no manual or help page of any tool opened; every statement about a tool is from its files |

Entries added to `research/theory/BIBLIOGRAPHY.md`: [UcamcoGerber] addition, [UcamcoXNC], [GerbonaraResources], [CadSampleRepos].
