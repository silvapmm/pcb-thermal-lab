#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file sitecustomize.py
@brief Run a study on the 2.9.0 tree with the time stepping of 2.8.0, to explain a transient shift (DECISION.md 4).

@details Put this folder FIRST on PYTHONPATH (before the tree): Python imports `sitecustomize` at start-up, and this
one wraps `fvm.solve_transient`, `fvm.transient_from_network` and `fdm.solve_transient` so that an argument the caller
did not give takes its 2.8.0 value: `theta_scheme` 1.0 (implicit Euler), `first_stage_split` 1, `rannacher` False
(`fix/transient-default-stepping`: these give the old stepping bit for bit). An argument the caller gave is kept. A
transient number of a study that shifts between the tree and v2.8.0 is EXPLAINED by the stepping item only when the
tree with this shim prints it bit-identical to v2.8.0. Nothing of the program is edited; the FEM is not wrapped (its
time simulation is new in 2.9.0).
"""
import functools
import inspect

OLD = {"theta_scheme": 1.0, "first_stage_split": 1, "rannacher": False}


def old_defaults(func):
    """!
    @brief Wrap a transient entry so the arguments its caller left out take their 2.8.0 values.

    @param func  The program function to wrap.

    @return callable The wrapper (same signature by `functools.wraps`).
    """
    sig = inspect.signature(func)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        """!
        @brief Call the wrapped function with the 2.8.0 stepping for every argument left out.

        @param args    Positional arguments of the caller.
        @param kwargs  Keyword arguments of the caller.

        @return object What the wrapped function returns.
        """
        bound = sig.bind_partial(*args, **kwargs)
        for name, value in OLD.items():
            # Only what the caller left to the default changes; an explicit choice of the study is its own
            if name in sig.parameters and name not in bound.arguments:
                kwargs[name] = value
        return func(*args, **kwargs)

    return wrapper


def install():
    """!
    @brief Replace the transient entries of fvm and fdm by their old-default wrappers.

    @return None
    """
    from pcbthermal import fdm, fvm
    fvm.transient_from_network = old_defaults(fvm.transient_from_network)
    fvm.solve_transient = old_defaults(fvm.solve_transient)
    fdm.solve_transient = old_defaults(fdm.solve_transient)


try:
    install()
except ImportError:
    # A tree without the program on the path (the v2.8.0 copy is never run with this shim)
    pass
