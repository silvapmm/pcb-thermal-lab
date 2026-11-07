# Integration: a first ring that does not grow with the board

Status: a proposal for 2.6.0 (`fix/lumped-first-ring`), measured on a copy (`lib/lumped_log.py`); nothing of `pcbthermal/` was edited. The reviewer has not yet gone over this folder.

## 1. The change

`pcbthermal/lumped.py`, `ring_edges` and its two call sites (`_one_node_network` and `_zone_network`).

```python
def ring_edges(rho_max, dx, dy, rings, min_width=None, a_eq=None):
    ...
    rho1 = max(1.5 * min(dx, dy), 0.04 * rho_max)
    if a_eq is not None:                                   # the first ring is at most one equivalent radius of the footprint wide
        rho1 = min(rho1, max(1.5 * min(dx, dy), a_eq))
    rho1 = min(rho1, rho_max * 0.5)
    ...

# both call sites
edges = ring_edges(rho_max, net.dx, net.dy, rings, a_eq=math.sqrt(max(float((cov > 0).sum()), 1.0) * net.dx * net.dy / math.pi))
```

In formulas (`docs/theory.md` 5.1, eq. 5.1): `E1 = min(max(1.5 min(Δx,Δy), 0.04 E_max), max(1.5 min(Δx,Δy), a_eq), 0.5 E_max)`, `a_eq = sqrt(N0 Δx Δy / π)` with `N0` the number of cells the footprint touches. A footprint with `a_eq >= 0.04 E_max` (and every footprint on a board where `0.04 E_max` is under 1.5 cells) keeps the program's first ring to the last bit. The docstring of `ring_edges`, the module docstring and theory 5.1 say "the width of the first ring is capped at the footprint's equivalent radius". The patched copy in `lib/lumped_log.py` is exactly this change (`FIRST_A = 1.0`) plus switches for the study; the diff to apply is the text above.

## 2. Measured impact (all in the README)

| Where | Result |
| :-- | :-- |
| Uniform boards, 1 mm part, centred | 100 x 80 mm -13.7 % to +0.3 %; 200 x 150 mm -25.3 % to +2.5 % (3 mm part: -8.8 % to -2.4 %); 30 x 20 and 60 x 40 mm unchanged within a point |
| Conditions (1, 2, 4 layers, fill 1 and 0.6, 10 to 200 W/m2K, with and without edge) | 2 mm source on 100 x 80 mm: -5.5 .. -10.8 % to -1.1 .. -4.3 % |
| Independent 3D solver, 1 mm part off centre | -15.0 % to -3.0 % |
| Imported boards, uniform sheet | RP2040 27 parts mean -10.6 % to -4.2 %; CO60 5 parts -19.6 % to -8.0 %; oswlight 51 parts -9.0 % to -8.1 % (small board, no effect by construction) |
| Imported copper (RP2040) | mean -59.6 % to -56.8 %: the copper structure remains the cause |
| 62 via boards of the Lumped via studies, the example board with its via variants | bit-identical |
| Frozen records (17 boards at 2, 1 and 0.5 mm) | **none moves** (every difference exactly 0 with this variant) |

## 3. Frozen records and tests

Expected to move: none. The release procedure should still run the frozen test at 2, 1 and 0.5 mm (`PCBT_FROZEN_CELLS=2,1,0.5`) on the branch and state "0 records moved" (this folder measured it with `study_frozen_impact.py`, which reads `tests/regression/regress_boards.py` as it is). A **pending-shift file is not needed** for this variant. Tests to add on the `fix/` branch: (a) a 1 mm part on a 100 x 80 mm uniform board within 5 % of the FVM at 0.5 mm (program before the fix: -13.7 %); (b) `ring_edges` first ring `= 1.5 cells` for a one-cell footprint on a 0.5 m board and `= program` for a footprint of 10 mm; (c) bit identity of the example board's Lumped field; the tests of `tests/test_lumped*.py` as they are.

## 4. The alternative, and the decision for the maintainer

**First ring always 1.5 cells** (`FIRST_RING = 0`): the uniform deficit goes further (CO60 mean -19.6 % to -4.6 %, RP2040 -5.4 %, the 1 mm part on 100 x 80 +0.3 %), and the Lumped result becomes nearly independent of the raster (example board 86.29 degC at 1 mm and 86.21 at 0.5 mm; the program 86.63 and 85.45). Cost: it changes the Lumped of the large footprints too. Six frozen records move at 2 mm (example and profile board -0.34 K, reference board +0.58 K, example cut to a T +0.26 K, plate with vias -0.38 K, two-layer partial copper -2.61 K, the last from -0.3 % to -2.2 % of the FVM rise), many more at 0.5 mm (plate with a pad -10.6 K, one-layer pad -2.0 K, where the Lumped is already 10 to 14 % cool and becomes 3 points cooler), and the example board with its via arrays reads 1.3 to 4.3 % hot instead of 0.0 to 1.3 %. It would need a pending-shift file and the explanation of every record. **Recommendation: the capped first ring** (no record moves, fixes the part sizes that fail); the 1.5-cells variant only if the maintainer wants the raster independence and accepts the refreeze.

## 5. What it does not do, and the risks

* **A source near an edge or corner stays 5 to 15 % cool in the Lumped** (README 9; the Analytic is exact there). It needs a different representation and is a separate investigation. More rings are not the answer (README 5).
* **The equivalent rectangle of a board with an outline** is a limit shared with the Analytic (oswlight SW2 10 to 19 % cool next to the outline) and is not touched; the warning text of the Lumped and Analytic on an outline board stays.
* **The text of the warnings about imported copper** (17 to 42 % and 22 to 75 % too cool on the whole RP2040 board, `docs/validation.md` 27.7) quotes numbers that include the uniform-sheet deficit; they move by a few points (RP2040 imported mean -59.6 % to -56.8 %), so the wording stays valid ("a sample, not a bound") and only the numbers need re-running at the release.
* **Risk**: low for the capped variant (it acts only when the footprint is smaller than `0.04 E_max`); the transient and profile runs (`step_responses`, `run_profile`) use the same `ring_edges` and were not run here, so the `fix/` branch must compare the time to 63 % of the Lumped on the frozen boards (it should not move: the frozen boards are bit-identical in the steady state) and one step response of a 1 mm part on a 100 x 80 mm board before and after.
* **Not studied**: boards with several heaters at once, a metal block or a heatsink, and the zone network with a part just larger than a core.

## 6. Documents to carry the finding (text in `docs/`)

`docs/theory-text.md` holds the sentence for theory 5.1, the validation paragraph and the changelog entry; the Planned item (the near-edge deficit, the 1.5-cells variant) is in `docs/versions-entry.md`.
