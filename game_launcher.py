"""Entry point for the Game Launcher application."""

from game_launcher.app import main
from game_launcher.launcher import GameLauncher

__all__ = ["main", "GameLauncher"]


if __name__ == "__main__":
    main()
