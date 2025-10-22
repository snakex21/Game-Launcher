"""Podstawowe testy struktury aplikacji."""
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_imports():
    """Test podstawowych importów."""
    logger.info("Test 1: Importy modułów...")
    try:
        from app.core import AppContext, EventBus, DataManager
        from app.services import GameService, ReminderService, MusicService, ThemeService
        from app.plugins import LibraryPlugin, NewsPlugin
        from app.ui import MainWindow
        logger.info("✓ Wszystkie moduły importują się poprawnie")
        return True
    except ImportError as e:
        logger.error(f"✗ Błąd importu: {e}")
        return False


def test_event_bus():
    """Test EventBus."""
    logger.info("\nTest 2: EventBus...")
    from app.core import EventBus
    
    results = []
    bus = EventBus()
    
    def callback(value):
        results.append(value)
    
    bus.subscribe("test_event", callback)
    bus.emit("test_event", value=42)
    
    if results == [42]:
        logger.info("✓ EventBus działa poprawnie")
        return True
    else:
        logger.error(f"✗ EventBus zwrócił: {results}, oczekiwano: [42]")
        return False


def test_data_manager():
    """Test DataManagera."""
    logger.info("\nTest 3: DataManager...")
    from app.core import DataManager
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    
    try:
        dm = DataManager(temp_path)
        dm.set("test_key", "test_value")
        
        dm2 = DataManager(temp_path)
        value = dm2.get("test_key")
        
        if value == "test_value":
            logger.info("✓ DataManager działa poprawnie")
            return True
        else:
            logger.error(f"✗ DataManager zwrócił: {value}, oczekiwano: test_value")
            return False
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_app_context():
    """Test AppContext."""
    logger.info("\nTest 4: AppContext...")
    from app.core import AppContext
    from app.services import GameService
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    
    try:
        context = AppContext(temp_path)
        context.register_service("games", GameService(context.data_manager, context.event_bus))
        
        games_service = context.service("games")
        if games_service and hasattr(games_service, 'games'):
            logger.info("✓ AppContext działa poprawnie")
            return True
        else:
            logger.error("✗ AppContext nie zarejestrował serwisu poprawnie")
            return False
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_game_service():
    """Test GameService."""
    logger.info("\nTest 5: GameService...")
    from app.core import AppContext
    from app.services import GameService
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    
    try:
        context = AppContext(temp_path)
        game_service = GameService(context.data_manager, context.event_bus)
        
        # Dodaj grę
        game = game_service.add({"name": "Test Game", "exe_path": "/test/path"})
        
        # Pobierz grę
        found = game_service.get(game.id)
        
        if found and found.name == "Test Game":
            logger.info("✓ GameService działa poprawnie")
            return True
        else:
            logger.error("✗ GameService nie dodał/znalazł gry")
            return False
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_theme_service():
    """Test ThemeService."""
    logger.info("\nTest 6: ThemeService...")
    from app.core import AppContext
    from app.services import ThemeService
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    
    try:
        context = AppContext(temp_path)
        theme_service = ThemeService(context.data_manager, context.event_bus)
        
        theme = theme_service.get_active_theme()
        
        if theme and hasattr(theme, 'name'):
            logger.info(f"✓ ThemeService działa poprawnie (aktywny motyw: {theme.name})")
            return True
        else:
            logger.error("✗ ThemeService nie zwrócił motywu")
            return False
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def main():
    """Uruchom wszystkie testy."""
    logger.info("=" * 60)
    logger.info("Game Launcher 2.0 - Testy Podstawowe")
    logger.info("=" * 60)
    
    tests = [
        test_imports,
        test_event_bus,
        test_data_manager,
        test_app_context,
        test_game_service,
        test_theme_service,
    ]
    
    results = [test() for test in tests]
    
    logger.info("\n" + "=" * 60)
    logger.info(f"Wyniki: {sum(results)}/{len(results)} testów zakończonych sukcesem")
    logger.info("=" * 60)
    
    if all(results):
        logger.info("\n✅ Wszystkie testy przeszły pomyślnie!")
        return 0
    else:
        logger.error("\n❌ Niektóre testy nie powiodły się")
        return 1


if __name__ == "__main__":
    sys.exit(main())
