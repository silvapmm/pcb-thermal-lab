#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file shortcuts_dialog.py
@brief The window Help - Keyboard and mouse: the key table in two columns of key/description pairs, in a resizable dialog that fits any screen.
"""

import html
import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QTextBrowser, QVBoxLayout

from . import theme as th

DEFAULT_SIZE = (900, 600)       # Width, height in pixels when the screen allows it
SCREEN_FRACTION = 0.8           # The dialog never takes more than this share of the available screen, in each direction


def parse_rows(table_html):
    """!
    @brief Read the (keys, description) rows of the key table (the HTML of MainWindow.SHORTCUTS_HTML).
    @param table_html HTML table with one `<tr><td><b>keys</b></td><td>text</td></tr>` per row.
    @return List of (keys, text) pairs, in the HTML form of the source (entities and tags kept).
    """
    return re.findall(r"<tr><td><b>(.*?)</b></td><td>(.*?)</td></tr>", table_html, flags=re.S)


def two_column_html(rows):
    """!
    @brief Lay the rows out as a table of two key/description pairs per line, so the table is about half as tall.
    @param rows List of (keys, text) pairs (HTML text).
    @return str HTML table. The first half of the rows fills the left pair, the second half the right one.
    """
    half = (len(rows) + 1) // 2
    left, right = rows[:half], rows[half:]
    out = ['<table cellpadding="4" cellspacing="0" width="100%">']
    for i, (k, t) in enumerate(left):
        out.append(f"<tr><td valign='top' width='18%'><b>{k}</b></td><td valign='top' width='32%'>{t}</td>")
        if i < len(right):
            k2, t2 = right[i]
            out.append(f"<td valign='top' width='18%'><b>{k2}</b></td><td valign='top' width='32%'>{t2}</td></tr>")
        else:
            out.append("<td></td><td></td></tr>")
    out.append("</table>")
    return "".join(out)


class ShortcutsDialog(QDialog):
    """!
    @brief Dialog with the keyboard and mouse table: wide rather than tall, scrolls when needed, closes with Esc or the Close button.
    """

    def __init__(self, table_html, theme_name, parent=None):
        """!
        @param table_html HTML table of the keys (MainWindow.SHORTCUTS_HTML).
        @param theme_name "light" or "dark" (theme tokens of the document style sheet).
        @param parent Parent window.
        """
        super().__init__(parent)
        self.setWindowTitle("Keyboard and mouse")
        self.setSizeGripEnabled(True)
        lay = QVBoxLayout(self)
        self.browser = QTextBrowser()
        self.browser.setObjectName("shortcutsText")
        self.browser.document().setDefaultStyleSheet(th.document_css(theme_name))
        rows = parse_rows(table_html)
        # A table the parser cannot read is still shown, in one column
        self.browser.setHtml(two_column_html(rows) if rows else table_html)
        self.browser.setAccessibleName("Keyboard and mouse shortcuts")
        lay.addWidget(self.browser)
        box = QDialogButtonBox(QDialogButtonBox.Close)
        box.rejected.connect(self.reject)                    # Close is a reject role: Esc does the same
        lay.addWidget(box)
        self.resize(*self.fitted_size(parent))

    @staticmethod
    def fitted_size(parent=None):
        """!
        @brief The default size: 900 x 600 px, capped at 80 % of the available geometry of the screen the window is on.
        @param parent Window whose screen is used (the primary screen without one).
        @return (width, height) in pixels.
        """
        screen = (parent.screen() if parent is not None else None) or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry()
        return (min(DEFAULT_SIZE[0], int(avail.width() * SCREEN_FRACTION)), min(DEFAULT_SIZE[1], int(avail.height() * SCREEN_FRACTION)))
