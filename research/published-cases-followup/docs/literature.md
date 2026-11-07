# Literature status of this folder (copied to `research/theory/BIBLIOGRAPHY.md` by the reviewer or the maintainer)

R = read in full for the parts used, S = summary or earlier reader, M = memory, N = not obtained.

| key | what | status here | what was done |
| :-- | :-- | :-- | :-- |
| [YovanovichMuzychkaCulham1999] | JTHT 13(4) 495-500 | **R** for pages 3 to 6 (equations 17 to 29, Tables 1 to 3) | text from the local copy; page 6 (printed 500, equation 29 and Table 3) rendered and read as an image; Table 2 and 3 digits compared with the equations by `scripts/study_table2_strip.py`; the Table 3 mean row is the mean of equations (24) and (27) |
| [Lemczyk1992] | J. Electronic Packaging 114(4) 413-419 | **R** (text of the whole file, Tables 1 to 4, equations 1 to 39); pages not re-rendered here | OCR text (pages flagged verified by image by the pipeline); Tables 1 to 4 reproduced with an independent solver; three inconsistencies recorded |
| [ShenWang2019Vias] | IEEE TPEL 35(1) 882-900 | **R** for sections I to IV-A (equations 1 to 9, Table I, the numbers of pages 7 and 14); **S** for Fig. 17(b) and Fig. 18 as plots (the 1.82 K/W is an earlier reader's plot reading) | closed-form claims reproduced by `scripts/study_shen_vias.py`; Pattern II reductions; CFD conductivity 0.35 |
| [CulhamYovanovich1998] | ITherm'98 460-467 | **R** (pages 4 to 8 of the text); the numbers 8.28 (text), 11.6 (plot) are those of `research/effective-conductivity` | the program run on the base stack and case 2 |
| [SeriLee1998] | Electronics Cooling, January 1998 | **S** (the three Rc values and the geometry from `research/effective-conductivity` 4.4) | exact thin-plate series and the program run; the article itself was not opened |
| [Razavi2016Thesis], [Muzychka2006EdgeCooling] | spreading resistance with edge cooling | **N** (not read in this pass; the cover pages only) | not needed: the exact cosine series is the independent closed form for the plate near an edge or corner |
