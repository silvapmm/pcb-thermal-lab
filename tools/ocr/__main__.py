#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file __main__.py
@brief Entry point of `python -m tools.ocr`.
"""

import sys

from tools.ocr.cli import main

if __name__ == "__main__":
    sys.exit(main())
