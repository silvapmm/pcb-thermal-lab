#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file a11y.py
@brief Names for screen readers and the keyboard order of rebuilt forms: every field gets the text of its label as its accessible name and the label as buddy.
@details Qt names a field from its buddy label on most platforms, but a field laid out in a QGridLayout (the grouped Simulation settings) or a QFormLayout row
         built with a QLabel of our own has no buddy, so a screen reader read only its value ("1.00 mm"). The review of the window counted 6 accessible names
         set in the whole interface.
"""

import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractSpinBox, QComboBox, QFormLayout, QGridLayout, QLabel, QLayout, QLineEdit, QSlider, QWidget)

FIELDS = (QAbstractSpinBox, QComboBox, QLineEdit, QSlider)          # Controls that show a value and need a name from a label (buttons and boxes carry their own text)


def _plain(text):
    """!
    @brief The text of a label as a name: tags, entities and a final colon removed, blanks joined.
    @param text Label text (plain or rich).
    @return str.
    """
    text = re.sub(r"<[^>]+>", " ", text).replace("&nbsp;", " ").replace("&amp;", "&")
    return " ".join(text.split()).rstrip(" :")


def _fields(item):
    """!
    @brief The value controls of a layout item (a widget, or the widgets of a nested layout such as a spin box with an Auto button).
    @param item QLayoutItem or None.
    @return list of QWidget.
    """
    if item is None:
        return []
    w = item.widget()
    if w is not None:
        return [w] if isinstance(w, FIELDS) else [c for c in w.findChildren(QWidget) if isinstance(c, FIELDS)][:1]
    lay = item.layout()
    if isinstance(lay, QLayout):
        out = []
        for k in range(lay.count()):
            out += _fields(lay.itemAt(k))
        return out[:1]
    return []


def _pair(label_item, field_item):
    """!
    @brief Name the first value control of a row from its label and make the label its buddy (when the control has no name of its own).
    @param label_item Layout item of the label.
    @param field_item Layout item of the field.
    @return 1 when a name was given, else 0.
    """
    label = label_item.widget() if label_item is not None else None
    if not isinstance(label, QLabel) or not label.text():
        return 0
    for f in _fields(field_item):
        if label.buddy() is None:
            label.setBuddy(f)
        if not f.accessibleName():
            f.setAccessibleName(_plain(label.text()))
            return 1
    return 0


def name_fields(root):
    """!
    @brief Give every value control under `root` that has no accessible name the text of the label of its row (form rows, and label/field pairs of grids).
    @param root A QWidget (a panel, a page or a whole window).
    @return Number of names given.
    """
    added = 0
    for form in root.findChildren(QFormLayout):
        for r in range(form.rowCount()):
            added += _pair(form.itemAt(r, QFormLayout.LabelRole), form.itemAt(r, QFormLayout.FieldRole))
    for grid in root.findChildren(QGridLayout):
        for r in range(grid.rowCount()):
            for c in range(grid.columnCount() - 1):
                added += _pair(grid.itemAtPosition(r, c), grid.itemAtPosition(r, c + 1))
    return added


def chain_after(anchor, widgets):
    """!
    @brief Put `widgets` in the keyboard order right after `anchor`, in the given order (a rebuilt form was appended at the end of the window's chain,
           after the tool bar, so Tab left the Properties dock before its fields).
    @param anchor A widget already in the window's focus chain (the form's container; when it takes no focus, its nearest ancestor that does).
    @param widgets The focusable fields of the form, top to bottom.
    @return None
    """
    # Qt 6 ignores setTabOrder from a widget without focus: start from the nearest ancestor that takes it (the scroll area of the dock)
    while anchor is not None and not anchor.focusPolicy() & Qt.TabFocus:
        anchor = anchor.parentWidget()
    if anchor is None:
        return
    prev = anchor
    for w in widgets:
        if w.focusPolicy() & Qt.TabFocus:
            QWidget.setTabOrder(prev, w)
            prev = w
