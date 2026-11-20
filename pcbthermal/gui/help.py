#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file help.py
@brief The Help menu: the user guide (an HTML file, shown in the program or in the browser) and the About box.
"""

import re
from pathlib import Path

from .. import bundle_info, defaults
from . import theme as th
from PySide6.QtCore import QObject, QSize, QUrl, Qt
from PySide6.QtGui import QDesktopServices, QFont, QFontDatabase, QGuiApplication, QIcon, QTextCursor
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QPlainTextEdit, QPushButton, QTextBrowser, QTreeWidget, QTreeWidgetItem, QVBoxLayout

from .. import __author__, __contact__, __project_url__, __version__

GUIDE = Path(__file__).resolve().parents[1] / "help" / "index.html"
ICON_DIR = Path(__file__).resolve().parents[2] / "ico"
LOGO = ICON_DIR / "pcb-board.png"
## Sizes in px of the PNG set `ico/png/pcb-board_<size>.png` (the small ones are hand-tuned, see `examples/make_icon.py`).
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256, 512, 1024)


def app_icon():
    """!
    @brief Build the application icon from the PNG set of `ico/png/`, so that every size uses its own drawing.
    @return QIcon The icon with one file per size; only the 1024 px master if the folder `ico/png/` is missing; an empty icon without `ico/`.
    """
    icon = QIcon()
    for size in ICON_SIZES:
        path = ICON_DIR / "png" / f"pcb-board_{size}.png"
        if path.exists():
            icon.addFile(str(path), QSize(size, size))
    # Fallback: the master, scaled by Qt, when the set of sizes is not shipped
    if icon.isNull() and LOGO.exists():
        icon.addFile(str(LOGO))
    return icon


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
        if not app_icon().isNull():
            logo = QLabel()
            logo.setPixmap(app_icon().pixmap(72, 72))
            top.addWidget(logo)
        self.text = QLabel(
            f"<h2>PCB Thermal Lab</h2><p>Version <b>{__version__}</b><br><small>{bundle_info.live_line()}</small></p>"
            "<p>Thermal simulation of printed circuit boards: finite volumes, finite differences, a thermal network, an analytical series, a 3D solid and finite elements, "
            "with power profiles, computed convection, parts with junction temperature, any board shape and the import of a board from Gerber files.</p>"
            "<p>pyamg (MIT) is an optional library: the finite-element model uses it on large meshes, and without it only small meshes are solved.</p>"
            "<p>The models are checked against independent solutions (a resolved 3D solid, finite elements, closed forms, published cases and one datasheet board), not against a measured board.</p>"
            f"<p>Author: {__author__}<br>"
            f"Project: <a href=\"{__project_url__}\">{__project_url__}</a><br>"
            f"Contact: <a href=\"mailto:{__contact__}\">{__contact__}</a><br>"
            "Copyright © 2025-2026 Pedro Silva (PMS Labs). Released under the MIT License (see the LICENSE file).</p>"
            f"<p style=\"margin-bottom:8px\">{bundle_info.qt_sentence()}</p>"
            + (f"<p>Custom defaults in use: {defaults.diff_text()}<br>{defaults.user_file()}</p>" if defaults.has_user_file() and defaults.diff_text() else ""))
        self.text.setTextFormat(Qt.RichText)
        self.text.setOpenExternalLinks(True)
        self.text.setWordWrap(True)
        self.text.setToolTip("Program information.")
        # A word-wrapped rich-text label in a dialog was given less height than its text needs at its final width (the last line was cut): fix the width and ask the height for it
        self.text.setFixedWidth(560)
        self.text.setMinimumHeight(self.text.heightForWidth(560))
        lay.setContentsMargins(20, 18, 20, 14)
        lay.setSpacing(16)                                      # Air between the text and the buttons (the Qt sentence was glued to them)
        top.addWidget(self.text, 1)
        lay.addLayout(top)
        box = QDialogButtonBox(QDialogButtonBox.Close)
        box.rejected.connect(self.reject)
        # LGPL 3.0 section 4(c): a program that shows copyright notices must point to the licence texts; this button opens them
        self.b_licences = box.addButton("Licences…", QDialogButtonBox.ActionRole)
        self.b_licences.setToolTip("The licence texts of this program and of the libraries it bundles (Qt and PySide under the LGPL), the source offer and how to replace Qt.")
        self.b_licences.clicked.connect(self.show_licences)
        self.b_copy = box.addButton("Copy version info", QDialogButtonBox.ActionRole)
        self.b_copy.clicked.connect(self.copy_version_info)
        lay.addWidget(box)

    def show_licences(self):
        """!
        @brief Open the Licences window.
        """
        LicencesDialog(self).exec()

    def copy_version_info(self):
        """!
        @brief Put the version, the system and the loaded Qt and PySide versions on the clipboard (for a bug report).
        """
        QGuiApplication.clipboard().setText(bundle_info.version_info_text())


class LicencesDialog(QDialog):
    """!
    @brief The licence texts: a tree with three groups (the package, Qt and PySide, the bundled libraries), the entries under them, and the text of the chosen entry.
    """

    def __init__(self, parent=None):
        """!
        @param parent Qt parent.
        """
        super().__init__(parent)
        self.setWindowTitle("Licences")
        self.resize(900, 600)
        self.setMinimumSize(760, 400)                           # Narrower than this the library table (wrapped to the window) would need a horizontal scroll bar
        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        self.groups = bundle_info.licence_groups()
        self.entries = [e for _, items in self.groups for e in items]      # The flat list; a leaf of the tree holds its index in Qt.UserRole
        self.rows = bundle_info.libraries()                     # Read once: the table is re-wrapped from these rows at every resize (the metadata scan takes about 0.1 s)
        self.shown_width = None                                 # Width of the view when the library table was last wrapped (None: another text is shown)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(False)
        self.tree.setIndentation(14)
        self.tree.setFixedWidth(260)
        self.tree.setToolTip("The notices of the package, Qt and PySide, and the bundled libraries; choose an entry to read its licence files.")
        bold = QFont(self.tree.font())
        bold.setBold(True)
        self.leaves = []
        index = 0
        for group, items in self.groups:
            head = QTreeWidgetItem([group])
            head.setFlags(Qt.ItemIsEnabled)                      # A header: not selectable, the keyboard and the mouse skip it
            head.setFont(0, bold)
            self.tree.addTopLevelItem(head)
            for e in items:
                leaf = QTreeWidgetItem([e[0]])
                leaf.setData(0, Qt.UserRole, index)
                leaf.setToolTip(0, e[2])                         # The full name or path: the list is narrow and cuts long names
                head.addChild(leaf)
                self.leaves.append(leaf)
                index += 1
            head.setExpanded(True)
        self.tree.setItemsExpandable(False)                      # Three short groups: always open
        self.view = QPlainTextEdit()
        self.view.setReadOnly(True)
        self.view.setLineWrapMode(QPlainTextEdit.NoWrap)       # The table is wrapped by hand (hanging indent), the licence texts keep their own lines
        # The library table is padded text: a fixed-width font keeps its columns aligned (a style sheet, because the theme's own style sheet would override setFont alone)
        self.view.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        self.view.setStyleSheet("font-family: Menlo, Consolas, 'DejaVu Sans Mono', monospace;")
        self.view.setToolTip("The text of the chosen licence file.")
        self.tree.currentItemChanged.connect(self.on_current_changed)
        self.tree.itemPressed.connect(self.on_item_pressed)
        self.tree.setAccessibleName("Licence entries")
        self.view.setAccessibleName("Licence text")
        row.addWidget(self.tree)
        row.addWidget(self.view, 1)
        lay.addLayout(row, 1)
        box = QDialogButtonBox(QDialogButtonBox.Close)
        box.rejected.connect(self.reject)
        lay.addWidget(box)
        if self.leaves:
            self.tree.setCurrentItem(self.leaves[0])

    def usable_width(self):
        """!
        @brief The width in pixels that a line of the text view can take without a horizontal scroll bar.
        @return int pixels: the view minus its frame, the document margins and a vertical scroll bar (reserved even if not shown yet: the table may need one).
        """
        return (self.view.width() - 2 * self.view.frameWidth() - 2 * int(self.view.document().documentMargin())
                - self.view.verticalScrollBar().sizeHint().width() - 2)

    def table_width(self):
        """!
        @brief How many characters of the text font fit in the text view, so that the library table needs no horizontal scroll bar.
        @return int, at least 60 (the name and version columns alone take about 35).
        @note The widest of a few broad glyphs is used, not the advance of "0": if the fixed-width fonts of the style sheet are all missing and a proportional
              font stands in, the estimate stays on the safe side; show_entry() then checks the real pixel width of the wrapped lines.
        """
        fm = self.view.fontMetrics()
        char = max(max(fm.horizontalAdvance(c) for c in "0MWm_-"), 1)
        return max(self.usable_width() // char, 60)

    def wrapped_table(self):
        """!
        @brief The library table wrapped to the text view: the width from table_width(), then narrowed while a measured line is still wider than the view.
        @return str.
        """
        fm = self.view.fontMetrics()
        usable = self.usable_width()
        width = self.table_width()
        text = bundle_info.table_text(width, self.rows)
        for _ in range(8):                                        # A few passes at most: each removes the measured overflow in characters
            over = max((fm.horizontalAdvance(ln) for ln in text.splitlines()), default=0) - usable
            if over <= 0 or width <= 40:
                break
            width -= max(1, -(-over // max(fm.horizontalAdvance("0"), 1)))
            text = bundle_info.table_text(width, self.rows)
        return text

    def target_of_header(self, head, going_up):
        """!
        @brief The entry the tree moves to when a group header becomes current (headers hold no text).
        @param head     int index of the group header.
        @param going_up bool, True when the move came from an entry below the header (Up, PageUp, Home).
        @return QTreeWidgetItem or None (no entry at all).
        """
        before = [leaf for leaf in self.leaves if self.tree.indexOfTopLevelItem(leaf.parent()) < head]
        after = [leaf for leaf in self.leaves if self.tree.indexOfTopLevelItem(leaf.parent()) >= head]
        if going_up and before:                                   # Up: the last entry of the groups above
            return before[-1]
        # Down, Home at the top, the first time or a click: the first entry of this group (or of the next one that has entries), else the last above
        return after[0] if after else (before[-1] if before else None)

    def on_current_changed(self, cur, prev):
        """!
        @brief Keep the keyboard on the entries: when an arrow key, Home, End or a page key lands on a group header, move on to the nearest entry in the direction of
               travel (Home goes to the first entry); otherwise show the text of the entry.
        @param cur QTreeWidgetItem now current (may be a header).
        @param prev QTreeWidgetItem that was current (None at the start).
        """
        if cur is not None and cur.parent() is None:
            head = self.tree.indexOfTopLevelItem(cur)
            going_up = prev is not None and prev.parent() is not None and self.tree.indexOfTopLevelItem(prev.parent()) >= head
            target = self.target_of_header(head, going_up)
            if target is not None:
                self.tree.setCurrentItem(target)                  # Raises currentItemChanged again with an entry, which shows its text
            else:
                self.show_entry(None)
            return
        self.show_entry(cur)

    def on_item_pressed(self, item, column):
        """!
        @brief A click on a group header opens the first entry of that group (currentItemChanged alone cannot tell a click from the Up key).
        @param item   QTreeWidgetItem under the mouse.
        @param column int column (always 0).
        """
        if item is not None and item.parent() is None:
            target = self.target_of_header(self.tree.indexOfTopLevelItem(item), False)
            if target is not None and target is not self.tree.currentItem():
                self.tree.setCurrentItem(target)

    def show_entry(self, item):
        """!
        @brief Show the text of a tree item (nothing for a group header or no item); the library table is wrapped to the width of the view.
        @param item QTreeWidgetItem or None.
        """
        i = item.data(0, Qt.UserRole) if item is not None else None
        self.shown_width = None
        if i is None:
            self.view.setPlainText("")
            return
        title, text, _ = self.entries[i]
        if title in bundle_info.TABLE_TITLES:
            text = self.wrapped_table()
            self.shown_width = self.view.width()                  # The re-wrap on resize is skipped while the view keeps this width
        self.view.setPlainText(text)

    def resizeEvent(self, event):
        """!
        @brief Wrap the library table again when the text view changed width (the children are laid out before this handler runs).
        @param event QResizeEvent.
        """
        super().resizeEvent(event)
        item = self.tree.currentItem()
        if self.shown_width is not None and item is not None and self.view.width() != self.shown_width:
            self.show_entry(item)
