#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_expected_shifts.py
@brief Writes the table `reference/expected_shifts_2.7.0.json` from the pending files of the integration and the two result sets of the harness (baseline v2.6.0 and the final tree).
@details Each pending file of `tests/regression/data/pending/` belongs to one item of the version (map `ID`); a record that a pending file covers gets that item, a record that
         moved with no pending file is marked "??" (to be explained). The numeric limits are 1.25 times the shifts of this run (floor 1e-6 K), so the table holds the next
         version to the reviewed sizes, it does not predict them. The 2.5.0 table has the same reading.
         Usage, from the repository root, with the sets `out/v2.6.0.json` and `out/final.json` made by the harness (`study_baseline_release.py`, `study_run_suite.py`):

         .venv/bin/python releases/regression-harness/scripts/make_expected_shifts.py
"""

import json,glob,os,sys,collections
sys.path.insert(0,"releases/regression-harness/lib")
import regress_classify as C  # noqa: E402


def main():
    """!
    @brief Builds the rules, the transient rules and the item list, and writes the JSON table.

    @return None
    """
    bs=C.load_set("releases/regression-harness/out/v2.6.0.json"); fs=C.load_set("releases/regression-harness/out/final.json")
    b=C.index(bs); f=C.index(fs)
    P={os.path.basename(fn)[:-5]:json.load(open(fn)) for fn in sorted(glob.glob("tests/regression/data/pending/*.json"))}
    ID={"simple-stackup-physical-layers":"L1","drawn-layers-edge-film-centroid":"L2","fdm-harmonic-face-mean":"L3","fdm-copper-edge-faces":"L4"}
    items=[
     ("L1","Simple stack-up slabs are the physical layers","fix/simple-stackup-physical-layers","docs/validation.md 43; research/strong-edge-laminate 8","FVM, Lumped and Analytic of boards with three or more simple layers (example_board, profile_board, example_cut_to_T up +0.063 to +0.091 K; times to 63 % U1 -1.6 to -2.4 %, U2 -10.6 to -17.0 %)"),
     ("L2","Centroid edge film for the drawn layers (FVM)","fix/drawn-layers-edge-film-centroid","docs/validation.md 40","FVM of part_across_outline and round_outline (+0.0024 to +0.0091 K, times +0.01 to +0.03 %)"),
     ("L3","FDM face between nodes is the harmonic mean of the physical sheets","fix/fdm-harmonic-face-mean","docs/validation.md 41","FDM of seven boards (0 to +0.0026 K)"),
     ("L4","FDM in-plane face sheet of a drawn copper layer from the copper fill of the cells","fix/fdm-copper-edge-faces","docs/validation.md 47; research/fdm-inset-edge","FDM of boards with a copper edge inside the board (plate_pad +45.0 / +27.3 / +15.3 K, one_layer_pad +8.5 / +5.4 / +3.1, part_top_path +1.35 / +0.98 / +0.59, two_layer_partial +1.71 / +1.52 / +0.87 K at 2 / 1 / 0.5 mm; example boards +0.107 to +0.136 K, U2 time -9 to -14.5 %); the 3D solid moves nowhere"),
     ("L0","Items with no frozen record","imported via rim mask; imported copper edge film and outline mask; Lumped lone-via grouping; hole kinds; text and GUI items","docs/versions.md 2.7.0","none: a shift attributed to them would be a defect"),
     ("L8","Round-off","last bits of the sums (order of the operations)","CLAUDE.md Decisions Log (symmetric LU)","at most 1e-8 K")]
    by=collections.defaultdict(list)
    mx={}
    for (bd,m,c,s),rb in b.items():
        rf=f[(bd,m,c,s)]
        if s!="direct" or rb["status"]!="ok" or rf["status"]!="ok": continue
        k=f"{bd}|{m}|{c:g}"; its=tuple(sorted({ID[n] for n,p in P.items() if k in p["records"]}))
        mb,mf=C.metrics_of(rb),C.metrics_of(rf)
        t=w=u=0.0
        for n in mf:
            d=abs(mf[n]-mb.get(n,mf[n]))
            if d<=1e-8: continue
            g=C.metric_group(n)
            if g=="temperature": t=max(t,d)
            elif g=="balance": w=max(w,d)
            elif g=="count": u=max(u,d/abs(mb[n]))
        if not its:
            if t or w or u: its=("??",)
            else: continue
        by[(its,m)].append((bd,c,k,t,w,u))
    rules=[]
    for i,((its,m),recs) in enumerate(sorted(by.items())):
        lim={}
        for bd,c,k,t,w,u in recs:
            e={"abs_k":[0,round(max(1.25*t,1e-6),6)]}
            if w: e["abs_w"]=[0,max(1.25*w,1e-9)]
            if u: e["rel"]=[0,round(max(1.25*u,1e-3),5)]
            lim[k]=e
        boards=sorted({r[0] for r in recs}); cells=sorted({r[1] for r in recs})
        rules.append({"id":f"R{i+1}","item":"+".join(its),"boards":boards,"models":[m],"cells":cells,"metrics":"*","direction":"any","abs_k":[0,50],"abs_w":[0,1e-6],"rel":[0,1],
          "status":"quantified" if "??" not in its else "to be explained","note":"items from the pending files of the integration; limits = 1.25 x the shift of this run (floor 1e-6 K)","limits":lim})

    sb,sf=C.index(bs,"sor"),C.index(fs,"sor")
    for (bd,m,c,sv),rb in sorted(sb.items()):
        rf=sf[(bd,m,c,sv)]
        if rb["status"]!="ok" or rf["status"]!="ok": continue
        mb,mf=C.metrics_of(rb),C.metrics_of(rf)
        t=max([abs(mf[n]-mb[n]) for n in mf if n in mb and C.metric_group(n)=="temperature"]+[0])
        its=sorted({ID[n] for n,p in P.items() if f"{bd}|fvm|{c:g}" in p["records"]})
        if t<=1e-8: continue
        rules.append({"id":f"S{len(rules)}","item":"+".join(its) or "??","boards":[bd],"models":["fvm_sor"],"cells":[c],"metrics":"*","direction":"any","abs_k":[0,round(max(1.25*t,1e-6),6)],"abs_w":[0,1e-6],"rel":[0,1],"status":"quantified","note":"the SOR run reaches the direct FVM solution: the same items as the FVM record"})
    rules.append({"id":"R0","item":"L8","boards":"*","models":"*","cells":"*","metrics":"*","direction":"any","abs_k":[0,1e-8],"abs_w":[0,1e-8],"rel":[0,0],"status":"derived","note":"round-off of the order of the sums"})
    # transients
    tb={(t["board"],t["model"]):t for t in bs["transients"]}; tf={(t["board"],t["model"]):t for t in fs["transients"]}
    may=[]
    for key,t in sorted(tf.items()):
        o=tb[key]
        if t["status"]!="ok" or o["status"]!="ok": continue
        k=f"{key[0]}|{key[1]}"; its=sorted({ID[n] for n,p in P.items() if k in p["transients"]})
        po={p["name"]:p["t63_s"] for p in o["parts"]}; mxr=0
        for p in t["parts"]:
            if p["t63_s"] is None or po[p["name"]] is None: continue
            mxr=max(mxr,abs(p["t63_s"]-po[p["name"]])/po[p["name"]])
        if mxr>1e-6 or its:
            may.append({"id":f"T{len(may)+1}","boards":[key[0]],"models":[key[1]],"direction":"any","rel_change":[0,round(max(1.25*mxr,0.01),4)],"item":"+".join(its) or "??","note":"time to 63 %"})
    trans={"must_not_move":[],"may_move":may+[{"id":"T0","boards":"*","models":"*","direction":"any","rel_change":[0,1e-6],"note":"round-off of the time to 63 %"}]}
    out={"format":1,"baseline":"v2.6.0","target":"2.7.0","how_to_read":"Same reading as expected_shifts_2.6.0.json. Items and rules come from the four pending files of 2.7.0 (one per item; each record is in one file only). The numeric limits are 1.25 times the shifts of this run: the table does not predict the sizes, it holds the next version to them.",
     "items":[{"id":a,"title":t,"branch":br,"evidence":ev,"moves":mv} for a,t,br,ev,mv in items],"rules":rules,"must_not_move":[],"transients":trans,"board_matrix":{}}
    json.dump(out,open("releases/regression-harness/reference/expected_shifts_2.7.0.json","w"),indent=1)
    print(len(rules),"rules",len(may),"transient rules"); print([r['item'] for r in rules if '??' in r['item']])


if __name__ == "__main__":
    main()
