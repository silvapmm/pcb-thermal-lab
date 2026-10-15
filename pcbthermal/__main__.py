"""!
@file __main__.py
@brief Allows `python -m pcbthermal`.
"""

import sys

from .cli import main

sys.exit(main())
