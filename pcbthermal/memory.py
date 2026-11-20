#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file memory.py
@brief Memory guard: the physical memory of the machine, the estimated peak memory of a solve, the verdict (ok, slow, refuse) and the cell that fits.
@details A sparse direct factorisation needs memory that grows faster than the number of unknowns, and the number is set by the cell the user chooses, so a fine cell
         could swap the machine or hang the program. This module estimates the peak of a solve **before anything is allocated** from the unknown count that the models
         already provide (`fvm.unknowns`, `fdm.unknowns`, `solid3d.unknowns`) and refuses a run above a fraction of the installed memory.

         The law, one per model (research/memory-guard README 14.2, fitted on 67 measured points of a 16 GB machine):

             peak = base + safety * factor * k1 * t_eff**a * N * (N / N_REF)**(p - 1),

         with N the unknowns, t = N / (nx ny) the nodes per plan cell and t_eff = min(t, cells / t) (a board that is very thick in layers is also thin in plan),
         `safety` the safety factor of the model and `factor` that of a time simulation or a profile run (1 for a steady solve).
         The vias of the FVM and FDM add a factor `1 + VIA_GAIN (1 - exp(-F / VIA_CELLS_REF))` on the allocated part, F the cells of their footprints (`via_cells`): the
         mean-potential couplings of viawell.py join the copper layers across the laminate nodes, and the factorisation of a board with vias took up to 1.6 times the memory
         of the same board without them in SuperLU's default mode (CO60 at 0.5 mm, 769 vias); in the symmetric mode that the solver now uses the excess is 0.82 to 1.09 times, and the gain is
         the small VIA_GAIN = 0.10 (if the solver ever falls back to the default mode the law does not cover the peaks of up to 4.75 times). A board without vias is unchanged.
         `base` is the resident size of the process read once (`baseline_bytes`: at the start of the calculation process, else at the first estimate; not the live size, which grows with the history; not multiplied by the factors: it is measured, not estimated). The coefficients are bytes of the algorithm, mostly independent of the machine, but they were
         measured on one machine and are logged against the measured peak after each run so that other machines can check them.

         Units: bytes inside the code; messages use GB of 10^9 bytes. No GUI import and no new dependency (the memory is read with the standard library).
"""

import contextlib
import logging
import math
import os
import subprocess
import sys
import threading
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Tuple

from .femcore import FEM_DIRECT_MAX, FEM_TRANSIENT_DIRECT_MAX
from .results import MODEL_FULL

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
# The FEM transient is NOT two factors (one factor or one hierarchy is alive, femcore.Stepper): a factor per solver path, applied to the steady law of that path (DESIGN.md 14.3).
# REFITTED from the measurements of `releases/2.9.0/fem-transient/scripts/measure_fem_transient_law.py` (15 fresh-process cases) and `measure_fem_transient_direct_limit.py`
# (example board, five cells), tree ec15bdc0, see `releases/2.9.0/fem-transient/MEASURED.md`: the factor is the largest measured ratio of the growth over the steady law of the path
# times 1.15. Direct: largest ratio 2.011 (example board 2 mm, 67 229 unknowns, a step response, 2.15 GB against 15.9 kB per unknown) times 1.15 = 2.31. CG: the ratio is taken
# over the law the time run uses (`estimate_bytes` model "fem_time_cg": the CG law WITHOUT the floor of the steady estimate at the direct limit) on the sizes where a run can take
# CG (above FEM_DIRECT_MAX): largest 1.10 (example board 1.6 mm, 106 122 unknowns, 0.90 GB) times 1.15 = 1.27 (review: the first refit, 1.22, took 1.065 over the floored steady law
# and left 11 % on that case). The earlier 2.0 for the direct path UNDER-predicted the 2.15 GB case. The direct law holds up to FEM_TRANSIENT_DIRECT_MAX (`estimate_bytes` model "fem_time").
FEM_TRANSIENT_FACTOR_CG = 1.27
FEM_TRANSIENT_FACTOR_DIRECT = 2.31
# Time of a FEM time simulation, from the same measurements (a model of the STEPPING: the build, 2 to 15 s, is the steady law's `TIME_LAWS["fem"]`). A run is a setup per stage (the
# factorisation on the direct path, the AMG hierarchy on CG) plus a cost per step. Direct: the factorisation of 20 930 / 32 637 / 46 644 / 67 229 / 106 122 unknowns took 0.54 / 1.31 /
# 3.09 / 7.31 / 10.95 s (superlinear fill), modelled as 7.31 s (n / 67 229)^1.7 (1.0 / 2.1 / 3.9 / 7.3 / 15.9 s: above every measured value); a step is 5 / 10 / 18 / 33 / 53 ms (0.25 to 0.5 us
# per unknown), modelled as 5.7e-7 s per unknown. CG: the hierarchy is 0.06 to 0.16 s (neglected: 0.2 s per stage) and a step takes 1.15 / 1.84 / 2.41 / 3.16 / 4.24 s with 330 to 475
# iterations (5.5e-5 to 4.0e-5 s per unknown), modelled as 6.0e-5 s per unknown. A profile run above FEM_RUN_SECONDS_MAX is refused with the ProfileError text (and the wall clock
# stops it at twice that); the step response of an animation is only warned "slow" (SLOW_SECONDS). FEM_RUN_SECONDS_MAX stays 10 minutes (review): a project saved with the FEM ticked
# also runs the FEM in its power profiles, inside Run simulation and without a progress of its own, so a longer run is refused rather than made to wait.
FEM_SETUP_SECONDS_DIRECT_REF = 7.31         # factorisation at FEM_SETUP_REF_UNKNOWNS unknowns, s
FEM_SETUP_REF_UNKNOWNS = 67229.0
FEM_SETUP_EXPONENT_DIRECT = 1.7
FEM_SETUP_SECONDS_CG = 0.2
FEM_STEP_SECONDS_DIRECT = 5.7e-7
FEM_STEP_SECONDS_CG = 6.0e-5
FEM_RUN_SECONDS_MAX = 600.0
SOR_BLOCK_SHARE = 0.25              # Share of the limit that ALL the dense SOR blocks together (the sum of 75 n^2) may take (sor_block_fits)
EXIT_CODE = 3                       # Exit code of the command line for a refusal (2 is argparse's usage error)
VIA_GAIN = 0.10                     # FVM and FDM: largest extra share of the allocated memory that the via couplings add. Fitted at 0.40 on the default SuperLU mode (CO60 striped 0.5 mm: 3.96 against 2.42 GB without vias), refitted at 0.10 on the symmetric mode of fvm.lu_factor (peak with vias 0.82 to 1.09 of the same board without them; worst underestimate 1.27 on 85 via cases)
VIA_CELLS_REF = 500.0               # Footprint cells at which the via term reaches 63 % of its gain (25 vias of 0.3 mm at 0.5 mm are 100 cells and measured nothing; CO60 is 2 500 to 5 400)
MEMORY_ENV = "PCBTHERMAL_MEMORY_BYTES"   # Environment variable that states the physical memory in bytes (tests, containers whose limit is not visible)

# FEM (releases/2.8.0/fem-model/scripts/measure_fem_law.py, 21 runs of 10 boards of the harness at 2, 1 and 0.5 mm, each in a fresh process, growth of the resident size over the build and the solve):
# conjugate gradients with pyamg 6410 to 6961 bytes per unknown (mean 6692, no trend with the size from 40 000 to 215 000 unknowns, vias, a block, an outline and one layer included),
# the direct solve 9552 to 12313 bytes per unknown at 10 000 to 19 000. The safety factor makes safety x k1 the largest measured growth times 1.1 (7657).
# The direct figure grows with the size (the fill of a 3D factor is superlinear): the review measured 11 388 to 14 402 bytes per unknown at 26 900 to 29 800 unknowns, just under
# FEM_DIRECT_MAX (the example board at 26 910 and the finned block at 29 413 above the first fit of 13 600), so the direct figure is 1.1 x 14 402.
FEM_K1 = 6700.0
FEM_SAFETY = 1.15
FEM_DIRECT_BYTES = 15900.0
# CONTINUOUS law of the review: model -> (k1 bytes per unknown at N_REF and t_eff = 1, exponent p in N, exponent a in t_eff, safety factor)
CONTINUOUS = {
    "fvm": (1469.0, 1.24, 0.79, 1.40),
    "fdm": (1228.0, 1.34, 1.03, 1.24),
    "solid3d": (1063.0, 1.30, 0.98, 1.30),
    # The FEM with conjugate gradients and an AMG preconditioner is linear in the unknowns (p = 1) and does not grow with the thickness of the graph (a = 0): bytes per unknown
    # (FEM_K1) and the safety factor that makes safety x k1 the largest measured growth times 1.1 (measure_fem_law.py, 21 runs of 10 boards); `FEM_DIRECT` is the direct solve
    "fem": (FEM_K1, 1.0, 0.0, FEM_SAFETY),
}

# Solve time law of the classes of README 5.4 (model -> list of (largest t, seconds at N_REF, exponent q)); the last row has no upper edge. Times of the
# measuring machine shared with other work, so lower bounds for a loaded one; only the "slow" mark uses them.
TIME_LAWS = {
    "fvm": [(3.5, 1.5, 1.32), (4.5, 5.4, 1.31), (math.inf, 9.2, 1.50)],
    "fem": [(math.inf, 15.7, 0.69)],             # build and CG + AMG solve of 13 runs (40 000 to 215 000 unknowns), measured with another job running: a lower bound
    "fdm": [(math.inf, 11.5, 1.47)],
    "solid3d": [(6.5, 11.2, 1.70), (12.0, 14.8, 1.52), (math.inf, 44.1, 1.50)],
}

# In a sentence ("the finite volume (FVM) model would have ..."): the full name of results.MODEL_FULL with a lower-case first letter
MODEL_LABELS = {k: (v[0].lower() + v[1:] if not v[0].isdigit() else v) for k, v in MODEL_FULL.items() if k in ("fvm", "fdm", "solid3d", "fem")}


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
    unknowns: int                     # Unknowns the model would build (a lower bound, said "at least" in the message, when the bound alone refused the run)
    estimate: float                   # Estimated peak in bytes
    limit: float                      # Limit in bytes
    verdict: str                      # "ok", "slow" or "refuse"
    seconds: float                    # Predicted solve time in s
    cell_fit: Optional[float]         # Smallest cell in mm that fits (None if none up to 50 mm, or if the run is not refused)
    message: str                      # Text for the user ("" when ok)
    exceeds_available: bool = False   # The estimate is above the memory available now (a warning, not a refusal)
    exact: bool = True                # False when unknowns and estimate are the lower bound (the exact count was not made because the bound alone was above the limit)


_fraction_override: Optional[float] = None       # Fraction forced for the process by the command line (None: the Preferences value, see default_fraction)
_accept_unknowns = {}                            # model -> unknowns accepted whatever the memory estimate (size_limit)


def ram_bytes() -> Optional[int]:
    """!
    @brief Physical memory the process may use, in bytes, read without a dependency; None if it cannot be read.
    @details os.sysconf (Linux, macOS), `sysctl -n hw.memsize` (macOS), /proc/meminfo (Linux), GlobalMemoryStatusEx by ctypes (Windows); the cgroup limit (v2, then v1)
             of a container lowers it because the host memory is not what the process may use. Only the cgroup files at the root of /sys/fs/cgroup are read (the view
             of a container); a limit set on a nested cgroup of the host (a systemd slice) is not seen. The environment variable MEMORY_ENV (bytes) replaces the
             reading: it is inherited by the calculation process, so a test battery or a container whose limit is not visible can state the memory of the machine.
    @return int bytes (> 0) or None.
    """
    forced = os.environ.get(MEMORY_ENV, "").strip()
    if forced:
        try:
            if int(float(forced)) > 0:
                return int(float(forced))
        except ValueError:
            log.warning("memory guard: %s=%r is not a number of bytes; the memory of the machine is read instead", MEMORY_ENV, forced)
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


_BASELINE: Optional[float] = None       # Resident size read once for the process, kept for every later estimate (see baseline_bytes)
_BASELINE_LOCK = threading.Lock()        # The first reading is made once even when two threads estimate at the same moment


def baseline_bytes() -> float:
    """!
    @brief The base of the estimates: the resident size of this process read ONCE, kept for the rest of its life.
    @details The live size (`resident_bytes`) grows with what the process has already solved (the allocator keeps pages: 0.08 GB when fresh, 0.67 GB after one 1 mm run
             of the CO60 import, 1.5 GB after a 0.7 mm run), and the calculation process of the window serves every job of the session, so the same problem at the same
             cell was `ok` in the panel (which counts a fixed base) and refused by the run for no reason but the history. The calculation process reads it at start-up,
             after its imports and before its first job (`jobs.serve`), so a job that runs without an estimate (the Power Calculator, an Analytic animation) cannot
             inflate it; any other process (command line, scripts) reads it at its first estimate. What is really held beside the unknowns (the masks of an import)
             is counted apart (`copper_run_bytes`, `check_import`).
    @return Bytes.
    """
    global _BASELINE
    if _BASELINE is None:
        with _BASELINE_LOCK:
            if _BASELINE is None:
                _BASELINE = resident_bytes()
    return _BASELINE


def reset_baseline() -> None:
    """!
    @brief Forget the baseline so that the next estimate reads the process again (tests that fake `resident_bytes`).
    @return None.
    """
    global _BASELINE
    _BASELINE = None


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
    @details A machine preference, not a property of a project: the process-wide override (command line `--memory-fraction`) wins, then the Preferences value
             `solver.memory_fraction` (the shipped defaults plus the user's file), then DEFAULT_FRACTION. A value out of range in the user's file is ignored.
    @return Fraction between MIN_FRACTION and MAX_FRACTION.
    """
    if _fraction_override is not None:
        return _fraction_override
    try:
        from . import defaults                                                  # Lazy: the module has no other need of the defaults
        value = float(defaults.load()["solver"].get("memory_fraction", DEFAULT_FRACTION))
    except (KeyError, TypeError, ValueError, OSError):
        return DEFAULT_FRACTION
    return value if MIN_FRACTION <= value <= MAX_FRACTION else DEFAULT_FRACTION


def set_default_fraction(fraction: Optional[float]) -> None:
    """!
    @brief Set the process-wide override of the fraction (None removes it: the Preferences value, then DEFAULT_FRACTION); used by the command line.
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


def estimate_bytes(model: str, unknowns: float, cells: float, base: Optional[float] = None, factor: float = 1.0, via_footprint_cells: float = 0.0) -> float:
    """!
    @brief Estimated peak memory of a solve, with the safety factor of the model.
    @details peak = base + safety * factor * k1 t_eff^a N (N / N_REF)^(p - 1). The safety and time factors multiply the part that the solve allocates, not the
             resident size the process already has: the base is measured, and a process that already holds memory (the test battery, a script after a large run)
             would otherwise see it counted 1.4 to 2.8 times (the research prototype multiplied a fixed base of 0.08 GB, where the difference was 0.03 to 0.14 GB).
    @param model "fvm", "fdm", "solid3d" or "fem".
    @param unknowns Unknowns the model builds (count, not bytes).
    @param cells Cells of the plan grid, nx * ny (the nodes of one layer for the FDM), count.
    @param base Resident bytes of the process (None: baseline_bytes(), the size read once for the process).
    @param factor Multiplier of a time simulation or profile run (TRANSIENT_FACTOR, PROFILE_FACTOR); 1 for a steady solve.
    @param via_footprint_cells Cells of the via footprints of the FVM or FDM (via_cells), count; 0 for no vias, which leaves the estimate unchanged. Ignored by the 3D solid.
    @return Bytes.
    @throws KeyError If the model has no law (lumped, analytic).
    """
    if model == "fem_time":
        # A FEM time run (femcore.Stepper): the direct factor up to FEM_TRANSIENT_DIRECT_MAX with its own law, the conjugate gradients above it. The direct law is the steady direct
        # bytes per unknown times FEM_TRANSIENT_FACTOR_DIRECT at EVERY size, the conservative top of the measured 15.3 to 29.3 kB per unknown (rising with the size: superlinear
        # fill; 32 kB at the worst case, 36.7 kB here); measured 3.11 GB at 106 122 unknowns against 3.90 GB here. No floor against the steady law (the search for a cell does not bisect)
        n = max(float(unknowns), 1.0)
        b = baseline_bytes() if base is None else base
        if n <= FEM_TRANSIENT_DIRECT_MAX:
            return b + FEM_DIRECT_BYTES * n * FEM_TRANSIENT_FACTOR_DIRECT
        return estimate_bytes("fem_time_cg", n, cells, b, 1.0, via_footprint_cells)
    if model == "fem_time_cg":
        # the conjugate-gradient time run, whatever the size (used above the direct limit, and below it when the direct factor does not fit the memory)
        k1c, pc, ac, sc = CONTINUOUS["fem"]
        nc = max(float(unknowns), 1.0)
        tc = nc / max(float(cells), 1.0)
        tc_eff = max(min(tc, float(cells) / tc), 1.0)
        return (baseline_bytes() if base is None else base) + k1c * tc_eff ** ac * nc * (nc / N_REF) ** (pc - 1.0) * sc * FEM_TRANSIENT_FACTOR_CG * via_gain("fem", via_footprint_cells)
    k1, p, a, safety = CONTINUOUS[model]
    n = max(float(unknowns), 1.0)
    if model == "fem" and n <= FEM_DIRECT_MAX:
        # Up to the direct-solve limit the FEM factorises (SuperLU): more bytes per unknown than the conjugate gradients, and the factor is the whole growth.
        # (a time run has its own law, model "fem_time", with the direct factor up to femcore.FEM_TRANSIENT_DIRECT_MAX, which may be above this steady limit)
        return (baseline_bytes() if base is None else base) + FEM_DIRECT_BYTES * n * factor
    t = n / max(float(cells), 1.0)
    t_eff = max(min(t, float(cells) / t), 1.0)
    b = baseline_bytes() if base is None else base
    grown = k1 * t_eff ** a * n * (n / N_REF) ** (p - 1.0) * safety * factor * via_gain(model, via_footprint_cells)
    if model == "fem":
        # The conjugate gradients take fewer bytes per unknown than the factorisation below FEM_DIRECT_MAX, but a mesh that has just crossed the limit is not estimated as
        # smaller than the one just under it: the estimate never decreases with the unknowns (the bisection of largest_unknowns relies on it)
        grown = max(grown, FEM_DIRECT_BYTES * FEM_DIRECT_MAX * factor)
    return b + grown


def via_gain(model: str, via_footprint_cells: float) -> float:
    """!
    @brief Multiplier of the allocated memory for the via couplings of the FVM and FDM (1 for no vias and for the 3D solid).
    @details 1 + VIA_GAIN (1 - exp(-F / VIA_CELLS_REF)): continuous, zero at no vias, saturating, so one via costs nothing and a board with thousands costs VIA_GAIN more.
             Fitted on boards whose vias are scattered (CO60) and checked on regular arrays; a regular array whose pitch is commensurate with the cell can need more
             (up to 4.2 times the law without vias in the study, research/memory-guard README), which no function of the via count predicts (see docs/theory.md 2.7).
    @param model "fvm", "fdm" or "solid3d".
    @param via_footprint_cells Cells of the via footprints, count.
    @return Multiplier, at least 1.
    """
    if model in ("solid3d", "fem") or via_footprint_cells <= 0.0:
        return 1.0
    return 1.0 + VIA_GAIN * (1.0 - math.exp(-float(via_footprint_cells) / VIA_CELLS_REF))


def via_cells(problem, cell_mm: float) -> float:
    """!
    @brief Cells of the via footprints of a problem at a cell size, counted without building the network.
    @details The footprint of a via (viawell.footprint) depends on its drill and on the cell, and on where its centre falls in the cell: the count is the mean over six offsets
             of a drill disc on a plane of full cover, cached by (drill, cell). Vias with the centre outside the board box are left out. Overlapping footprints are counted
             once per via (the sum, not the union: the two differ by less than a factor of 1.7 on the boards studied and the term saturates).
    @param problem A Problem.
    @param cell_mm Cell size in mm (the grid is round(size / cell) cells, as the models build it).
    @return Cells, a float (0 when the problem has no via).
    """
    vias = problem.vias
    if not vias:
        return 0.0
    b = problem.board
    nx = max(int(round(b.width * 1000.0 / cell_mm)), 2)
    ny = max(int(round(b.height * 1000.0 / cell_mm)), 2)
    dx, dy = b.width / nx, b.height / ny
    counts = {}
    for v in vias:
        # A via outside the board box conducts nothing (viawell.build skips it); the box test is a cheap upper bound of the exact test
        if 0.0 <= v.x <= b.width and 0.0 <= v.y <= b.height:
            key = round(v.diameter, 6)
            counts[key] = counts.get(key, 0) + 1
    return float(sum(n * _footprint_mean(d, dx, dy) for d, n in counts.items()))


_FOOTPRINT_CACHE = {}


def _footprint_mean(diameter: float, dx: float, dy: float) -> float:
    """!
    @brief Mean number of cells of the footprint of a via of a drill on a cell size, over six positions of its centre in the cell.
    @param diameter Drill diameter in m.
    @param dx Cell size along x in m.
    @param dy Cell size along y in m.
    @return Cells, a float (at least 1).
    """
    key = (round(diameter, 6), round(dx, 7), round(dy, 7))
    hit = _FOOTPRINT_CACHE.get(key)
    if hit is not None:
        return hit
    import numpy as np
    from . import viawell
    # A plane of full cover large enough for the enlarged footprint (the radius grows until the lattice radius is 0.78 r_via; 25 cells each way is far beyond it)
    cover = np.ones((50, 50))
    total, k = 0.0, 0
    for fx in (0.0, 0.25, 0.5):
        for fy in (0.0, 0.5):
            w, _r, _t = viawell.footprint((25.0 + fx) * dx, (25.0 + fy) * dy, diameter / 2.0, dx, 0.0, cover, dy, 0.0)
            total += max(len(w), 1)
            k += 1
    if len(_FOOTPRINT_CACHE) > 4096:
        _FOOTPRINT_CACHE.clear()
    _FOOTPRINT_CACHE[key] = total / k
    return total / k


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


def largest_unknowns(model: str, cells: float, limit: float, base: Optional[float] = None, factor: float = 1.0, via_footprint_cells: float = 0.0) -> int:
    """!
    @brief Largest unknown count whose estimate stays within a limit, at a given plan grid (bisection; the estimate grows with N).
    @param model "fvm", "fdm" or "solid3d".
    @param cells Cells of the plan grid, count.
    @param limit Limit in bytes.
    @param base Resident bytes of the process (None: read).
    @param factor Multiplier of a time simulation.
    @param via_footprint_cells Cells of the via footprints, count (0 for no vias).
    @return Unknown count (0 if even the base is above the limit).
    """
    b = baseline_bytes() if base is None else base
    if estimate_bytes(model, cells, cells, b, factor, via_footprint_cells) > limit:
        return 0
    lo, hi = float(cells), 1.0e10
    for _ in range(100):
        mid = math.sqrt(lo * hi)
        if estimate_bytes(model, mid, cells, b, factor, via_footprint_cells) <= limit:
            lo = mid
        else:
            hi = mid
    return int(lo)


def cell_that_fits(count: Callable[[float], Tuple[int, int]], model: str, limit: float, cell_mm: float, base: Optional[float] = None,
                   factor: float = 1.0, cell_max: float = 50.0, max_unknowns: Optional[float] = None,
                   bound: Optional[Callable[[float], Tuple[int, int]]] = None, vias: Optional[Callable[[float], float]] = None,
                   extra: Optional[Callable[[float], float]] = None) -> Optional[float]:
    """!
    @brief Smallest cell, grown in steps of 10 % and rounded up to 0.1 mm, not finer than cell_mm, whose model fits a limit (the refusal message and the Auto suggestion).
    @param count Function cell_mm -> (unknowns, plan cells), both counts.
    @param model "fvm", "fdm" or "solid3d".
    @param limit Limit in bytes.
    @param cell_mm Cell tried first, in mm.
    @param base Resident bytes of the process (None: baseline_bytes()).
    @param factor Multiplier of a time simulation.
    @param cell_max Largest cell tried, in mm.
    @param max_unknowns Also require at most this many unknowns (the ceiling of the 3D solid); None for no such bound.
    @param bound Optional cheap function cell_mm -> (lower bound of the unknowns, plan cells); a cell whose bound is already above the limit is skipped without the
                 exact count (which samples the copper of every cell and costs about 300 bytes per plan cell). The bound has no via term (a lower bound stays one).
    @param vias Optional function cell_mm -> cells of the via footprints (via_cells), applied to the exact estimate only; None for no vias.
    @param extra Optional function cell_mm -> bytes held beside the unknowns that depend on the cell (the raster of drawn copper with a cut cell, `drawn_run_bytes`), added to the
           base of the exact estimate as `check` adds it; None for none. Without it the cell proposed for a drawn board could be refused again by `check`.
    @return Cell in mm, or None if even cell_max does not fit.
    """
    b = baseline_bytes() if base is None else base
    c = max(cell_mm, 0.05)
    while c <= cell_max:
        if bound is not None:
            try:
                n0, cells0 = bound(c)
            except ValueError:
                c = math.ceil(c * 1.1 * 10.0) / 10.0
                continue
            if estimate_bytes(model, n0, cells0, b, factor) > limit or (max_unknowns is not None and n0 > max_unknowns):
                c = math.ceil(c * 1.1 * 10.0) / 10.0
                continue
        try:
            n, cells = count(c)
        except ValueError:                                  # a cell for which the model has no mesh (the FEM refusals): try a coarser one
            c = math.ceil(c * 1.1 * 10.0) / 10.0
            continue
        b_c = b + (extra(c) if extra is not None else 0.0)
        if estimate_bytes(model, n, cells, b_c, factor, vias(c) if vias is not None else 0.0) <= limit and (max_unknowns is None or n <= max_unknowns):
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
    @param base Resident bytes (None: baseline_bytes()).
    @return Bytes.
    """
    n = float(tiles) * layers
    b = baseline_bytes() if base is None else base
    return b + 4.0 * 8.0 * n * n + 2.0 * 8.0 * modes * tiles


def sor_block_bytes(n: int) -> float:
    """!
    @brief Memory of the dense inverse of one SOR block with the copies of the build (dense block, its inverse, the sparse form kept for the iterations, the LAPACK work).
    @param n Unknowns of the block, count.
    @return Bytes: 75 n^2 (measured 66 to 75 n^2, the largest used; 5 000 unknowns take about 1.9 GB).
    """
    return 75.0 * float(n) * float(n)


def sor_block_fits(n, limit: float, share: float = SOR_BLOCK_SHARE) -> bool:
    """!
    @brief Whether the SOR blocks may be inverted dense.
    @details The inverses of all the blocks stay for the iterations (as sparse matrices that hold every entry), and the dense inverses of all the blocks of one
             colour are alive at once while they are built, so the rule is on the sum of 75 n^2 over the blocks, not on the largest block alone (300 via blocks
             of 2 000 unknowns would keep about 14 GB although each block alone takes 0.3 GB). One block: 75 n^2.
    @param n Unknowns of one block (int) or a sequence of the unknowns of every block, counts.
    @param limit Limit in bytes of the memory guard.
    @param share Share of the limit the blocks may take.
    @return True if the sum of sor_block_bytes over the blocks is at most share x limit.
    """
    sizes = list(n) if hasattr(n, "__iter__") else [n]             # One count (also a NumPy integer) or a sequence of counts
    return sum(sor_block_bytes(int(k)) for k in sizes) <= share * limit


@contextlib.contextmanager
def accept_unknowns(model: str, max_unknowns: int):
    """!
    @brief Accept a model up to a number of unknowns whatever the memory estimate, and refuse it above that number, inside a with block (offline studies).
    @details The window is the old meaning of `solid3d.size_limit`: `size_limit(2_000_000)` lets a study solve large models on a large machine, and
             `size_limit(250_000)` keeps a study to the sizes it was written for (above the number the model is refused whatever the memory). The ceiling of
             the 3D solid is lifted to the number given when it is larger.
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


# Imported copper (copper.py). Measured on the implementation (scripts/study_import_memory.py of research/gerber-real-boards is the prototype's; the numbers below are those of
# the program: see docs/versions.md). Bytes per pixel of one mask.
IMPORT_DRAW_BYTES_PER_PIXEL = 3.0     # import: the layer being drawn, its outline mask, the copy made by the packing (the other layers are packed text)
IMPORT_OUTLINE_BYTES = 250.0e6        # import: the strips of the point-in-polygon test of a non-rectangular outline (measured on a 285 x 95 mm board: about 0.2 GB)
IMPORT_HELD_BYTES_PER_PIXEL = 1.0     # run: an unpacked mask kept by the cache (one byte per pixel and layer)
FACES_BYTES_PER_PIXEL = 40.0          # run: the face construction of the largest layer, per source pixel (measured 26 to 38: the float32 sheet, the resampling, the windows)
FACES_FIXED_BYTES = 50.0e6            # run: the local conduction problems of one batch of windows (WINDOW_BATCH_PIXELS pixels)


DRAWN_RASTER_BYTES_PER_PIXEL = 4.0    # run, drawn copper: the float32 coverage raster of a layer with a cut cell, kept for the run (copper.DRAWN_RASTER_BYTES_PER_PIXEL)
DRAWN_FACES_BYTES_PER_PIXEL = 80.0    # run, drawn copper: the construction of the raster and of the faces of the largest such layer, per pixel (measured: the FDM growth is 84 B per pixel in all, theory 2.7)
DRAWN_EXACT_CELLS = 4_000_000        # most plan cells for which `drawn_run_bytes` finds the layers with a cut cell exactly; above, every layer with a zone counts
DRAWN_FIXED_BYTES = 50.0e6            # run, drawn copper: the local conduction problems of one batch of windows


def drawn_run_bytes(problem, cell_mm: float) -> float:
    """!
    @brief Memory that the drawn copper adds to a FVM or FDM run: the float32 rasters of its layers that have a cell cut by a zone edge and the face construction of one layer.
    @details The raster has `copper.DRAWN_PIXELS_PER_CELL` ^ 2 pixels per cell. Zero for a board whose drawn layers have no cut cell (the earlier path), for imported copper alone and for a
             problem with no zone. It is the same model as the import's (`copper_run_bytes`) with the measured per-pixel terms of the drawn raster.
    @param problem A Problem.
    @param cell_mm Cell size of the run in mm.
    @return Bytes.
    """
    from . import copper
    b = problem.board
    nx = max(int(round(b.width * 1000.0 / cell_mm)), 2)
    ny = max(int(round(b.height * 1000.0 / cell_mm)), 2)
    if nx * ny > DRAWN_EXACT_CELLS:
        # Too many cells to find the cut layers (the exact areas of a 0.5 m board at 0.05 mm took 3 GB, before anything is refused): take every layer with a zone as cut, the bound
        src = copper.CopperSource.of(problem)
        imported = set(src.layers) if src is not None else set()               # (a mixed board: only the drawn layers carry the drawn raster)
        layers = {z.layer for z in problem.zones if z.layer not in imported}
    else:
        layers = copper.drawn_layer_cuts(problem, nx, ny)
    if not layers:
        return 0.0
    px = float(nx * ny) * copper.DRAWN_PIXELS_PER_CELL ** 2
    src = copper.CopperSource.of(problem)
    if src is not None:                                                        # a mixed board: the drawn rasters have the pixel grid of the import
        r, c = (int(v) for v in next(iter(src.entries.values()))["mask"]["shape"])
        px = float(r * c)
    return float(DRAWN_RASTER_BYTES_PER_PIXEL * px * len(layers) + DRAWN_FACES_BYTES_PER_PIXEL * px + DRAWN_FIXED_BYTES)


def copper_run_bytes(problem) -> float:
    """!
    @brief Memory that the imported copper of a problem adds to a run, besides the unknowns of the network: the unpacked masks held and the working set of the face construction.
    @details The masks are 1 byte per pixel and layer (kept unpacked by `copper.py`, at most its cache); the faces are built one layer at a time, 4 bytes per pixel of the
             float32 sheet and about as much again for the resampling, then released; the local problems of a batch of windows have a fixed size. Zero for a drawn board.
    @param problem A Problem.
    @return Bytes (0.0 without imported copper).
    """
    c = getattr(problem, "imported", None)
    if c is None:
        return 0.0
    from .copper import has_mask
    shapes = [tuple(e["mask"]["shape"]) for e in c.layers if has_mask(e)]
    if not shapes:
        return 0.0
    pixels = [r * q for r, q in shapes]
    held = IMPORT_HELD_BYTES_PER_PIXEL * sum(pixels)
    work = FACES_BYTES_PER_PIXEL * max(pixels) + (FACES_FIXED_BYTES if c.mapping != "fill" else 0.0)
    return float(held + work)


def import_draw_bytes(rows: int, cols: int, n_layers: int) -> float:
    """!
    @brief Estimated peak of drawing and packing the masks of an import (one layer at a time; the packed text of the other layers stays).
    @param rows Raster rows, count.
    @param cols Raster columns, count.
    @param n_layers Copper layers, count.
    @return Bytes, without the resident size of the process.
    """
    from .gerber import raster
    px = float(rows) * float(cols)
    side = min(raster.TILE_SUBPIXELS, max(rows, cols) * raster.DEFAULT_SUPERSAMPLE)
    working = side * min(raster.TILE_SUBPIXELS, min(rows, cols) * raster.DEFAULT_SUPERSAMPLE) * raster.WORKING_BYTES_PER_SUBPIXEL      # the rasteriser's tile
    return IMPORT_DRAW_BYTES_PER_PIXEL * px + working + IMPORT_OUTLINE_BYTES + (n_layers - 1) * px / 8.0     # (a packed layer is below 1/8 of its pixels in bytes on the boards measured)


def check_import(rows: int, cols: int, n_layers: int, cell_mm: float, fraction: Optional[float] = None, ram: Optional[int] = None, base: Optional[float] = None,
                 pixel_mm: Optional[float] = None) -> float:
    """!
    @brief Refuse an import whose masks would not fit in memory, BEFORE anything is drawn, and name the pixel that fits.
    @details Two peaks must fit: the draw and pack of one layer, and the run that follows (the unpacked masks and the face construction). Both are about proportional to
             the number of pixels, so the pixel that fits is the pixel times the square root of the ratio of the estimate to the room.
    @param rows Raster rows, count.
    @param cols Raster columns, count.
    @param n_layers Copper layers, count.
    @param cell_mm Cell of the thermal grid in mm (for the message).
    @param fraction Share of the physical memory allowed (None: default_fraction()).
    @param ram Physical memory in bytes (None: read it).
    @param base Resident bytes of the process (None: read it).
    @param pixel_mm Pixel of the raster in mm (for the message).
    @return Estimated peak in bytes (the larger of the two).
    @throws MemoryGuardError If it does not fit.
    """
    f = default_fraction() if fraction is None else fraction
    r = ram if ram is not None else ram_bytes()
    limit = limit_bytes(f, r)
    b = resident_bytes() if base is None else float(base)
    px = float(rows) * float(cols)
    draw = import_draw_bytes(rows, cols, n_layers)
    run = IMPORT_HELD_BYTES_PER_PIXEL * px * n_layers + FACES_BYTES_PER_PIXEL * px + FACES_FIXED_BYTES
    peak = b + max(draw, run)
    if peak > limit:
        room = max(limit - b - FACES_FIXED_BYTES, 1.0)
        need = max(draw, run - FACES_FIXED_BYTES)
        fit = (pixel_mm or 0.0) * math.sqrt(need / room)
        where = f" ({cols} × {rows} pixels of {pixel_mm:g} mm, {n_layers} layers)" if pixel_mm else f" ({cols} × {rows} pixels, {n_layers} layers)"
        src = f"{f * 100:.0f} % of the {r / GB:.1f} GB of memory" if r else "the fixed limit (the memory of the machine could not be read)"
        raise MemoryGuardError(f"the import{where} would need about {peak / GB:.1f} GB, more than the {limit / GB:.1f} GB allowed ({src})"
                               + (f"; use a pixel of {math.ceil(fit * 1000.0) / 1000.0:g} mm or more" if fit > 0 else ""))
    return peak


def _counter(problem, model: str, n_diel=None, fem_params=None) -> Callable[[float], Tuple[int, int]]:
    """!
    @brief Function cell_mm -> (unknowns, plan cells) of a model, from the model's own counter.
    @param problem A Problem.
    @param model "fvm", "fdm", "solid3d" or "fem".
    @param n_diel Slabs across the dielectric gaps of the 3D solid: None (the rule of solid3d.slabs_per_gap), an int for every gap or a list per gap, count.
    @param fem_params Tuple (elements across a dielectric gap, refinement ratio) of the FEM, or None for the defaults (6, 2).
    @return Callable (the FEM one raises ValueError, with the reason, for a problem that has no mesh).
    """
    from . import fdm, femmesh, fvm, solid3d
    if model == "fem":
        gap, ref = fem_params or (6, 2.0)
        return lambda c: (lambda r: (int(r[0]), int(r[2]) * int(r[3])))(femmesh.unknowns(problem, c, gap, ref))
    if model == "fvm":
        return lambda c: (lambda r: (int(r[0]), int(r[2]) * int(r[3])))(fvm.unknowns(problem, c))
    if model == "fdm":
        return lambda c: (lambda r: (int(r[0]), int(r[2]) * int(r[3])))(fdm.unknowns(problem, c))
    return lambda c: (lambda r: (int(r[0]), int(r[2]) * int(r[3])))(solid3d.unknowns(problem, c, n_diel))


def _bound(problem, model: str, n_diel=None, fem_params=None) -> Callable[[float], Tuple[int, int]]:
    """!
    @brief Function cell_mm -> (lower bound of the unknowns, plan cells) of a model, without sampling the copper: one node per copper layer and plan cell
           (FVM), per corner node (FDM), or the exact slab count (3D solid, already cheap).
    @details The estimate grows with N at fixed plan cells (k1 t_eff^a N^p with p > a for every model), so a bound above the limit refuses the run without the
             exact count, whose copper sampling takes about 300 bytes per plan cell (0.31 GB for a million plan cells; tens of GB for a 0.5 m board at 0.05 mm).
    @param problem A Problem.
    @param model "fvm", "fdm" or "solid3d".
    @param n_diel Slabs across the dielectric gaps of the 3D solid: None (the rule of solid3d.slabs_per_gap), an int for every gap or a list per gap, count.
    @param fem_params Tuple (elements across a dielectric gap, refinement ratio) of the FEM, or None for the defaults.
    @return Callable.
    """
    b = problem.board

    def grid(c):
        """!
        @brief Plan grid of a cell size.
        @param c Cell size in mm.
        @return Tuple (nx, ny).
        """
        # The plan grid of the FVM and the 3D solid (round(width / cell), at least 2), as their counters
        return max(int(round(b.width * 1000.0 / c)), 2), max(int(round(b.height * 1000.0 / c)), 2)

    if model == "fvm":
        return lambda c: (lambda g: (b.layers * g[0] * g[1], g[0] * g[1]))(grid(c))
    if model == "fdm":
        return lambda c: (lambda g: (b.layers * (g[0] + 1) * (g[1] + 1), (g[0] + 1) * (g[1] + 1)))(grid(c))
    return _counter(problem, model, n_diel, fem_params)       # the exact 3D and FEM counts are cheap (slabs and the 2D plan, no 3D arrays)


def _message(model: str, n: int, estimate: float, limit: float, ram: Optional[int], fraction: float, cell_fit: Optional[float], cell_mm: float, why: str,
             exact: bool = True) -> str:
    """!
    @brief Text of a refusal or a warning, in GB of 10^9 bytes, naming the cell that fits.
    @param model "fvm", "fdm", "solid3d" or "fem".
    @param n Unknowns, count.
    @param estimate Estimated peak in bytes.
    @param limit Limit in bytes.
    @param ram Physical memory in bytes or None.
    @param fraction Share of the physical memory used for the limit.
    @param cell_fit Cell that fits in mm or None.
    @param cell_mm Cell requested, in mm.
    @param why "refuse", "slow", "ceiling" or "window" (above the unknowns accepted by a with block of accept_unknowns).
    @param exact False when n and the estimate come from the lower bound (the exact count was not made because the bound is already above the limit).
    @return Text (counts without a thousands separator, the rule of every number shown by the program).
    """
    label = MODEL_LABELS.get(model, model)
    src = f"{fraction * 100:.0f} % of the {ram / GB:.1f} GB of memory" if ram else "the fixed limit (the memory of the machine could not be read)"
    least = "" if exact else "at least "
    if why == "ceiling":
        head = f"the {label} model would have {n} unknowns, more than the {CEILING_3D} that no machine is asked to solve"
    elif why == "window":
        head = f"the {label} model would have {n} unknowns, more than the {_accept_unknowns.get(model, 0)} accepted by this study (solid3d.size_limit)"
    elif why == "refuse":
        head = (f"the {label} model would have {least}{n} unknowns and need {least or 'about '}{estimate / GB:.1f} GB at the cell of {cell_mm:g} mm, "
                f"more than the {limit / GB:.1f} GB allowed ({src})")
    else:
        head = f"the {label} model has {n} unknowns: about {estimate / GB:.1f} GB of memory and a solve that may take more than {SLOW_SECONDS:.0f} s"
    if why == "slow":
        return head
    return head + (f"; use a cell of {cell_fit:.1f} mm or more" if cell_fit else "; no cell up to 50 mm fits")


def fem_time_law(unknowns: float, cells: float, base: Optional[float], limit: float) -> str:
    """!
    @brief The law of a FEM time run: "fem_time" (the direct factor) while it fits the memory limit, "fem_time_cg" when the mesh is above the transient direct limit or the direct factor
           would not fit and the conjugate gradients (which take about a tenth of the bytes, at the price of the iterations at every step) would.
    @details `fem._prepare_time` takes the same decision, so that the guard and the stepper agree: a mesh at or below the steady direct limit is always direct.
    @param unknowns Unknowns of the mesh, count.
    @param cells Plan cells, count.
    @param base Resident bytes of the process (None: baseline_bytes()).
    @param limit Limit in bytes left for the solve: the memory limit less the frames the run holds (the guard adds the frames to the estimate after the choice).
    @return "fem_time" or "fem_time_cg".
    """
    n = float(unknowns)
    if n <= FEM_DIRECT_MAX:
        return "fem_time"
    if n > FEM_TRANSIENT_DIRECT_MAX or estimate_bytes("fem_time", n, cells, base) > limit:
        return "fem_time_cg"
    return "fem_time"


def fem_transient_factor(unknowns: float) -> float:
    """!
    @brief Multiplier of the steady law for a FEM time simulation, by the solver path the stepper will take for that many unknowns.
    @param unknowns Unknowns of the FEM mesh, count.
    @return float FEM_TRANSIENT_FACTOR_DIRECT up to FEM_TRANSIENT_DIRECT_MAX, otherwise FEM_TRANSIENT_FACTOR_CG.
    """
    return FEM_TRANSIENT_FACTOR_DIRECT if unknowns <= FEM_TRANSIENT_DIRECT_MAX else FEM_TRANSIENT_FACTOR_CG


def fem_transient_seconds(unknowns: float, steps: float, stages: float = 1.0) -> float:
    """!
    @brief Predicted seconds of the time stepping of a FEM run (without the build): a setup per stage (factorisation or hierarchy) plus a cost per step, by solver path.
    @details The numbers are the model fitted to the measured table (see the constants above and `releases/2.9.0/fem-transient/MEASURED.md`).
    @param unknowns Unknowns of the FEM mesh, count.
    @param steps Time steps of the run, count.
    @param stages Matrices factored or hierarchies built, count (a power-step response has 10 stages and the steady solve; a profile run has the steady solve and one step matrix).
    @return float Seconds.
    """
    n = float(unknowns)
    if n <= FEM_TRANSIENT_DIRECT_MAX:
        setup = FEM_SETUP_SECONDS_DIRECT_REF * (n / FEM_SETUP_REF_UNKNOWNS) ** FEM_SETUP_EXPONENT_DIRECT
        return stages * setup + n * float(steps) * FEM_STEP_SECONDS_DIRECT
    return stages * FEM_SETUP_SECONDS_CG + n * float(steps) * FEM_STEP_SECONDS_CG


def check(problem, models: Sequence[str], cell_mm: float, fraction: Optional[float] = None, transient: bool = False,
          factor: Optional[float] = None, refuse: str = "raise", ram: Optional[int] = None, available: Optional[int] = None,
          base: Optional[float] = None, n_diel=None, quiet: bool = False,
          laminate_params: Optional[Tuple[float, int]] = None, fem_params: Optional[Tuple[int, float]] = None, frames_bytes: float = 0.0) -> List[Verdict]:
    """!
    @brief The entry the callers use: count the unknowns of every selected model that has a law, estimate the peak and give the verdicts, before anything is allocated.
    @details The LPTN and Analytic models are not checked here: their arrays are small (455 bytes per unknown measured for the LPTN) and the Analytic has its own guard of
             4 800 tile unknowns in `viaconstriction`. Inside a with block of `accept_unknowns` a model is never refused on memory up to the number given
             (it may still be "slow") and always refused above it. The layered models are first estimated from a lower bound of their unknowns (one node per
             copper layer and plan cell): a bound above the limit refuses without the exact count, which samples the copper of every plan cell.
    @param problem A Problem.
    @param models Model keys of the run; only "fvm", "fdm", "solid3d" and "fem" are estimated.
    @param cell_mm Cell size in mm that the run will use.
    @param fraction Share of the physical memory allowed (None: default_fraction()).
    @param transient True for a time simulation or an animation (factor TRANSIENT_FACTOR).
    @param factor Explicit multiplier of the peak, overrides transient (PROFILE_FACTOR for a profile run).
    @param refuse "raise" raises MemoryGuardError for the first refused model; "return" only returns the verdicts (the caller decides).
    @param ram Physical memory in bytes (None: read it); for tests with a fake machine.
    @param available Memory available now in bytes (None: read it); for tests.
    @param base Resident bytes the solving process will have (None: baseline_bytes(), this process read once; the window passes BASE_DEFAULT, since the solve runs in the
                calculation process and not in the window's).
    @param n_diel Slabs across the dielectric gaps of the 3D solid (Solid's own argument): None for the rule of solid3d.slabs_per_gap, an int or a list per gap, count.
    @param quiet True for a check that is not a run (the solver panel at every edit, the Auto cell): no log lines, so that the log holds the estimates of the runs only.
    @param laminate_params Tuple (s_max in m, n_max) of the laminate rule the run will use (SolverOptions.laminate_params()), or None for the values in force: the sub-gaps add
                           node layers, so they change the unknowns that are counted.
    @param fem_params Tuple (elements across a dielectric gap, refinement ratio) of the FEM mesh (SolverOptions.fem_gap_elements, fem_refine), or None for the defaults (6, 2).
    @param frames_bytes Bytes of the output frames a FEM time run holds (n_out x layers x ny x nx float64), added to the FEM estimate and NOT multiplied by the time factor.
    @return List of Verdict, one per checked model. A problem that has no FEM mesh (a slanted outline, too many break lines) is a "refuse" verdict of the FEM whose message is the reason.
    @throws MemoryGuardError If refuse is "raise" and a model is refused.
    """
    from . import laminate
    with laminate.using(*(laminate_params or (None, None))):
        return _check(problem, models, cell_mm, fraction, transient, factor, refuse, ram, available, base, n_diel, quiet, fem_params, frames_bytes)


def _check(problem, models, cell_mm, fraction, transient, factor, refuse, ram, available, base, n_diel, quiet, fem_params=None, frames_bytes=0.0) -> List[Verdict]:
    """!
    @brief Body of check(), run with the laminate numbers in force.
    @param problem A Problem.
    @param models Model keys of the run.
    @param cell_mm Cell size in mm.
    @param fraction Share of the physical memory allowed (None: default).
    @param transient True for a time simulation or an animation.
    @param factor Explicit multiplier of the peak (None: from transient).
    @param refuse "raise" or "return".
    @param ram Physical memory in bytes (None: read).
    @param available Memory available now in bytes (None: read).
    @param base Resident bytes of the solving process (None: baseline_bytes()).
    @param n_diel Slabs across the dielectric gaps of the 3D solid: None (the rule of solid3d.slabs_per_gap), an int for every gap or a list per gap, count.
    @param quiet True: no log lines.
    @param fem_params Tuple (elements across a dielectric gap, refinement ratio) of the FEM, or None.
    @param frames_bytes Bytes of the FEM output frames (see check).
    @return List of Verdict.
    """
    f = default_fraction() if fraction is None else fraction
    mult = factor if factor is not None else (TRANSIENT_FACTOR if transient else 1.0)
    time_run = factor is not None or transient                                  # a time simulation or a profile run: the FEM has its own factor per solver path
    r = ram if ram is not None else ram_bytes()
    limit = limit_bytes(f, r)
    avail = available if available is not None else available_bytes()
    base = (baseline_bytes() if base is None else float(base)) + copper_run_bytes(problem)       # The imported masks and the face construction are held beside the unknowns
    out: List[Verdict] = []
    for model in models:
        if model not in CONTINUOUS:
            continue
        count, bound = _counter(problem, model, n_diel, fem_params), _bound(problem, model, n_diel, fem_params)
        accepted = _accept_unknowns.get(model)
        try:
            n, cells = bound(cell_mm)
        except ValueError as exc:
            # The FEM has no mesh for this problem (a slanted outline, too many break lines, a cell that is too fine): a refusal of that model with the reason
            out.append(Verdict(model, 0, 0.0, limit, "refuse", 0.0, None, str(exc), False, True))
            continue
        exact = model in ("solid3d", "fem")                                     # The 3D and FEM counts are exact and cheap; the layered ones sample the copper
        # A FEM time run has its own law (direct factor above the steady limit, factor per path). The frames are added to the estimate below, so the path is chosen against the
        # limit less the frames: a direct factor that fits only without them falls back to CG instead of refusing a run that CG would take (fem._check_transient does the same)
        law = fem_time_law(n, cells, base, limit - frames_bytes) if (model == "fem" and time_run) else model
        if accepted is not None or estimate_bytes(law, n, cells, base, 1.0 if law == "fem_time" else mult) <= limit:
            n, cells = count(cell_mm)                                           # The bound fits (or the caller sets a window): count exactly
            exact = True
        layered = model in ("fvm", "fdm")
        vc = via_cells(problem, cell_mm) if layered and exact else 0.0                   # The via term goes with the exact count; the bound stays a lower bound
        # The raster of a drawn layer with a cut cell is held beside the unknowns (FVM and FDM, exact count only; the search for the cell that fits adds it at every cell it tries)
        drawn = drawn_run_bytes(problem, cell_mm) if layered and exact else 0.0
        law = fem_time_law(n, cells, base, limit - frames_bytes) if (model == "fem" and time_run) else model
        m_mult = 1.0 if law.startswith("fem_time") else mult
        est = estimate_bytes(law, n, cells, base + drawn, m_mult, vc) + (frames_bytes if model == "fem" else 0.0)
        secs = estimate_seconds(model, n, cells) * (mult if mult > 1.0 else 1.0)
        if model == "solid3d" and n > CEILING_3D:
            v, why = "refuse", "ceiling"
        elif accepted is not None:
            # A window set by the caller (solid3d.size_limit): accepted up to it whatever the memory, refused above it
            v, why = ("refuse", "window") if n > accepted else (verdict(0.0, limit, secs), "slow")
        else:
            v = verdict(est, limit, secs)
            why = v
        fit = (cell_that_fits(count, law, math.inf if accepted is not None else limit, cell_mm, base, m_mult, max_unknowns=accepted if accepted is not None else
                              (CEILING_3D if model == "solid3d" else None), bound=bound,
                              vias=(lambda c, _p=problem: via_cells(_p, c)) if layered else None,
                              extra=(lambda c, _p=problem: drawn_run_bytes(_p, c)) if layered else None)
               if v == "refuse" else None)
        msg = "" if v == "ok" else _message(model, n, est, limit, r, f, fit, cell_mm, why, exact)
        low = avail is not None and est > avail and v != "refuse"
        if low:
            msg = (msg + "; " if msg else "") + f"the estimate of {est / GB:.1f} GB is above the {avail / GB:.1f} GB available now, the machine may swap"
            if not quiet:
                log.warning("memory guard: %s", msg)                            # Also in the log: the animation job has no warnings list to carry it
        out.append(Verdict(model, n, est, limit, v, secs, fit, msg, low, exact))
        if not quiet:
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
