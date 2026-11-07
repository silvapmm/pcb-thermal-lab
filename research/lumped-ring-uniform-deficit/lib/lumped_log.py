#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file lumped_log.py
@brief A copy of pcbthermal.lumped with switches for the ring construction, built by patching the program's source in memory (the program is not edited).
@details The module reads the text of pcbthermal/lumped.py, checks that the anchor lines are where the patch expects them (it fails loudly otherwise), replaces them, and executes the
         result as the module `pcbthermal.lumped_log`. With every switch at its default the module is the program's code bit for bit (tests/test_lumped_log.py). Switches (module
         attributes, set before a run):

         - RING_LINK: "strip" (the program: the link between two ring means is the sum of the two half-widths, each as a straight strip of length area / width) or "log" (each half
           ring is a piece of an annulus: R = ln((a + rho_to) / (a + rho_from)) / (2 pi S c), a the equivalent radius of the footprint, c the length of the real contour in the ring
           divided by the circle's 2 pi (a + rho_mean), which is 1 for an unobstructed ring and falls where the board edge cuts the contour).
         - FIRST_RING: factor of rho_max that sets the width rho1 of the first ring (the program: 0.04).
         - FIRST_CELLS: lower bound of rho1 in cells (the program: 1.5).

         A patched copy is installed with install() into pcbthermal.api so that simulate() runs it; uninstall() restores the program.
"""

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pcbthermal  # noqa: E402
from pcbthermal import api as _api  # noqa: E402
from pcbthermal import lumped as _orig  # noqa: E402

_SRC = Path(_orig.__file__).read_text()


def _replace(text, old, new):
    """!
    @brief Replace one anchor text, which must occur exactly once.
    @param text Source text.
    @param old Anchor.
    @param new Replacement.
    @return The new text.
    @throws RuntimeError When the anchor is not found exactly once (the program's source changed).
    """
    if text.count(old) != 1:
        raise RuntimeError("patch anchor not found exactly once: " + old[:60])
    return text.replace(old, new)


def build():
    """!
    @brief Build the patched module from the current source of pcbthermal.lumped.
    @return The module object (also registered as pcbthermal.lumped_log).
    """
    s = _SRC.replace("from . import profiles, viaconstriction", "from pcbthermal import profiles, viaconstriction")
    s = s.replace("from .fvm import", "from pcbthermal.fvm import").replace("from . import blocks", "from pcbthermal import blocks")
    s = s.replace("from .geometry import", "from pcbthermal.geometry import").replace("from .results import", "from pcbthermal.results import")
    s = _replace(s, "RING_MIN_WIDTH = 1.0 ", "RING_LINK = \"strip\"\nFIRST_RING = 0.04\nFIRST_CELLS = 1.5\nFIRST_A = None\nBESSEL = True\nPEAK = True\nRING_MIN_WIDTH = 1.0 ")
    s = _replace(s, "def ring_edges(rho_max, dx, dy, rings, min_width=None):", "def ring_edges(rho_max, dx, dy, rings, min_width=None, a_eq=None):")
    s = _replace(s, "    rho1 = max(1.5 * min(dx, dy), 0.04 * rho_max)\n",
                 "    rho1 = max(FIRST_CELLS * min(dx, dy), FIRST_RING * rho_max)\n"
                 "    if FIRST_A is not None and a_eq is not None:         # The first ring is at most FIRST_A equivalent radii of the footprint wide\n"
                 "        rho1 = min(rho1, max(FIRST_CELLS * min(dx, dy), FIRST_A * a_eq))\n")
    call = "ring_edges(rho_max, net.dx, net.dy, rings)"
    if s.count(call) != 2:
        raise RuntimeError("ring_edges calls not found twice")
    s = s.replace(call, "ring_edges(rho_max, net.dx, net.dy, rings, a_eq=math.sqrt(max(float((cov > 0).sum()), 1.0) * net.dx * net.dy / math.pi))")
    # The positions needed by the logarithmic link: the outer edge of every ring and the contour factor c of the real ring against a circle
    s = _replace(s, "    length = np.where(thick > 0, cnt * cell / np.maximum(thick, 1e-12), 0.0)\n\n    S = np.array([ring_sum(net.S[l]) / cnt for l in range(L)])           # Mean sheet conductance (W/K)\n",
                 "    length = np.where(thick > 0, cnt * cell / np.maximum(thick, 1e-12), 0.0)\n"
                 "    e_out = np.zeros(R)                                 # Outer edge of every ring (ring 0: the boundary of the footprint, 0)\n"
                 "    for k in range(1, R):\n"
                 "        e_out[k] = min(edges[used[k]], rho_max)\n"
                 "    a_eq_ring = math.sqrt(cnt[0] * cell / math.pi)       # Equivalent radius of the footprint\n"
                 "    rho_node = np.minimum(rho_mean, e_out)               # Distance of the node of a ring (the mean distance of its cells)\n"
                 "    c_ring = np.where(thick > 0, length / (2.0 * math.pi * (a_eq_ring + rho_node)), 1.0)\n\n"
                 "    S = np.array([ring_sum(net.S[l]) / cnt for l in range(L)])           # Mean sheet conductance (W/K)\n")
    old = ("            half_k1 = 0.5 * thick[k + 1] / (S[l, k + 1] * length[k + 1])\n"
           "            if k == 0:\n"
           "                return f_r[l] * max(phi_bnd - phi_mean, 1e-3) / (2.0 * np.pi * S[l, 0]) + half_k1\n"
           "            return 0.5 * thick[k] / (S[l, k] * length[k]) + half_k1\n")
    new = ("            if RING_LINK == \"log\":\n"
           "                # Each half ring as a piece of an annulus around the equivalent disc of the footprint\n"
           "                lower = math.log((a_eq_ring + rho_node[k + 1]) / (a_eq_ring + e_out[k])) / (2.0 * np.pi * S[l, k + 1] * c_ring[k + 1])\n"
           "                if k == 0:\n"
           "                    return f_r[l] * max(phi_bnd - phi_mean, 1e-3) / (2.0 * np.pi * S[l, 0]) + lower\n"
           "                return math.log((a_eq_ring + e_out[k]) / (a_eq_ring + rho_node[k])) / (2.0 * np.pi * S[l, k] * c_ring[k]) + lower\n"
           + old)
    s = _replace(s, old, new)
    # Ablations for the sensitivity table: the vertical-loss factors of the footprint-to-ring link and of the peak set to 1, and the footprint peak set to 0
    old_f = "        f_r, f_p = _interior_factors(a_eq * np.sqrt(np.maximum(g_eff, 1e-12) / np.maximum(S[:, 0], 1e-12)))\n"
    s = _replace(s, old_f, old_f + "        if not BESSEL:\n            f_r, f_p = np.ones(L), np.ones(L)\n")
    old_p = "    peak_extra = max(lat, 0.0) * f_p[layer] * (phi_mean - phi_min) / (2.0 * np.pi * S[layer, 0])\n"
    s = _replace(s, old_p, old_p + "    if not PEAK:\n        peak_extra = 0.0\n")
    mod = types.ModuleType("pcbthermal.lumped_log")
    mod.__file__ = str(Path(_orig.__file__))
    mod.__package__ = "pcbthermal"
    sys.modules["pcbthermal.lumped_log"] = mod
    exec(compile(s, "lumped_log(patched)", "exec"), mod.__dict__)
    return mod


MOD = build()


def install():
    """!
    @brief Make pcbthermal.api use the patched module.
    @return The patched module.
    """
    _api.lumped = MOD
    return MOD


def uninstall():
    """!
    @brief Restore the program's module in pcbthermal.api.
    @return None.
    """
    _api.lumped = _orig


def configure(link="strip", first_ring=0.04, first_cells=1.5, first_a=None, bessel=True, peak=True, min_width=1.0):
    """!
    @brief Set the switches of the patched module.
    @param link "strip" or "log".
    @param first_ring Factor of rho_max for the first ring.
    @param first_cells Lower bound of the first ring in cells.
    @param first_a Largest width of the first ring in equivalent radii of the footprint (None: no such limit).
    @param bessel False: the vertical-loss factors of the link to ring 1 and of the footprint peak are set to 1 (an ablation).
    @param peak False: the footprint peak correction is left out (an ablation).
    @param min_width Minimum ring width in cells (the program: 1; 0 keeps every edge).
    @return None.
    """
    MOD.RING_LINK = link
    MOD.FIRST_RING = first_ring
    MOD.FIRST_CELLS = first_cells
    MOD.FIRST_A = first_a
    MOD.BESSEL = bessel
    MOD.PEAK = peak
    MOD.RING_MIN_WIDTH = min_width
