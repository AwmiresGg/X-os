"""X-OS system library.

Shared, dependency-free (Python stdlib only) backends used by X-OS command-line
tools, the boot self-test and the Control Center. Every function that reads system
state accepts a ``root`` argument so it can be unit-tested against fixture trees.
"""

__version__ = "0.1.0"
