#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
# PyInstaller specification of PCB Thermal Lab (one folder, not one file: the Qt libraries stay ordinary, replaceable files, which the LGPL asks for).
# Run through packaging/build.py, which makes the venv, the licence staging folder (PCBT_STAGING) and the icons first:
#   python packaging/build.py
# A spec file is Python: SPECPATH, DISTPATH and the classes below are provided by PyInstaller.
import os
import re
import sys
from pathlib import Path

import importlib.util

from PyInstaller.utils.hooks import collect_submodules, copy_metadata

ROOT = Path(SPECPATH).resolve().parent                       # noqa: F821  (SPECPATH is set by PyInstaller): the repository
STAGING = Path(os.environ["PCBT_STAGING"])                   # licences, SOURCE-OFFER.txt, BUILD-INFO.txt and the icons made by build.py
VERSION = re.search(r'__version__\s*=\s*"([^"]+)"', (ROOT / "pcbthermal" / "__init__.py").read_text(encoding="utf-8")).group(1)   # Read, not imported
NAME = "PCB-Thermal-Lab"
sys.path.insert(0, str(ROOT))                                # The build environment imports the program (bundle_info lists the libraries to bundle)
_spec = importlib.util.spec_from_file_location("pcbt_packaging_build", ROOT / "packaging" / "build.py")   # FORBIDDEN is defined once, in build.py
packaging_build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(packaging_build)
from pcbthermal import bundle_info                           # noqa: E402  (after the path is set)

# The program reads these files next to its own modules (data, user guide) and the icon from <root>/ico (gui/help.py, gui/main_window.py)
datas = [
    (str(ROOT / "pcbthermal" / "data"), "pcbthermal/data"),
    (str(ROOT / "pcbthermal" / "help"), "pcbthermal/help"),
    (str(ROOT / "ico"), "ico"),
    (str(STAGING / "licenses"), "licenses"),                  # LGPL-3.0, GPL-3.0, Qt notices and the licence of every bundled package
    (str(STAGING / "NOTICE.txt"), "."),
    (str(STAGING / "SOURCE-OFFER.txt"), "."),
    (str(STAGING / "REPLACING-QT.txt"), "."),
    (str(STAGING / "BUILD-INFO.txt"), "."),
    (str(ROOT / "LICENSE"), "."),
]

# What must not be in the package (the self-test checks the first group): developer tools, research, tests, and the Qt modules that the program does not use
excludes = [
    "tools", "research", "releases", "tests", "pytest", "pytest_qt", "pytest_timeout", "_pytest", "IPython", "tkinter", "wx",
    "matplotlib.backends.backend_tkagg", "matplotlib.backends.backend_tkcairo", "matplotlib.backends.backend_gtk3", "matplotlib.backends.backend_gtk4",
    "matplotlib.backends.backend_wx", "matplotlib.backends.backend_webagg", "matplotlib.backends.backend_nbagg",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick", "PySide6.QtWebView", "PySide6.QtPdf", "PySide6.QtPdfWidgets",
    "PySide6.QtQuick", "PySide6.QtQuickWidgets", "PySide6.QtQuickControls2", "PySide6.QtQml", "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
    "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtDesigner", "PySide6.QtHelp",
    "PySide6.QtLocation", "PySide6.QtPositioning", "PySide6.QtSensors", "PySide6.QtSerialPort", "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtBluetooth",
    "PySide6.QtNfc", "PySide6.QtRemoteObjects", "PySide6.QtScxml", "PySide6.QtWebSockets", "PySide6.QtWebChannel", "PySide6.QtSpatialAudio",
    # The GPL-3-only modules of open-source Qt 6.12 (one of them in the package would make the whole package GPL-3), and the other add-ons we never import
    "PySide6.QtGraphs", "PySide6.QtGraphsWidgets", "PySide6.QtHttpServer", "PySide6.QtLottie", "PySide6.QtNetworkAuth", "PySide6.QtCanvasPainter",
    "PySide6.QtQmlCompiler", "PySide6.QtQuick3D", "PySide6.QtQuickTest", "PySide6.QtQuickTimeline", "PySide6.QtVirtualKeyboard", "PySide6.QtGrpc", "PySide6.QtProtobuf",
    "PySide6.QtMqtt", "PySide6.QtCoap", "PySide6.QtNetwork", "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets", "PySide6.QtStateMachine", "PySide6.QtTextToSpeech",
    "PySide6.QtWaylandCompositor", "PySide6.QtXml", "PySide6.QtConcurrent", "PySide6.QtPrintSupport", "PySide6.QtUiTools", "PySide6.QtAxContainer",
]

# pyamg is imported lazily (femcore.available()), so a static scan would miss it and the finite elements would fall back to small meshes silently
hiddenimports = collect_submodules("pcbthermal") + collect_submodules("pyamg")

# The metadata of every bundled distribution: the About box reads the library table from it at run time
for _dist in bundle_info.closure().values():
    datas += copy_metadata(_dist.metadata["Name"])

a = Analysis([str(ROOT / "packaging" / "entry.py")], pathex=[str(ROOT)], datas=datas, hiddenimports=hiddenimports, excludes=excludes, noarchive=False)   # noqa: F821
# A hook that collects a whole plug-in folder can bring a forbidden library with it (the qpdf image plug-in links QtPdf, the tls plug-ins load OpenSSL): drop them here
a.binaries = [b for b in a.binaries if not packaging_build.FORBIDDEN.search(b[0].replace("\\", "/"))]
a.datas = [d for d in a.datas if not packaging_build.FORBIDDEN.search(d[0].replace("\\", "/"))]
pyz = PYZ(a.pure)                                                                                                                                   # noqa: F821

if sys.platform == "win32":
    icon = str(ROOT / "ico" / "pcb-board_256x256.ico")
elif sys.platform == "darwin":
    icon = str(STAGING / "pcb-board.icns")
else:
    icon = None                                                                       # An ELF file has no icon; the window icon comes from the code

# The windowed program has no console on Windows (so it never flashes a black window); a second program with a console answers the command line there
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name=NAME, console=sys.platform != "win32", icon=icon, upx=False)                                # noqa: F821
programs = [exe]
if sys.platform == "win32":
    programs.append(EXE(pyz, a.scripts, [], exclude_binaries=True, name=NAME + "-cli", console=True, icon=icon, upx=False))                          # noqa: F821

coll = COLLECT(*programs, a.binaries, a.datas, name=NAME, upx=False)                                                                                   # noqa: F821

if sys.platform == "darwin":
    app = BUNDLE(coll, name="PCB Thermal Lab.app", icon=icon, bundle_identifier="io.github.silvapmm.pcb-thermal-lab", version=VERSION,                # noqa: F821
                 info_plist={"CFBundleName": "PCB Thermal Lab", "CFBundleDisplayName": "PCB Thermal Lab", "CFBundleShortVersionString": VERSION,
                             "NSHighResolutionCapable": True, "NSHumanReadableCopyright": "Copyright (c) 2025-2026 Pedro Silva (PMS Labs). MIT License; Qt under the LGPL-3.0."})
