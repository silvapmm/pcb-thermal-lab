# Literature status for the Gerber / copper-mapping research

Written 2026-10-23. Honest record of what was read, what could only be seen in a summary, and what is still from memory.

## Not reachable in this session

The environment's network policy denies `www.electronics-cooling.com` and `www.ucamco.com` (HTTP 403 from the proxy). To read them, the host has to be added under *Allowed domains* of the cloud environment (Network access, see https://code.claude.com/docs/en/cloud-environments#network-access), or the PDFs can be put in the repository. Search summaries were used instead.

## 1. Electronics Cooling articles (summaries only)

* *Problem: effective thermal conductivity* (April 2017, https://www.electronics-cooling.com/2017/04/problem-effective-thermal-conductivity/). From the search summary: the common volume-weighted "smearing" of copper and board into one conductivity can give large errors in PCB temperature; the authors propose **two alternative procedures** that are more accurate (their content is not in the summary). The motivation quoted is the cost of a detailed model: a 6-layer 100 x 100 mm board with 0.25 mm traces would need about 1 000 000 nodes. The example in the summary: a 10 % copper path smeared gives about 40 W/m K against a board conductivity near 0.59 W/m K.
  **Not confirmed**: that the recommended procedures are "conductances between neighbouring nodes" (that wording of the previous summary came from an earlier snippet and is not in this one).
* *Strategies for the thermal modeling of metal traces on printed circuit boards* (2015) and *Creating PCB thermal conductivity maps using image processing* (2010): only titles and one line, nothing new this time. The 2010 article is described as a layer-scale method that estimates in-plane and through-plane conductivity from the copper content, noting that single-material approximations are inadequate when the board is on the critical heat path.

## 2. Effective-medium formulas (from search summaries and memory)

* Confirmed by a search summary: for 2D two-phase conductivity, **duality** (Keller 1964; Dykhne 1970) relates the effective conductivity at swapped phase conductivities; at equal volume fractions it gives an exact result (geometric mean sqrt(k1 k2) for an isotropic, self-dual microstructure). The effective conductivity lies between the Neumann and Dirichlet (Wiener-type) values, both bracketed by the phase conductivities. Hashin and Shtrikman gave optimal bounds for statistically isotropic composites, explicit in the volume fractions and conductivities.
  Sources seen: Universal bounds on the electrical and elastic response of two-phase bodies (arXiv:1105.0954); Bulgadaev, *Effective conductivity* (cond-mat/0410073); a 2017 note in Comptes Rendus Mécanique (Peigney, nonlinear HS-type bounds in 2D).
* **Not confirmed by any text read**: the explicit closed forms used in `conduction.py` for the 2D Hashin-Shtrikman bounds and the 2D Bruggeman equation k² − (a − b)(2f − 1)k − ab = 0. They agree with the known limits (f = 0, 1, equal phases, the duality sqrt(ab) at f = 1/2, the bounds ordering) in `tests/test_conduction.py`. The summaries suggest Milton, *The Theory of Composites*, and Torquato, *Random Heterogeneous Materials*, as the places to check them.

## 3. Ucamco Gerber Layer Format Specification

* Confirmed by a summary: the latest revision is 2024.05 (July 2024); the file function is written `%TF.FileFunction,Copper,L1,Top*%` (KiCad documentation) or `%TF.FileFunction,Copper,L4,Bot,Signal*%` (JLCPCB); aperture attributes use `%TA.AperFunction,...`.
* Not confirmed: the text on aperture holes and clear macro primitives, and the definition of `TO.N`. What the reader does with them comes from gerbonara's test files (their own comments say a hole does not clear) and from how KiCad writes the files, not from the specification text.

## 4. What would close the gaps

1. The two Electronics Cooling procedures (2017 article, full text): decide whether the flow-based faces are the same idea.
2. Milton or Torquato for the 2D Bruggeman / Hashin-Shtrikman closed forms, and Keller / Dykhne for the dates.
3. The Ucamco specification (free PDF), sections on apertures with holes, macros (exposure), regions and the object attributes.
