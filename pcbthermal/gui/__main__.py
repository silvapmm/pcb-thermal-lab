#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file __main__.py
@brief Allows `python -m pcbthermal.gui [project]`.
"""

import sys

from .app import main

sys.exit(main())
