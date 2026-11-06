#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file uicontext.py
@brief Where the user changes a setting depends on the front end: the warnings name a control of the window ('gui') or an option of the command line ('cli').
@details Every message that tells the user to change the cell size or the laminate rule is built from ONE source string, with the place of the control taken from
         here at the moment the message is made, so that the application never names a command-line flag and the command line never names a dock. The context is
         thread-local: `using_ui` sets it around a block (checks.check_input, api.simulate with `SolverOptions.ui`), and the default is 'cli' (the API and the
         command line).
"""

import threading
from contextlib import contextmanager

UIS = ("gui", "cli")                             # The two front ends
_state = threading.local()                       # Thread-local, so that parallel runs do not see each other's context


def current():
    """!
    @brief The context in force in this thread.
    @return 'gui' or 'cli' ('cli' when none was set).
    """
    return getattr(_state, "ui", "cli")


@contextmanager
def using_ui(ui):
    """!
    @brief Set the context for a block of this thread; None keeps the one in force.
    @param ui 'gui', 'cli' or None.
    @return Context manager.
    @throws ValueError If ui is not one of UIS or None.
    """
    if ui is not None and ui not in UIS:
        raise ValueError(f"ui must be one of {UIS}")
    old = current()
    _state.ui = ui or old
    try:
        yield
    finally:
        _state.ui = old


def cell_where(ui=None):
    """!
    @brief The place to change the cell size, for the end of a sentence.
    @param ui 'gui', 'cli' or None for the context in force.
    @return Text such as 'Simulation settings, Cell size, or the Auto button'.
    """
    if (ui or current()) == "gui":
        return "Simulation settings, Cell size, or the Auto button"
    return "--cell-mm on the command line, or --cell-mm auto"


def laminate_where(setting, ui=None):
    """!
    @brief The name of a laminate setting as the user finds it.
    @param setting 'sub-gap' (the longest sub-gap) or 'sub-gaps' (their count).
    @param ui 'gui', 'cli' or None for the context in force.
    @return Text such as "'Laminate sub-gap'" or "--laminate-s-max-mm".
    """
    if (ui or current()) == "gui":
        return {"sub-gap": "'Laminate sub-gap'", "sub-gaps": "'Laminate sub-gaps'"}[setting]
    return {"sub-gap": "--laminate-s-max-mm", "sub-gaps": "--laminate-n-max"}[setting]
