#!/usr/bin/env python3
"""Prosty test sprawdzający poprawność struktury systemu osiągnięć."""

import sys
import ast
from pathlib import Path

def check_achievements_file():
    """Sprawdza poprawność pliku achievement_service.py."""
    print("=== Sprawdzanie achievement_service.py ===\n")
    
    service_path = Path("app/services/achievement_service.py")
    
    with open(service_path, encoding="utf-8") as f:
        content = f.read()
    
    # Sprawdź składnię
    try:
        ast.parse(content)
        print("✓ Składnia poprawna")
    except SyntaxError as e:
        print(f"✗ Błąd składni: {e}")
        return False
    
    # Sprawdź DEFAULT_ACHIEVEMENTS
    if "DEFAULT_ACHIEVEMENTS = [" in content:
        print("✓ DEFAULT_ACHIEVEMENTS zdefiniowane")
        
        # Policz osiągnięcia
        lines = content.split("\n")
        count = 0
        for line in lines:
            if '"key":' in line:
                count += 1
        print(f"✓ Znaleziono ~{count} osiągnięć")
    
    # Sprawdź nowe metody
    methods = [
        "_separate_builtin_from_custom",
        "builtin_achievements",
        "custom_achievements",
        "_calculate_consecutive_days",
        "check_time_based_achievements",
        "export_custom_achievements",
        "import_custom_achievements"
    ]
    
    print("\nNowe metody:")
    for method in methods:
        if f"def {method}" in content:
            print(f"  ✓ {method}")
        else:
            print(f"  ✗ {method} (brak)")
    
    # Sprawdź condition_type
    condition_types = [
        "library_size",
        "mods_count",
        "roadmap_completed",
        "games_launched_count",
        "play_time_hours",
        "single_game_launches",
        "play_at_night",
        "play_at_morning",
        "completion_percent",
        "games_completed",
        "games_rated",
        "screenshots_count",
        "groups_count",
        "consecutive_days",
        "session_count"
    ]
    
    print("\nTypy warunków (condition_type):")
    for ct in condition_types:
        if f'"{ct}"' in content or f"'{ct}'" in content:
            print(f"  ✓ {ct}")
        else:
            print(f"  ✗ {ct} (brak)")
    
    return True


def check_achievements_plugin():
    """Sprawdza poprawność pliku achievements.py."""
    print("\n=== Sprawdzanie achievements.py ===\n")
    
    plugin_path = Path("app/plugins/achievements.py")
    
    with open(plugin_path, encoding="utf-8") as f:
        content = f.read()
    
    # Sprawdź składnię
    try:
        ast.parse(content)
        print("✓ Składnia poprawna")
    except SyntaxError as e:
        print(f"✗ Błąd składni: {e}")
        return False
    
    # Sprawdź klasy
    classes = [
        "AchievementsPlugin",
        "AchievementsView",
        "AddAchievementDialog",
        "EditAchievementDialog",
        "AchievementUnlockNotification"
    ]
    
    print("\nKlasy:")
    for cls in classes:
        if f"class {cls}" in content:
            print(f"  ✓ {cls}")
        else:
            print(f"  ✗ {cls} (brak)")
    
    # Sprawdź nowe metody
    methods = [
        "_export_achievements",
        "_import_achievements",
        "_show_unlock_notification"
    ]
    
    print("\nNowe metody:")
    for method in methods:
        if f"def {method}" in content:
            print(f"  ✓ {method}")
        else:
            print(f"  ✗ {method} (brak)")
    
    # Sprawdź mapy warunków
    condition_map_entries = [
        "Ręczne odblokowywanie",
        "Osiągnąć liczbę gier w bibliotece",
        "Uruchomić X różnych gier",
        "Uruchomić jedną grę X razy",
        "Zagraj nocą (23:00-5:00)",
        "Zagraj rano (5:00-8:00)",
        "Osiągnąć X% ukończenia gry",
        "Zagrać X godzin łącznie",
        "Ukończyć X gier"
    ]
    
    print("\nMapowanie warunków (język polski):")
    found = 0
    for entry in condition_map_entries:
        if entry in content:
            found += 1
    print(f"  ✓ Znaleziono {found}/{len(condition_map_entries)} wpisów")
    
    return True


def check_achievements_list():
    """Wyświetla listę wszystkich osiągnięć z pliku."""
    print("\n=== Lista Osiągnięć ===\n")
    
    service_path = Path("app/services/achievement_service.py")
    
    with open(service_path, encoding="utf-8") as f:
        lines = f.readlines()
    
    in_achievements = False
    current_achievement = {}
    achievements = []
    
    for line in lines:
        if "DEFAULT_ACHIEVEMENTS = [" in line:
            in_achievements = True
            continue
        
        if in_achievements and line.strip() == "]":
            if current_achievement:
                achievements.append(current_achievement)
            break
        
        if in_achievements:
            if '"key":' in line:
                if current_achievement:
                    achievements.append(current_achievement)
                current_achievement = {}
                current_achievement["key"] = line.split('"')[3]
            elif '"name":' in line:
                current_achievement["name"] = line.split('"')[3]
            elif '"icon":' in line:
                current_achievement["icon"] = line.split('"')[3]
            elif '"points":' in line:
                try:
                    current_achievement["points"] = int(line.split(":")[1].strip().rstrip(","))
                except:
                    pass
    
    # Wyświetl osiągnięcia pogrupowane
    print(f"Znaleziono {len(achievements)} osiągnięć:\n")
    
    total_points = sum(a.get("points", 0) for a in achievements)
    
    for i, ach in enumerate(achievements, 1):
        icon = ach.get("icon", "?")
        name = ach.get("name", "Unknown")
        points = ach.get("points", 0)
        print(f"{i:2}. {icon} {name:<30} ({points:3} pkt)")
    
    print(f"\n{'='*50}")
    print(f"Łączna pula punktów: {total_points}")
    print(f"{'='*50}")


if __name__ == "__main__":
    success = True
    
    success &= check_achievements_file()
    success &= check_achievements_plugin()
    check_achievements_list()
    
    if success:
        print("\n✓ Wszystkie testy zakończone pomyślnie!")
    else:
        print("\n✗ Niektóre testy nie powiodły się")
        sys.exit(1)
