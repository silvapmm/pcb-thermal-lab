#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file jobs.py
@brief Calculations run by the application in a separate process (no Qt imports), so they can be cancelled and never outlive the program.

@details The application starts one calculation process (gui/compute.py) that serves the jobs below one at a time. A job is a function
         job(progress, *args) that returns its result; `progress(message, fraction)` reports the state to the window.
         Everything passed in and out is pickled, so arguments must be plain data (Problem, SolverOptions, dicts).
"""

from . import analytic, fdm, fvm, memory, profiles
from .api import TIME_MODELS, simulate, step_response


def job_simulate(progress, problem, options):
    """!
    @brief Run api.simulate.
    @param progress Callable progress(message, fraction).
    @param problem Problem.
    @param options SolverOptions.
    @return Simulation.
    """
    return simulate(problem, options, progress=progress)


def job_transient(progress, problem, kwargs):
    """!
    @brief Power-step transient of the chosen model (animation tab).
    @param progress Callable progress(message, fraction) (unused: the solvers report nothing).
    @param problem Problem.
    @param kwargs Arguments of the transient solver; the key "model" picks fvm (default), fdm or analytic.
    @return Transient result of the solver.
    """
    kw = dict(kwargs)
    model = kw.pop("model", "fvm")
    lam = kw.pop("laminate", None)                  # (s_max in m, n_max) of the run's options, or None for the defaults
    if lam is not None:
        from . import laminate
        with laminate.using(*lam):                  # The network, the guard and the solve all see the same laminate rule
            return job_transient(progress, problem, dict(kw, model=model))
    # The animation holds the matrix factor and the frames: checked before anything is allocated. The window checks it too before it sends the job (so the
    # message comes at once); this check covers the other callers, and a refusal here comes back as the job's error text. The fraction is the default one
    # (the Preferences value: the kwargs carry no SolverOptions).
    verdicts = memory.check(problem, (model,), kw.get("cell_mm", 2.0), transient=True) if model in ("fvm", "fdm") else []
    if model == "analytic":
        # The closed-form model needs neither a scheme nor a step; it takes the frames and the spacing
        kw.pop("theta_scheme", None)
        return analytic.solve_transient(problem, **kw)
    result = fdm.solve_transient(problem, **kw) if model == "fdm" else fvm.solve_transient(problem, **kw)
    memory.log_peak(verdicts)                                   # Estimate and measured peak side by side, once per animation
    return result


def job_analyze(progress, problem, options):
    """!
    @brief Step response of the reference model and the average-or-resolve decisions (power profile tab).
    @param progress Callable progress(message, fraction) (unused).
    @param problem Problem.
    @param options SolverOptions.
    @return Tuple (StepResponse, list of HeaterDecision, name of the reference model).
    @throws ValueError If no model able to run in time is selected.
    """
    ref = next((m for m in TIME_MODELS if m in options.models), None)
    if ref is None:
        raise ValueError("select a model first")
    if ref in ("fvm", "fdm"):
        memory.check(problem, (ref,), max(options.cell_mm, 2.0), fraction=options.memory_fraction, factor=memory.PROFILE_FACTOR,
                     laminate_params=options.laminate_params())   # The step responses run on a cell of at least 2 mm
    resp = step_response(problem, ref, options)
    return resp, profiles.decide(problem, resp, options.profile.threshold_c), ref


def job_inverse(progress, problem, index, measured_c, point, ambient_c, cell_mm, psi_jt=0.0, band=False, uncertainty=None, laminate_params=None):
    """!
    @brief Power of a part from a measured temperature (inverse.power_from_temperature).
    @param progress Callable progress(message, fraction) (unused).
    @param problem Problem.
    @param index Heater index.
    @param measured_c Measured temperature in degC.
    @param point "max", "mean", "ring", "junction" or "top".
    @param ambient_c Ambient of the measurement in degC.
    @param cell_mm Cell size in mm.
    @param psi_jt Datasheet psi_JT in K/W for the point "top".
    @param band True to also compute the uncertainty band (inverse.power_band).
    @param uncertainty Optional dict of uncertainties for the band (see inverse.power_band).
    @param laminate_params Tuple (s_max in m, n_max) of the project's laminate rule (SolverOptions.laminate_params()), or None for the defaults: the board model run backwards
                           must be the board of the run.
    @return Dict of inverse.power_from_temperature, or of inverse.power_band with the band.
    """
    from .inverse import power_band, power_from_temperature
    if laminate_params is not None:
        from . import laminate
        with laminate.using(*laminate_params):
            return job_inverse(progress, problem, index, measured_c, point, ambient_c, cell_mm, psi_jt, band, uncertainty)
    if band:
        return power_band(problem, index, measured_c, point=point, ambient_c=ambient_c, cell_mm=cell_mm, psi_jt=psi_jt, uncertainty=uncertainty, progress=progress)
    return power_from_temperature(problem, index, measured_c, point=point, ambient_c=ambient_c, cell_mm=cell_mm, psi_jt=psi_jt)


def job_sleep(progress, seconds):
    """!
    @brief Wait, reporting progress (used by the tests of cancellation).
    @param progress Callable progress(message, fraction).
    @param seconds Duration in seconds.
    @return The duration.
    """
    import time
    t0 = time.time()
    while time.time() - t0 < seconds:
        progress("Waiting", min((time.time() - t0) / seconds, 1.0))
        time.sleep(0.05)
    return seconds


JOBS = {"inverse": job_inverse, "simulate": job_simulate, "transient": job_transient, "analyze": job_analyze, "sleep": job_sleep}


def _watch_parent():
    """!
    @brief Stop this process as soon as the process that started it is gone (killed, crashed or closed without a clean shutdown).
    @details Without it a calculation process would wait for jobs forever after its application died.
    """
    import multiprocessing
    import os
    import time
    parent = multiprocessing.parent_process()
    while parent is not None:
        time.sleep(1.0)
        if not parent.is_alive():
            os._exit(0)


def serve(tasks, results):
    """!
    @brief Body of the calculation process: execute jobs from the task queue until a None arrives.
    @param tasks Queue of (job id, job name, args) tuples or None.
    @param results Queue receiving (job id, kind, payload) with kind progress, done or failed.
    """
    import threading
    threading.Thread(target=_watch_parent, daemon=True).start()
    # The base of every memory estimate of the session: the size after the imports, before any job (a job that runs without an estimate, the Power
    # Calculator for one, would otherwise leave its pages in the first reading)
    memory.baseline_bytes()
    while True:
        item = tasks.get()
        if item is None:
            return
        job_id, name, args = item
        try:
            out = JOBS[name](lambda message, fraction, j=job_id: results.put((j, "progress", (message, float(fraction)))), *args)
            results.put((job_id, "done", out))
        except Exception as exc:                       # Any solver or validation error goes back to the window
            results.put((job_id, "failed", str(exc)))
