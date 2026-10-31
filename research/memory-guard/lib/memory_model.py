#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file memory_model.py
@brief Prototype of `pcbthermal/memory.py`: the physical memory of the machine, the estimate of the peak memory of a solve from its unknown count and class, the verdict and the fit of the coefficients.
@details The program would adopt this module almost as it is (see INTEGRATION.md). Everything here is standard library plus NumPy; no new dependency.
         The estimate has the form  peak = base + k * N * (N / N_REF) ** (p - 1)  with N the unknowns, N_REF = 500 000 and p about 4/3 for a sparse direct factorisation
         of a 3D-like graph (nested dissection: the fill-in grows as N^(4/3) in three dimensions and as N log N in two; the layered boards are thin 3D graphs, so the fitted
         exponent decides, see README 4). The class coefficients in COEFFS are PROVISIONAL: they are read from the earlier measurements of the documents
         (the numbers are quoted in README 2) and are replaced by the fit of scripts/study_memory_ladder.py.
"""

import math
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Sequence, Tuple

import numpy as np

N_REF = 500_000                      # Unknown count at which the coefficient k of a class is defined
BASE_DEFAULT = 0.25e9                # Bytes of the interpreter with NumPy and SciPy loaded, before any solve (PROVISIONAL: the baseline run of the study measures it; the application with Qt is larger)
GB = 1.0e9                         # Bytes in the unit used by the documents (decimal, as the measurements were quoted)
DEFAULT_FRACTION = 0.70              # Default share of the physical memory a solve may use (maintainer's rule)
SLOW_FRACTION = 0.35                 # Share of the physical memory above which the verdict is "slow" (a number to be set from the ladder)
FALLBACK_LIMIT = 8.0 * GB            # Limit used when the physical memory cannot be read
ABSOLUTE_CEILING_3D = 2_000_000      # Unknowns of the 3D solid that no machine is asked to attempt, whatever its memory


@dataclass(frozen=True)
class Coeffs:
    """!
    @brief Coefficients of the memory law of one class of model: peak = base + k * N * (N / N_REF) ** (p - 1), in bytes.
    """
    base: float          # Bytes held by the program before the solve (Python, NumPy, SciPy, Qt in the application)
    k: float             # Bytes per unknown at N = N_REF
    p: float             # Growth exponent of the peak with N (1.0 linear, 4/3 sparse direct in 3D)
    note: str = ""       # Where the provisional value comes from


# PROVISIONAL values (README 2): read from the documents' measurements, scaled to N_REF with the exponent p = 4/3. The ladder study replaces them.
COEFFS: Dict[str, Coeffs] = {
    # Layered FVM / FDM, copper everywhere (one node per layer): 1 million unknowns 2.7 GB (docs, quiet 16 GB machine)
    # (992 000 unknowns 2.7 GB and 1 975 000 unknowns 5.5 GB: the growth between them is linear, p = 1.0; the ladder must say whether that holds on finer boards)
    "layered_plain": Coeffs(BASE_DEFAULT, 2.7e3, 1.0, "992 000 unknowns 2.7 GB and 1 975 000 unknowns 5.5 GB, linear between them"),
    # Laminate nodes of the rule, 2 copper layers: 637 000 unknowns 4.5 GB (fix/laminate-nodes), layer-major ordering
    "layered_laminate_few": Coeffs(BASE_DEFAULT, 6.0e3, 4.0 / 3.0, "637 000 unknowns 4.5 GB, 2 layers, layer-major order"),
    # Laminate nodes of the rule, 3 or more copper layers: 681 000 unknowns 7.6 GB (4 layers, fix/laminate-nodes)
    "layered_laminate_many": Coeffs(BASE_DEFAULT, 9.5e3, 4.0 / 3.0, "681 000 unknowns 7.6 GB, 4 layers, layer-major order"),
    # 3D solid, few slabs (a plain two-layer board, 6 slabs): 500 000 unknowns 3.3 GB
    "solid3d_few": Coeffs(BASE_DEFAULT, 6.0e3, 4.0 / 3.0, "500 000 unknowns 3.3 GB, 6 slabs"),
    # 3D solid, many slabs (the example board): 247 000 unknowns 3.5 GB, 392 000 7.4 GB, 512 000 9.9 GB resident
    "solid3d_many": Coeffs(BASE_DEFAULT, 17.0e3, 4.0 / 3.0, "247 000 / 392 000 / 512 000 unknowns 3.5 / 7.4 / 9.9 GB"),
    # Lumped: dense systems per heater, a few ring unknowns; the arrays of the plan grid dominate (nothing measured yet)
    "lumped": Coeffs(BASE_DEFAULT, 0.4e3, 1.0, "not measured: arrays of the plan grid only"),
}

# Transient: the steady factorisation and the step matrix are both kept (profiles.py calls splu twice), so the factor is about 2 (to be measured)
TRANSIENT_FACTOR = 2.0


def ram_bytes() -> Optional[int]:
    """!
    @brief Physical memory of the machine in bytes, read without a dependency; None if it cannot be read.
    @details Order: os.sysconf (Linux, macOS), `sysctl -n hw.memsize` (macOS if sysconf lacks the names), /proc/meminfo (Linux), GlobalMemoryStatusEx through ctypes (Windows).
             A container limit (cgroup) is looked at on Linux because the host memory is not what the process may use.
    @return int bytes (> 0) or None.
    """
    # A cgroup limit (v2 then v1) is smaller than the host memory inside a container
    cg = None
    for path in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        try:
            with open(path) as fh:
                txt = fh.read().strip()
            if txt.isdigit() and int(txt) < (1 << 60):
                cg = int(txt)
                break
        except OSError:
            pass
    phys = None
    try:
        pages, size = os.sysconf("SC_PHYS_PAGES"), os.sysconf("SC_PAGE_SIZE")
        if pages > 0 and size > 0:
            phys = int(pages) * int(size)
    except (ValueError, OSError, AttributeError):
        pass
    if phys is None and sys.platform == "darwin":
        try:
            phys = int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=5).stdout.strip())
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    if phys is None and sys.platform.startswith("linux"):
        try:
            with open("/proc/meminfo") as fh:
                for line in fh:
                    if line.startswith("MemTotal:"):
                        phys = int(line.split()[1]) * 1024
                        break
        except (OSError, ValueError):
            pass
    if phys is None and sys.platform == "win32":
        try:
            import ctypes

            class _Status(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                            ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong),
                            ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong),
                            ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            st = _Status()
            st.dwLength = ctypes.sizeof(_Status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):
                phys = int(st.ullTotalPhys)
        except (OSError, AttributeError, ImportError):
            pass
    if phys is not None and cg is not None:
        return min(phys, cg)
    return phys if phys else cg


def estimate_bytes(unknowns: float, klass: str, coeffs: Optional[Dict[str, Coeffs]] = None, transient: bool = False) -> float:
    """!
    @brief Estimated peak memory of a solve.
    @param unknowns Number of unknowns of the model (the count of fvm.unknowns, fdm.unknowns or solid3d.unknowns).
    @param klass Key of the coefficient table (see COEFFS).
    @param coeffs Table to use instead of COEFFS (the fitted one).
    @param transient True for a time simulation (two factorisations held).
    @return Bytes.
    @throws KeyError If klass is unknown.
    """
    c = (coeffs or COEFFS)[klass]
    n = max(float(unknowns), 0.0)
    peak = c.base + c.k * n * (n / N_REF) ** (c.p - 1.0) if n > 0 else c.base
    return peak * (TRANSIENT_FACTOR if transient else 1.0)


def classify_layered(copper_layers: int, laminate_rule: bool) -> str:
    """!
    @brief Class of a layered (FVM or FDM) model.
    @param copper_layers Copper layers of the board.
    @param laminate_rule True when the laminate nodes of the rule are built (laminate.uses_rule).
    @return Key of COEFFS.
    """
    if not laminate_rule:
        return "layered_plain"
    return "layered_laminate_few" if copper_layers <= 2 else "layered_laminate_many"


def classify_solid3d(slabs: int) -> str:
    """!
    @brief Class of the 3D solid by its slab count.
    @param slabs Number of slabs (solid3d.unknowns returns it).
    @return Key of COEFFS ("solid3d_few" up to 6 slabs).
    """
    return "solid3d_few" if slabs <= 6 else "solid3d_many"


def limit_bytes(fraction: float = DEFAULT_FRACTION, ram: Optional[int] = None) -> float:
    """!
    @brief Memory a solve may use.
    @param fraction Share of the physical memory (the setting of the Preferences).
    @param ram Physical memory in bytes (None: read it; if it cannot be read the fixed FALLBACK_LIMIT is used).
    @return Bytes.
    """
    r = ram if ram is not None else ram_bytes()
    return float(r) * fraction if r else FALLBACK_LIMIT


def verdict(estimate: float, limit: float, slow_fraction: float = SLOW_FRACTION, ram: Optional[int] = None) -> str:
    """!
    @brief Verdict of a run: "ok", "slow" (runs, but warn) or "refuse".
    @param estimate Estimated peak in bytes.
    @param limit Limit in bytes (limit_bytes).
    @param slow_fraction Share of the RAM above which the run is slow.
    @param ram Physical memory in bytes (None: half the limit is the slow mark).
    @return "ok", "slow" or "refuse".
    """
    if estimate > limit:
        return "refuse"
    slow_at = slow_fraction * ram if ram else 0.5 * limit
    return "slow" if estimate > min(slow_at, limit) else "ok"


def largest_unknowns(klass: str, limit: float, coeffs: Optional[Dict[str, Coeffs]] = None) -> int:
    """!
    @brief Largest unknown count whose estimate stays within a limit (bisection; the estimate is monotone).
    @param klass Key of the coefficient table.
    @param limit Limit in bytes.
    @param coeffs Table to use instead of COEFFS.
    @return Unknown count (0 if even the base is above the limit).
    """
    if estimate_bytes(1, klass, coeffs) > limit:
        return 0
    lo, hi = 1.0, 1.0e9
    for _ in range(80):
        mid = math.sqrt(lo * hi)
        if estimate_bytes(mid, klass, coeffs) <= limit:
            lo = mid
        else:
            hi = mid
    return int(lo)


def cell_that_fits(count: Callable[[float], int], klass: str, limit: float, cell_mm: float, coeffs: Optional[Dict[str, Coeffs]] = None,
                   cell_max: float = 50.0) -> Optional[float]:
    """!
    @brief Smallest cell, grown in steps of 10 % and rounded up to 0.1 mm, not finer than cell_mm, whose model fits a limit (the refusal message and the Auto suggestion).
    @param count Function cell_mm -> unknowns (for example `lambda c: fvm.unknowns(problem, c)[0]`).
    @param klass Key of the coefficient table.
    @param limit Limit in bytes.
    @param cell_mm Cell tried first.
    @param coeffs Table to use instead of COEFFS.
    @param cell_max Largest cell tried.
    @return Cell in mm, or None if even cell_max does not fit.
    """
    c = max(cell_mm, 0.05)
    while c <= cell_max:
        if estimate_bytes(count(c), klass, coeffs) <= limit:
            return c
        c = math.ceil(c * 1.1 * 10.0) / 10.0              # Grow 10 % and round up to 0.1 mm: the count is not smooth in c
    return None


def analytic_bytes(tiles: int, layers: int, modes: int = 300, base: float = BASE_DEFAULT) -> float:
    """!
    @brief Estimate of the memory of the Analytic model's local correction: dense matrices of (tiles x layers)^2 entries (G, C and the Woodbury system, about four alive at once) plus the projections of the modes.
    @details Read from analytic.py (the arrays Gm, G, C and the matrix that is inverted); the factor four and the absence of a measurement are PROVISIONAL (README 9). The tiles are those
             that carry a via, a heatsink coefficient or a block; the program would count them from the tile map before building the matrices.
    @param tiles Tiles with a local correction.
    @param layers Copper layers.
    @param modes Cosine modes per direction (the projections are 2 x modes x tiles).
    @param base Bytes before the solve.
    @return Bytes.
    """
    n = float(tiles) * layers
    return base + 4.0 * 8.0 * n * n + 2.0 * 8.0 * modes * tiles


def sor_block_bytes(n: int) -> float:
    """!
    @brief Memory of the dense inverse of one SOR block (8 bytes per entry) with a working copy of the same size while it is inverted.
    @param n Unknowns of the block.
    @return Bytes (16 n^2).
    """
    return 16.0 * float(n) * float(n)


def sor_block_fits(n: int, limit: float, share: float = 0.25) -> bool:
    """!
    @brief Whether a SOR block may be inverted dense; it replaces the constant MAX_SOR_BLOCK = 5000 (16 n^2 = 400 MB).
    @param n Unknowns of the largest block.
    @param limit Limit in bytes of the memory guard.
    @param share Share of the limit one block may take (the blocks are inverted one after the other; the factors of all stay).
    @return True if it fits.
    """
    return sor_block_bytes(n) <= share * limit


def fit_class(points: Sequence[Tuple[float, float]], base: float = BASE_DEFAULT, p_range: Tuple[float, float] = (1.0, 1.7)) -> Coeffs:
    """!
    @brief Fit the law peak = base + k N (N / N_REF)^(p - 1) to measured points of one class by least squares on the logarithms.
    @param points Pairs (unknowns, peak bytes), at least two with different N.
    @param base Bytes before the solve, subtracted before the fit (measure it with an empty run).
    @param p_range Allowed range of the exponent; the fit is clipped to it and the clipping is reported in the note.
    @return Coeffs with k at N_REF and the fitted p.
    @throws ValueError If there are fewer than two points with different N.
    """
    pts = [(float(n), float(m) - base) for n, m in points if m > base and n > 0]
    if len(set(n for n, _ in pts)) < 2:
        raise ValueError("at least two points with different unknown counts are needed")
    x = np.log([n for n, _ in pts])
    y = np.log([m for _, m in pts])
    slope, icpt = np.polyfit(x, y, 1)                   # log(M) = icpt + slope log(N); slope = p
    note = ""
    p = float(slope)
    if not p_range[0] <= p <= p_range[1]:
        p = float(np.clip(p, *p_range))
        icpt = float(np.mean(y - p * x))                 # Refit the intercept at the clipped exponent
        note = f"exponent {slope:.2f} clipped to {p:.2f}"
    k = math.exp(icpt) * N_REF ** (p - 1.0)              # M(N_REF) / N_REF, bytes per unknown at N_REF
    return Coeffs(base, k, p, note)
