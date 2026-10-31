# Literature status (real boards)

The entries are in `research/theory/BIBLIOGRAPHY.md`, section 22 (R read, S summary, M memory, N not obtained).

| Source | Used for | Status |
| :-- | :-- | :-- |
| Ucamco downloads page | the list of specifications and test files | S |
| Ucamco layer-format test files (21 files) | study of rare primitives | S (member list only; the files are opened by `study_conformance_rare.py`) |
| Ucamco X3 sample StickHub | X3 component layer, paste with `TO.C`, job file | R (the heads of three files) |
| Ucamco X3 samples Coldfire, Li-ion charger, spec component layer | more X3 files | S (member lists) |
| Ucamco fabrication examples 1 and 2 (with IPC-2581 `.ipc`) | 4 and 10 copper layers; IPC-2581 | S (member lists) |
| Gerber specification 2024.05 and 2026.05, the attribute, component-layer, aperture-block and transformation sections | attribute names and semantics, `AB`, `LM`, `LR`, `LS` | N (the text could not be extracted here; to read before adoption) |
| ISASTM (GPL-3.0) | paste with `TO.C`, KiCad and JLCPCB placement files, job file | R (heads) |
| CMM2-JLC, open-smartwatch-light, RP2040-minimal-design, CO60, vstcm, PiFinder, Vitamins-included | boards, licences | S (file lists) and R (licences by repository metadata) |
| ODB++ specification (Siemens) | the format of `lib/odb.py` | N (registration needed); layout M |
| mcix/odbpp (MIT), ODBPy (Apache-2.0), odb-pp-parser, OdbDesign (AGPL-3.0, ideas only) | sample archives and parsers | S |
| IPC-2581 | not read | N |
| research/gerber-import, research/gerber-models | the base | S (parts quoted; not re-run) |

A statement that rests on a source with status M, S or N is marked in the README of the folder.
