#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file measured_data.py
@brief The published numbers of the two measured via cases, written once with their source and their reading status: Soleymani Koohbanani (2016) Table 9, Table 10, Fig. 33 (plot) and
       Shen and others (2020) Table II. Pure data, imports nothing.
@details Reading status of every block is stated next to it. "table" is a printed number (read in full), "plot" a number read from a figure (digitised from the page image, uncertainty
         stated), "derived" a number computed here from printed ones.
         Soleymani Koohbanani, A. (2016) MSc thesis, Simon Fraser University, "Board-level thermal management" (held as papers/SoleymaniKoohbanani2016.pdf, outside the repository):
         equations 17 to 29 are images (read from the page images of PDF pages 73 to 76, thesis pages 56 to 59), Table 9 is on thesis page 60, Table 10 on page 61, Fig. 33 on page 63.
         Shen, Wang, Blaabjerg, Zhao, Long, IEEE Trans. Power Electron. 35 (1) (2020) 882-900 (accepted manuscript of 20 pages, Table II on manuscript page 17).
"""

# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Soleymani Koohbanani (2016), Table 9 (thesis page 60), all lengths in mm: sample number -> (spacing, pitch, inner diameter D_i, outer diameter D_o, "copper barrel thickness")
# The column "copper barrel thickness 0.04" is the DIFFERENCE of the two diameters (0.65 - 0.61 = 0.04), so the wall is 0.02 mm; the table header gives no thickness of the board.
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
TABLE_9 = {
    1: (2.5, 2.5, 0.61, 0.65, 0.04),
    2: (2.5, 2.5, 0.51, 0.55, 0.04),
    3: (2.5, 2.5, 0.36, 0.40, 0.04),
    4: (2.5, 1.25, 0.61, 0.65, 0.04),
    5: (2.5, 1.25, 0.51, 0.55, 0.04),
    6: (2.5, 1.25, 0.36, 0.40, 0.04),
    7: (1.25, 1.25, 0.61, 0.65, 0.04),
    8: (1.0, 1.0, 0.51, 0.55, 0.04),
    9: (1.0, 1.0, 0.36, 0.40, 0.04),
}

# Table 10 (page 61), the benchmark of the thesis's own COMSOL unit cell: isothermal top (323 K) and bottom (303 K), sides insulated, FR-4 0.33 W/mK, copper 385 W/mK
TABLE_10 = {"k_fr4": 0.33, "k_cu": 385.0, "k_air": 0.026, "wall_mm": 0.02, "d_outer_mm": 0.65, "d_inner_mm": 0.61, "t_top_K": 323.0, "t_bottom_K": 303.0}
K_AIR = 0.026        # W/mK; the thesis's own value is not read (the equations name k_air without a number in the pages read): the textbook value is used and the effect is 3e-4 of k_overall

# The four ARRANGEMENTS (the thesis says "four different thermal via arrangements", page 59): the nine samples fall in four groups, and Fig. 33 shows one measured marker per group
# group -> (kind, cell side in mm for eq. 28/29 [u straight, v staggered], samples, x of Fig. 33 in mm)
ARRANGEMENTS = {
    "straight_2.5": ("straight", 2.5, (1, 2, 3), 2.5),
    "staggered_2.5": ("staggered", 2.5, (4, 5, 6), 2.5),
    "straight_1.25": ("straight", 1.25, (7,), 1.25),
    "straight_1.0": ("straight", 1.0, (8, 9), 1.0),
}
# A staggered cell holds two vias in v x v, with v = spacing: samples 4 to 6 have spacing 2.5 and pitch 1.25, so the area per via is 2.5 x 1.25 = 3.125 mm2 = v^2 / 2 (consistent)

# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Fig. 33 (thesis page 63), MEASURED markers, READ FROM THE PLOT (PDF page 80 rendered at 4x; marker centroids by colour; axes calibrated on the ticks x 0 to 3.5 mm, y 0 to 20 W/mK).
# Values are the centroids found on the image at 2x pixels (x 262 -> 0, 1011 -> 3.5; y 870 -> 0, 429 -> 20), i.e. +-0.02 mm in x and +-0.1 W/mK in y from the pixel read alone; the
# staggered diamond is partly hidden by a numerical-simulation triangle, so its centroid is biased (read 4.35, the visible edge says about 4.2 to 4.4). Error bars exist only on the
# straight markers at 1.0 mm (about 11.5 to 14.5) and 1.25 mm (about 6.1 to 7.6); read by eye (plot, +-0.2). The numerical-simulation and analytical-model markers of the figure are
# the thesis's own calculations, not measurements, and are not data here.
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
FIG33_MEASURED = {                  # group -> (k_overall in W/mK, lower, upper) all "plot"
    "straight_1.0": (12.9, 11.5, 14.5),
    "straight_1.25": (7.0, 6.1, 7.6),
    "straight_2.5": (2.5, None, None),
    "staggered_2.5": (4.3, None, None),
}
FIG33_PLOT_UNCERTAINTY = 0.2         # W/mK, the reading uncertainty applied to every plot value
THESIS_CLAIMS = {"analytic_vs_experiment_max": 0.13, "analytic_vs_numerical_max": 0.09}   # page 62 text (read in full)

# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Shen and others (2020), Table II (manuscript page 17), "table": top-case temperature of a DPAK diode VS-6EWL06FN-M3 at 2.8 W on a heatsink-cooled PCB, and psi_ta = (T_t - T_a) / P
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
SHEN_POWER_W = 2.8
SHEN_PHI_MM = (0.2, 0.25, 0.4, 0.8)
SHEN_TABLE_II = {                    # (pattern, filler) -> [(T_t degC, psi_ta degC/W) for phi = 0.2, 0.25, 0.4, 0.8 mm]
    ("I", "solder"): [(68.2, 15.43), (67.3, 15.1), (66.4, 14.8), (65.7, 14.5)],
    ("II", "air"): [(72.9, 17.1), (72.4, 16.9), (72.6, 17.0), (74.8, 17.8)],
    ("I", "air"): [(75.2, 17.9), (74.1, 17.5), (74.6, 17.7), (76.5, 18.4)],
}
SHEN_AMBIENT_DERIVED = 25.0          # derived, not printed: (T_t - psi P) is 25.0 +- 0.1 in all twelve cells (see tests), so the ambient of the experiment is 25 degC
# Package numbers read in the text (page 14 / manuscript): junction-case 2.47 degC/W, junction-top-case 44.12 degC/W (CFD, ANSYS Icepak); the top-case-ambient resistance (eq. 39) and the
# heatsink, TIM and solder resistances are NOT given as numbers in the text read; Fig. 16(b) (package outline), Fig. 20 (eq. 39 against CFD) and Fig. 22 (the vertical structure) have to
# be read from the page images before the program can be set up (study part B is conditional on that).
SHEN_THETA_JC = 2.47
SHEN_THETA_JT = 44.12
SHEN_CFD_NO_VIA_K_PER_W = 120.3      # p. 14, Fig. 17(a): 5.6 mm square pad, no via, CFD
SHEN_CFD_VIA_K_PER_W = 1.86          # p. 14, Fig. 17(b): 0.25 mm unfilled vias, CFD

# Shen Fig. 24 (manuscript page 17): maximum temperatures printed on the IR images of four 2-layer 70 um boards with a rectangular copper pad, natural convection, 0.5 W and 1 W;
# the numbers are printed on the images ("table"-like, read in full), the camera scale minimum is the ambient (about 26 to 27 degC, read from the scale). The board outline and thickness
# are not stated in the text read: an optional third set, only if they are found (Fig. 25 and section III).
SHEN_PAD_MAX_T = {                   # pad size (mm x mm) -> (max T at 0.5 W, max T at 1 W) in degC
    (7.8, 8.4): (75.9, 116.0),
    (13.0, 14.0): (64.0, 96.0),
    (18.2, 19.6): (53.2, 76.2),
    (26.0, 28.0): (44.6, 66.6),
}
