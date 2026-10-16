"""!
@file app.py
@brief Application entry point.
"""

import os
import sys

# Matplotlib must know the Qt binding before it is imported anywhere
os.environ.setdefault("QT_API", "pyside6")


def main(argv=None):
    """!
    @brief Start the GUI.
    @param argv Argument list (defaults to sys.argv); an optional first argument is a project file.
    @return Process exit code.
    """
    from PySide6.QtWidgets import QApplication

    from .main_window import MainWindow

    argv = list(sys.argv if argv is None else argv)
    app = QApplication.instance() or QApplication(argv)
    app.setApplicationName("PCB Thermal Lab")
    app.setOrganizationName("PMS Labs")
    win = MainWindow()
    if len(argv) > 1 and os.path.exists(argv[1]):
        win.open_file(argv[1])
    else:
        win._load_problem(__import__("pcbthermal.examples", fromlist=["x"]).example_board(), "example-4layer")
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
