# packaging: the downloadable packages

How the packages of a release (`PCB-Thermal-Lab-<version>-windows-x64.zip`, `-linux-x64.tar.gz`, `-macos-arm64.zip`) are built, what is in them and what must be checked.
Not legal advice (see CLAUDE.md section 5 for the rule).

## Build it here

```sh
python3 packaging/build.py --selftest     # own environment packaging/.venv-build, PyInstaller, package, archive, then --selftest of the unpacked archive
```

Output in `packaging/dist/` (git-ignored): the archive, `SHA256SUMS.txt`, `BUILD-RESULT.json`, and on Linux `qt-source/` (the Qt and PySide source tarballs). The build
needs the network (PyPI, download.qt.io) and about 1.5 GB of disk; it installs the run-time lines of `requirements.txt` (PySide6 replaced by PySide6-Essentials, the same
QtCore/QtGui/QtWidgets without the add-ons) and `requirements-build.txt`. `build.py --reuse-venv` keeps the environment.

| File | What it is |
| :-- | :-- |
| `build.py` | the whole build: environment, licence material, PyInstaller, checks, archive |
| `PCB-Thermal-Lab.spec` | the PyInstaller specification (one folder, not one file; excludes; the data, help and icon; the metadata the About box reads) |
| `entry.py` | entry point of the frozen program: `multiprocessing.freeze_support()` first, the window by default, any command of `python -m pcbthermal` after it |
| `qt_sources.py` | downloads and checks the Qt and PySide source tarballs of a release (the release assets) and makes the Qt third-party notices from them |
| `release_notes.py` | extracts the CHANGELOG section of a version (the text of a release) |
| `licenses/Qt/` | the LGPL-3.0 and GPL-3.0 texts (third-party, no header); `licenses/_fallback/` the licence text of a library whose wheel carries none (pyamg) |
| `requirements-build.txt` | PyInstaller (pinned to a major version) |

The workflow `.github/workflows/build-release.yml` runs `build.py` on Windows, Ubuntu 22.04 and macOS (arm64), runs the packed program's `--selftest` there, and on a tag
`v*` attaches the files to the release: it never creates a public release (if none exists it creates a DRAFT with the CHANGELOG notes), never marks Latest, never uses
generated notes. A push to a branch `build-test/**` builds and self-tests only. It runs no test battery. Executables before 2.9.0 do not exist (no retroactive builds).

## What a package contains (the LGPL checklist, per system)

- [ ] onedir: the Qt libraries are separate files (`_internal/PySide6` on Windows and Linux, `PCB Thermal Lab.app/Contents/Frameworks/PySide6` on macOS)
- [ ] at the top of the archive and inside the program: `LICENSE`, `NOTICE.txt`, `SOURCE-OFFER.txt`, `REPLACING-QT.txt`, `BUILD-INFO.txt`, `licenses/`
- [ ] `licenses/Qt/LGPL-3.0.txt` and `GPL-3.0.txt` (verbatim), `licenses/Qt/THIRD-PARTY-NOTICES.txt` (names FreeType with its credit line, libjpeg with the IJG sentence, libpng, zlib, PCRE2, HarfBuzz, double-conversion, MD4C, libtiff, libwebp, Unicode)
- [ ] a folder in `licenses/` for every bundled library (the build fails otherwise), `licenses/Python/`, `licenses/INDEX.txt`
- [ ] nothing that matches `FORBIDDEN` in `build.py` (the GPL-3-only Qt modules, FFmpeg, QtPdf and its image plug-in, WebEngine, QML and Quick, the TLS plug-ins): the build fails if one is there
- [ ] the versions agree: `SOURCE-OFFER.txt` = `BUILD-INFO.txt` = Help - About (live) = the tarballs attached to the release (`QT-SOURCE-SHA256.txt`)
- [ ] no EULA text, no encryption, no hash check of the Qt files, no static Qt: nothing may block replacing the Qt files
- [ ] the release carries the source tarballs (`qtbase`, `qtsvg`, `qtimageformats`, `pyside-setup`, and `qtwayland` for Linux), once per release, about 76 MB; the workflow attaches them from `packaging/dist/qt-source/`. `python3 packaging/qt_sources.py --qt X --pyside Y --out DIR` makes them by hand.
- [ ] fresh machine (a VM or a second account without Python): download through a browser, clear Gatekeeper or SmartScreen, unzip, run, solve a board; replace `QtGui` (the file from a `PySide6_Essentials` wheel), on macOS re-sign as `REPLACING-QT.txt` says, run again; Help - About shows the Qt version that was loaded; `--selftest` exits 0

## Signing (constraint for later)

The packages are unsigned (macOS: ad hoc only, which Apple silicon requires). **If a Developer ID and the hardened runtime are ever used** (needed for notarisation), library
validation would block a Qt library built by the user unless the entitlement `com.apple.security.cs.disable-library-validation` is kept, or `REPLACING-QT.txt` tells
users to re-sign the whole app ad hoc. Do not sign in a way that stops the replacement of the Qt files.
