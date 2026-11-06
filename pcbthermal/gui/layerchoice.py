#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file layerchoice.py
@brief The single layer choice of the application: what the toolbar Layer box lists in each context, and the fallback rule.
@details The editor drawing layer and the layer of every map are one choice. The Temperature tab can also show "All layers", "All (2 x 2)" and a
         metal block; the other contexts show one copper layer. The choice stores the latest explicit pick and the last single layer, so that a
         context that cannot show the pick shows the last single layer (and says so) and the pick returns when it can be shown again.
         No Qt widgets and no solver here: the model is tested without a window.
"""

from PySide6.QtCore import QObject, Signal

ALL_LAYERS, ALL_GRID, BLOCK_BASE = -1, -2, 100      # Data of the entries that are not one copper layer (block: 100 top, 101 bottom)
EXTENDED_CONTEXT = "temperature"                    # The only context whose list has the extra entries

NOTE = "'{what}' is for Temperature only: showing layer {layer}, the last single layer"


def is_single(value):
    """!
    @brief Tell whether a choice is one copper layer.
    @param value Choice data: layer index (0-based), -1, -2 or 100 + face of a metal block.
    @return True for a copper layer.
    """
    return 0 <= value < BLOCK_BASE


def entry_name(value):
    """!
    @brief Name of an entry that is not one copper layer.
    @param value Choice data (-1, -2 or 100 + face).
    @return str.
    """
    if value == ALL_LAYERS:
        return "All layers"
    if value == ALL_GRID:
        return "All (2 x 2)"
    return f"Metal block ({'top' if value == BLOCK_BASE else 'bottom'})"


def layer_label(layer, n):
    """!
    @brief Text of a layer entry of the toolbar box.
    @param layer Layer index (0-based).
    @param n Number of copper layers of the board.
    @return str, for example "1 top", "2" or "4 bottom".
    """
    return f"{layer + 1}" + (" top" if layer == 0 else " bottom" if layer == n - 1 else "")


def items(context, n, block_faces=()):
    """!
    @brief The entries of the Layer box in a context.
    @param context Context name; "temperature" gets the extended list.
    @param n Number of copper layers of the board.
    @param block_faces Faces (0 top, 1 bottom) of the metal blocks that the result has (used in the extended list only).
    @return List of (text, data).
    """
    out = []
    if context == EXTENDED_CONTEXT:
        out += [("All layers", ALL_LAYERS)]
        if n > 1:
            out += [("All (2 x 2)", ALL_GRID)]          # A one-layer board has no grid to show (it would show All layers under another name)
    out += [(layer_label(l, n), l) for l in range(n)]
    if context == EXTENDED_CONTEXT:
        out += [(entry_name(BLOCK_BASE + f), BLOCK_BASE + f) for f in sorted(block_faces)]
    return out


class LayerChoice(QObject):
    """!
    @brief The one layer choice: the latest explicit pick and the last single layer.
    """

    changed = Signal()

    def __init__(self, parent=None):
        """!
        @param parent Qt parent.
        """
        super().__init__(parent)
        self.pick_value = 0                 # The latest explicit choice (any entry)
        self.last_single = 0                # The latest explicit single layer

    def pick(self, value):
        """!
        @brief Record an explicit choice of the user.
        @param value Choice data.
        """
        value = int(value)
        if value == self.pick_value and (not is_single(value) or value == self.last_single):
            return
        self.pick_value = value
        if is_single(value):
            self.last_single = value
        self.changed.emit()

    def reset(self):
        """!
        @brief Go back to layer 1 (the top) as a new project starts: the choice is also the drawing layer, and a stale inner layer would put the first element there.
        @return None.
        """
        if self.pick_value == 0 and self.last_single == 0:
            return
        self.pick_value = 0
        self.last_single = 0
        self.changed.emit()

    def follow(self, layer):
        """!
        @brief Move the single layer for a reason that is not a pick of the box (an element selected on another layer, a clicked warning).
        @details A stored single layer is replaced; a stored All layers, All (2 x 2) or metal block stays (it is still what Temperature shows), and only the
                 drawing layer and the single-layer maps move.
        @param layer Layer index (0-based).
        """
        layer = int(layer)
        if is_single(self.pick_value):
            self.pick(layer)
        elif layer != self.last_single:
            self.last_single = layer
            self.changed.emit()

    def single(self, n):
        """!
        @brief The single layer that every context can show.
        @param n Number of copper layers of the board.
        @return int in 0..n-1.
        """
        return min(max(self.last_single, 0), max(n - 1, 0))

    def effective(self, context, n, block_faces=()):
        """!
        @brief What a context shows for the stored choice.
        @param context Context name.
        @param n Number of copper layers of the board.
        @param block_faces Faces of the metal blocks of the result.
        @return Tuple (value, note): the data of the entry shown and a one-line note when it is the fallback (else "").
        """
        v = self.pick_value
        if context == EXTENDED_CONTEXT:
            if is_single(v):
                return min(v, max(n - 1, 0)), ""
            if v >= BLOCK_BASE and (v - BLOCK_BASE) not in block_faces:
                return self.single(n), ""       # A block the result does not have: the layer (no note, the list does not offer it)
            return (v, "") if v != ALL_GRID or n > 1 else (ALL_LAYERS, "")
        if is_single(v):
            return min(v, max(n - 1, 0)), ""
        s = self.single(n)
        return s, NOTE.format(what=entry_name(v), layer=layer_label(s, n))
