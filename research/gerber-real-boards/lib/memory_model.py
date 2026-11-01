#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file memory_model.py
@brief Measuring the memory of a solve and fitting the memory per unknown, to feed the program's memory guard.
@details The guard of the program (docs/versions.md, chapter "Planned") needs a number of bytes per unknown. The older coefficients (research/solid3d-verification/docs/for-the-project-documents.md)
         were measured before the laminate nodes of the rule existed and on plain boards; an import makes boards whose unknowns are mostly in cells with fine copper. Each case is run in a fresh child
         process (scripts/study_time_memory.py --case) so that the peak resident size of the process is the peak of that case; this module has the helpers: the peak size, the fit and the guard's estimate.
"""

import resource
import sys

import numpy as np


def peak_rss_bytes():
    """!
    @brief The peak resident set size of this process so far.
    @return int bytes (macOS reports bytes, Linux kilobytes; both are handled).
    """
    v = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(v if sys.platform == "darwin" else v * 1024)


def fit_bytes_per_unknown(unknowns, peak_bytes, baseline_bytes=0.0):
    """!
    @brief The memory per unknown from a set of runs: least-squares slope through the origin of (peak - baseline) against the unknowns, and the relative scatter.
    @param unknowns Array of unknown counts (one per run).
    @param peak_bytes Array of peak resident sizes (bytes), same length.
    @param baseline_bytes Resident size of the process before the model is built (interpreter, NumPy, SciPy, the mask), subtracted.
    @return dict with bytes_per_unknown, max_relative_deviation (largest |measured / fitted - 1|), n.
    @throws ValueError If the arrays are empty or of different length.
    """
    u, m = np.asarray(unknowns, float), np.asarray(peak_bytes, float) - baseline_bytes
    if u.size == 0 or u.size != m.size:
        raise ValueError("need the same non-zero number of unknown counts and peak sizes")
    k = float((u * m).sum() / (u * u).sum())
    dev = float(np.max(np.abs(m / (k * u) - 1.0)))
    return {"bytes_per_unknown": k, "max_relative_deviation": dev, "n": int(u.size)}


def guard_estimate_gb(unknowns, bytes_per_unknown, baseline_gb=0.5):
    """!
    @brief The memory the guard would estimate for a model.
    @param unknowns Number of unknowns.
    @param bytes_per_unknown Fitted coefficient.
    @param baseline_gb Fixed part (interpreter, libraries, the imported masks) in GB.
    @return float GB.
    """
    return baseline_gb + unknowns * bytes_per_unknown / 1e9
