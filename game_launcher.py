"""Legacy entry point maintained for backwards compatibility.

The original monolithic implementation has been refactored into modular
packages.  This module now simply delegates to :mod:`main`, which boots the
new :class:`core.launcher.GameLauncher` class.
"""

from __future__ import annotations

from main import main


def run() -> None:
    """Execute the launcher using the new modular entry point."""

    main()


if __name__ == "__main__":
    run()
