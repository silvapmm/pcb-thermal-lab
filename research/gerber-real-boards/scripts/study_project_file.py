#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_project_file.py
@brief How big is a project file that embeds the imported copper, against one that only references the Gerber files, and does the migration from format 1 to 2 lose nothing?
@details For every downloaded board and pixels of 0.1, 0.05 and 0.025 mm the copper layers are drawn (binary mask) and packed as `lib/project_format.py` does (bits, deflate, base64): the size of the JSON text per layer
         and per board, for the binary mask and for the 8-bit coverage mask, and the size of the Gerber sources for comparison. The round trip pack -> JSON -> unpack must give the binary mask back exactly and the coverage
         within 1/255; the migration 1 -> 2 -> 1 must give a project dict equal to the original. The sizes decide the default of INTEGRATION.md (embed the mask at the pixel of the import, or keep only references).
         Output: out/project_file.json and the printed table. Success criterion (before the run): a 4-layer board of about 100 x 100 mm at 0.05 mm embedded as binary masks is under 20 MB of JSON (so the
         project can still be opened and saved in a second or two); the round trips are exact. NOT verified: the load time in the program, the size with compression of the whole file by the user's tools,
         projects that hold several imported boards.
         Run (from the repository root): .venv-research/bin/python research/gerber-real-boards/scripts/study_project_file.py   (a few minutes)
"""

import _bootstrap  # noqa: F401  (puts the import paths in order)

import json
import sys

import numpy as np

import boardrun
import project_format as pf
import rb_paths
import registry


def main(argv):
    """!
    @brief Measure the sizes and check the round trips.
    @param argv Unused.
    @return None.
    """
    rows = []
    for key in registry.available():
        r = registry.roles(key)
        src = sum(p.stat().st_size for p in r["copper"]) + sum(p.stat().st_size for p in r["drills"]) + (r["outline"].stat().st_size if r["outline"] else 0)
        for pix in (0.1, 0.05, 0.025):
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
            rows.append(rec)
            print(f"{key:9s} pix {pix:5.3f}: {rec['layers']} layers {rec['mask_shape']}  binary {rec['binary_json_bytes'] / 1e6:7.2f} MB  coverage {rec['coverage_json_bytes'] / 1e6:7.2f} MB  (Gerber sources {src / 1e6:.2f} MB)", flush=True)
    d1 = {"format": pf.FORMAT_1, "board": {"width": 0.1}, "zones": [], "solver": {}, "view": {}}
    d2 = pf.migrate_1_to_2(d1)
    assert d2["format"] == pf.FORMAT_2 and d2["imports"] == []
    assert pf.downgrade_2_to_1(d2) == d1, "migration 1 -> 2 -> 1 changed the project"
    print("migration 1 -> 2 -> 1: identical")
    rb_paths.OUT.mkdir(parents=True, exist_ok=True)
    with open(rb_paths.OUT / "project_file.json", "w") as fh:
        json.dump(rows, fh, indent=1)


if __name__ == "__main__":
    main(sys.argv[1:])
