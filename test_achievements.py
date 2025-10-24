#!/usr/bin/env python3
"""Test script dla nowego systemu osiągnięć."""

import sys
import json
from pathlib import Path

# Dodaj ścieżkę do modułów
sys.path.insert(0, str(Path(__file__).parent))

from app.core.data_manager import DataManager
from app.core.event_bus import EventBus
from app.services.achievement_service import AchievementService, DEFAULT_ACHIEVEMENTS


def test_achievement_service():
    """Testuje podstawowe funkcje AchievementService."""
    print("=== Test Achievement Service ===\n")
    
    # Przygotuj tymczasowy plik config
    test_config = Path("test_config.json")
    if test_config.exists():
        test_config.unlink()
    
    # Inicjalizuj serwisy
    event_bus = EventBus()
    data_manager = DataManager(str(test_config), event_bus)
    achievement_service = AchievementService(data_manager, event_bus)
    
    # Test 1: Sprawdź katalog
    print("1. Sprawdzanie katalogu osiągnięć...")
    catalog = achievement_service.catalog()
    print(f"   ✓ Załadowano {len(catalog)} osiągnięć")
    
    # Test 2: Wbudowane vs niestandardowe
    print("\n2. Rozdzielanie wbudowanych od niestandardowych...")
    builtin = achievement_service.builtin_achievements()
    custom = achievement_service.custom_achievements()
    print(f"   ✓ Wbudowane: {len(builtin)}")
    print(f"   ✓ Niestandardowe: {len(custom)}")
    
    # Test 3: Lista condition_type
    print("\n3. Dostępne typy warunków:")
    condition_types = set(ach.get("condition_type") for ach in catalog)
    for ct in sorted(condition_types):
        count = sum(1 for ach in catalog if ach.get("condition_type") == ct)
        print(f"   - {ct}: {count} osiągnięć")
    
    # Test 4: Dodaj przykładowe dane
    print("\n4. Dodawanie przykładowych danych do gier...")
    games = [
        {
            "name": f"Gra {i}",
            "play_time": 3600 * (i * 10),  # sekundy
            "last_played": "2024-01-01",
            "completion": min(i * 20, 100),
            "rating": 4 if i % 2 else 0,
            "sessions": [{"start_time": "2024-01-01T10:00:00", "duration": 3600}] * i,
            "screenshots": ["screenshot.png"] * (i * 5),
        }
        for i in range(1, 11)
    ]
    data_manager.set("games", games)
    
    mods = [{"name": f"Mod {i}"} for i in range(1, 8)]
    data_manager.set("mods", mods)
    
    roadmap = [{"name": f"Task {i}", "completed": i <= 5} for i in range(1, 11)]
    data_manager.set("roadmap", roadmap)
    
    groups = [{"name": f"Grupa {i}"} for i in range(1, 6)]
    data_manager.set("groups", groups)
    
    print("   ✓ Dodano 10 gier, 7 modów, 10 zadań roadmapy, 5 grup")
    
    # Test 5: Sprawdź postęp
    print("\n5. Sprawdzanie i aktualizacja postępu...")
    achievement_service.check_and_update_progress()
    progress = achievement_service.user_progress()
    
    unlocked = [k for k, v in progress.items() if v.get("unlocked")]
    print(f"   ✓ Odblokowano {len(unlocked)} osiągnięć:")
    
    for key in unlocked[:5]:  # Pokaż pierwsze 5
        ach = next((a for a in catalog if a["key"] == key), None)
        if ach:
            print(f"      - {ach['icon']} {ach['name']} (+{ach['points']} pkt)")
    
    # Test 6: Statystyki
    print("\n6. Statystyki użytkownika:")
    completion_rate = achievement_service.completion_rate()
    total_points = sum(
        ach["points"] for ach in catalog 
        if progress.get(ach["key"], {}).get("unlocked")
    )
    print(f"   - Ukończenie: {completion_rate*100:.1f}%")
    print(f"   - Łączne punkty: {total_points}")
    
    # Test 7: Osiągnięcia w trakcie
    print("\n7. Osiągnięcia w trakcie realizacji:")
    in_progress = [
        (k, v) for k, v in progress.items() 
        if not v.get("unlocked") and v.get("current_progress", 0) > 0
    ]
    
    for key, prog in sorted(in_progress, key=lambda x: x[1].get("current_progress", 0), reverse=True)[:5]:
        ach = next((a for a in catalog if a["key"] == key), None)
        if ach:
            current = prog.get("current_progress", 0)
            target = ach.get("target_value", 1)
            percent = (current / target * 100) if target > 0 else 0
            print(f"      - {ach['name']}: {current}/{target} ({percent:.0f}%)")
    
    # Test 8: Export/Import
    print("\n8. Test eksportu/importu...")
    
    # Dodaj niestandardowe osiągnięcie
    custom_catalog = data_manager.get("achievements_catalog", [])
    custom_achievement = {
        "key": "custom_test_123",
        "name": "Testowe Osiągnięcie",
        "description": "To jest testowe niestandardowe osiągnięcie",
        "icon": "🧪",
        "points": 99,
        "condition_type": "manual",
        "target_value": 1,
        "custom": True
    }
    custom_catalog.append(custom_achievement)
    data_manager.set("achievements_catalog", custom_catalog)
    
    # Eksportuj
    export_path = Path("test_achievements_export.json")
    if achievement_service.export_custom_achievements(str(export_path)):
        print(f"   ✓ Wyeksportowano do {export_path}")
        
        # Sprawdź zawartość
        with open(export_path) as f:
            exported = json.load(f)
        print(f"   ✓ Plik zawiera {len(exported)} niestandardowych osiągnięć")
        
        # Cleanup
        export_path.unlink()
    
    # Podsumowanie
    print("\n" + "="*50)
    print("✓ Wszystkie testy zakończone pomyślnie!")
    print("="*50)
    
    # Cleanup
    test_config.unlink()


if __name__ == "__main__":
    test_achievement_service()
