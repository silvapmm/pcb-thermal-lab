# Reviewer's opinion: warning accordion icons (2.7.0)

Read only; nothing was edited in the program. Images seen: overview_3b_vs_5.png, legibility_12_14_16.png,
option_4_contact_sheet.png (version 4b, centred, did not exist yet when I wrote this; the opinion on the shape does not depend on the centring).
Code read: gui/warning_box.py (_TopicRow._apply), checks.warning_severity / _SEVERE_WORDS, the Cancel calculation action in main_window.py.

## 1. Which design: 3b (filled) against 4 (outline), with 5 as a reference

**I recommend 3b (both icons filled), with one adjustment: the note "i" stays in the `muted` colour (grey), not in the blue accent.**

* **Legibility at 12 px.** The filled triangle of 3b still reads as a triangle with "!" at 12 px in both themes and in greyscale.
  The outline triangle of option 4 is the ⚠ glyph of the font: a stroke of about 1 px. At 12 px, in amber `#8a5a00` on the light theme, the "!" merges with the stroke.
  In the dark theme, amber `#e0a030` holds up better, but it is still much weaker than the filled one.
  **Direct answer: no, an outline-only warning triangle is not as visible as a filled one at 12 px**, especially in the light theme.
  At 14 and 16 px the difference shrinks, but the accordion row uses the text size, about 12 to 13 px.
* **Colour blindness.** Amber and blue differ by only 0.10 to 0.11 in luminance, so it is the shape that must tell the two classes apart, not the colour.
  Triangle against circle is distinguishable in all variants. The fill adds a second signal: the filled one has more mass than the outline.
  Even so, this only helps if the warning is the heaviest element of the list.
* **Visual weight.** This is the problem of 3b as drawn. In a long list of notes, the filled blue discs compete with the warnings, because they have the same mass and a more saturated colour in the light theme.
  Option 5 solves this (filled warning, outline note) and is the one that emphasises warnings most.
  Option 4 takes weight away from both and therefore loses the warning.
  The adjustment I propose (3b with the "i" filled but in `muted`, and only the triangle in `alert`) achieves the same hierarchy as 5 without a thin ring, which at 12 px looks jagged (see legibility, row "5 light 12px").
  If the maintainer prefers 5 as it is, I also accept it. **I do not accept 4.**
* **Coherence.** The toolbar icons (gui/toolbar_icons.py) are filled shapes, drawn with QPainter in a theme colour. A filled icon drawn the same way is coherent with them.
  The Unicode glyphs of option 4 depend on the system font: on macOS ⚠ can come out as a colour emoji, and ⓘ may be missing or come from another font.
  **This is an argument against option 4, beyond taste.**
* **Summary and dock.** The results summary and the dock use the same `WarningAccordion` and change together.

## 2. The vertical offset

**I agree with the diagnosis.** In Qt rich text, an `<img>` sits its base on the text baseline, so the centre of a 14 px icon is 7 px above it.
The centre of the x-height is about 0.45 × x-height, that is about 3 to 3.5 px above the baseline at 13 px. This gives an offset of about 3.5 px.

**I do not agree with the correction.** `vertical-align:middle` plus an offset of -0.5 px calibrated on the offscreen font is not robust:
* on macOS the font is SF, with other metrics (ascent and x-height);
* with dpr 2 the half pixel rounds differently;
* Qt's support for `vertical-align` on `<img>` is partial (`middle` aligns on the centre of the line, which includes the descent, and not on the x-height).
A constant tuned on one font is misaligned on another.

**Recommended implementation:**
* Take the icon out of the rich text. The row head becomes a `QWidget` with:
  * an icon drawn in `paintEvent`, or a pixmap QLabel of fixed size;
  * the arrow and the title in a **plain-text** QLabel (HTML escaping is no longer needed).
* The icon is drawn by QPainter from a path in a unit square (as in `ThemedToolbar`), on a pixmap of `size × dpr` with `setDevicePixelRatio(dpr)`, in the theme colour. It is redrawn on `PaletteChange` and when the screen changes (`screenChanged`).
* Size: `round(QFontMetricsF(font).height() × 0.9)`. The vertical position comes from the metrics of the title label:
  `y = title_top + ascent − 0.5 × xHeight − size/2`, rounded to the physical pixel.
  The title may wrap onto several lines, so the icon aligns with the **first** line (QHBoxLayout with `AlignTop` and a computed top margin).
* **Test** (tests/test_warning_icons.py):
  * offscreen render of the row with dpr 1 and dpr 2 (`QWidget.grab()` with the `devicePixelRatio` forced, or `QT_SCALE_FACTOR=2` in a subprocess);
  * measure the ink centre of the icon (pixels that differ from the background) and the ink centre of the lowercase letters of the title (probe text "uxv" without ascenders);
  * the difference must be ≤ 1 logical px, for fonts of 11, 13 and 16 pt.
  This does not validate macOS's SF (the test runs offscreen), but the rule is based on metrics and not on a constant. **One point remains to be checked on the maintainer's real screen.**

## 3. The severity rule

Today severity is a list of words searched in the whole text, and this fails in both directions:
* "U1: 9 vias under the footprint" becomes a warning because the long text contains "(the part **too hot**)" in a measurement sentence.
* The card text "Heater U1: the whole footprint is outside the board" has none of the words in the list.
  In the program the full text carries "heats nothing" and passes as a warning, but an abbreviated title or a new wording may miss it.
  **This classification comes from the text and not from the intention of whoever wrote the warning.**

**The smallest and most robust rule:** severity is an explicit field of each warning.
* `CheckWarning.severity` becomes "high" or "note", and `_add(..., severity="note")` gets the argument.
* The "high" warnings are marked one by one where they are created. There are few: a model that does not run or is refused, a part outside the board, not converging, runaway, memory refused, invalid data.
* `warning_severity(w)` returns `getattr(w, "severity", None)` and falls back on the word list only for loose strings (the warnings from `api` and from the run that are still `str`), with the list documented there as the old path.

Tests:
1. For each high-warning factory (a table in the test), a case that triggers it and checks "high".
2. "9 vias under the footprint" gives "note" and "outside the board" gives "high", the maintainer's two examples.
3. A sweep: all warnings from `check_input` / `check_problem` on the examples and the 17 harness boards have `severity` set (none falls back on the word list).
4. The word-list text still classifies loose strings as it does today.

## 4. The dot in the summary

It can be kept with a constructor argument, `WarningAccordion(dock, select=False, note_marker="dot"|"icon")`, passed to `_TopicRow`.
**I recommend not keeping it.** The summary and the dock show the same classes of warnings. Two different markers for the same thing force the user to learn two codes.
The dot is also too small to tell apart from a list bullet (see the row "dot kept for notes" of option 4, where the arrow, the dot and the text blur together).
One component with one look is also one test.

## 5. Plan for the branch `fix/gui-warning-icons-270` (from `develop` 5bcaf57c)

**Files:**
* `pcbthermal/gui/warning_box.py`: row head as a widget (icon + plain QLabel), `_WarningIcon` drawn with QPainter with a cache by (kind, size, dpr, theme), alignment by QFontMetricsF.
* `pcbthermal/gui/theme.py`: only if a new token is needed (proposal: reuse `alert` and `muted`, none new).
* `pcbthermal/checks.py`: the `severity` field, `_add(severity=)` and the marking of the high warnings.
* The warnings of `api.py` that deserve "high" become `CheckWarning` with severity.
* **Run becomes Stop:**
  * `panels.py`: the `Run simulation (F5)` button shows `Stop (Ctrl+.)` while a calculation runs and calls `cancel_simulation`;
  * `main_window.py`: connects the calculation state to the button, and F5 during the calculation does nothing;
  * the `Cancel calculation` action and Ctrl+. stay as they are;
  * the label goes next to "Cancel" in the `NO_TOOLTIP_BUTTONS` list of the tooltip test, or gets the hint "Stop the running calculation (Ctrl+.)";
  * the button returns to Run at the end, on error and on cancellation.

**Tests:**
* `tests/test_warning_icons.py`: shape and colour by severity in both themes; ink offset ≤ 1 px with dpr 1 and 2; the icon redrawn when the theme changes.
* **Accessibility**: `accessibleName` of the head = "Warning: <title>" / "Note: <title>"; the icon has its own `accessibleName` ("Warning" / "Note") or is ignored by the reader. The test checks that the severity is in the accessible name and in the hint text, so that the icon is never the only carrier.
* Severity as in point 3.
* `tests/test_gui_boxes.py` updated (it no longer looks for ⚠ / • in the text).
* `tests/test_gui_stress.py`: a Run → Stop → Run scenario.
* `tests/test_shortcuts.py` and `tests/test_tooltips.py`.

**Documents:**
* CHANGELOG `[2.7.0]`, under Changed: the warning icons and the Run/Stop button;
* user guide (`help/index.html`): the two icons, that the summary uses the same ones and that Run becomes Stop; and `tests/test_help.py` with the new words;
* `docs/versions.md` 2.7.0;
* the screenshots that show the warnings dock (`examples/make_screenshots.py`).

**Risk for 2.7.0:** low on the physics (no number changes; the refreeze on `release/2.7.0-refreeze` is not affected). But:
* the explicit severity touches `checks.py`, so confirm that no warning text changes (`tests/test_warning_texts_plain.py`, `test_warning_context.py`);
* Run/Stop touches the flow of the calculation process, which is the most sensitive part of the GUI (races, cancellation, late result).

It needs the GUI tests and the whole battery again after the merge.
If the schedule is tight, the safe minimum for 2.7.0 is icons + alignment + explicit severity. **Stop can wait for the next one, if the reviewer of that branch finds the cancellation flow risky.**
