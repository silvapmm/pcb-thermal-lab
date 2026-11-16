# Lumped first link near an edge (A27), for `docs/research.md`

Investigation `research/lumped-edge-link`. The near-edge deficit of the Lumped part read-out was re-measured after the part read-out fix: -9.4 % of the rise on average over 432 near-edge cases (worst -22.4 %), -9.9 % and -15.9 % against an independent
converged 3D solver for a part touching a side and a corner (the FVM reference is within 0.2 %). The cause is the footprint-to-ring-1 link, which uses the potential of the part alone over a full circle and a strip for half of ring 1; the rings, areas and edge film of
the clipped board are right. A correction on a copy (ring-1 mean of the potential of the footprint and its eight mirror images, in the one-node link and in the zone model's A to ring 1 link) takes the average to -2.5 % (worst cool -8.6 %, up to +9.4 % hot at a cooled
side in a corner) and moves all 51 Lumped frozen records by -0.47 to +3.13 % of the rise and 14 times by -19.9 to +1.1 %. Proposed as a `fix/` of 2.8.0 (`INTEGRATION.md`).
