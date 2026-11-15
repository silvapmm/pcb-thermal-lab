#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_typography.py
@brief The unit and typography sweep: no visible text of the program uses a form that pcbthermal/units.py forbids (degC, um, 'x' between numbers, a difference in °C, ...).
@details The visible texts are the string literals of the modules that write what the user reads (the window, the reports, the warnings, the command line, the
         Gerber messages), with the f-strings read as text (a placeholder stands for each value), docstrings left out; and the text of the HTML pages of
         pcbthermal/help (tags removed). Each match is reported with its file, line and the rule it breaks. A justified exception is listed in units.ALLOWED.
"""

import ast
import html
import pathlib
import re

from pcbthermal import units

ROOT = pathlib.Path(__file__).resolve().parents[1] / "pcbthermal"
# Modules whose strings the user reads: every GUI module, the help pages, and the core modules that write reports, warnings and messages
MODULES = sorted(set((ROOT / "gui").glob("*.py")) | set((ROOT / "gerber").glob("*.py"))
                 | {ROOT / n for n in ("api.py", "checks.py", "cli.py", "plots.py", "memory.py", "femmesh.py", "fem.py", "results.py", "model.py", "copper.py",
                                       "analytic.py", "lumped.py", "profiles.py", "profile_io.py", "inverse.py", "analysis.py", "project.py", "package.py",
                                       "fileschema.py", "thickness.py", "stackimpedance.py", "convection.py")})
PAGES = sorted((ROOT / "help").glob("*.html"))
RULES = [(re.compile(p), instead, why) for p, instead, why in units.FORBIDDEN]


def _module_texts(path):
    """!
    @brief The visible texts of a module: string literals that are not docstrings, f-strings joined with '9' for each value.
    @param path Module path.
    @return List of (line, text).
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docs, parts_of_f = set(), set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and body and isinstance(body[0], ast.Expr) \
                and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            docs.add(id(body[0].value))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            text = []
            for v in node.values:
                if isinstance(v, ast.Constant):
                    parts_of_f.add(id(v))
                    text.append(str(v.value))
                else:
                    text.append("9")
            out.append((node.lineno, "".join(text)))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs and id(node) not in parts_of_f:
            out.append((node.lineno, node.value))
    return out


def _page_texts(path):
    """!
    @brief The visible text of an HTML page, line by line, without tags, scripts and styles.
    @param path Page path.
    @return List of (line, text).
    """
    raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", lambda m: "\n" * m.group(0).count("\n"), path.read_text(encoding="utf-8"), flags=re.S)
    return [(i + 1, html.unescape(re.sub(r"<[^>]+>", " ", line))) for i, line in enumerate(raw.splitlines())]


def _breaks(path, texts):
    """!
    @brief The matches of the forbidden forms in the texts of one file, without the allowed exceptions.
    @param path File path.
    @param texts List of (line, text).
    @return List of messages.
    """
    allowed = [t for name, t, _why in units.ALLOWED if name == path.name]
    found = []
    for line, text in texts:
        if any(a in text for a in allowed):
            continue
        for rx, instead, why in RULES:
            m = rx.search(text)
            if m:
                found.append(f"{path.name}:{line}: {m.group(0)!r} -> {instead} ({why})")
    return found


def test_the_visible_strings_of_the_program_follow_the_unit_rule():
    """!
    @brief No visible string of the window, the reports, the warnings or the messages uses a forbidden form.
    """
    found = [msg for path in MODULES if path.exists() for msg in _breaks(path, _module_texts(path))]
    assert not found, "\n".join(found)


def test_the_help_pages_follow_the_unit_rule():
    """!
    @brief The user guide and the calculator help write °C, K for differences, µm, × and the other forms of units.py.
    """
    found = [msg for path in PAGES for msg in _breaks(path, _page_texts(path))]
    assert not found, "\n".join(found)


def test_the_sweep_finds_what_it_must_find(tmp_path):
    """!
    @brief The sweep itself is checked on a small module and page holding each old form (so a broken scan cannot pass silently).
    @param tmp_path pytest fixture.
    """
    mod = tmp_path / "sample.py"
    mod.write_text('"""!\n@brief Docstring with degC is fine.\n"""\nA = "35 um copper"\nB = f"{1} x {2} mm"\nC = "Preset shape..."\nD = "rise of 3.0 °C"\n',
                   encoding="utf-8")
    assert len(_breaks(mod, _module_texts(mod))) == 4
    page = tmp_path / "page.html"
    page.write_text("<p>ΔT °C and 20 degC</p>\n<p width='10 x 10'>ok</p>\n", encoding="utf-8")
    assert len(_breaks(page, _page_texts(page))) == 2
