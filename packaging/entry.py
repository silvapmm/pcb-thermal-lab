#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file entry.py
@brief Entry point of the frozen program (PyInstaller): `PCB-Thermal-Lab` opens the window; any command of `python -m pcbthermal` works after it.
@details The first statement that runs is `multiprocessing.freeze_support()`. The calculation process of the program is started with the "spawn" method
         (`pcbthermal/gui/compute.py`), which in a frozen program launches the executable again with a hidden argument; without this call every
         simulation would open another copy of the window instead of calculating.
"""

import multiprocessing

multiprocessing.freeze_support()                # The first statement of the program: a no-op unless this is a frozen spawned child, which it runs and ends

import sys  # noqa: E402  (after freeze_support on purpose)

COMMANDS = ("run", "transient", "calibrate", "convergence", "solvers", "convert", "gui", "example")   # The sub-commands of pcbthermal.cli
PASS_THROUGH = ("-h", "--help", "--version")                                             # Options that belong to the top-level parser


def arguments(argv):
    """!
    @brief The argument list for `pcbthermal.cli.main`: the window by default, and a project path or a `gui` option alone means the window too.
    @param argv Arguments after the program name (sys.argv[1:]).
    @return list of str.
    """
    # A macOS launch from the Finder may add a process-serial-number argument; it is not ours
    argv = [a for a in argv if not a.startswith("-psn_")]
    if not argv:
        return ["gui"]
    if argv[0] in COMMANDS or argv[0] in PASS_THROUGH:
        return argv
    return ["gui"] + argv                       # A project file (open with) or a gui option such as --selftest


def main():
    """!
    @brief Run the program.
    @return Process exit code.
    """
    from pcbthermal import cli

    return cli.main(arguments(sys.argv[1:]))


if __name__ == "__main__":
    sys.exit(main())
