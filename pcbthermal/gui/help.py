#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file help.py
@brief The Help menu: the user guide (an HTML file, shown in the program or in the browser) and the About box.
"""

import re
from pathlib import Path

from .. import defaults
from . import theme as th
from PySide6.QtCore import QObject, QUrl, Qt
from PySide6.QtGui import QDesktopServices, QGuiApplication, QIcon, QTextCursor
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextBrowser, QVBoxLayout

from .. import __author__, __project_url__, __version__

GUIDE = Path(__file__).resolve().parents[1] / "help" / "index.html"
LOGO = Path(__file__).resolve().parents[2] / "ico" / "pcb-board.png"


class _PageReloader(QObject):
    """!
    @brief Child of a help browser that reloads its page when the application palette changes (the theme is switched).
    """

    def __init__(self, view, path):
        """!
        @param view QTextBrowser whose page is reloaded (and the Qt parent, so that this object dies with it).
        @param path Path of the HTML file shown.
        """
        super().__init__(view)
        self._view, self._path = view, path
        QGuiApplication.instance().paletteChanged.connect(self.reload)

    def reload(self, *_):
        """!
        @brief Load the page again with the colours of the theme now in use.
        @param _ Ignored (the palette sent by the Qt signal).
        """
        set_themed_page(self._view, self._path)


def set_themed_page(view, path, name=None):
    """!
    @brief Show an HTML help file in a QTextBrowser with the colours of the application theme.
    @details Qt's rich text ignores the prefers-color-scheme block of the page (written for a web browser), so the style sheet of
             the file is replaced by the one built from the theme table; the scroll position, the images (searched next to the
             file) and the internal links are kept, so the page can be reloaded when the theme is switched while it is open.
    @param view QTextBrowser that shows the page.
    @param path Path of the HTML file.
    @param name "dark" or "light"; None for the theme in use.
    """
    name = name or th.current_name()
    text = Path(path).read_text(encoding="utf-8")
    text = re.sub(r"<style>.*?</style>", lambda _m: "<style>" + th.document_css(name) + "</style>", text, count=1, flags=re.S)
    bar = view.verticalScrollBar()
    keep = bar.value()
    view.setSearchPaths([str(Path(path).parent)])
    view.document().setBaseUrl(QUrl.fromLocalFile(str(Path(path).parent) + "/"))
    view.setHtml(text)
    bar.setValue(keep)
    if getattr(view, "_themed", None) is None:
        # The page follows the application from now on: a theme switch while it is open (the user guide stays open, the help of the
        # calculator opens over a modal dialog) reloads it, since a page already loaded keeps its colours otherwise
        _PageReloader(view, path)
    view._themed = (str(path), name)                         # what is shown now, for the tests


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
        self.search.setToolTip("Type a word and press Enter to find it; Enter again for the next.")
        self.search.returnPressed.connect(self.find_next)
        self.browser_btn = QPushButton("Open in the browser")
        self.browser_btn.clicked.connect(open_guide_in_browser)
        bar.addWidget(self.search, 1)
        bar.addWidget(self.browser_btn)
        lay.addLayout(bar)
        self.view = QTextBrowser()
        self.view.setOpenExternalLinks(True)
        self.view.setToolTip("The user guide; click a contents link to jump to a section.")
        set_themed_page(self.view, GUIDE)
        lay.addWidget(self.view, 1)
        box = QDialogButtonBox(QDialogButtonBox.Close)
        box.rejected.connect(self.reject)
        lay.addWidget(box)

    def set_theme(self, name=None):
        """!
        @brief Redraw the guide in a theme (a page already loaded keeps its old colours when the theme is switched).
        @param name "dark" or "light"; None for the theme in use.
        """
        set_themed_page(self.view, GUIDE, name)

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
            "with power profiles, computed convection, parts with junction temperature, any board shape and the import of a board from Gerber files.</p>"
            "<p>The models are validated against independent models (a resolved 3D solid, closed forms, datasheet cases), not against a measured board.</p>"
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
