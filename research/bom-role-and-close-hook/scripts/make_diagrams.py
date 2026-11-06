#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the design: the data flow from the files to the heaters with the BOM role (figure 01), the mock-up of step 1 with the BOM line (figure 02), and the close sequence of the import window now and with the explicit hook (figure 03).
@details No data and no program. Run from the repository root: `.venv/bin/python research/bom-role-and-close-hook/scripts/make_diagrams.py`.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
import diagram_kit as dk  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

FIG = os.path.join(os.path.dirname(HERE), "figures")


def fig_01():
    """!
    @brief Figure 01: BOM + placement + paste/X3 -> parts -> role -> heaters, with who wins.
    @return None.
    """
    fig, ax = dk.canvas(11.5, 5.4)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    dk.box(ax, 0.2, 4.4, 2.4, 0.9, "Paste layers\n(openings, TO.C)", "#f6e3b4")
    dk.box(ax, 0.2, 3.2, 2.4, 0.9, "Placement file\nRef, Val, Package, X, Y", "#f6e3b4")
    dk.box(ax, 0.2, 2.0, 2.4, 0.9, "X3 component layer\n(.CVal .CMnt .CMPN)", "#f6e3b4")
    dk.box(ax, 0.2, 0.6, 2.4, 1.1, "BOM (new, optional)\nDesignator, Value,\nFootprint, MPN, DNP", "#c9e7c3", bold=True)
    dk.box(ax, 3.7, 2.6, 2.3, 1.6, "build_parts\n(polygon, side,\nfrom_file)", "#cfe3f5")
    dk.box(ax, 3.7, 0.6, 2.3, 1.1, "read_bom\n(columns, groups,\nDNP) NEW", "#c9e7c3", bold=True)
    dk.box(ax, 6.9, 0.6, 2.2, 1.1, "role rule NEW\nprefix + footprint\n+ value", "#c9e7c3", bold=True)
    dk.box(ax, 6.9, 2.6, 2.2, 1.6, "ImportPart\nfrom_file[\"bom\"] NEW\nedits[\"role\"]", "#cfe3f5")
    dk.box(ax, 9.7, 2.6, 2.1, 1.6, "Step 2 table\nRole column:\nproposal, user wins", "#cfe3f5")
    dk.box(ax, 9.7, 0.6, 2.1, 1.1, "Heater.role\n\"source\" / \"component\"", "#e6b0aa")
    for y in (4.85, 3.65, 2.45):
        dk.arrow(ax, 2.6, y, 3.7, 3.4)
    dk.arrow(ax, 2.6, 1.15, 3.7, 1.15)
    dk.arrow(ax, 6.0, 1.15, 6.9, 1.15)
    dk.arrow(ax, 8.0, 1.7, 8.0, 2.6, label="role, DNP, MPN")
    dk.arrow(ax, 6.0, 3.4, 6.9, 3.4)
    dk.arrow(ax, 9.1, 3.4, 9.7, 3.4)
    dk.arrow(ax, 10.75, 2.6, 10.75, 1.7, label="build_problem")
    ax.text(6.0, 5.4, "A BOM never moves a part and never sets a power: it only proposes the role (and says which parts are not populated).\nWhat the user typed in the table (edits) always wins; a re-import rewrites from_file and keeps edits.", ha="center", fontsize=8.5)
    dk.save(fig, os.path.join(FIG, "fig_01_data_flow.png"), "From files to heaters: where the BOM role enters")


def fig_02():
    """!
    @brief Figure 02: mock-up of step 1 of the import window with a BOM file and a BOM line.
    @return None.
    """
    fig, ax = dk.canvas(9.6, 5.2)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.add_patch(Rectangle((0.1, 0.1), 9.8, 5.8, fc="#f4f4f4", ec="k"))
    ax.text(0.3, 5.6, "Import Gerber board        1 Files     2 Parts     3 Model", fontsize=9, fontweight="bold", va="center")
    ax.text(0.3, 5.1, "CAD tool: KiCad (high confidence)", fontsize=8.5, va="center")
    ax.text(0.3, 4.75, "BOM: board-bom.csv  - 86 designators, 5 not populated, proposed: 63 component, 5 source, 18 none", fontsize=8.5, va="center", color="#1e6b2c", fontweight="bold")
    rows = [("board-F_Cu.gbr", "Top copper"), ("board-F_Paste.gbr", "Solder paste top"), ("board-pos.csv", "Placement (pick and place)"),
            ("board-bom.csv", "BOM (bill of materials)"), ("board-drl.drl", "Plated drill")]
    ax.text(0.4, 4.3, "File", fontsize=8, fontweight="bold")
    ax.text(4.2, 4.3, "Role", fontsize=8, fontweight="bold")
    ax.text(7.4, 4.3, "Found by", fontsize=8, fontweight="bold")
    for i, (f, r) in enumerate(rows):
        y = 3.85 - i * 0.5
        hl = r.startswith("BOM")
        ax.add_patch(Rectangle((0.3, y - 0.2), 9.3, 0.42, fc="#c9e7c3" if hl else "white", ec="#999"))
        ax.text(0.4, y, f, fontsize=8.5, va="center")
        ax.text(4.2, y, r + "  v", fontsize=8.5, va="center", fontweight="bold" if hl else None)
        ax.text(7.4, y, "columns of a BOM table" if hl else "file name", fontsize=8, va="center", color="#555")
    ax.text(0.3, 1.0, "The BOM role is read: the table is parsed once, its columns are shown above, and the roles it proposes appear in step 2\n(a role the user changed there stays; a part that is in the BOM as not populated is unticked and says so).", fontsize=8.3, va="top")
    ax.text(0.3, 0.3, "Add files... / Replace / Cancel", fontsize=8, color="#555")
    dk.save(fig, os.path.join(FIG, "fig_02_step1_mockup.png"), "Mock-up of step 1 with the BOM file and the BOM line (not built)")


def fig_03():
    """!
    @brief Figure 03: what runs when the import window closes, now (package branch wrapper) and with the explicit before_close list.
    @return None.
    """
    fig, (a, b) = dk.canvas(11.5, 4.6, 1, 2)
    for ax in (a, b):
        ax.set_xlim(0, 6)
        ax.set_ylim(0, 6)
    a.text(3, 5.7, "Now (feature/project-package): replace an attribute", ha="center", fontsize=9, fontweight="bold")
    dk.box(a, 0.3, 4.2, 5.4, 0.8, "MainWindow: cap = capture_on_close(dlg)\ndlg.session.close = wrapper   (monkey patch)", "#f6e3b4")
    dk.box(a, 0.3, 2.9, 5.4, 0.8, "dlg.done() -> session.close()  (wrapper: read files, then original)", "#cfe3f5")
    dk.box(a, 0.3, 1.6, 5.4, 0.8, "set_files() -> self.close() fires the same wrapper\n(also when only other files are opened)", "#e6b0aa")
    dk.box(a, 0.3, 0.3, 5.4, 0.8, "A second feature that patches close() replaces the first", "#e6b0aa")
    for y in (4.2, 2.9, 1.6):
        dk.arrow(a, 3, y, 3, y - 0.4)
    b.text(3, 5.7, "Proposed: a list the window and the session run", ha="center", fontsize=9, fontweight="bold")
    dk.box(b, 0.3, 4.2, 5.4, 0.8, "MainWindow: dlg.before_close.append(cap.read)\n(no change to session.close)", "#c9e7c3", bold=True)
    dk.box(b, 0.3, 2.9, 5.4, 0.8, "dlg.done(): run each hook(dlg, result), in order,\nexceptions logged; then session.close()", "#c9e7c3", bold=True)
    dk.box(b, 0.3, 1.6, 5.4, 0.8, "set_files() releases the archive with reason \"new_files\":\nthe hooks of the session see the old files first", "#cfe3f5")
    dk.box(b, 0.3, 0.3, 5.4, 0.8, "Several hooks coexist; each is removed by the owner", "#c9e7c3")
    for y in (4.2, 2.9, 1.6):
        dk.arrow(b, 3, y, 3, y - 0.4)
    dk.save(fig, os.path.join(FIG, "fig_03_close_hook.png"), "The close of the import window: the wrapper now and the explicit hook")


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    fig_01()
    fig_02()
    fig_03()
