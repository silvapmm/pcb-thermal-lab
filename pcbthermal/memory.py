#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file memory.py
@brief Memory guard: the physical memory of the machine, the estimated peak memory of a solve, the verdict (ok, slow, refuse) and the cell that fits.
@details A sparse direct factorisation needs memory that grows faster than the number of unknowns, and the number is set by the cell the user chooses, so a fine cell
         could swap the machine or hang the program. This module estimates the peak of a solve **before anything is allocated** from the unknown count that the models
         already provide (`fvm.unknowns`, `fdm.unknowns`, `solid3d.unknowns`) and refuses a run above a fraction of the installed memory.

         The law, one per model (research/memory-guard README 14.2, fitted on 67 measured points of a 16 GB machine):

             peak = base + k1 * t_eff**a * N * (N / N_REF)**(p - 1),   times the safety factor of the model,

         with N the unknowns, t = N / (nx ny) the nodes per plan cell and t_eff = min(t, cells / t) (a board that is very thick in layers is also thin in plan).
         `base` is the resident size of the process when the check is made. The coefficients are bytes of the algorithm, mostly independent of the machine, but they were
         measured on one machine and are logged against the measured peak after each run so that other machines can check them.

         Units: bytes inside the code; messages use GB of 10^9 bytes. No GUI import and no new dependency (the memory is read with the standard library).
"""

import contextlib
import logging
import math
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple

log = logging.getLogger(__name__)

GB = 1.0e9                          # Bytes in the unit of the messages (decimal, as the measurements were quoted)
N_REF = 500_000                     # Unknown count at which the coefficient k1 of a model is defined
BASE_DEFAULT = 0.108e9              # Resident bytes of the calculation process (Python, NumPy, SciPy) when it cannot be read (measured)
DEFAULT_FRACTION = 0.60             # Share of the physical memory a solve may use (maintainer: 60 or 70 %; the usable memory of a used 16 GB machine is about 12 GB)
MIN_FRACTION, MAX_FRACTION = 0.10, 0.95
FALLBACK_LIMIT = 8.0 * GB           # Limit when the physical memory cannot be read
CEILING_3D = 2_000_000              # Unknowns of the 3D solid that no machine is asked to attempt (it never binds below about 26 GB of memory)
SLOW_SECONDS = 30.0                 # Predicted solve time above which the verdict is "slow"
TRANSIENT_FACTOR = 2.0              # Time simulation and animation: one factor of the matrix plus the previous stage while the next is built (measured 1.9, one-factor fix)
PROFILE_FACTOR = 2.0                # Power-profile runs (two factors; not measured)
SOR_BLOCK_SHARE = 0.25              # Share of the limit one dense SOR block may take
EXIT_CODE = 3                       # Exit code of the command line for a refusal (2 is argparse's usage error)

# CONTINUOUS law of the review: model -> (k1 bytes per unknown at N_REF and t_eff = 1, exponent p in N, exponent a in t_eff, safety factor)
CONTINUOUS = {
    "fvm": (1469.0, 1.24, 0.79, 1.40),
    "fdm": (1228.0, 1.34, 1.03, 1.24),
    "solid3d": (1063.0, 1.30, 0.98, 1.30),
}

# Solve time law of the classes of README 5.4 (model -> list of (largest t, seconds at N_REF, exponent q)); the last row has no upper edge. Times of the
# measuring machine shared with other work, so lower bounds for a loaded one; only the "slow" mark uses them.
TIME_LAWS = {
    "fvm": [(3.5, 1.5, 1.32), (4.5, 5.4, 1.31), (math.inf, 9.2, 1.50)],
    "fdm": [(math.inf, 11.5, 1.47)],
    "solid3d": [(6.5, 11.2, 1.70), (12.0, 14.8, 1.52), (math.inf, 44.1, 1.50)],
}

MODEL_LABELS = {"fvm": "finite volume (FVM)", "fdm": "finite difference (FDM)", "solid3d": "3D solid"}


class MemoryGuardError(ValueError):
    """!
    @brief A run refused because its estimated memory is above the limit; the text names the cell that fits.
    """


@dataclass
class Verdict:
    """!
    @brief The guard's answer for one model.
    """
    model: str                        # "fvm", "fdm" or "solid3d"
    unknowns: int                     # Unknowns the model would build
    estimate: float                   # Estimated peak in bytes
    limit: float                      # Limit in bytes
    verdict: str                      # "ok", "slow" or "refuse"
    seconds: float                    # Predicted solve time in s
    cell_fit: Optional[float]         # Smallest cell in mm that fits (None if none up to 50 mm, or if the run is not refused)
    message: str                      # Text for the user ("" when ok)
    exceeds_available: bool = False   # The estimate is above the memory available now (a warning, not a refusal)


_fraction_override: Optional[float] = None       # Fraction forced for the process (None: DEFAULT_FRACTION)
_accept_unknowns = {}                            # model -> unknowns accepted whatever the memory estimate (size_limit)


def ram_bytes() -> Optional[int]:
    """!
    @brief Physical memory the process may use, in bytes, read without a dependency; None if it cannot be read.
    @details os.sysconf (Linux, macOS), `sysctl -n hw.memsize` (macOS), /proc/meminfo (Linux), GlobalMemoryStatusEx by ctypes (Windows); the cgroup limit (v2, then v1)
             of a container lowers it because the host memory is not what the process may use.
    @return int bytes (> 0) or None.
    """
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


def available_bytes() -> Optional[int]:
    """!
    @brief Memory that can be used now without paging, read without a dependency; None if it cannot be read.
    @details Linux: MemAvailable of /proc/meminfo. macOS: free + inactive + speculative + purgeable pages of `vm_stat`. Windows: ullAvailPhys of GlobalMemoryStatusEx.
    @return int bytes or None.
    """
    if sys.platform.startswith("linux"):
        try:
            with open("/proc/meminfo") as fh:
                for line in fh:
                    if line.startswith("MemAvailable:"):
                        return int(line.split()[1]) * 1024
        except (OSError, ValueError):
            return None
    if sys.platform == "darwin":
        try:
            txt = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=5).stdout
            page = int(txt.split("page size of")[1].split()[0])
            pages = {}
            for line in txt.splitlines()[1:]:
                if ":" in line:
                    key, val = line.split(":", 1)
                    pages[key.strip()] = int(val.strip().rstrip("."))
            return page * sum(pages.get(k, 0) for k in ("Pages free", "Pages inactive", "Pages speculative", "Pages purgeable"))
        except (OSError, ValueError, IndexError, subprocess.SubprocessError):
            return None
    if sys.platform == "win32":
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
                return int(st.ullAvailPhys)
        except (OSError, AttributeError, ImportError):
            return None
    return None


def resident_bytes() -> float:
    """!
    @brief Resident size of this process now, the base of the estimate; BASE_DEFAULT if it cannot be read.
    @return Bytes.
    """
    try:
        if sys.platform.startswith("linux"):
            with open("/proc/self/statm") as fh:
                return float(int(fh.read().split()[1]) * os.sysconf("SC_PAGE_SIZE"))
        if sys.platform == "darwin":
            out = subprocess.run(["ps", "-o", "rss=", "-p", str(os.getpid())], capture_output=True, text=True, timeout=5).stdout.strip()
            return float(int(out) * 1024)
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        pass
    return BASE_DEFAULT


def peak_rss_bytes() -> Optional[float]:
    """!
    @brief Largest resident size this process has reached (to compare with the estimate after a run).
    @return Bytes (macOS reports bytes, Linux kilobytes) or None where `resource` does not exist.
    """
    try:
        import resource
    except ImportError:
        return None
    peak = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return peak if sys.platform == "darwin" else peak * 1024.0


def default_fraction() -> float:
    """!
    @brief Fraction of the physical memory a solve may use when the caller gives none.
    @return Fraction between MIN_FRACTION and MAX_FRACTION.
    """
    return DEFAULT_FRACTION if _fraction_override is None else _fraction_override


def set_default_fraction(fraction: Optional[float]) -> None:
    """!
    @brief Set the process-wide default fraction (None restores DEFAULT_FRACTION); used by the command line.
    @param fraction Share of the physical memory, MIN_FRACTION to MAX_FRACTION, or None.
    @return None.
    @throws ValueError If the fraction is out of range.
    """
    global _fraction_override
    if fraction is not None and not MIN_FRACTION <= fraction <= MAX_FRACTION:
        raise ValueError(f"the memory fraction must be between {MIN_FRACTION} and {MAX_FRACTION}")
    _fraction_override = fraction


def limit_bytes(fraction: Optional[float] = None, ram: Optional[int] = None) -> float:
    """!
    @brief Memory a solve may use.
    @param fraction Share of the physical memory (None: default_fraction()).
    @param ram Physical memory in bytes (None: read it; FALLBACK_LIMIT if it cannot be read).
    @return Bytes.
    """
    f = default_fraction() if fraction is None else fraction
    r = ram if ram is not None else ram_bytes()
    return float(r) * f if r else FALLBACK_LIMIT


def estimate_bytes(model: str, unknowns: float, cells: float, base: Optional[float] = None, factor: float = 1.0) -> float:
    """!
    @brief Estimated peak memory of a solve, with the safety factor of the model.
    @param model "fvm", "fdm" or "solid3d".
    @param unknowns Unknowns the model builds (count, not bytes).
    @param cells Cells of the plan grid, nx * ny (the nodes of one layer for the FDM), count.
    @param base Resident bytes of the process (None: resident_bytes()).
    @param factor Multiplier of a time simulation or profile run (TRANSIENT_FACTOR, PROFILE_FACTOR); 1 for a steady solve.
    @return Bytes.
    @throws KeyError If the model has no law (lumped, analytic).
    """
    k1, p, a, safety = CONTINUOUS[model]
    n = max(float(unknowns), 1.0)
    t = n / max(float(cells), 1.0)
    t_eff = max(min(t, float(cells) / t), 1.0)
    b = resident_bytes() if base is None else base
    return (b + k1 * t_eff ** a * n * (n / N_REF) ** (p - 1.0)) * safety * factor


def estimate_seconds(model: str, unknowns: float, cells: float) -> float:
    """!
    @brief Predicted solve time of a steady solve on the measuring machine (a lower bound on a loaded one).
    @param model "fvm", "fdm" or "solid3d".
    @param unknowns Unknowns, count.
    @param cells Cells of the plan grid, count.
    @return Seconds.
    """
    t = float(unknowns) / max(float(cells), 1.0)
    for edge, t500, q in TIME_LAWS[model]:
        if t <= edge:
            return t500 * (max(float(unknowns), 1.0) / N_REF) ** q
    return 0.0


def verdict(estimate: float, limit: float, seconds: float = 0.0) -> str:
    """!
    @brief Verdict of one run.
    @param estimate Estimated peak in bytes.
    @param limit Limit in bytes.
    @param seconds Predicted solve time in s ("slow" above SLOW_SECONDS).
    @return "refuse" above the limit, "slow" above SLOW_SECONDS, otherwise "ok".
    """
    if estimate > limit:
        return "refuse"
    return "slow" if seconds > SLOW_SECONDS else "ok"


def largest_unknowns(model: str, cells: float, limit: float, base: Optional[float] = None, factor: float = 1.0) -> int:
    """!
    @brief Largest unknown count whose estimate stays within a limit, at a given plan grid (bisection; the estimate grows with N).
    @param model "fvm", "fdm" or "solid3d".
    @param cells Cells of the plan grid, count.
    @param limit Limit in bytes.
    @param base Resident bytes of the process (None: read).
    @param factor Multiplier of a time simulation.
    @return Unknown count (0 if even the base is above the limit).
    """
    b = resident_bytes() if base is None else base
    if estimate_bytes(model, cells, cells, b, factor) > limit:
        return 0
    lo, hi = float(cells), 1.0e10
    for _ in range(100):
        mid = math.sqrt(lo * hi)
        if estimate_bytes(model, mid, cells, b, factor) <= limit:
            lo = mid
        else:
            hi = mid
    return int(lo)


def cell_that_fits(count: Callable[[float], Tuple[int, int]], model: str, limit: float, cell_mm: float, base: Optional[float] = None,
                   factor: float = 1.0, cell_max: float = 50.0, max_unknowns: Optional[float] = None) -> Optional[float]:
    """!
    @brief Smallest cell, grown in steps of 10 % and rounded up to 0.1 mm, not finer than cell_mm, whose model fits a limit (the refusal message and the Auto suggestion).
    @param count Function cell_mm -> (unknowns, plan cells), both counts.
    @param model "fvm", "fdm" or "solid3d".
    @param limit Limit in bytes.
    @param cell_mm Cell tried first, in mm.
    @param base Resident bytes of the process (None: read once).
    @param factor Multiplier of a time simulation.
    @param cell_max Largest cell tried, in mm.
    @param max_unknowns Also require at most this many unknowns (the ceiling of the 3D solid); None for no such bound.
    @return Cell in mm, or None if even cell_max does not fit.
    """
    b = resident_bytes() if base is None else base
    c = max(cell_mm, 0.05)
    while c <= cell_max:
        n, cells = count(c)
        if estimate_bytes(model, n, cells, b, factor) <= limit and (max_unknowns is None or n <= max_unknowns):
            return c
        c = math.ceil(c * 1.1 * 10.0) / 10.0              # Grow 10 % and round up to 0.1 mm: the count is not smooth in the cell
    return None


def analytic_bytes(tiles: int, layers: int, modes: int = 300, base: Optional[float] = None) -> float:
    """!
    @brief Estimate of the memory of the Analytic model's local correction: dense matrices of (tiles x layers)^2 entries (about four alive at once) plus the mode projections.
    @details Provisional (not measured). `viaconstriction` has its own 4800-unknown guard, so `check` does not use it yet.
    @param tiles Tiles with a local correction, count.
    @param layers Copper layers, count.
    @param modes Cosine modes per direction, count.
    @param base Resident bytes (None: read).
    @return Bytes.
    """
    n = float(tiles) * layers
    b = resident_bytes() if base is None else base
    return b + 4.0 * 8.0 * n * n + 2.0 * 8.0 * modes * tiles


def sor_block_bytes(n: int) -> float:
    """!
    @brief Memory of the dense inverse of one SOR block with the copies of the build (dense block, its inverse, the sparse form kept for the iterations, the LAPACK work).
    @param n Unknowns of the block, count.
    @return Bytes: 75 n^2 (measured 66 to 75 n^2, the largest used; 5 000 unknowns take about 1.9 GB).
    """
    return 75.0 * float(n) * float(n)


def sor_block_fits(n: int, limit: float, share: float = SOR_BLOCK_SHARE) -> bool:
    """!
    @brief Whether a SOR block may be inverted dense.
    @param n Unknowns of the largest block, count.
    @param limit Limit in bytes of the memory guard.
    @param share Share of the limit one block may take (the blocks are inverted one after the other, but the inverses of all of them stay).
    @return True if sor_block_bytes(n) is at most share x limit.
    """
    return sor_block_bytes(n) <= share * limit


@contextlib.contextmanager
def accept_unknowns(model: str, max_unknowns: int):
    """!
    @brief Accept a model up to a number of unknowns whatever the memory estimate, inside a with block (offline studies on a large machine).
    @details The ceiling of the 3D solid still applies above the number given, which is also lifted to it for the 3D solid. See `solid3d.size_limit`.
    @param model "fvm", "fdm" or "solid3d".
    @param max_unknowns Largest accepted unknown count.
    @return Context manager (yields nothing).
    """
    global CEILING_3D
    old, old_ceiling = _accept_unknowns.get(model), CEILING_3D
    _accept_unknowns[model] = int(max_unknowns)
    if model == "solid3d":
        CEILING_3D = max(CEILING_3D, int(max_unknowns))
    try:
        yield
    finally:
        if old is None:
            _accept_unknowns.pop(model, None)
        else:
            _accept_unknowns[model] = old
        CEILING_3D = old_ceiling


def _counter(problem, model: str) -> Callable[[float], Tuple[int, int]]:
    """!
    @brief Function cell_mm -> (unknowns, plan cells) of a model, from the model's own counter.
    @param problem A Problem.
    @param model "fvm", "fdm" or "solid3d".
    @return Callable.
    """
    from . import fdm, fvm, solid3d
    if model == "fvm":
        return lambda c: (lambda r: (int(r[0]), int(r[2]) * int(r[3])))(fvm.unknowns(problem, c))
    if model == "fdm":
        return lambda c: (lambda r: (int(r[0]), int(r[2]) * int(r[3])))(fdm.unknowns(problem, c))
    return lambda c: (lambda r: (int(r[0]), int(r[2]) * int(r[3])))(solid3d.unknowns(problem, c))


def _message(model: str, n: int, estimate: float, limit: float, ram: Optional[int], fraction: float, cell_fit: Optional[float], cell_mm: float, why: str) -> str:
    """!
    @brief Text of a refusal or a warning, in GB of 10^9 bytes, naming the cell that fits.
    @param model "fvm", "fdm" or "solid3d".
    @param n Unknowns, count.
    @param estimate Estimated peak in bytes.
    @param limit Limit in bytes.
    @param ram Physical memory in bytes or None.
    @param fraction Share of the physical memory used for the limit.
    @param cell_fit Cell that fits in mm or None.
    @param cell_mm Cell requested, in mm.
    @param why "refuse" or "slow" or "ceiling".
    @return Text.
    """
    label = MODEL_LABELS.get(model, model)
    src = f"{fraction * 100:.0f} % of the {ram / GB:.1f} GB of memory" if ram else "the fixed limit (the memory of the machine could not be read)"
    if why == "ceiling":
        head = f"the {label} model would have {n:,} unknowns, more than the {CEILING_3D:,} that no machine is asked to solve"
    elif why == "refuse":
        head = f"the {label} model would have {n:,} unknowns and need about {estimate / GB:.1f} GB at the cell of {cell_mm:g} mm, more than the {limit / GB:.1f} GB allowed ({src})"
    else:
        head = f"the {label} model has {n:,} unknowns: about {estimate / GB:.1f} GB of memory and a solve that may take more than {SLOW_SECONDS:.0f} s"
    if why == "slow":
        return head
    return head + (f"; use a cell of {cell_fit:.1f} mm or more" if cell_fit else "; no cell up to 50 mm fits")


def check(problem, models: Sequence[str], cell_mm: float, fraction: Optional[float] = None, transient: bool = False,
          factor: Optional[float] = None, refuse: str = "raise", ram: Optional[int] = None, available: Optional[int] = None) -> List[Verdict]:
    """!
    @brief The entry the callers use: count the unknowns of every selected model that has a law, estimate the peak and give the verdicts, before anything is allocated.
    @details The Lumped and Analytic models are not checked here: their arrays are small (455 bytes per unknown measured for the Lumped) and the Analytic has its own guard of
             4 800 tile unknowns in `viaconstriction`. A model accepted with `accept_unknowns` is never refused on memory (it may still be "slow").
    @param problem A Problem.
    @param models Model keys of the run; only "fvm", "fdm" and "solid3d" are estimated.
    @param cell_mm Cell size in mm that the run will use.
    @param fraction Share of the physical memory allowed (None: default_fraction()).
    @param transient True for a time simulation or an animation (factor TRANSIENT_FACTOR).
    @param factor Explicit multiplier of the peak, overrides transient (PROFILE_FACTOR for a profile run).
    @param refuse "raise" raises MemoryGuardError for the first refused model; "return" only returns the verdicts (the caller decides).
    @param ram Physical memory in bytes (None: read it); for tests with a fake machine.
    @param available Memory available now in bytes (None: read it); for tests.
    @return List of Verdict, one per checked model.
    @throws MemoryGuardError If refuse is "raise" and a model is refused.
    """
    f = default_fraction() if fraction is None else fraction
    mult = factor if factor is not None else (TRANSIENT_FACTOR if transient else 1.0)
    r = ram if ram is not None else ram_bytes()
    limit = limit_bytes(f, r)
    avail = available if available is not None else available_bytes()
    base = resident_bytes()
    out: List[Verdict] = []
    for model in models:
        if model not in CONTINUOUS:
            continue
        count = _counter(problem, model)
        n, cells = count(cell_mm)
        est = estimate_bytes(model, n, cells, base, mult)
        secs = estimate_seconds(model, n, cells) * (mult if mult > 1.0 else 1.0)
        accepted = _accept_unknowns.get(model)
        if model == "solid3d" and n > CEILING_3D:
            v, why = "refuse", "ceiling"
        elif accepted is not None and n <= accepted:
            v, why = verdict(0.0, limit, secs), "slow"                          # Accepted by the caller whatever the memory
        else:
            v = verdict(est, limit, secs)
            why = v
        fit = (cell_that_fits(count, model, limit, cell_mm, base, mult, max_unknowns=CEILING_3D if model == "solid3d" else None)
               if v == "refuse" else None)
        msg = "" if v == "ok" else _message(model, n, est, limit, r, f, fit, cell_mm, why)
        low = avail is not None and est > avail and v != "refuse"
        if low:
            msg = (msg + "; " if msg else "") + f"the estimate of {est / GB:.1f} GB is above the {avail / GB:.1f} GB available now, the machine may swap"
        out.append(Verdict(model, n, est, limit, v, secs, fit, msg, low))
        log.info("memory guard: %s %d unknowns, estimate %.2f GB, limit %.2f GB, %s", model, n, est / GB, limit / GB, v)
    if refuse == "raise":
        for item in out:
            if item.verdict == "refuse":
                raise MemoryGuardError(item.message)
    return out


def log_peak(estimates: Sequence[Verdict]) -> None:
    """!
    @brief Log the measured peak of this process next to the largest estimate, so that other machines can check the law.
    @param estimates Verdicts returned by check for the run that has just ended.
    @return None.
    """
    peak = peak_rss_bytes()
    if peak is not None and estimates:
        log.info("memory guard: measured peak of the process %.2f GB, largest estimate %.2f GB", peak / GB, max(e.estimate for e in estimates) / GB)
