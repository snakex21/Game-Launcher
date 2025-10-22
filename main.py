"""
Game Launcher 2.0 - Punkt wejścia aplikacji
"""
import logging
import sys
from pathlib import Path

from app.core import AppContext
from app.plugins import (
    LibraryPlugin,
    MusicPlayerPlugin,
    NewsPlugin,
    ReminderPlugin,
    SettingsPlugin,
    StatisticsPlugin,
)
from app.services import (
    CloudService,
    DiscordService,
    GameService,
    MusicService,
    NotificationService,
    ReminderService,
    SessionTracker,
    ThemeService,
)
from app.ui import MainWindow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("game_launcher.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Uruchamianie Game Launcher 2.0...")

    context = AppContext("config.json")

    context.register_service("games", GameService(context.data_manager, context.event_bus))
    context.register_service("sessions", SessionTracker(context.service("games"), context.event_bus))
    context.register_service("reminders", ReminderService(context.data_manager, context.event_bus))
    context.register_service("music", MusicService(context.data_manager, context.event_bus))
    context.register_service("theme", ThemeService(context.data_manager, context.event_bus))
    context.register_service("notifications", NotificationService(context.data_manager))
    context.register_service("discord", DiscordService(context.data_manager))
    context.register_service("cloud", CloudService(context.data_manager, context.event_bus))

    context.add_plugin(LibraryPlugin())
    context.add_plugin(StatisticsPlugin())
    context.add_plugin(NewsPlugin())
    context.add_plugin(ReminderPlugin())
    context.add_plugin(MusicPlayerPlugin())
    context.add_plugin(SettingsPlugin())

    context.bootstrap()

    app = MainWindow(context)
    
    try:
        logger.info("Aplikacja uruchomiona")
        app.mainloop()
    except KeyboardInterrupt:
        logger.info("Przerwano przez użytkownika")
    except Exception:
        logger.exception("Błąd krytyczny aplikacji")
    finally:
        logger.info("Zamykanie aplikacji...")
        if hasattr(context, "discord") and context.discord:
            context.discord.disconnect()


if __name__ == "__main__":
    main()
