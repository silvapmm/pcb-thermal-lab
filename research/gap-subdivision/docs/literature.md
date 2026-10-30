# Literature status (gap-subdivision)

| Source | Status | What was done |
| :-- | :-- | :-- |
| Yovanovich, Muzychka, Culham, *Spreading resistance of isoflux rectangles and strips on compound flux channels*, J. Thermophysics and Heat Transfer 13 (4) (1999) 495-500 | R for Eqs. 11 to 18 and Table 1 (Eq. 15 on the page image); not read: the strip tables, the square-flux-tube correlation | Eqs. 14 and 15 implemented (`lib/yovanovich1999.py`); reproduced by the independent series to 2.4e-6 on three two-layer cases; `phi` equals Eq. 17 in the semi-infinite limit; no printed number of the paper's tables compared |
| Muzychka, Culham, Yovanovich, *Thermal spreading resistance of eccentric heat sources on rectangular flux channels*, J. Electronic Packaging 125 (2003) 178-185 | R for Eqs. 16 to 28 (read earlier by `bare-spot-under-source`) | reproduced by the series to +0.0007 % (single layer) |
| Muzychka, Yovanovich, Culham, *Thermal spreading resistance in compound and orthotropic systems*, J. Thermophysics and Heat Transfer 18 (1) (2004) 45-51 | R for the orthotropic section as recorded in `effective-conductivity`, S for the rest | the orthotropic thickness `t sqrt(k_xy / k_z)` used for an order of magnitude in README 4 |
| Monier-Vinard, Laraqi and others, multilayer analytical model of a PCB (Thermal Science 2013; HAL hal-01473763) | N (TLS certificate of the host expired, fetch refused and not bypassed; HAL bot protection); S for the search summary (about 10 % of numerical results) | nothing taken |
| Lasance and others on PCB compact models, JEDEC JESD51-3 and -7 constructions | N / not read | the node count through the dielectric was searched for and no source states one; D1 reads the JEDEC boards |
