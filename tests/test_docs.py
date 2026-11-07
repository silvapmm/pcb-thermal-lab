#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_docs.py
@brief Documentation gate: every module, class, function and method must be documented in Doxygen style.

@details Rules enforced on the `pcbthermal` package, on `examples/`, on `tools/` and on `research/<topic>/scripts/`, `releases/**/scripts/` and `releases/regression-harness/lib/`:
- a module docstring with @file and @brief,
- a class docstring with @brief,
- a function or method docstring with @brief (constructors may list only their parameters),
- an @param entry for every parameter except self and cls,
- an @return entry whenever the function returns a value.
Nested helper functions (defined inside another function) are exempt.
"""

import ast
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCES = sorted(list((ROOT / "pcbthermal").rglob("*.py")) + list((ROOT / "examples").glob("*.py"))
                 + list((ROOT / "tools").rglob("*.py"))      # tools/ (the OCR tool) follows the same Doxygen rule
                 + [f for f in (ROOT / "research").glob("*/scripts/*.py") if f.parent.parent.name != "gerbers"]
                 + list((ROOT / "releases").glob("**/scripts/*.py"))      # releases/<version>/*/scripts and the harness scripts
                 + list((ROOT / "releases" / "regression-harness" / "lib").glob("*.py")))      # research/<topic>/scripts (the Gerber research is kept by its own session)


def _returns_value(fn):
    """!
    @brief True if the function body contains a `return <value>` (outside nested functions).
    @param fn ast.FunctionDef node.
    @return bool.
    """
    stack = list(fn.body)
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        if isinstance(node, ast.Return) and node.value is not None and not (
                isinstance(node.value, ast.Constant) and node.value.value is None):
            return True
        stack.extend(ast.iter_child_nodes(node))
    return False


def _problems(path):
    """!
    @brief Documentation problems of one source file.
    @param path File path.
    @return List of strings.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    rel = path.relative_to(ROOT)
    out = []
    doc = ast.get_docstring(tree) or ""
    if path.name != "__main__.py" or doc:
        if "@file" not in doc or "@brief" not in doc:
            out.append(f"{rel}: module docstring needs @file and @brief")

    def visit_function(fn, owner):
        name = f"{rel}:{fn.lineno} {owner}{fn.name}"
        d = ast.get_docstring(fn) or ""
        if not d:
            out.append(f"{name}: missing docstring")
            return
        if fn.name != "__init__" and "@brief" not in d:
            out.append(f"{name}: missing @brief")
        args = [a.arg for a in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs if a.arg not in ("self", "cls")]
        if fn.args.vararg:
            args.append(fn.args.vararg.arg)
        if fn.args.kwarg:
            args.append(fn.args.kwarg.arg)
        for a in args:
            if f"@param {a}" not in d and f"@param[in] {a}" not in d:
                out.append(f"{name}: missing @param {a}")
        if _returns_value(fn) and "@return" not in d:
            out.append(f"{name}: missing @return")

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            visit_function(node, "")
        elif isinstance(node, ast.ClassDef):
            d = ast.get_docstring(node) or ""
            if "@brief" not in d:
                out.append(f"{rel}:{node.lineno} class {node.name}: missing @brief")
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    visit_function(item, node.name + ".")
    return out


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: str(p.relative_to(ROOT)))
def test_source_is_documented(path):
    problems = _problems(path)
    assert not problems, "\n" + "\n".join(problems)


def test_theory_document_covers_every_model_and_formula_family():
    """docs/theory.md must describe every model module and the features built on them (a new model needs its theory section)."""
    text = (ROOT / "docs" / "theory.md").read_text()
    for module in ("fvm.py", "fdm", "solid3d.py", "lumped.py", "analytic", "convection.py"):
        assert module in text, f"docs/theory.md does not mention {module}"
    for heading in ("## 2. FVM", "## 3. FDM", "## 4. 3D solid", "## 5. Lumped", "## 6. Analytic", "## 7. Metal blocks",
                    "## 8. Heat transfer coefficients", "## 9. Parts", "## 10. Power profiles", "## 11. Verification summary"):
        assert heading in text, f"docs/theory.md lost the section '{heading}'"
    # The key equations are stated
    for formula in ("G_x = (2 S₁ S₂", "(C/Δt + ϑK)", "(I + G_mod C_loc) y = y₀", "A_mn a_mn = q_mn", "ΔT = P₀ R/(1 − α P₀ R)", "Nu = 0.54 Ra"):
        assert formula in text or formula.replace("S₁ S₂", "S₁ S₂") in text, f"docs/theory.md lost the equation {formula}"


def test_theory_convection_claims_are_true():
    """The horizontal-face laws are not in Lienhard, Example 8.1 uses the laminar form, and the face turned down has the 1/5 law with its limit written."""
    text = (ROOT / "docs" / "theory.md").read_text()
    # The false statements found by the review of the sources must not return
    assert "the same forms are read in [Lienhard2024]" not in text
    assert "general form reproduces the worked example" not in text
    # What the pages of Lienhard print, and the limit of the face turned down
    for needle in ("Raithby-Hollands", "Example 8.1", "laminar** form 8.13a", "Face turned down and its limit", "exponent 1/5",
                   "No convection coefficient of the program has been compared with a measurement"):
        assert needle in text, f"docs/theory.md lost '{needle}'"
    models = (ROOT / "docs" / "models.md").read_text()
    assert "face turned down" in models and "edge-circulation limit" in models
    # The face down is the 1/5 law; the McAdams form and the unconfirmed Incropera constant are not presented as the program's law
    assert "hot face down `Nu = 0.475 Ra^{1/5}`" in text and "hot face down `Nu = 0.27" not in text
    assert "was NOT confirmed" in text and "conservative side" not in text.split("Face turned down and its limit")[1][:3000]
    assert "down: `0.475 Ra^(1/5)`" in models and "down: `0.27" not in models
