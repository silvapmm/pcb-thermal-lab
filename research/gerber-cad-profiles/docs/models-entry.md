# `docs/models.md` and `docs/theory.md` text (import chapter), to adopt with the feature

> **Review note.** Adapt this text to `INTEGRATION.md` 7 before adopting it: the user's assignment of a file is final (above X2); the reader tolerances are general, not per profile; no user-file profiles and no outline pruning in 2.5.0; no Zuken profile; evidence shown only as marker ids and a sanitised version.

## CAD profile (import, no physics)

The Gerber import does not depend on a CAD profile for any physical quantity. A profile (`pcbthermal/data/cad_profiles.json`, module `pcbthermal.gerber.profiles`) is a set of defaults for **reading** the files of one eCAD program, applied in this order of trust for the function of a file:

0. the user's assignment of the file in the import window (final);
1. the X2 attribute `TF.FileFunction` the file carries;
2. the Excellon header (`M48`, the `; #@! TF.FileFunction` comment, `;TYPE=PLATED`);
2b. the content of the file (a Gerber head is never an Excellon drill file);
3. the name rules of the **profile** (regular expressions on the file name, with kind and side);
4. the generic name rules of `functions.py`.

`detect_profile(files)` scores the markers of the table on the names and the first 8 kB of each file (a marker of weight 9 or more is decisive) and returns the profile, a confidence (high, mixed, medium, low, declared, unknown) and the evidence (marker ids and the version, never the text of the file). The choice of the user replaces the detection. The profile also supplies tolerances for known quirks of a tool's drill and Gerber files, the outline rule (file, prune dangling segments, or none) and the placement columns; it never presets the bottom-side X sign of a placement file (detected from the paste openings).

Picture for the documents (to copy to `docs/images/` when adopted): `research/gerber-cad-profiles/figures/fig_01_recognition_flow.png` (the flow), `fig_02_tool_differences.png` (what differs between tools), `fig_03_bottom_x_sign.png` (the placement sign, schematic).

Sources: the Gerber specification revision 2026.05 (section `.GenerationSoftware`, status R), the XNC specification 2021 (section 4, R), and the sample sets of `research/gerber-cad-profiles/` (R for the files, see its README section 11). No physical model, so no equations.
