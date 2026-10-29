#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
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
    from .theme import fix_number_locale

    fix_number_locale()
    app.setApplicationName("PCB Thermal Lab")
    app.setOrganizationName("PMS Labs")
    win = MainWindow()
    if len(argv) > 1 and os.path.exists(argv[1]):
        win.open_file(argv[1])
    # Without a file the program starts with an empty board (the defaults of a new board); the examples are in File - Open example
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
