#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file collect_hints.py
@brief Collect every tooltip of the application offscreen, or compare two collections (the before/after table of the shorter hints of 2.7.0).
@details Two commands, run from the root of a checkout:

         `python releases/2.7.0/hints/scripts/collect_hints.py collect <out.json>` opens the main window on the block example board, every inspector form, the
         Power profile page in its three profile kinds, the Results tabs, the Display panel, the Power Calculator, Preferences, the New board, Background image and
         Export package dialogs and the three steps of the Gerber import window (on the synthetic board of the tests), and writes {key: tooltip} for every widget
         and menu action that has one. The key is the context, the class, the object name, the label and the position in the widget tree, so the same key in two
         trees names the same control.

         `python releases/2.7.0/hints/scripts/collect_hints.py compare <before.json> <after.json>` prints the counts, the mean and largest lengths and the 20
         largest cuts (one per hint; the greyed and JSON-key variants of a hint count once).

         The warnings of the checks are list items, not widget tooltips, so they are not collected. To measure `develop`, run `collect` in a checkout of `develop`.
"""

import json
import os
import statistics
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]          # releases/2.7.0/hints/scripts -> repository root


def _label(w):
    """!
    @brief A short label of a widget for the key: its text, title or window title.
    @param w QWidget.
    @return str The first 40 characters of the label, or "".
    """
    for attr in ("text", "title", "windowTitle"):
        f = getattr(w, attr, None)
        try:
            t = f() if callable(f) else ""
        except Exception:                                # A widget whose text() needs arguments
            t = ""
        if t:
            return str(t)[:40]
    return ""


def _grab(out, root, ctx):
    """!
    @brief Add the tooltips of a widget, its children and their actions to `out`.
    @param out Dict {key: tooltip} that is filled.
    @param root QWidget to scan.
    @param ctx Name of the context (which window or state).
    @return None
    """
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QWidget
    for i, w in enumerate([root] + root.findChildren(QWidget)):
        if w.toolTip():
            out[f"{ctx}|{type(w).__name__}|{w.objectName()}|{_label(w)}|{i}"] = w.toolTip()
    for i, a in enumerate(root.findChildren(QAction)):
        t = a.toolTip()
        if t and t.replace("&", "") != a.text().replace("&", ""):         # Qt's default tooltip of an action is its text: not a hint
            out[f"{ctx}|QAction|{a.objectName()}|{a.text()}|{i}"] = t


def collect(path):
    """!
    @brief Open the windows offscreen and write every tooltip to a JSON file.
    @param path Output JSON file.
    @return int Number of tooltips written.
    """
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["PCBTHERMAL_CONFIG"] = tempfile.mkdtemp()                  # Shipped defaults: no user file changes a hint
    sys.path.insert(0, str(ROOT))
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication, QMessageBox
    app = QApplication.instance() or QApplication([])
    # Modal questions would block an offscreen run
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Discard)
    QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.Ok)
    QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.Ok)
    from pcbthermal import SolverOptions, SquareWave, TableProfile, simulate
    from pcbthermal.examples import example_block_board
    from pcbthermal.gui import tips
    from pcbthermal.gui.calculator import PowerCalculator
    from pcbthermal.gui.document import Document
    from pcbthermal.gui.import_window import ImportBoardWindow
    from pcbthermal.gui.main_window import BackgroundDialog, MainWindow, NewBoardDialog
    from pcbthermal.gui.package_actions import ExportPackageDialog
    from pcbthermal.gui.preferences import PreferencesDialog
    from pcbthermal.gui.profile_results import ProfileResultsTab
    from tests.helpers.synthetic_board import make_board
    out = {}
    tmp = Path(tempfile.mkdtemp())
    win = MainWindow(Document(), QSettings(str(tmp / "t.ini"), QSettings.IniFormat))
    win.resize(1500, 900)
    win.show()
    _grab(out, win, "empty")
    win._load_problem(example_block_board(), "tips")
    app.processEvents()
    _grab(out, win, "main")
    win.stackup_page.mode.setCurrentIndex(1)                              # The advanced stack-up table
    _grab(out, win.stackup_page, "stackup-adv")
    win.stackup_page.mode.setCurrentIndex(0)
    pr = win.doc.problem
    for kind, n in (("zone", len(pr.zones)), ("heater", len(pr.heaters)), ("heatsink", len(pr.heatsinks)), ("via", len(pr.vias))):
        for i in range(n):
            win.inspector.set_selection([(kind, i)])
            _grab(out, win.inspector.form_host, f"insp-{kind}{i}")
    win.inspector.set_selection([("heater", 0), ("zone", 0)])
    _grab(out, win.inspector.form_host, "insp-several")
    for profile in (None, SquareWave(3.0, 1.0, 0.5), TableProfile([0.0, 1.0, 2.0], [1.0, 3.0], True)):
        pr.heaters[0].set_profile(profile)
        win.doc.changed.emit()
        app.processEvents()
        _grab(out, win.profile_page, f"profile-{type(profile).__name__}")
    pr.heaters[0].set_profile(None)
    sim = simulate(pr, SolverOptions(models=("fvm", "lumped", "analytic"), cell_mm=2.0))
    win.sim = sim
    win.results.set_simulation(sim)
    tips.apply(win.results)
    app.processEvents()
    _grab(out, win, "results")
    win._toggle_display_popover()
    app.processEvents()
    if win.display_popover is not None:
        _grab(out, win.display_popover, "display")
    _grab(out, ProfileResultsTab(), "profile-results")
    _grab(out, PowerCalculator(win.doc), "calculator")
    _grab(out, PreferencesDialog(), "preferences")
    _grab(out, NewBoardDialog(), "newboard")
    _grab(out, BackgroundDialog(None, (100, 80)), "background")
    _grab(out, ExportPackageDialog(win, False, False), "export")
    imp = ImportBoardWindow()
    imp.show()
    imp.open_path(str(make_board(tmp / "fab", inner=1)))
    for step in range(3):
        imp.go(step)
        app.processEvents()
        _grab(out, imp, f"import{step + 1}")
    Path(path).write_text(json.dumps(out, indent=0, ensure_ascii=False), encoding="utf-8")
    return len(out)


def compare(before, after, top=20):
    """!
    @brief Print the before/after statistics of two collections and the largest cuts.
    @param before JSON file written by `collect` on the old tree.
    @param after JSON file written by `collect` on the new tree.
    @param top Number of cuts listed.
    @return dict The statistics (counts, means, medians, maxima, rows of the largest cuts).
    """
    b = json.loads(Path(before).read_text(encoding="utf-8"))
    a = json.loads(Path(after).read_text(encoding="utf-8"))
    ub, ua = set(b.values()), set(a.values())
    stats = {"controls": (len(b), len(a)), "distinct": (len(ub), len(ua)),
             "mean": (round(sum(map(len, ub)) / len(ub)), round(sum(map(len, ua)) / len(ua))),
             "median": (statistics.median(map(len, ub)), statistics.median(map(len, ua))),
             "max": (max(map(len, ub)), max(map(len, ua))),
             "over_200": (sum(len(t) > 200 for t in ub), sum(len(t) > 200 for t in ua)),
             "over_100": (sum(len(t) > 100 for t in ub), sum(len(t) > 100 for t in ua)),
             "characters": (sum(map(len, ub)), sum(map(len, ua))),
             "missing_after": sorted(k for k in b if not a.get(k))}        # A hint that disappeared (must be empty)
    pairs = {}
    for k, old in b.items():
        if a.get(k) and a[k] != old:
            pairs.setdefault(old, (a[k], k))
    rows, seen = [], set()
    for old, (new, key) in sorted(pairs.items(), key=lambda kv: len(kv[1][0]) - len(kv[0])):
        base = old.split("\n\nGreyed")[0].split("\nJSON key")[0]              # One row per hint, not per state
        if base in seen:
            continue
        seen.add(base)
        rows.append((key, len(old), len(new)))
        if len(rows) == top:
            break
    stats["changed"] = len(pairs)
    stats["rows"] = rows
    for k, v in stats.items():
        if k != "rows":
            print(f"{k}: {v}")
    for key, lo, ln in rows:
        print(f"{lo:4d} -> {ln:4d}  ({lo - ln:4d})  {key}")
    return stats


if __name__ == "__main__":
    # Plain arguments: collect <out.json> | compare <before.json> <after.json>
    if len(sys.argv) >= 3 and sys.argv[1] == "collect":
        print(collect(sys.argv[2]), "tooltips")
        os._exit(0)                                                       # Skip the teardown of the offscreen windows
    elif len(sys.argv) >= 4 and sys.argv[1] == "compare":
        compare(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
