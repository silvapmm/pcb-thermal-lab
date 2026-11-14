# Comparison of the program's models with other finite-element and thermal solvers on the market (study)

**Status: desk study, nothing run.** Question: besides our own reference (`research/independent-fem-edge`, `research/independent-fem-extensions`, scikit-fem, BSD-3), can the five
models be compared with OTHER solvers, is it feasible and is it licit? The study opened the vendors' and projects' pages (section 6 marks how each statement was obtained),
checked what installs on this machine (`scripts/check_candidates.py`, nothing was installed) and ends in a recommendation (section 4) and a plan (INTEGRATION.md).
Hours, memory and risks are ESTIMATES of the author, not measurements. No measured board is involved: every comparison here is numerical against numerical.

Legend of statuses (as `research/theory/BIBLIOGRAPHY.md`): **R** a page fetched and quoted (the fetch tool returns a summary of the page, so a quotation is checked to the page text it returned, not to a printed licence file); **S** a search snippet; **M** memory; **N** not obtained.

## 1. What the comparison is for, and what it cannot be

![The comparison workflow](figures/fig_01_workflow.png)
*Figure 1 (fig_01_workflow.png): one case description feeds the program and each external solver through an adapter; every solver writes the same read-out points.*

![The via cluster case](figures/fig_02_case_section.png)
*Figure 2 (fig_02_case_section.png): section of the via-cluster case with a plate and the three read-out points shared by all solvers (not to scale).*

The cases are those of `research/independent-fem-extensions` (README 2 and 8): (1) the hollow plated barrel against the program's barrel length `d + 0.5 t_cu`; (2) a part over a via cluster with a plate under the board;
(3) stripes (copper aligned with mesh lines); (4) the L outline (and the T of `independent-fem-edge`); (5) the transient (step response, time to 63 %).
What an extra solver adds over scikit-fem: **an independent code, mesh generator and assembly path** (a bug in our own `fem.py` or in our meshes cannot be shared), **a different formulation**
(second-order tetrahedra or serendipity bricks in place of our trilinear bricks; cell-centred finite volumes in OpenFOAM), and a **name that a reader knows** (a statement 'agrees with CalculiX/Elmer' is weighed more than 'agrees with our own tool').
What it cannot add: **any physical truth**. All of them solve the same conduction equation with the same boundary conditions we give them; the idealisations (film coefficients, layered laminate, hollow barrel as a wall) are ours. Agreement shows the discretisation and the
meshing are right, not that the board behaves like that: only a measurement does (the measured board stays a separate item).

## 2. The candidates

Licence column: SPDX-like, `C` marks copyleft. 'How a case is described' decides the cost of building our cases. Hours are the author's estimate for the five cases with the adapter and one tested case (section 5).

### 2.1 Free and open source

| Tool | Licence (status) | Platform on this machine (macOS arm64) | How a case is described | Our cases: effort | Verdict |
| :-- | :-- | :-- | :-- | :-- | :-- |
| FEniCSx / DOLFINx | LGPL-3.0-or-later, `C` weak (R: repository README) | conda-forge `osx-arm64` 0.10.0 (S, anaconda.org); README lists conda (recommended), pip beta wheels for Apple silicon on macOS 15 or later without PETSc, Docker arm64 (R) | **Python API**, weak forms in UFL; any element order | 14 to 20 h | **Recommended 1** |
| CalculiX (ccx, cgx) | GPL-2 `C` (S: FreeCAD wiki, OSArch wiki; one AlternativeTo listing says MIT, not trusted) | Homebrew taps by third parties, tested on an M2 (S: CalculiX forum) | text input deck (`.inp`), heat transfer step (`*HEAT TRANSFER`), quadratic bricks C3D20 and tets C3D10; mesh from Gmsh (M) | 16 to 24 h | **Recommended 2** |
| Elmer FEM | GPL-2 and LGPL-2.1 badges, policy file not read (R: repository page) | macOS compile guide, built regularly on Apple silicon (S: a mirror's issue); Homebrew formula reported inconsistent (S) | text `.sif` file, a `Heat Equation` solver, meshes from Gmsh or ElmerGrid (M); Python only through ElmerPy (M) | 18 to 26 h | Alternate of CalculiX (the install is the risk) |
| OpenFOAM (`chtMultiRegionFoam`, Foundation or ESI) | GPL-3 `C` both lines (S) | the Foundation line points Mac users to Multipass (an Ubuntu VM) (S); ESI line has a native third-party app `gerlero/openfoam-app`, v2406 via Homebrew, Apple silicon needs macOS 14 (S) | dictionaries (`blockMesh`, `snappyHexMesh`, region files, `thermophysicalProperties`); no Python | 30 to 45 h; a 25 um barrel wall is hard in a finite-volume mesh | Only for a finite-volume cross-check; do last, or skip |
| MFEM | BSD-3-Clause (R: mfem.org) | Docker images (R); a pip name `mfem` exists, version list printed by the script (it builds from source: M) | C++ or Python wrapper (PyMFEM); example heat solvers exist (M) | 20 to 28 h | Not needed if FEniCSx works; BSD makes it the cleanest licence |
| deal.II | 'open source', LGPL-2.1-or-later (M), the page did not print it (R) | not stated (R: page); conda/Homebrew (M) | C++ only | 30 h or more | Not recommended (C++ build cost) |
| FreeFEM | LGPL-3.0 (R: freefem.org) | 'All platforms' (R); macOS binary packages discussed in the forum (S) | own scripting language | 12 to 18 h | Possible, but a language only for this; lower priority |
| Code_Aster with Salome-Meca | GPL (code_aster, S); SALOME LGPL-2.1-or-later (S) | mainly Linux/Unix; the Docker image found is 8 years old (S) | Python command files | 40 h or more | Not recommended (Linux heavy, large) |
| MOOSE | LGPL-2.1 (M); the page fetch failed (403) (N) | conda on macOS (M) | text input files; Heat Conduction module | 25 to 35 h | Not recommended (install and learning cost) |
| Gmsh | GPL-2-or-later in the PyPI metadata (R: pypi json); a licence exception for OpenCASCADE exists (M) | wheel `macosx_12_0_arm64` for 4.15.2 (R); pip index OK on this machine (script) | scripted geometry in Python or `.geo`; **a mesher, not a solver** | shared by all (about 6 h, counted in the tools above) | Use as the common mesher |
| Salome (mesher and platform) | LGPL-2.1-or-later (S) | Linux and Windows listed, macOS unconfirmed (S) | GUI plus Python | not needed | Not needed |
| Python wrappers and I/O | meshio MIT (M), pygmsh (M), PyVista MIT (M), pyfreefem, FiPy (public-domain NIST, M) | all install by pip here (script: versions printed) | Python | small | meshio and PyVista only as helpers |

### 2.2 Electronics-thermal and commercial tools

| Tool | Licence and cost | Platform | How a case is described | Publishing numbers | Verdict |
| :-- | :-- | :-- | :-- | :-- | :-- |
| Ansys Icepak / Mechanical / Fluent | commercial; free **student** product limited to 'student instruction, student projects and student demonstrations'; **research needs a research licence**; academic licences bar commercial work (R: ansys.com academic terms) | Windows and Linux (S: the help pages list those; macOS not found) | GUI, Workbench, PyAnsys scripting (M) | the academic licence form says 'may not be used for competitive analysis (such as benchmarking)' and screenshots, name and logo may not appear in a benchmarking work (R) | **No** |
| COMSOL Multiphysics | commercial; trial licence: functionality test only, no commercial or academic use, **'Nor may you publish any results obtained through the use of a license to a trial version'** (R: comsol_la_license 6.4, section 2(m)); no benchmarking clause found in that version (R) | Windows, Linux, macOS (M); Apple silicon version not confirmed here (N) | GUI, Java/Python (MPh, M), Model Builder | allowed with a paid licence as far as that page shows; a licence of the maintainer's own would need reading | Only if the maintainer already holds a licence: one case by hand |
| Cadence Celsius (Thermal Solver, EC Solver) | commercial, trial form exists (S) | Windows; Linux for the solve nodes as an option (S) | GUI, from Allegro | EULA not obtained (N) | No |
| Siemens Simcenter Flotherm / Flotherm XT | commercial (S) | Windows listed in a directory page (S); no macOS | GUI, Flotherm XT scriptable (M) | EULA not obtained (N); benchmark restrictions are usual in vendor EULAs (M) | No |
| Autodesk CFD | commercial; status in 2026 unclear (S) | Windows (M) | GUI | not obtained (N) | No |
| Fusion 360 simulation | personal tier free for non-commercial use under a revenue limit; whether thermal is included on it: Autodesk's page says yes, a third-party guide says no (S, conflicting) | Windows and macOS (M) | GUI | not obtained (N); personal licence is non-commercial | No (undecided facts, closed meshing) |
| SolidWorks Simulation, Altair, KiCad | SolidWorks Windows only (M); Altair student edition not researched (N); KiCad has no thermal solver (M) | - | - | - | No |
| SimScale (cloud) | free **Community** plan: up to 2000 core hours, 10 unrestricted simulations, qualitative output beyond that, no private projects, one user; heat transfer and conjugate heat transfer marked 'Limited' (R: simscale.com/pricing); non-commercial, public projects (S) | browser | GUI plus a Python SDK (M) | public projects publish the case and the result by design; terms of service not read (N) | Possible as a third, outside check; a free tier that publishes everything fits an open repository |
| OnScale Solve | free private account, 500 core hours a year in 2019 to 2021 coverage (S); today's terms not obtained (N) | cloud | Python scripting (M) | not obtained (N) | Not worth a try before SimScale |
| Open PCB thermal tools | `KiCad_Thermal_Sim` (MIT, a 2.5D layout estimator, S), Circuit Nova (a browser tool, S), `fcad_pcb` and Salome-Elmer pipelines (S) | - | - | - | Estimators and pipelines, not references; none is a solver independent enough to add value |

### 2.3 What installs here (script `scripts/check_candidates.py`, nothing installed)

`pip index versions` on this machine printed: gmsh 4.15.2, meshio 1.2.0, scikit-fem 0.2.0, pygmsh 2.7.0, mfem (PyMFEM) up to 4.3.0.1, fenics-basix 0.11.0, pyvista 4.0, pyfreefem 1.1.5 and **no distribution of `fenics-dolfinx`** (it is a conda package; PyPI has only beta wheels: R, README of the repository, and this Python's pip finds none), `femm` none (a Windows tool). Platform tags: the Gmsh 4.15.2 release has a
`macosx_12_0_arm64` wheel (R). The script prints only the index; the wheel tag of the others was not checked (N).

## 3. The licence rule of CLAUDE.md applied

* **Never vendored, never copied.** Every copyleft tool above (Gmsh GPL, CalculiX GPL, Elmer GPL, OpenFOAM GPL, DOLFINx LGPL) is an EXTERNAL program or a library imported by a research script in a scratch
  environment (as scikit-fem and pyamg already are in `independent-fem-edge`); nothing is added to `requirements.txt`; no source, mesh template or input deck of a third party is committed. Our own adapters (MIT) write input decks that we generate.
* **Importing a GPL library inside a research process** (the Gmsh Python module is GPL-2-or-later) does not change the licence of our MIT scripts so long as we do not distribute the combination; the research scripts do not ship the library. This is not legal advice;
  a calling-as-a-subprocess route (Gmsh as an executable) removes the question and costs one more hour, so the plan uses the Gmsh executable or the module only in the scratch environment.
* **Comparison numbers**: for a free tool the number is ours (we computed it) and can be published with the tool's name and version. For commercial tools the EULA decides: Ansys academic terms forbid benchmarking use (R), COMSOL forbids publishing results of a TRIAL licence (R); the others were not read (N).
  So the plan has no commercial solver in the committed numbers.

## 4. Recommendation (1): which solvers, on which cases, in which order

1. **FEniCSx (DOLFINx)**, first. Python makes the adapter cheap, second-order Lagrange elements on Gmsh tetrahedra or bricks give a different discretisation from our Q1 bricks, and the transient (implicit Euler or Crank-Nicolson in UFL) is a few lines, so
   it is the only free candidate that serves all five cases. Install by conda-forge in a scratch environment (R: README). Case order: hollow barrel (the barrel wall of 25 um needs 3 to 4 layers of elements across it: a quadratic element is the test); part over the via cluster with the plate; stripes; L outline; transient last.
2. **CalculiX**, second. It is the solver an engineer outside the project recognises, reads a plain input deck that our adapter can write (C3D20 quadratic bricks or C3D10 tets from the same Gmsh mesh), and runs heat transfer natively (S). Order: the plate/via-cluster case and the L outline (the two where mesh and boundary handling differ most), then the hollow barrel; skip the transient unless the first three agree.
3. **Third only if the first two disagree with each other or with the program**: Elmer if CalculiX does not install, or OpenFOAM `chtMultiRegionFoam` only for the cell-centred finite-volume formulation (the L outline and stripes: the cut-cell and edge-film questions of the program are formulation-sensitive there). The cost and the thin hollow barrel make OpenFOAM the last choice.
4. **Outside, no code of ours**: one SimScale Community run of the plate/via-cluster case, for the existence of a third independent vendor path, only if the maintainer wants it (public project, 2000 core hours, 'Limited' heat transfer: the free plan may not run a case with a thermal-via cluster; to be checked in the account, N).

## 5. Recommendation (2) and (3): value, cost, memory, risks

| Item | FEniCSx | CalculiX | Elmer (alternate) | OpenFOAM (last) |
| :-- | :-- | :-- | :-- | :-- |
| What it adds over scikit-fem | independent code, P2 elements, own meshing path (Gmsh) | industry-known code, C3D20 / C3D10, input deck | same as CalculiX, different code | finite-volume formulation, no mesh element shared with any of the others |
| Hours for the five cases (estimate) | 14 to 20 | 16 to 24 | 18 to 26 | 30 to 45 |
| Hours to a first tested case | 5 to 7 | 6 to 9 | 8 to 12 | 12 to 16 |
| Memory of one solve (estimate; the cases of the extensions folder are at most about 2 GB for our tool) | under 3 GB at 300 000 unknowns (P2 tets cost more per unknown than Q1) | under 3 GB with the sparse direct solver (SPOOLES or PaStiX: M) | under 3 GB | 2 to 4 GB |
| Main risk | conda environment size (several GB on disk); pip wheels beta | brew formula by a third party; mesh converters; check that thin copper layers keep their anisotropy | macOS build fragility (S) | a thin wall and the sub-gap rule are hard on a hexahedral mesh; no Python, long learning |

**What agreement would mean.** A match within the discretisation error of the cases the extensions folder already has (about 0.1 to 1 %) with two further codes would remove the objection that the whole reference is one program; a mismatch would be a finding about our reference (not about the five models) and would be investigated before anything is said about the program.

## 6. What was read and what was not verified

Obtained **R** (page fetched and quoted by the fetch tool, which returns a summary of the page): COMSOL licence agreement 6.4 section 2 (trial, publishing, no benchmarking clause); Ansys academic terms and conditions (tiers, benchmarking, screenshots);
SimScale pricing (Community plan); Elmer repository page (licence badges, platforms); DOLFINx repository README (licence, install routes, Python); FreeFEM home page (LGPL-3.0, own language); MFEM home (BSD-3-Clause); PyPI JSON of Gmsh (version, `GPLv2+`, arm64 wheel).
**S** (search snippets only): CalculiX licence and Homebrew taps; Elmer Apple silicon status; OpenFOAM Foundation and ESI macOS routes; Ansys, Cadence, Flotherm and Autodesk platforms and status; conda-forge DOLFINx osx-arm64 build; Fusion 360 personal tier (conflicting); OnScale; Salome and Code_Aster licences and platforms; open PCB thermal tools.
**M** (memory): deal.II and MOOSE licences, MFEM and deal.II install routes, the Gmsh licence exception, Flotherm and Autodesk EULA habits, the Python-scripting routes of commercial tools, the input-deck details of CalculiX and Elmer, solver names.
**N** (not obtained): the deal.II licence page, MOOSE (403), the Elmer licence policy file, any Celsius, Flotherm and Autodesk EULA, the COMSOL licence of the maintainer, the SimScale terms of service, any Apple silicon proof for COMSOL, the Altair student licence.
Not done: no tool was installed or run, no case was built, no memory or time was measured; every hour and memory figure above is an estimate. The licence texts are not legal advice. Vendor terms change: re-read a clause on the day it matters.
