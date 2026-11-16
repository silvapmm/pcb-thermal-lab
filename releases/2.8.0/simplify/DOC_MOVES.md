# Document moves of the simplification (2.8.0)

The moves made by the branches of the documentation simplification (`DOCS_PLAN.md`). Every move is checked by
`scripts/check_doc_moves.py`: nothing is deleted without a destination, and a moved body is byte for byte the
same in its new place.

## Moves done on `docs/simplify-docs-plan` (base `development` e7dfb609)

The bodies of the four history sections of `docs/validation.md` went to the new `docs/validation-history.md`.
Each heading stays in `docs/validation.md` with one pointer line, so the numbering and every reference of the
kind 'validation 20' or 'section 21.2' still resolve; 21.2 and 21.3 (the current laminate rule and the 3D slabs)
stay in `docs/validation.md` untouched. The list 'Which table is current' at the top of `docs/validation.md`
already called these sections superseded.

| # | Source (lines at e7dfb609) | Section | Destination | Lines moved |
| --: | :-- | :-- | :-- | --: |
| 1 | `docs/validation.md` 363 to 385 | 6. The removed wxPython program against the current one | `docs/validation-history.md` | 23 |
| 2 | `docs/validation.md` 856 to 888 | 20. Corrections found in a review of the models | `docs/validation-history.md` | 33 |
| 3 | `docs/validation.md` 890 to 951 | 21. One-layer boards and the rings of the Lumped model (body before 21.1) | `docs/validation-history.md` | 62 |
| 4 | `docs/validation.md` 953 to 964 | 21.1 The error of the 2-layer boards | `docs/validation-history.md` | 12 |

`docs/validation.md` 2967 to 2849 lines (520 to 502 KB); `docs/validation-history.md` 149 lines, 21 KB. The image
links of the moved bodies (`../research/...`) stay valid because both files are in `docs/`.

### How it was checked

```sh
.venv/bin/python releases/2.8.0/simplify/scripts/check_doc_moves.py --base e7dfb609
#   4 moves checked against e7dfb609: OK
.venv/bin/python releases/2.8.0/simplify/scripts/check_doc_moves.py --base e7dfb609 --numbers-kept docs/validation.md docs/validation-history.md
#   numbers of docs/validation.md: OK
```

The first command checks (1) every moved body is in the destination under its heading, byte for byte; (2) the
source keeps the heading and the pointer and no longer the body; (3) putting the four bodies back into the
source gives the file of e7dfb609 exactly (this third check is valid only until another branch edits
`docs/validation.md`; the first two stay valid, and the script without `--base` checks the pointers alone). The
second command checks that every precise number (two decimals or more, or a signed percentage) that left
`docs/validation.md` is in the destination; as a negative control, the same check against `docs/theory.md`
reports the one number of section 21 found nowhere else (`−9.5 %`), so the check does detect a loss.

Documentation tests on the branch: `tests/test_docs.py`, `tests/test_license_header.py`, `tests/test_version.py`,
`tests/test_help.py`, `tests/test_third_party_text.py`, `tests/test_no_fabricator_names.py` and
`research/theory/tests`: 859 passed.

## Moves planned (later branches)

Listed in `DOCS_PLAN.md`, section 4, with the line ranges at e7dfb609; each branch adds its entries to `MOVES`
in the script (byte-for-byte moves) or uses `--numbers-kept` (rewrites that split a paragraph), and adds a row
to this file.
