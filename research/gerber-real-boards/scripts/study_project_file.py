#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_project_file.py
@brief How big is a project file that embeds the imported copper, against one that only references the Gerber files, and does the program's own project API (format 2, nested) keep the imports?
@details For every downloaded board and pixels of 0.1, 0.05 and 0.025 mm the copper layers are drawn (binary mask) and packed (bits, deflate, base64): the size of the JSON text per layer by the packing of
         `lib/project_format.py` (the old prototype) and the size of the FILE the program writes (`pcbthermal.project.save_project` of the example board plus one import record with the masks packed by
         `pcbthermal.copper.pack_coverage`), for the binary mask and for the 8-bit coverage mask, against the size of the Gerber sources. The round trip pack -> JSON -> unpack must give the binary mask
         back exactly and the coverage within 1/255. The FORMAT is not prototyped here any more: the first version of this study wrote the flat layout of the research prototype (the format key changed and
         "imports" beside the keys of format 1), which the program refuses since format 2 is nested under "project". `format2_check` now goes through the program's own API: a project with an import record is
         saved and loaded back, the file is nested, a project without imports stays format 1, the flat layout is refused.
         Success criterion (before the run): a 4-layer board of about 100 x 100 mm at 0.05 mm embedded as binary masks is under 20 MB of JSON; the round trips are exact. NOT verified: the load time in the
         program, the size with compression of the whole file by the user's tools, projects that hold several imported boards, the behaviour of the released 2.4.5 with a nested file (measured in an earlier run
         on the tag extracted apart; not repeated).
         Run (from the repository root): .venv-research/bin/python research/gerber-real-boards/scripts/study_project_file.py [--pix 0.1 0.05 0.025]   (a few minutes; the pixel of 0.025 mm peaks at about 6.5 GB on CO60)
"""

import _bootstrap  # noqa: F401  (puts the import paths in order)

import json
import sys
import tempfile
from pathlib import Path

import numpy as np

import boardrun
import project_format as pf       # the old prototype: its FORMAT_2 key and pack_mask (to compare the packed sizes with the program's own)
import rb_paths
import registry


def format2_check():
    """!
    @brief What the program's project API (`pcbthermal.project`, format 2 nested under "project") does with a project that carries an import record.
    @details Four checks: (1) a project with an ImportRecord is saved and loaded by the program and the record and the packed mask come back unchanged; (2) the file on disk is nested ("project" and
             "imports" at the top, no "board" key at the top, which is what makes a 2.4.x reader refuse it); (3) a project without imports is written as format 1; (4) the flat layout of the old
             prototype is refused with ProjectFormatError.
    @return None (prints the outcome of each check; an assertion fails if one does not hold).
    """
    from pcbthermal import project as pj
    from pcbthermal import copper as cu
    from pcbthermal.model import ImportRecord, ImportedCopper
    src = json.loads((Path(rb_paths.REPO) / "examples" / "example_board.pcbt.json").read_text())
    mask = (np.arange(64 * 48).reshape(64, 48) % 7 > 2)
    layer = {"name": "F.Cu", "role": "top", "index": 0, "mask": cu.pack_coverage(mask, "binary")}
    rec = ImportRecord(name="board", copper=ImportedCopper(pix_mm=0.05, embed=True, layers=[layer]))
    with tempfile.TemporaryDirectory() as d:
        p_plain, p_imp = Path(d) / "plain.pcbt.json", Path(d) / "imp.pcbt.json"
        base = pj.project_from_dict(src)
        pj.save_project(p_plain, base)
        plain = json.loads(p_plain.read_text())
        base.imports = [rec]
        pj.save_project(p_imp, base)
        raw = json.loads(p_imp.read_text())
        back = pj.load_project(p_imp)
        mask_back = cu.unpack_coverage(back.imports[0].copper.layers[0]["mask"])
        flat = dict(src, format=pf.FORMAT_2, imports=[{"name": "board"}])
        try:
            pj.project_from_dict(flat)
            flat_msg = "OPENED (unexpected)"
        except pj.ProjectFormatError as exc:
            flat_msg = f"refused (ProjectFormatError: {exc})"
    assert plain.get("format") == pj.FORMAT_1 and "imports" not in plain
    assert raw["format"] == pj.FORMAT_2 and "project" in raw and "imports" in raw and "board" not in raw
    assert len(back.imports) == 1 and np.array_equal(mask_back > 127, mask), "the record or the mask changed in the round trip"
    assert flat_msg.startswith("refused"), "the flat layout must be refused"
    print(f"program, project without imports: written as {plain['format']}, no imports key")
    print(f"program, project with one import record: written as {raw['format']}, top-level keys {sorted(raw)}; read back with {len(back.imports)} record, mask identical")
    print(f"program, flat layout of the old prototype: {flat_msg}")


def project_file_bytes(ib, kind):
    """!
    @brief Size of the file the program writes for an imported board: the example board's project plus one import record with all the copper layers packed by the program.
    @param ib Imported board with `layers`, each a dict with "binary" and "coverage" masks.
    @param kind "binary" or "coverage".
    @return int bytes of the .pcbt.json written by `pcbthermal.project.save_project`.
    """
    from pcbthermal import project as pj
    from pcbthermal import copper as cu
    from pcbthermal.model import ImportRecord, ImportedCopper
    src = json.loads((Path(rb_paths.REPO) / "examples" / "example_board.pcbt.json").read_text())
    layers = [{"name": f"L{i + 1}", "role": "copper", "index": i, "mask": cu.pack_coverage(ly[kind], kind)} for i, ly in enumerate(ib.layers)]
    proj = pj.project_from_dict(src)
    proj.imports = [ImportRecord(name="board", copper=ImportedCopper(pix_mm=0.0, embed=True, layers=layers))]
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "p.pcbt.json"
        pj.save_project(path, proj)
        return path.stat().st_size


def main(argv):
    """!
    @brief Measure the sizes and check the round trips.
    @param argv Command-line words: "--pix 0.1 0.05" limits the pixels (the default 0.1 0.05 0.025 peaks at about 6.5 GB on CO60 at 0.025 mm).
    @return None.
    """
    pixels = (0.1, 0.05, 0.025)
    if "--pix" in argv:
        pixels = tuple(float(a) for a in argv[argv.index("--pix") + 1:] if not a.startswith("--"))
    format2_check()
    rows = []
    for key in registry.available():
        r = registry.roles(key)
        src = sum(p.stat().st_size for p in r["copper"]) + sum(p.stat().st_size for p in r["drills"]) + (r["outline"].stat().st_size if r["outline"] else 0)
        for pix in pixels:
            ib = boardrun.import_window(key, None, pix, max(pix * 10, 0.5), supersample=2)
            rec = {"board": key, "pix": pix, "layers": len(ib.layers), "mask_shape": list(ib.layers[0]["binary"].shape), "source_bytes": src}
            for kind, field in (("binary", "binary"), ("coverage", "coverage")):
                tot = 0
                for ly in ib.layers:
                    packed = pf.pack_mask(ly[field], kind)
                    text = json.dumps(packed)
                    tot += len(text)
                    back = pf.unpack_mask(json.loads(text))
                    if kind == "binary":
                        assert np.array_equal(back, ly[field]), "binary round trip changed the mask"
                    else:
                        assert np.max(np.abs(back - ly[field])) <= 1.0 / 255 + 1e-9, "coverage round trip beyond 1/255"
                rec[f"{kind}_json_bytes"] = tot
                rec[f"{kind}_program_file_bytes"] = project_file_bytes(ib, kind)     # the whole file of the program (the example board's own JSON, a few kB, is in it)
            rows.append(rec)
            print(f"{key:9s} pix {pix:5.3f}: {rec['layers']} layers {rec['mask_shape']}  binary {rec['binary_json_bytes'] / 1e6:7.2f} MB  coverage {rec['coverage_json_bytes'] / 1e6:7.2f} MB  "
                  f"program file binary {rec['binary_program_file_bytes'] / 1e6:7.2f} MB  coverage {rec['coverage_program_file_bytes'] / 1e6:7.2f} MB  (Gerber sources {src / 1e6:.2f} MB)", flush=True)
    rb_paths.OUT.mkdir(parents=True, exist_ok=True)
    with open(rb_paths.OUT / "project_file.json", "w") as fh:
        json.dump(rows, fh, indent=1)


if __name__ == "__main__":
    main(sys.argv[1:])
