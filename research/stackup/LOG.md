# Log: stack-up

| Date | What |
| :-- | :-- |
| 2026-10-21 | Advanced stack-up implemented in all five models; `stackup_outline_study.py` written with the exact series-circuit check and the tables A to C. |
| 2026-10-22 | The maintainer asked for the typical stack-ups to be checked against fabricators. Pages of JLCPCB, PCBWay, OSH Park, Bittele 7pcb, PCBGOGO and AdvancedPCB were read (layer tables); NextPCB gives only prepreg thicknesses. `stackup_vendor_check.py` enters them layer by layer. Finding: the finished outer copper (35 against 43 µm) is the sensitive parameter, not the dielectric split. |
| 2026-10-23 | Folder created: both scripts moved from `examples/`; figures added (`make_figures.py` reads the tables the studies print). |

Read in full or from search snippets: the fabricator layer tables were taken from the pages found on 2026-10-22; two tables (PCBWay's old 8-layer blog table, PCBGOGO's 6-layer table) do not add up to their stated thickness and are shown as published. The addresses were not saved.
Not verified: no measurement of a physical board.
