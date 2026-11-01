#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file run.py
@brief Run the prototype of the Gerber import window in one of three layouts (hybrid, tabs, wizard).
@details Question it answers: which layout of the planned import window does the maintainer prefer? Run from the repository root:
         `.venv/bin/python research/gerber-real-boards/prototypes/import_window/run.py --layout hybrid|tabs|wizard [--board PATH] [--theme light|dark] [--previous demo|none|FILE] [--out DIR]`.
         The default board is the RP2040 board in the git-ignored `data/` folder (read from there, never copied), else a synthetic one. The Import button writes a summary JSON to `--out` (default `out/` of
         the investigation, git-ignored) instead of creating a project.
"""

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import backend as be  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


def main(argv=None):
    """!
    @brief Parse the command line, build the session and the window, run the event loop.
    @param argv List of arguments (None: sys.argv).
    @return int exit code.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--layout", choices=("hybrid", "tabs", "wizard"), default="hybrid")
    ap.add_argument("--board", help="folder or ZIP of fabrication files (default: the RP2040 board in data/, else a synthetic one)")
    ap.add_argument("--theme", choices=("light", "dark"), default="light")
    ap.add_argument("--previous", default="demo", help="the stored import of the open project: demo (the same board with edits), none, or a summary JSON")
    ap.add_argument("--out", default=str(HERE.parents[1] / "out"), help="folder for the summary the Import button writes")
    a = ap.parse_args(argv)
    app = QApplication.instance() or QApplication([])
    import ui
    from pcbthermal.gui import theme as th
    th.fix_number_locale()
    th.apply_theme(app, a.theme)
    work = be.temp_workdir()
    sx = ui.Session(work, a.out, a.previous)
    path, label = (Path(a.board), a.board) if a.board else be.default_source(work)
    sx.open(path, str(path))
    win = ui.create_window(a.layout, sx, a.theme, label if a.board else label)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
