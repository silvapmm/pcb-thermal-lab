#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_transient_edge_block.py
@brief Experiment (negative result): the per-layer edge mismatch inside the coupled block of the local modal transient, calibrated by one factor on the steady point.

@details Boards with unequal layers, an edge coefficient, a corner part and no vias. The plateau and the curve of the program (common beta) against the FVM at 1 mm and against
         the coupled block with the edge matrix S_l (beta_l - beta0) G added (lib/local_modal.py, edge=True), calibrated to the per-layer steady solution.
         Result: the matrix is indefinite where beta_l - beta0 changes sign across layers and the one-factor calibration diverges (factor 8.5 to 13) on two of four boards.
         Run from the repository root: .venv/bin/python research/analytic-2-6/scripts/study_transient_edge_block.py
"""

import sys
sys.path.insert(0,"research/analytic-2-6/lib"); sys.path.insert(0,"research/analytic-2-6/scripts"); sys.path.insert(0,"research/analytic-edge-spatial/scripts"); sys.path.insert(0,"research/analytic-edge-spatial/lib")
import numpy as np, boards26 as B, local_modal as LM, robin_perlayer as RP, study_review_checks as R
from study_transient_both import curve_err, square_peak
import cases
from pcbthermal import analytic
def tgt(p):
    """!
    @brief Steady field of the per-layer edge solution of a problem (the target of the calibration).
    @param p Problem.
    @return Array (L, ny, nx) in degC.
    """
    r=RP.solve(p,1.0)
    sh=r["sh"]; bx,by=analytic._bases(sh,300)
    cx,cy=bx.evaluate(sh["xs"]),by.evaluate(sh["ys"])
    return np.stack([cy@r["a"][:,:,l].T@cx.T for l in range(sh["L"])])+25.0
for label,L,adv,fills,hs in (("2L 1/0.2",2,False,(1,0.2),200.0),("2L .2/1",2,False,(0.2,1),200.0),("4L adv",4,True,(1,1,1,1),200.0),("2L .2/1 hs50",2,False,(0.2,1),50.0)):
    p=R.board(L,adv,hs,"corner",fills)
    t,z,r=B.step(p,"fvm",1.0); ref=B.t63(t,z[:1],r[:1])[0]
    ti,zi,ri=B.step(p,"analytic",1.0)
    print(f"{label}: FVM R {r[0]:.3f} t63 {ref:.1f} | program R {ri[0]:.3f} t63 {B.t63(ti,zi[:1],ri[:1])[0]:.1f} curve {curve_err(t,z[0],r[0],ti,zi[0],ri[0]):.1f}%",end="")
    for K in (16,):
        tl,zl,rl,s=LM.step_local(p,1.0,300,K,edge=True,target_solver=tgt)
        print(f" | edge-block K{K} s={s:.2f} R {rl[0]:.3f} t63 {B.t63(tl,zl,rl)[0]:.1f} curve {curve_err(t,z[0],r[0],tl,zl[0],rl[0]):.1f}%",flush=True)
