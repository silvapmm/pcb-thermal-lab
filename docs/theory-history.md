# Theory: history

Passages of `docs/theory.md` that describe an earlier state of the program or a value that was replaced, kept as
the record. They were moved here byte for byte, each under the number of the section it left, and the theory
keeps only what is implemented now. What each version did is in `versions.md`; the current numbers are in
`validation.md`. The list of moves and its check are `releases/2.9.0/simplify/theory_moves.json` and
`releases/2.9.0/simplify/scripts/theory_moves.py`.

## 1.5

**Via target ratio: the figure quoted before the barrel length of 2.6.0 (audit of 2.8.0)**

> ; the -2.1 to +3.9 % quoted before was with the barrel over `d` alone (audit of 2.8.0, the study re-run with both lengths by `releases/2.8.0/audit/scripts/study_via_checks.py target`)

## 2.1.1

**The links before the open-fraction rule (sentence of the paragraph on the cut-cell flux)**

> The earlier links scaled the sheet of a cut cell by `c` and took the harmonic mean, a factor about `c` too weak into a sliver; the edge film sat on the node, behind that weak link. The program now uses

**The distance used by the drawn layers before 2.7.0**

> Before 2.7.0 the drawn layers used the signed distance from the cell centre (negative off the board); the

**The earlier statement about the floor 0.25 (measured with the cell-centre distance of 2.6.0)**

> The earlier statement (it binds in 80 node cells at 2000 W/m²K and moves the peak 0.06 to 0.15 K) was measured with the cell-centre distance of 2.6.0 and no longer holds. 

## 2.2

**The first numbers of the positive entries (program before the rim rule of 2.6.0)**

> *The numbers first written here (832 / 864 and 3104 / 3872 entries, the largest 0.74 and 1.31 times the diagonal, up to 2.2) are those of the program before the rim rule of 2.6.0 (section 2.6), which uncouples the via from the bare third layer of that board: the audit printed 832 / 864, 0.74 / 1.31 on the tag v2.5.2 and 432 / 432, 0.018 / 0.015 on v2.6.0; they are history.* 

**The via effect before the rim rule of 2.6.0, against the smeared-barrel 3D solid**

> **Before the rim rule of 2.6.0** (section 2.6), against the program's own 3D solid at 1/16 to 1/20 mm (which smears the barrel over its disc with no wall), the FVM read the effect 31 to 47 % low for a copper edge through the via, 45 to 68 % low for a track ending on it and 3 to 4 times high for a via just outside a copper edge at 0.5 mm or coarser; those numbers are history (`validation.md` 30.1). 

## 2.5

**The spread of the peak with the earlier cut-cell links**

> ; the earlier links 0.25 to 3.0 K, `validation.md` 32.2

## 2.6

**The first figures of the image limit, withdrawn**

> . The '4 to 10 % at 1 mm' and '19 points at 1 mm' written here before were against a cell-centred 3D reference later found hot, and are withdrawn

**The error of the partial-copper reading before the contact rule**

> ; 31 to 68 % before the rule

**The contact of an imported via before the ray test**

> ; before it the full contact read the effect 1.5 to 5 times high, `validation.md` 45
