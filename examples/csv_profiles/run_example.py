"""!
@file run_example.py
@brief Runs the CSV-profile example with the Python API and prints the decisions and the results.

Usage: python examples/csv_profiles/run_example.py [pwm]
Without arguments U2 follows the start-up profile (one-shot); with "pwm" U2 is the 1 kHz switching load of the second scenario.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from pcbthermal import SolverOptions, load_project, read_profile_csv, simulate     # noqa: E402


def main(scenario="startup"):
    """!
    @brief Load the board, attach the CSV profiles, simulate and save the results.
    @param scenario "startup" (U2 runs its one-shot start-up profile) or "pwm" (U2 is the 1 kHz load).
    @return The Simulation.
    """
    project = load_project(os.path.join(HERE, "board.pcbt.json"))
    problem = project.problem
    # Heaters are U1 and U2 (see the Elements list in the application)
    by_name = {h.name: h for h in problem.heaters}
    by_name["U1"].set_profile(read_profile_csv(os.path.join(HERE, "profiles", "u1_motor_driver_cycle.csv")))
    second = "u2_pwm_1khz.csv" if scenario == "pwm" else "u2_regulator_startup.csv"
    by_name["U2"].set_profile(read_profile_csv(os.path.join(HERE, "profiles", second)))
    sim = simulate(problem, SolverOptions(cell_mm=1.0))
    print(sim.report())
    out = os.path.join(HERE, "output_" + scenario)
    sim.save(out)                       # Report, JSON, CSV of the temperatures versus time, figures
    print(f"results written to {out}")
    return sim


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "startup")
