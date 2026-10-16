"""!
@file make_screenshots.py
@brief Renders the application off-screen and saves the screenshots used in the README and the docs.

Usage: python examples/make_screenshots.py [output_folder]   (default: docs/images)
"""

import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_API", "pyside6")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QSettings                                        # noqa: E402
from PySide6.QtWidgets import QApplication                                  # noqa: E402

from pcbthermal import SolverOptions, simulate                              # noqa: E402
from pcbthermal.examples import example_board                               # noqa: E402
from pcbthermal.gui.main_window import MainWindow                           # noqa: E402


def main(out_dir):
    """!
    @brief Produce the screenshots.
    @param out_dir Folder that receives the PNG files.
    @return List of written file paths.
    """
    os.makedirs(out_dir, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    settings = QSettings(os.path.join(tempfile.mkdtemp(), "shots.ini"), QSettings.IniFormat)
    settings.setValue("theme", "dark")
    win = MainWindow(settings=settings)
    win._load_problem(example_board(), "example-4layer")
    win.resize(1480, 900)
    win.show()
    app.processEvents()
    written = []

    def shot(name):
        app.processEvents()
        path = os.path.join(out_dir, name)
        win.grab().save(path)
        written.append(path)

    win.canvas.set_selection([("heater", 0)])
    win._on_canvas_selection([("heater", 0)])
    shot("editor.png")

    sim = simulate(win.doc.problem, SolverOptions(cell_mm=1.0))
    win._on_done(sim)
    for tab, name in ((1, "results_temperature.png"), (0, "results_summary.png"), (4, "results_components.png")):
        win.results.tabs.setCurrentIndex(tab)
        shot(name)

    win.tabs.setCurrentIndex(1)
    win.results.tabs.setCurrentIndex(win.results.tabs.count() - 1)
    anim = win.results.animation
    anim.t_end.setValue(120.0)
    anim.frames.setValue(40)
    anim.compute.click()
    while anim.tr is None:
        app.processEvents()
    anim.slider.setValue(int(anim.slider.maximum() * 0.55))
    shot("animation.png")
    return written


if __name__ == "__main__":
    for f in main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "images")):
        print(f)
