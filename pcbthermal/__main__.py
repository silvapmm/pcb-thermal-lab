#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file __main__.py
@brief Allows `python -m pcbthermal`.
"""

import sys

from .cli import main

sys.exit(main())
