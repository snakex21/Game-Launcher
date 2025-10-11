"""
Menedżer statystyk
Zarządza statystykami gier, wykresy i analizy.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class StatsManager:
    """
    Klasa zarządzająca statystykami gier i aplikacji.
    Generuje wykresy, analizy i raporty.
    """
    
    def __init__(self, launcher_instance=None):
        """
        Inicjalizuje menedżer statystyk.
        
        Args:
            launcher_instance: Referencja do głównej instancji launchera
        """
        self.launcher = launcher_instance
        logger.debug("StatsManager zainicjalizowany")
    
    def get_playtime_by_game(self) -> List[Dict[str, Any]]:
        """
        Zwraca czas gry dla każdej gry.
        
        Returns:
            Lista słowników z nazwą gry i czasem gry
        """
        if not self.launcher or not hasattr(self.launcher, 'games_data'):
            return []
        
        stats = []
        for game in self.launcher.games_data:
            stats.append({
                'name': game.get('name', 'Nieznana'),
                'playtime': game.get('total_playtime', 0),
                'playtime_hours': game.get('total_playtime', 0) / 3600
            })
        
        # Sortuj po czasie gry
        stats.sort(key=lambda x: x['playtime'], reverse=True)
        return stats
    
    def get_launch_count_by_game(self) -> List[Dict[str, Any]]:
        """
        Zwraca liczbę uruchomień dla każdej gry.
        
        Returns:
            Lista słowników z nazwą gry i liczbą uruchomień
        """
        if not self.launcher or not hasattr(self.launcher, 'games_data'):
            return []
        
        stats = []
        for game in self.launcher.games_data:
            stats.append({
                'name': game.get('name', 'Nieznana'),
                'launches': game.get('launch_count', 0)
            })
        
        # Sortuj po liczbie uruchomień
        stats.sort(key=lambda x: x['launches'], reverse=True)
        return stats
    
    def get_playtime_by_month(self, months: int = 12) -> Dict[str, float]:
        """
        Zwraca czas gry w ostatnich N miesiącach.
        
        Args:
            months: Liczba miesięcy wstecz
            
        Returns:
            Słownik {miesiąc: czas_w_godzinach}
        """
        # TODO: Implementacja wymaga śledzenia historii sesji gry
        # Na razie placeholder
        return {}
    
    def get_total_stats(self) -> Dict[str, Any]:
        """
        Zwraca ogólne statystyki.
        
        Returns:
            Słownik z ogólnymi statystykami
        """
        if not self.launcher or not hasattr(self.launcher, 'games_data'):
            return {
                'total_games': 0,
                'total_playtime': 0,
                'total_launches': 0,
                'average_playtime': 0
            }
        
        games = self.launcher.games_data
        total_playtime = sum(g.get('total_playtime', 0) for g in games)
        total_launches = sum(g.get('launch_count', 0) for g in games)
        
        return {
            'total_games': len(games),
            'total_playtime': total_playtime,
            'total_playtime_hours': total_playtime / 3600,
            'total_launches': total_launches,
            'average_playtime': (total_playtime / len(games)) if games else 0,
            'average_launches': (total_launches / len(games)) if games else 0
        }
    
    def get_favorite_games(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Zwraca ulubione gry (według czasu gry).
        
        Args:
            limit: Liczba gier do zwrócenia
            
        Returns:
            Lista ulubionych gier
        """
        playtime_stats = self.get_playtime_by_game()
        return playtime_stats[:limit]
    
    def generate_summary_report(self) -> str:
        """
        Generuje tekstowy raport statystyk.
        
        Returns:
            Raport jako string
        """
        stats = self.get_total_stats()
        top_games = self.get_favorite_games(5)
        
        report = "=== RAPORT STATYSTYK ===\n\n"
        report += f"Liczba gier: {stats['total_games']}\n"
        report += f"Całkowity czas gry: {stats['total_playtime_hours']:.1f} godzin\n"
        report += f"Całkowita liczba uruchomień: {stats['total_launches']}\n"
        report += f"Średni czas gry na grę: {stats['average_playtime']/3600:.1f} godzin\n\n"
        
        report += "=== TOP 5 NAJCZĘŚCIEJ GRANYCH ===\n"
        for i, game in enumerate(top_games, 1):
            report += f"{i}. {game['name']}: {game['playtime_hours']:.1f}h\n"
        
        return report
