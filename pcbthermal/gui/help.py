"""!
@file help.py
@brief The Help menu: the user guide (an HTML file, shown in the program or in the browser) and the About box.
"""

from pathlib import Path

from .. import defaults
from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices, QIcon, QTextCursor
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextBrowser, QVBoxLayout

from .. import __author__, __project_url__, __version__

GUIDE = Path(__file__).resolve().parents[1] / "help" / "index.html"
LOGO = Path(__file__).resolve().parents[2] / "ico" / "pcb-board.png"


class GuideWindow(QDialog):
    """!
    @brief The user guide shown inside the program (offline), with a search box and a button to open it in the browser.
    """

    def __init__(self, parent=None):
        """!
        @param parent Qt parent.
        """
        super().__init__(parent)
        self.setWindowTitle("PCB Thermal Lab - User guide")
        self.resize(980, 760)
        lay = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search the guide…")
        self.search.setToolTip("Type a word and press Enter to find it in the guide; Enter again for the next one.")
        self.search.returnPressed.connect(self.find_next)
        self.browser_btn = QPushButton("Open in the browser")
        self.browser_btn.clicked.connect(open_guide_in_browser)
        bar.addWidget(self.search, 1)
        bar.addWidget(self.browser_btn)
        lay.addLayout(bar)
        self.view = QTextBrowser()
        self.view.setOpenExternalLinks(True)
        self.view.setToolTip("The user guide. Click a link in the contents to jump to a section.")
        self.view.setSource(QUrl.fromLocalFile(str(GUIDE)))
        lay.addWidget(self.view, 1)
        box = QDialogButtonBox(QDialogButtonBox.Close)
        box.rejected.connect(self.reject)
        lay.addWidget(box)

    def find_next(self):
        """!
        @brief Find the next occurrence of the search text (wrapping around at the end).
        """
        text = self.search.text()
        if text and not self.view.find(text):
            self.view.moveCursor(QTextCursor.Start)
            self.view.find(text)


def open_guide_in_browser():
    """!
    @brief Open the user guide in the default web browser.
    @return True if the system accepted the request.
    """
    return QDesktopServices.openUrl(QUrl.fromLocalFile(str(GUIDE)))


class AboutDialog(QDialog):
    """!
    @brief About box: program, version, author and project link.
    """

    def __init__(self, parent=None):
        """!
        @param parent Qt parent.
        """
        super().__init__(parent)
        self.setWindowTitle("About PCB Thermal Lab")
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        if LOGO.exists():
            logo = QLabel()
            logo.setPixmap(QIcon(str(LOGO)).pixmap(72, 72))
            top.addWidget(logo)
        self.text = QLabel(
            f"<h2>PCB Thermal Lab</h2><p>Version <b>{__version__}</b></p>"
            "<p>Thermal simulation of printed circuit boards: finite volumes, finite differences, a thermal network, an analytical series and a 3D solid, "
            "with power profiles, computed convection, parts with junction temperature and any board shape.</p>"
            f"<p>Author: {__author__}<br>"
            f"Project: <a href=\"{__project_url__}\">{__project_url__}</a><br>"
            "Copyright © 2025-2026 Pedro Silva (PMS Labs). Released under the MIT License (see the LICENSE file).</p>"
            + (f"<p>Custom defaults in use: {defaults.diff_text()}<br>{defaults.user_file()}</p>" if defaults.has_user_file() and defaults.diff_text() else ""))
        self.text.setTextFormat(Qt.RichText)
        self.text.setOpenExternalLinks(True)
        self.text.setWordWrap(True)
        self.text.setToolTip("Program information.")
        top.addWidget(self.text, 1)
        lay.addLayout(top)
        box = QDialogButtonBox(QDialogButtonBox.Close)
        box.rejected.connect(self.reject)
        lay.addWidget(box)
