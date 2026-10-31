# Literature status of the memory guard

| Key | Source | Status | Used for |
| :-- | :-- | :-- | :-- |
| George1973 | A. George, Nested dissection of a regular finite element mesh, SIAM J. Numer. Anal. 10 (1973) 345-363 | M (not opened) | fill-in of the factor of a grid, hypothesis of the exponent |
| Davis2006 | T. A. Davis, Direct Methods for Sparse Linear Systems, SIAM, 2006 | M | fill, orderings, memory of LU |
| GeorgeLiu1981 | A. George, J. W. H. Liu, Computer Solution of Large Sparse Positive Definite Systems, Prentice-Hall, 1981 | N | minimum degree and its tie-breaking |
| LiSuperLU2005 | X. S. Li, An overview of SuperLU, ACM Trans. Math. Softw. 31 (2005) 302-325; SuperLU user guide | N (the guide is an open copy to fetch) | memory held by `splu`, the column orderings |
| SciPySuperLU | SciPy documentation of `splu` and `spsolve` | M (entry exists as M) | arguments, copies of the matrix |
| PythonResource | Python documentation of `resource.getrusage` and `os.wait4`; man pages | M | the unit of `ru_maxrss`, the usage of one child |

Nothing was opened in the preparation; after the ladder is run the statements that the fit does not need are taken to R by reading the pages that matter and writing the page and theorem numbers here and in `research/theory/BIBLIOGRAPHY.md` section 22.
