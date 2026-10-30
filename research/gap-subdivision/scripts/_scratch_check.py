import sys, time
sys.path.insert(0, "research/gap-subdivision/lib")
import boards as B
cell = 0.5
for name, kw in [("pad20 bottom empty", dict(pad=20, empty_layers=(1,))), ("pad10 bottom empty", dict(pad=10, empty_layers=(1,)))]:
    bd = B.Board(name, layers=2, gap=1.6, source=3.0, **kw)
    for dx, ns in [(0.5, 8), (0.25, 8), (0.25, 16), (0.125, 8), (0.125, 16)]:
        t = time.time()
        r = B.resolved_peak(bd, cell, dx, ns)
        print(name, dx, ns, "%.3f" % r["peak"], "mean %.3f" % r["mean"], r["unknowns"], "%.1fs" % (time.time() - t))
