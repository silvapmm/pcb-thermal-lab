#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file package_actions.py
@brief The glue between the main window and the project package (`pcbthermal/package.py`): Save As with both file types, Export package, the source files of an import and their use by a re-import.

Kept apart from `main_window.py` so that the window needs only a few calls. The container itself (format, safety, hashes) is `pcbthermal.package`.
"""

import hashlib
from pathlib import Path

from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QLabel, QMessageBox, QVBoxLayout

from .. import package as pkg
from . import import_session as imp

SETTINGS_KEY = "package/include_sources"          # Machine preference: the state of the box of the export dialog
SAVE_FILTER = "PCB Thermal project (*.pcbt.json);;PCB Thermal project package (*.pcbtz)"
SOURCES_TIP = ("Store the files the board was imported from (copper, mask, paste and legend layers, outline, drills, the placement file, X3 component layers, a BOM if you "
               "gave one) inside the package, under their original names, so that a re-import can start from them. Off by default; the choice is remembered on this machine.")
SOURCES_NOTE = ("Gerber file headers may carry folder paths and user names, and a third-party board keeps its owner's licence. The files are stored exactly as read "
                "(no comment is removed).")


def kind_of(role, name):
    """!
    @brief The manifest kind of a source file.
    @param role Role the import gave the file (an import_session role text).
    @param name File name.
    @return str: one of package.KINDS.
    """
    low = name.lower()
    if role in (imp.PLATED, imp.NONPLATED):
        return "drill"
    if role == imp.PLACEMENT:
        return "placement"
    if role == imp.COMPONENT:
        return "x3"
    if "bom" in low and low.rsplit(".", 1)[-1] in ("csv", "txt", "xls", "xlsx", "tsv", "xml", "json"):
        return "bom"
    if role == imp.IGNORE:
        return "other"
    return "gerber"


def session_files(session):
    """!
    @brief The source files of an import session as (name, bytes, kind, function, origin), for `package.attach_sources`.
    @details The ORIGINAL bytes are stored, never the reader's decoded text (review: a member of a ZIP was stored as its text re-encoded, so a byte that is not UTF-8, a
             Latin-1 comment for instance, became U+FFFD and the backup was no longer the file). A file of a folder (or of a list of files) is read again from the disk and
             kept only when its SHA-256 is still the session's; a member of a ZIP is read again from the archive, still open, and checked the way the session hashed it
             (its text re-encoded, whole up to `import_session.HASH_WHOLE_BYTES`; a larger member is trusted to the CRC of the archive). A file that changed since it was
             read, or cannot be read, is left out with a note, as is a file above the size limit. `origin` ("folder" or "zip") lets `extract_sources` give a re-import the
             same container, so that the names and the hashes of the record are reproduced. The session keeps no BOM role: a BOM that sat in the folder is listed with the
             role Ignore and stored as kind "bom" when its name says so.
    @param session The ImportSession (still open: its files are read now).
    @return tuple (list of (name, bytes, kind, function, origin), list of warning texts).
    """
    out, notes = [], []
    archive = getattr(session, "_archive", None)
    paths = getattr(session, "paths", {}) or {}
    for f in session.files:
        if f.limit_error:
            notes.append(f"{f.name}: not stored ({f.limit_error})")
            continue
        try:
            if archive is not None:
                raw, origin = archive.read_bytes(f.name), "zip"
                same = (len(raw) > imp.HASH_WHOLE_BYTES
                        or hashlib.sha256(raw.decode("utf-8", "replace").encode("utf-8", "replace")).hexdigest() == f.sha256)
            elif f.name in paths:
                raw, origin = Path(paths[f.name]).read_bytes(), "folder"
                same = hashlib.sha256(raw).hexdigest() == f.sha256
            else:
                notes.append(f"{f.name}: not stored (its file is not known)")
                continue
        except Exception as exc:                               # a file that can no longer be read: say so, store the rest
            notes.append(f"{f.name}: not stored ({exc})")
            continue
        if not same:
            notes.append(f"{f.name}: not stored (it changed on the disk since the import read it)")
            continue
        out.append((f.name, raw, kind_of(f.role, f.name), f.role, origin))
    return out, notes


class SourceCapture:
    """!@brief The source files read from an import session just before the import window closes it (a ZIP can no longer be read after that)."""

    def __init__(self):
        """!@brief Create an empty capture."""
        self.files, self.notes = [], []


def capture_on_close(dlg):
    """!
    @brief Make the import window hand over its source files when it closes.
    @details Registers a hook on `dlg.before_close` (run by `done()` before the session, and a ZIP archive with it, is released): when an import record exists the files are read
             first. A cancelled window without a record reads nothing. The hook has no veto and shares the list with other features, so nothing is replaced.
    @param dlg The ImportBoardWindow (or any object with `session`, `record` and a `before_close` list).
    @return SourceCapture, filled when the window closes.
    """
    cap = SourceCapture()

    def capture(window, result):
        """!
        @brief Read the files of the session (once).
        @param window The import window.
        @param result Dialog result code.
        @return None
        """
        if dlg.record is not None and not cap.files:
            cap.files, cap.notes = session_files(dlg.session)
    dlg.before_close.append(capture)
    return cap


def remember_import(win, cap, replace=True):
    """!
    @brief Keep the source files of the import that just produced the open project, so that Export package can store them.
    @param win The MainWindow.
    @param cap The SourceCapture of the import window.
    @param replace False for a re-import that only adds files (the stored set is kept and the new files are added to it).
    @return None
    """
    files, notes = cap.files, cap.notes
    pkg.attach_sources(win.doc.project, files, replace=replace)
    if notes:
        win.statusBar().showMessage("Source files: " + "; ".join(notes[:3]), 15000)


def stored_sources(win):
    """!
    @brief Whether the open project holds the source files of its import (it came from a package that stores them, or was imported in this session).
    @param win The MainWindow.
    @return bool.
    """
    extras = win.doc.project.package
    return bool(extras and extras.has_sources())


def offer_stored_sources(win, dlg):
    """!
    @brief Offer a re-import the files stored in the project and, if the user agrees, open them in the import window.
    @details The files are written to a private folder that lives until the window closes its session: the session reads the files lazily (the placement file and the
             paste layers when the parts are built, every file again when the capture stores them), so the folder must not be removed right after `open_path` (review: it
             was, and the import then failed with FileNotFoundError and the stored files were lost). The removal is a `before_release` hook of the session (it runs after the `before_close`
             hooks, among them the capture of `capture_on_close`, which reads the files first), and also when the user opens other files in the window.
    @param win The MainWindow.
    @param dlg The ImportBoardWindow, before it is shown (after `capture_on_close`).
    @return None
    """
    box = QMessageBox(win)
    box.setWindowTitle("Source files stored in this project")
    box.setText("This project stores the files its board was imported from.")
    use = box.addButton("Use the stored files", QMessageBox.AcceptRole)
    box.addButton("Choose other files", QMessageBox.RejectRole)
    use.setToolTip("Start the re-import from the files saved in the project package; you can still change them in the window.")
    box.exec()
    if box.clickedButton() is not use:
        return
    folder = None
    try:
        folder = win.doc.project.package.extract_sources()
        dlg.open_path(folder)
    except Exception as exc:
        if folder:
            pkg.remove_extracted(folder)
        QMessageBox.warning(win, "Cannot use the stored files", str(exc))
        return

    def remove_folder(session, reason):
        """!
        @brief Remove the private folder of the stored files when the session is released (window closed, or other files opened).
        @param session The ImportSession.
        @param reason "close" or "new_files".
        @return None
        """
        pkg.remove_extracted(folder)
    dlg.session.before_release.append(remove_folder)


class ExportPackageDialog(QDialog):
    """!@brief The small dialog of 'Export package…': the box that decides whether the source files of the import go into the package."""

    def __init__(self, parent, has_sources, checked):
        """!
        @param parent Parent window (the MainWindow: its open project's stored files are scanned by `package.privacy_hints`).
        @param has_sources Whether the project holds source files (the box is disabled and the text says why when it does not).
        @param checked Initial state of the box (the remembered preference).
        """
        super().__init__(parent)
        self.setWindowTitle("Export package")
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Write the project and its images as one package file (.pcbtz)."))
        self.sources = QCheckBox("Include the source files (Gerbers, drills, placement, BOM)")
        self.sources.setToolTip(SOURCES_TIP)
        self.sources.setChecked(bool(checked and has_sources))
        self.sources.setEnabled(has_sources)
        lay.addWidget(self.sources)
        text = SOURCES_NOTE if has_sources else "This project holds no source files (it was not imported from files in this session, or its package stores none)."
        hints = pkg.privacy_hints(parent.doc.project.package.sources) if has_sources else []
        if hints:
            # Which files, and what kind of text: the text itself is never shown (it may be a user name or a path)
            shown = "; ".join(f"{name} ({', '.join(kinds)})" for name, kinds in hints[:6]) + (f"; and {len(hints) - 6} more" if len(hints) > 6 else "")
            text += f" Found in the first {pkg.PRIVACY_HEAD_BYTES // 1024} kB of {len(hints)} file(s): {shown}. Remove it from the files before sharing the package, or leave the box off."
        self.privacy = hints
        note = QLabel(text)
        note.setWordWrap(True)
        note.setToolTip(SOURCES_TIP)
        lay.addWidget(note)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)


def export_package(win):
    """!
    @brief File - Export package…: ask about the source files, then write a copy of the project as a `.pcbtz` (the open project keeps its own file).
    @param win The MainWindow.
    @return True if a file was written.
    """
    has = stored_sources(win)
    remembered = str(win.settings.value(SETTINGS_KEY, "false")).lower() in ("1", "true")
    dlg = ExportPackageDialog(win, has, remembered)
    if dlg.exec() != QDialog.Accepted:
        return False
    if has:
        win.settings.setValue(SETTINGS_KEY, bool(dlg.sources.isChecked()))
    path, _ = QFileDialog.getSaveFileName(win, "Export package", f"{win.doc.problem.name}.pcbtz", "PCB Thermal project package (*.pcbtz)")
    if not path:
        return False
    if not path.lower().endswith(pkg.PACKAGE_SUFFIX):
        path += pkg.PACKAGE_SUFFIX
    return write_copy(win, path, dlg.sources.isChecked())


def write_copy(win, path, include_sources):
    """!
    @brief Write a package copy of the open project without changing the open document.
    @param win The MainWindow.
    @param path Target `.pcbtz`.
    @param include_sources Whether the source files go in.
    @return True if written.
    """
    project = win.doc.project
    before = project.package
    try:
        backup, notes = pkg.save_package(path, project, include_sources)
    except Exception as exc:
        project.package = before
        QMessageBox.critical(win, "Cannot export", str(exc))
        return False
    project.package = before                                  # An export is a copy: the open project keeps its state
    win._report_backup(backup)
    if notes:
        win.statusBar().showMessage("Exported. " + "; ".join(notes), 15000)
    else:
        win.statusBar().showMessage(f"Package written to {path}", 8000)
    return True


def save_as(win):
    """!
    @brief File - Save as…: JSON project or package, by the type chosen in the dialog.
    @param win The MainWindow.
    @return True if saved.
    """
    start = f"{win.doc.problem.name}{pkg.PACKAGE_SUFFIX if (win.doc.project.package is not None and win.doc.project.package.is_package) else '.pcbt.json'}"
    path, chosen = QFileDialog.getSaveFileName(win, "Save project", start, SAVE_FILTER)
    if not path:
        return False
    as_package = path.lower().endswith(pkg.PACKAGE_SUFFIX) or (not path.lower().endswith(".json") and "pcbtz" in chosen)
    if as_package and not path.lower().endswith(pkg.PACKAGE_SUFFIX):
        path += pkg.PACKAGE_SUFFIX
    if not as_package and not path.endswith(".json"):
        path += ".pcbt.json"
    include = None
    if as_package and win.doc.project.package is not None and win.doc.project.package.has_sources():
        include = win.doc.project.package.include_sources
    try:
        backup = win.doc.save(path, as_package=as_package, include_sources=include)
    except Exception as exc:
        QMessageBox.critical(win, "Cannot save", str(exc))
        return False
    win._report_backup(backup)
    report_notes(win)
    return True


def report_read_warnings(win):
    """!
    @brief After opening a package, say what its reader dropped or could not verify (a member that does not match the manifest, one not listed, one missing).
    @details A message box, because the status bar line is replaced by the next message and a changed package is something the user must see (review: the warnings
             were collected and never shown, in the window or on the command line).
    @param win The MainWindow.
    @return None
    """
    extras = win.doc.project.package
    warnings = list(getattr(extras, "warnings", None) or [])
    if not warnings:
        return
    shown = "\n".join(f"- {w}" for w in warnings[:12]) + (f"\n- and {len(warnings) - 12} more" if len(warnings) > 12 else "")
    QMessageBox.warning(win, "Package opened with warnings", f"The project was opened, but some members of the package were not used as they are:\n\n{shown}")


def report_notes(win):
    """!
    @brief Show in the status bar what the last save could not store (an image missing on the disk, files a plain project cannot hold).
    @param win The MainWindow.
    @return None
    """
    notes = list(win.doc.save_notes)
    if notes:
        win.statusBar().showMessage("Saved. Note: " + "; ".join(notes), 15000)
