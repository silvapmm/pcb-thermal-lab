# packaging: the downloadable packages

How the packages of a release (`PCB-Thermal-Lab-<version>-windows-x64.zip`, `-linux-x64.tar.gz` (a tar.gz keeps the execute bits; never a zip on Linux), `-macos-arm64.zip`) are built, one folder each (onedir; never a single file), what is in them and what must be checked.
Not legal advice (see CLAUDE.md section 5 for the rule).

## Build it here

```sh
python3 packaging/build.py --selftest     # own environment packaging/.venv-build, PyInstaller, package, archive, then --selftest of the unpacked archive
```

Output in `packaging/dist/` (git-ignored): the archive, `SHA256SUMS.txt`, `BUILD-RESULT.json`, `FILES.txt` (every file of the package, with the native libraries outside Qt listed first), and on Linux `qt-source/` (the Qt and PySide source tarballs, attached to every release). The build
needs the network (PyPI, download.qt.io) and about 1.5 GB of disk; it installs the run-time lines of `requirements.txt` (PySide6 replaced by PySide6-Essentials, the same
QtCore/QtGui/QtWidgets without the add-ons) and `requirements-build.txt`. `build.py --reuse-venv` keeps the environment.

| File | What it is |
| :-- | :-- |
| `build.py` | the whole build: environment, licence material, PyInstaller, checks, archive |
| `PCB-Thermal-Lab.spec` | the PyInstaller specification (one folder, not one file; excludes; the data, help and icon; the metadata the About box reads) |
| `entry.py` | entry point of the frozen program: `multiprocessing.freeze_support()` first, the window by default, any command of `python -m pcbthermal` after it |
| `qt_sources.py` | downloads and checks the Qt and PySide source tarballs of a release (the release assets) and makes the Qt third-party notices from them |
| `release_notes.py` | extracts the CHANGELOG section of a version (the text of a release) |
| `licenses/Qt/` | the LGPL-3.0 and GPL-3.0 texts (third-party, no header); `licenses/_fallback/` the licence text of a library whose wheel carries none (pyamg); `licenses/_system/` the licence of a native library a Qt wheel bundles from outside Qt (ICU on Linux) |
| `requirements-build.txt` | PySide6-Essentials, shiboken6 and PyInstaller, pinned EXACTLY (`build.py` fails when the installed versions differ; the three Qt/PySide numbers move together) |
| `check_release.py` | the release job's guard: the three packages carry the same Qt and PySide versions, equal to the attached tarballs; it opens every archive: the documents at the top (`REQUIRED`), the program (and `PCB-Thermal-Lab-cli.exe` on Windows), no member matching `FORBIDDEN`, both contacts of the written offer and no trial TODO text |

The workflow `.github/workflows/build-release.yml` runs `build.py` on Windows, Ubuntu 22.04 and macOS (arm64), runs the packed program's `--selftest` there, and on a tag
`v*` attaches the files to the release: it never creates a public release (if none exists it creates a DRAFT with the CHANGELOG notes), never marks Latest, never uses
generated notes; a pre-release tag (`v2.9.0rc1`, with `__version__` 2.9.0rc1; notes from the Unreleased section when it has no section of its own) makes a draft marked pre-release. The actions are pinned to the commit of an exact release. A push to a branch `build-test/**` builds and self-tests only. It runs no test battery. Executables before 2.9.0 do not exist (no retroactive builds).

## What a package contains (the LGPL checklist, per system)

- [ ] onedir: the Qt libraries are separate files (`_internal/PySide6` on Windows and Linux, `PCB Thermal Lab.app/Contents/Frameworks/PySide6` on macOS)
- [ ] at the top of the archive and inside the program: `LICENSE`, `NOTICE.txt`, `SOURCE-OFFER.txt`, `REPLACING-QT.txt`, `BUILD-INFO.txt`, `licenses/`
- [ ] `licenses/Qt/LGPL-3.0.txt` and `GPL-3.0.txt` (verbatim, byte for byte on every system: `.gitattributes` keeps `packaging/licenses/**` out of the CRLF conversion of a Windows checkout, which had changed the GPL text of the Windows trial package), `licenses/Qt/THIRD-PARTY-NOTICES.txt` (names FreeType with its credit line, libjpeg with the IJG sentence, libpng, zlib, PCRE2, HarfBuzz, double-conversion, MD4C, libtiff, libwebp, Unicode)
- [ ] a folder in `licenses/` for every bundled library (the build fails otherwise) and for PyInstaller (its bootloader is in the program), but not for the build-only tools (altgraph, macholib, setuptools, pyinstaller-hooks-contrib are not in the package); `licenses/Python/` with the PSF `LICENSE.txt` and `INCORPORATED-SOFTWARE.rst` (Doc/license.rst of the exact CPython release: libmpdec, expat, libffi, zlib, mimalloc, HACL*, ...; fetched by the build, which fails without it); on Linux `licenses/ICU/` (the Qt wheel bundles ICU 73, whose source is not in the Qt tarballs; the text is `licenses/_system/ICU/LICENSE`, ICU release-73-2, and the build fails on another ICU major); `licenses/INDEX.txt`
- [ ] every native library has its notice in the package: `check_notices` in `build.py` lists the libraries that are neither Qt nor a wheel's vendored folder (`numpy.libs`, `scipy.libs`, `pillow.libs`, `PIL/.dylibs`: in the wheel's own licence file) nor CPython and what its notices cover (libffi, expat, zlib, mpdec) nor the Microsoft C/C++ run-time (Windows; `licenses/Python/LICENSE.txt` quotes Microsoft's conditions for its Distributable Code) nor ICU (`licenses/_system`); a **release build stops** when one is left, a trial build prints them and `BUILD-RESULT.json` records them (`without_notice`). The section 'Native libraries outside PySide6' of `FILES-<system>.txt` is read for each system too. Trial run of 2.8.0 in Actions: Windows and macOS none; Linux 83, of which 45 are pruned now (see the next item) and 38 remain (X11 and xcb, xkbcommon, GLib, D-Bus, systemd, libgcrypt, fontconfig, FreeType, libpng, libstdc++, ...): the Linux package cannot be released until they get their notices or are left to the system (an open decision of the maintainer)
- [ ] nothing that matches `FORBIDDEN` in `build.py` (the GPL-3-only Qt modules, FFmpeg, QtPdf and its image plug-in, WebEngine, QML and Quick, the TLS plug-ins, `opengl32sw.dll` (Mesa, Windows), the GTK 3 platform theme (Linux) and GNU Readline (GPL-3.0; CPython's `readline` module, excluded in the spec, linked it on Linux)): the build fails if one is there. The spec also drops the plug-ins the program never loads (`UNUSED_PLUGINS`: VNC, TUIO touch, which bring QtNetwork) and, on Linux, every library that no kept binary links any more (`unreferenced_libraries`: dropping the GTK 3 theme had left GTK's own dependencies, cairo, Pango, ATK, GdkPixbuf, GIO and their own dependencies, 38 libraries in the trial package; with QtNetwork and Kerberos, 45 go)
- [ ] the versions agree: `SOURCE-OFFER.txt` = `BUILD-INFO.txt` = Help - About (live) = the tarballs attached to the release (`QT-SOURCE-SHA256.txt`)
- [ ] no EULA text, no encryption, no hash check of the Qt files, no static Qt: nothing may block replacing the Qt files
- [ ] **the Qt and PySide source tarballs are attached to EVERY release** (maintainer's decision; Qt says a link to its own servers is not sufficient): `qtbase`, `qtsvg`, `qtimageformats`, `pyside-setup` and `qtwayland` (Linux), about 76 MB once per release, with `QT-SOURCE-SHA256.txt`, NOT committed to git. There is no mode without them. `python3 packaging/qt_sources.py --qt X --pyside Y --out DIR` downloads and checks them by hand. The release notes list them (`release_notes.py --build-result BUILD-RESULT-linux-x64.json` appends the paragraph; the draft the workflow creates carries it, so the release is never created by hand before the workflow).
- [ ] the release job checked `check_release.py` (the Qt and PySide versions of the three `BUILD-RESULT-*.json` equal each other and the tarballs); after the upload **`gh release view vX.Y.Z --json assets --jq '.assets[].name'` shows the five tarballs and `QT-SOURCE-SHA256.txt`** before the release is called closed
- [ ] no `.qm` file (the Qt translations: English-only program, their source is not attached) and no forbidden file in the package nor inside the `.app`; read the file list of every new build (top two levels, and `find . -name '*.qm'`), because a new PyInstaller hook or PySide version can bring in something the scan does not know
- [ ] **once per system before the first public release** a fresh machine (a VM or a second account without Python): download through a browser, clear Gatekeeper or SmartScreen, unzip, run, solve a board; replace `QtGui` with a REAL swap (the file from a `PySide6_Essentials` wheel of another patch version), on macOS re-sign as `REPLACING-QT.txt` says, run again; Help - About shows the Qt version that was loaded; `--selftest` exits 0

## Rules for releases (never broken)

Never delete a release, never remove one of its assets, never move or re-push its tag to other code, and never publish a package before the source assets are attached (the workflow only creates a DRAFT and uploads the source before the packages; the release is made public with `gh release edit vX.Y.Z --draft=false --latest` after `gh release view` shows the tarballs, never created by hand before the workflow). `SHA256SUMS.txt` on the release lists the packages and the tarballs by their flat names (`sha256sum -c SHA256SUMS.txt` in the download folder). The written offer runs three years and depends on the files staying there.

## Unsigned packages

macOS and Windows packages are UNSIGNED (macOS: ad hoc only, which Apple silicon requires). The README Download section explains Gatekeeper (System Settings, Privacy & Security, Open Anyway, which since macOS 15 replaces the right click, Open of older systems (Apple, "Updates to runtime protection in macOS Sequoia", and the Mac User Guide "Open a Mac app from an unknown developer"); or `xattr -dr com.apple.quarantine "PCB Thermal Lab.app"`) and SmartScreen (More info, Run anyway). `THIRD-PARTY-NOTICES.txt` is made from all the Qt modules' attribution files, so it is over-inclusive (the Qt attribution data does not say which component ends in which library); it lists every component of qtbase, qtsvg, qtimageformats and qtwayland, with the licence texts, and says so in its heading.

## Signing (constraint for later)

The hardened-runtime constraint, recorded for the future. **If a Developer ID and the hardened runtime are ever used** (needed for notarisation), library
validation would block a Qt library built by the user unless the entitlement `com.apple.security.cs.disable-library-validation` is kept, or `REPLACING-QT.txt` tells
users to re-sign the whole app ad hoc. Do not sign in a way that stops the replacement of the Qt files.
