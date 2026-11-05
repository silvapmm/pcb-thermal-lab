#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_preferences_layout.py
@brief No page of the Preferences dialog needs a horizontal scroll bar, at three dialog sizes and in both themes; the section list has no tooltip.
"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractScrollArea, QApplication

from pcbthermal.gui import theme
from pcbthermal.gui.preferences import PreferencesDialog

SIZES = ((980, 600), (1100, 700), (800, 600))


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_no_page_scrolls_sideways(qtbot, mode):
    """!
    @brief Every page, at the default, a large and a small dialog size, in both themes: no horizontal scroll bar and no content wider than its viewport.
    @param qtbot pytest-qt fixture.
    @param mode Theme name.
    """
    theme.apply_theme(QApplication.instance(), mode)
    dlg = PreferencesDialog()
    qtbot.addWidget(dlg)
    dlg.show()
    for w, h in SIZES:
        dlg.resize(w, h)
        for i in range(dlg.pages.count()):
            dlg.sections.setCurrentRow(i)
            QApplication.processEvents()
            page = dlg.pages.currentWidget()
            areas = [page] if isinstance(page, QAbstractScrollArea) else []
            areas += page.findChildren(QAbstractScrollArea)
            for a in areas:
                if not a.isVisible():
                    continue
                where = f"{mode} {w}x{h} {dlg.sections.item(i).text()} {type(a).__name__}"
                assert not a.horizontalScrollBar().isVisible(), where
                assert a.horizontalScrollBar().maximum() == 0, where
                inner = a.widget() if hasattr(a, "widget") else None
                if inner is not None:                           # A scroll area with the bar switched off must not clip its content either
                    assert inner.minimumSizeHint().width() <= a.viewport().width(), where


def test_section_list_has_no_tooltip(qtbot):
    """!
    @brief The list of sections shows no tooltip (its names are clear); the controls of the pages keep theirs.
    @param qtbot pytest-qt fixture.
    """
    dlg = PreferencesDialog()
    qtbot.addWidget(dlg)
    assert dlg.sections.toolTip() == ""
    assert all(dlg.sections.item(i).toolTip() == "" for i in range(dlg.sections.count()))
    assert all(w.toolTip() for w in dlg.widgets.values() if hasattr(w, "toolTip"))
