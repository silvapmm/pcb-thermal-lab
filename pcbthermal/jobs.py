"""!
@file jobs.py
@brief Calculations run by the application in a separate process (no Qt imports), so they can be cancelled and never outlive the program.

@details The application starts one calculation process (gui/compute.py) that serves the jobs below one at a time. A job is a function
         job(progress, *args) that returns its result; `progress(message, fraction)` reports the state to the window.
         Everything passed in and out is pickled, so arguments must be plain data (Problem, SolverOptions, dicts).
"""

from . import analytic, fdm, fvm, profiles
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
    if model == "analytic":
        # The closed-form model needs neither a scheme nor a step; it takes the frames and the spacing
        kw.pop("theta_scheme", None)
        return analytic.solve_transient(problem, **kw)
    if model == "fdm":
        return fdm.solve_transient(problem, **kw)
    return fvm.solve_transient(problem, **kw)


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
    resp = step_response(problem, ref, options)
    return resp, profiles.decide(problem, resp, options.profile.threshold_c), ref


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


JOBS = {"simulate": job_simulate, "transient": job_transient, "analyze": job_analyze, "sleep": job_sleep}


def serve(tasks, results):
    """!
    @brief Body of the calculation process: execute jobs from the task queue until a None arrives.
    @param tasks Queue of (job id, job name, args) tuples or None.
    @param results Queue receiving (job id, kind, payload) with kind progress, done or failed.
    """
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
