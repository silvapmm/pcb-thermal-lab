#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_expected_shifts.py
@brief Writes the table `reference/expected_shifts_2.6.0.json` from the pending files of the integration and the two result sets of the harness (baseline v2.5.2 and the final tree).
@details Each pending file of `tests/regression/data/pending/` belongs to one item of the version (map `ID`); a record that a pending file covers gets that item, a record that
         moved with no pending file is marked "??" (to be explained). The numeric limits are 1.25 times the shifts of this run (floor 1e-6 K), so the table holds the next
         version to the reviewed sizes, it does not predict them. The 2.5.0 table has the same reading.
         Usage, from the repository root, with the sets `out/v2.5.2.json` and `out/final.json` made by the harness (`study_baseline_release.py`, `study_run_suite.py`):

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
    bs=C.load_set("releases/regression-harness/out/v2.5.2.json"); fs=C.load_set("releases/regression-harness/out/final.json")
    b=C.index(bs); f=C.index(fs)
    P={os.path.basename(fn)[:-5]:json.load(open(fn)) for fn in sorted(glob.glob("tests/regression/data/pending/*.json"))}
    ID={"analytic-per-layer-edge":"K1","analytic-local-transient":"K2","exact-board-cover-reading-t":"K3","exact-board-cover-reading-cut-t":"K3","exact-board-cover-solvers":"K3",
        "cut-cell-aperture-film":"K4","solid3d-sliver-cells":"K4b","laminate-solid":"K5","laminate-edge":"K6","via-barrel-and-rim-uncoupling":"K7"}
    items=[
     ("K1","Analytic per-layer edge","feature/analytic-edge-and-local-transient","research/analytic-edge-and-transient; docs/theory.md 6","Analytic on boards with an edge coefficient"),
     ("K2","Analytic local modal transient","feature/analytic-edge-and-local-transient","research/analytic-edge-and-transient","time to 63 % of the Analytic on boards with vias"),
     ("K3","Exact board cover (and its part read-out)","fix/exact-board-cover","research/rotated-square-3d; docs/theory.md 1.3","boards with an outline across a part: FVM, FDM, 3D solid"),
     ("K4","Cut-cell aperture links and edge film (FVM)","fix/cut-cell-aperture-film","research/rotated-square-3d","FVM on boards with an outline or a block/copper edge in a cell"),
     ("K4b","3D solid cut-cell links and edge film at the closest outline point (sliver cells)","fix/solid3d-sliver-cells","research/rotated-square-3d","3D solid on boards with an outline"),
     ("K5","3D solid slabs by thickness and the face term","feature/solid3d-slabs-by-thickness","research/laminate-slabs-and-local-rule README 5","3D solid on every board (more unknowns, hence two 0.5 mm records over the harness cap)"),
     ("K6","Laminate edge band","fix/laminate-edge-band","research/laminate-slabs-and-local-rule","FVM and FDM on boards with an edge coefficient"),
     ("K7","Via barrel length d + 0.5 t_cu and rim uncoupling","fix/via-barrel-and-rim-uncoupling","research/via-partial-copper; docs/theory.md 2.6","every model on boards with vias"),
     ("K0","Items with no harness board that moves","Lumped first ring; Lumped near-edge raster; face-down convection 0.475 (harness boards use a manual h); fast-wave ripple (harness has no profile)","docs/versions.md 2.6.0","none: a shift attributed to them would be a defect"),
     ("K8","Round-off","last bits of the sums (order of the operations)","CLAUDE.md Decisions Log (symmetric LU)","at most 1e-8 K")]
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
    rules.append({"id":"R0","item":"K8","boards":"*","models":"*","cells":"*","metrics":"*","direction":"any","abs_k":[0,1e-8],"abs_w":[0,1e-8],"rel":[0,0],"status":"derived","note":"round-off of the order of the sums"})
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
    out={"format":1,"baseline":"v2.5.2","target":"2.6.0","how_to_read":"Same reading as expected_shifts_2.5.0.json. Items and rules come from the pending files of the integration branch (one per 2.6.0 item), checked by adding the pending shifts of every item that covers a record (study_pending_coverage and the additivity check of the refreeze: 1534 of 1545 metrics add up within 10 %; the other 11 are the 3D solid records where two items act on the same cells). The numeric limits are 1.25 times the shifts of this run: the table does not predict the sizes, it holds the next version to them.",
     "items":[{"id":a,"title":t,"branch":br,"evidence":ev,"moves":mv} for a,t,br,ev,mv in items],"rules":rules,"must_not_move":[],"transients":trans,"board_matrix":{}}
    json.dump(out,open("releases/regression-harness/reference/expected_shifts_2.6.0.json","w"),indent=1)
    print(len(rules),"rules",len(may),"transient rules"); print([r['item'] for r in rules if '??' in r['item']])


if __name__ == "__main__":
    main()
