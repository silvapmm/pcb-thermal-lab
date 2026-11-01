# Literature status (real boards)

The entries are in `research/theory/BIBLIOGRAPHY.md`, section 23 (R read, S summary, M memory, N not obtained).

| Source | Used for | Status |
| :-- | :-- | :-- |
| Ucamco downloads page | the list of specifications and test files | S |
| Ucamco layer-format test files (11 `.gbr` with their pictures) | study of rare primitives | R (all 11 read by `study_conformance_rare.py`; the picture of `sample_macro` compared by eye) |
| Ucamco X3 sample StickHub | X3 component layer, paste with `TO.C`, job file | R (the heads of three files) |
| Ucamco X3 samples Coldfire, Li-ion charger | more X3 files | R (areas of all 30 files against a second reader; contents not read in detail) |
| Ucamco fabrication examples 1 and 2 (with IPC-2581 `.ipc`) | 4 and 10 copper layers; IPC-2581 | R for the 32 Gerber and drill files (areas against a second reader); the `.ipc` files not opened (N) |
| Gerber specification 2026.05 (219 pages; the 2024.05 revision not opened), the component-layer, `.C` and `.Cxxx` sections and the overview of `AB` | component aperture functions, attribute names, block aperture | R for those passages (text layer extracted with PyMuPDF in a scratch environment), **page numbers not recorded** (review: to be read again with the pages written down before adoption); the rest of the attribute dictionary, the usage and transformation chapters, the paste file functions N |
| ISASTM (GPL-3.0) | paste with `TO.C`, KiCad and JLCPCB placement files, job file | R (heads, and the whole of the paste, placement and copper files by the studies) |
| CMM2-JLC, open-smartwatch-light, RP2040-minimal-design, CO60, vstcm, PiFinder, Vitamins-included | boards, licences | S (file lists) and R (licences by repository metadata) |
| ODB++ specification (Siemens) | the format of `lib/odb.py` | N (registration needed); the layout was M and was checked against three sample archives (R for those files) |
| mcix/odbpp (MIT), ODBPy (Apache-2.0), odb-pp-parser, OdbDesign (AGPL-3.0, ideas only) | sample archives and parsers | S for the parsers (READMEs); R for three sample archives of mcix/odbpp (downloaded and read by `study_odb_structure.py`; their licence is not stated) |
| IPC-2581 | not read | N |
| research/gerber-import, research/gerber-models | the base | S (parts quoted; not re-run) |

A statement that rests on a source with status M, S or N is marked in the README of the folder.
