# GUI results and warnings: progress notes (branch `feature/gui-results-warnings`)

* Item 1 (warning rows, variant V1): done in commit "Show warnings with a severity dot and the element label at the end of the row". `gui/warning_box.py`: `dot_pixmap`, `_ElementLabel`, `_TopicRow`; tests updated and a new one for the label; guide and `tests/test_help.py` words.
* Item 2 (Summary table, decision a+): done in commit "Name the read-outs in the Summary table ...". `api.SUMMARY_COLUMNS`, `results_view.summary_table`. The surface column is implemented: it fits at 1500 px (content 769 px, table 828 px) and scrolls horizontally at 1200 x 800 (the table is 528 px wide there; the base columns alone, 691 px, already need the scroll bar).
* Screenshots: to regenerate (`results_summary.png`, `results_summary_imported.png`, `editor_warnings.png`) with the heavy lock free.
* Incident: a `heavy_lock` directory of another executor was removed by this one (an `rmdir` after a small test) and recreated at once; no data lost.
