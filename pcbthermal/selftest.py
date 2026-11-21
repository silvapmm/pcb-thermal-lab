#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file selftest.py
@brief The self-test of the program (`pcbthermal gui --selftest`): proves that an installation, or a frozen executable, can start and solve a board.
@details It exists for the downloadable packages (`packaging/`), where nothing else tells that a library, a data file or the calculation process is missing
         on a machine nobody has tried. It checks, in this order:
         1. the version, and whether the program runs frozen (PyInstaller) or from source;
         2. the imports of the libraries and of every model, the optional pyamg, and the data, user-guide and icon files;
         3. in a frozen program, that the licence files of the package are present and that the folders that must not be shipped are not importable;
         4. that the main window opens (offscreen when the machine has no display) and closes;
         5. that the example board is solved by the FVM at a coarse cell **through the calculation process** (the "spawn" process of `gui/compute.py`,
            which a frozen program starts again from its own executable: this is what proves that `multiprocessing.freeze_support()` is in place) and
            that the energy balance closes;
         6. that no calculation process is left running.
         The result is printed and also written to a file (`--selftest-out`), because a windowed program on Windows has no console. The exit code is 0
         when every step passed. A watchdog ends the process with a failure if the whole test takes longer than the limit.
"""

import importlib
import importlib.util
import math
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

from . import __version__

TIMEOUT_S = 120.0                       # Longest the whole self-test may take (s)
SOLVE_CELL_MM = 2.0                     # Cell of the self-test solve (mm): coarse, well under a second
BALANCE_LIMIT = 1e-3                    # Largest |power out - power in| / power in accepted (dimensionless)
MODULES = ("numpy", "scipy", "scipy.sparse.linalg", "matplotlib", "matplotlib.backends.backend_qtagg", "PySide6.QtCore", "PySide6.QtGui",
           "PySide6.QtWidgets", "pcbthermal.api", "pcbthermal.fvm", "pcbthermal.fdm", "pcbthermal.lumped", "pcbthermal.analytic", "pcbthermal.solid3d",
           "pcbthermal.fem", "pcbthermal.gerber", "pcbthermal.package", "pcbthermal.gui.main_window")   # What the program imports at run time
FORBIDDEN = ("tools", "research", "releases", "tests", "pytest", "PySide6.QtWebEngineCore", "PySide6.QtPdf")   # Must not be in a frozen program
LICENSE_FILES = ("LGPL-3.0.txt", "GPL-3.0.txt", "THIRD-PARTY-NOTICES.txt")   # Under licenses/Qt/ of the package
PACKAGE_FILES = ("NOTICE.txt", "SOURCE-OFFER.txt", "REPLACING-QT.txt", "BUILD-INFO.txt", "LICENSE")   # At the top of the package (and inside the bundle)


class Report:
    """!
    @brief The lines of the self-test: printed, and appended to a file as they are made (a hang or a crash still leaves what was done).
    """

    def __init__(self, path=None):
        """!
        @param path File that receives every line, or None for none.
        """
        self.path, self.failures, self.lines = path, [], []

    def line(self, text):
        """!
        @brief Record one line (stdout when there is one, and the file).
        @param text Text of the line.
        """
        self.lines.append(text)
        if sys.stdout is not None:                   # A windowed Windows program has no stdout
            try:
                print(text, flush=True)
            except (OSError, ValueError):
                pass
        if self.path:
            try:
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(text + "\n")
            except OSError:
                pass

    def check(self, name, ok, detail=""):
        """!
        @brief Record the outcome of one step.
        @param name Name of the step.
        @param ok True when it passed.
        @param detail Numbers or the reason of the failure.
        @return The value of ok.
        """
        self.line(f"{'ok  ' if ok else 'FAIL'} {name}" + (f": {detail}" if detail else ""))
        if not ok:
            self.failures.append(name)
        return ok


def frozen():
    """!
    @brief Whether the program runs as a PyInstaller executable.
    @return bool.
    """
    return bool(getattr(sys, "frozen", False))


def check_files(rep):
    """!
    @brief The files the program reads at run time exist: data, user guide, icon.
    @param rep Report.
    """
    here = Path(__file__).resolve().parent
    for label, path in (("data/defaults", here / "data"), ("user guide", here / "help" / "index.html"), ("icon", here.parent / "ico" / "pcb-board.png")):
        rep.check(f"file {label}", path.exists(), str(path.name))
    rep.check("data json files", len(list((here / "data").glob("*.json"))) >= 2, f"{len(list((here / 'data').glob('*.json')))} files")


def check_imports(rep):
    """!
    @brief Import the libraries and the models; the optional pyamg is reported and, in a frozen program, required.
    @param rep Report.
    """
    for name in MODULES:
        try:
            importlib.import_module(name)
            rep.check(f"import {name}", True)
        except Exception as exc:                     # Any failure of an import is a failed step, not a crash of the test
            rep.check(f"import {name}", False, f"{type(exc).__name__}: {exc}")
    from . import femcore

    has_amg = femcore.available()
    rep.check("pyamg available (finite elements on large meshes)", has_amg or not frozen(), "yes" if has_amg else "no (allowed from source only)")


def check_package(rep):
    """!
    @brief In a frozen program: the licence material is shipped (Qt texts, notices, offer, a folder for every bundled library), the table of the libraries is complete
           and the folders that must not be shipped are not importable.
    @param rep Report.
    """
    if not frozen():
        return
    from . import bundle_info

    folder = bundle_info.licences_folder()
    rep.check("licence folder of the package", folder is not None and all((folder / "Qt" / n).exists() for n in LICENSE_FILES), str(folder))
    if folder is not None:
        top = folder.parent
        rep.check("NOTICE, SOURCE-OFFER, REPLACING-QT, BUILD-INFO and LICENSE", all((top / n).exists() for n in PACKAGE_FILES), str(top))
        have = {p.name.lower() for p in folder.iterdir() if p.is_dir()}
        lib = [(n, v, lic) for n, v, lic in bundle_info.libraries()]
        missing = [n for n, _, _ in lib if not any(h.startswith(bundle_info.normal(n).replace("_", "-")) or h.startswith(n.lower()) for h in have)
                   and bundle_info.normal(n) not in ("pyside6", "pyside6_essentials", "shiboken6")]
        rep.check("a licence folder for every bundled library", not missing, ", ".join(missing) if missing else f"{len(lib)} libraries")
        rep.check("licence of every library in the table", all(lic for _, _, lic in lib), ", ".join(n for n, _, lic in lib if not lic))
    for name in FORBIDDEN:
        try:
            present = importlib.util.find_spec(name) is not None
        except (ImportError, ValueError, AttributeError):   # A parent package that is absent counts as absent
            present = False
        rep.check(f"not shipped: {name}", not present)


def check_window(rep, settings_path):
    """!
    @brief Create the Qt application and the main window, let it paint, close it.
    @param rep Report.
    @param settings_path Temporary settings file (the user's preferences are not touched).
    @return The QApplication, or None when it could not be created.
    """
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication

    # A Linux machine without a display (a CI runner) cannot open the platform plug-in of the screen: the offscreen one draws the same widgets
    if sys.platform.startswith("linux") and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([sys.argv[0]])
    app.setApplicationName("PCB Thermal Lab")
    from .gui.main_window import MainWindow

    win = MainWindow(settings=QSettings(settings_path, QSettings.IniFormat))
    win.show()
    for _ in range(5):
        app.processEvents()
    rep.check("main window opens", win.isVisible(), f"platform {app.platformName()}")
    win._confirm_discard = lambda: True              # A new empty project has nothing to save: close without asking
    win.close()
    return app


def solve_through_process(rep, app):
    """!
    @brief Solve the example board with the FVM in the calculation process and check the answer.
    @param rep Report.
    @param app The QApplication (the process queue is read by its timers).
    """
    from PySide6.QtCore import QEventLoop, QTimer

    from . import SolverOptions
    from .examples import example_board
    from .gui import compute

    outcome = {}
    worker = compute.ProcessWorker("simulate", example_board(), SolverOptions(models=("fvm",), cell_mm=SOLVE_CELL_MM))
    loop = QEventLoop()
    worker.done.connect(lambda sim: outcome.update(sim=sim))
    worker.failed.connect(lambda msg: outcome.update(error=msg))
    worker.finished.connect(loop.quit)
    QTimer.singleShot(int(TIMEOUT_S * 500), loop.quit)        # Half of the limit: a process that never answers is a failure, not a hang
    t0 = time.perf_counter()
    worker.start()
    loop.exec()
    seconds = time.perf_counter() - t0
    if "sim" not in outcome:
        compute.shutdown()
        rep.check("example board solved in the calculation process", False, outcome.get("error", f"no answer after {seconds:.0f} s"))
        return
    r = outcome["sim"].results["fvm"]
    balance = abs(r.balance_error)
    rep.check("example board solved in the calculation process", math.isfinite(r.t_max) and r.delta_t > 0.0,
              f"FVM {SOLVE_CELL_MM:g} mm, peak {r.t_max:.2f} degC (rise {r.delta_t:.2f} K), {seconds:.1f} s")
    rep.check("energy balance closes", balance < BALANCE_LIMIT, f"{balance:.2e} (limit {BALANCE_LIMIT:g})")
    compute.shutdown()
    deadline = time.time() + 10.0
    import multiprocessing

    while multiprocessing.active_children() and time.time() < deadline:   # The process was stopped by shutdown(): give it a moment to be reaped
        time.sleep(0.1)
    rep.check("no calculation process left", not multiprocessing.active_children())


def _watchdog(rep, limit):
    """!
    @brief End the process with a failure when the test takes longer than the limit (a frozen program that forks itself, a dialog, a hang).
    @param rep Report.
    @param limit Seconds.
    """
    time.sleep(limit)
    rep.line(f"SELFTEST FAILED: no answer after {limit:.0f} s")
    os._exit(4)


def run(out_path=None, timeout_s=TIMEOUT_S):
    """!
    @brief Run the whole self-test.
    @param out_path File that receives the report (overwritten), or None.
    @param timeout_s Limit of the whole test in seconds.
    @return Exit code: 0 when every step passed, 1 otherwise (4 from the watchdog).
    """
    if out_path:
        try:
            Path(out_path).write_text("", encoding="utf-8")
        except OSError:
            out_path = None
    rep = Report(out_path)
    threading.Thread(target=_watchdog, args=(rep, timeout_s + 30.0), daemon=True).start()
    rep.line(f"PCB Thermal Lab selftest: version={__version__} frozen={frozen()} python={sys.version.split()[0]} platform={sys.platform}")
    check_files(rep)
    check_imports(rep)
    check_package(rep)
    with tempfile.TemporaryDirectory() as tmp:
        try:
            app = check_window(rep, str(Path(tmp) / "selftest.ini"))
            solve_through_process(rep, app)
        except Exception as exc:                     # Any other failure is reported with its type, never a traceback that a windowed program hides
            rep.check("window and calculation process", False, f"{type(exc).__name__}: {exc}")
    rep.line("SELFTEST OK" if not rep.failures else f"SELFTEST FAILED: {', '.join(rep.failures)}")
    return 0 if not rep.failures else 1
