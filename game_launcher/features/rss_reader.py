"""
RSS Reader - Pobieranie i parsowanie feedów RSS
AI-Friendly: Prosty reader z cache'owaniem
"""

import feedparser
import threading
import time
from datetime import datetime, timedelta
from utils.logger import get_logger


class RSSReader:
    """
    Pobiera i parsuje feedy RSS z newsami o grach.
    
    AI Note:
    - Automatyczne odświeżanie w tle
    - Cache newsów
    - Thread-safe
    """
    
    def __init__(self, feed_urls=None, refresh_interval=1800):
        """
        Inicjalizuje RSS Reader.
        
        Args:
            feed_urls (list): Lista URLi RSS feedów
            refresh_interval (int): Interwał odświeżania w sekundach (domyślnie 30 min)
        """
        self.logger = get_logger()
        self.feed_urls = feed_urls or [
            'https://www.ign.com/feed.xml',
            'https://www.pcgamer.com/rss/',
        ]
        self.refresh_interval = refresh_interval
        
        # Cache newsów
        self.news_cache = []
        self.last_update = None
        
        # Thread
        self.update_thread = None
        self.is_running = False
    
    def start_auto_refresh(self):
        """
        Startuje automatyczne odświeżanie w tle.
        
        AI Note: Wywołaj przy starcie aplikacji
        """
        if self.is_running:
            self.logger.warning("RSS auto-refresh already running")
            return
        
        self.is_running = True
        self.update_thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self.update_thread.start()
        self.logger.info("RSS auto-refresh started")
        
        # Natychmiastowe pierwsze pobranie
        self.fetch_news()
    
    def stop_auto_refresh(self):
        """
        Zatrzymuje auto-refresh.
        
        AI Note: Wywołaj przy zamykaniu aplikacji
        """
        self.is_running = False
        if self.update_thread:
            self.update_thread.join(timeout=2)
        self.logger.info("RSS auto-refresh stopped")
    
    def _refresh_loop(self):
        """
        Pętla odświeżania w tle.
        
        AI Note: Automatycznie pobiera co refresh_interval sekund
        """
        while self.is_running:
            try:
                self.fetch_news()
                time.sleep(self.refresh_interval)
            except Exception as e:
                self.logger.error(f"Error in RSS refresh loop: {e}")
                time.sleep(60)  # Odczekaj minutę przy błędzie
    
    def fetch_news(self, force=False):
        """
        Pobiera newsy ze wszystkich feedów.
        
        Args:
            force (bool): Wymuś pobranie nawet jeśli cache jest świeży
        
        Returns:
            list: Lista newsów (dict)
        
        AI Note: Możesz wywołać ręcznie do odświeżenia
        """
        # Sprawdź czy cache jest świeży (młodszy niż 5 minut)
        if not force and self.last_update:
            cache_age = (datetime.now() - self.last_update).total_seconds()
            if cache_age < 300:  # 5 minut
                self.logger.debug("Using cached news")
                return self.news_cache
        
        self.logger.info("Fetching news from RSS feeds...")
        all_news = []
        
        for url in self.feed_urls:
            try:
                feed = feedparser.parse(url)
                
                # Parsuj entries
                for entry in feed.entries[:10]:  # Max 10 z każdego feeda
                    news_item = self._parse_entry(entry, url)
                    if news_item:
                        all_news.append(news_item)
                
                self.logger.info(f"Fetched {len(feed.entries[:10])} news from {url}")
                
            except Exception as e:
                self.logger.error(f"Failed to fetch RSS from {url}: {e}")
        
        # Sortuj po dacie (najnowsze pierwsze)
        all_news.sort(key=lambda x: x['published'], reverse=True)
        
        # Update cache
        self.news_cache = all_news
        self.last_update = datetime.now()
        
        self.logger.info(f"Total news fetched: {len(all_news)}")
        return all_news
    
    def _parse_entry(self, entry, source_url):
        """
        Parsuje pojedynczy entry z RSS.
        
        Args:
            entry: Entry z feedparser
            source_url (str): URL źródła
        
        Returns:
            dict: Sparsowany news lub None
        
        AI Note: Konwertuje różne formaty RSS na unified dict
        """
        try:
            # Tytuł
            title = entry.get('title', 'Brak tytułu')
            
            # Link
            link = entry.get('link', '')
            
            # Opis (summary lub description)
            description = entry.get('summary', entry.get('description', ''))
            
            # Oczyszczenie HTML z opisu (prosty strip)
            import re
            description = re.sub('<[^<]+?>', '', description)
            description = description[:300] + '...' if len(description) > 300 else description
            
            # Data publikacji
            published = entry.get('published_parsed') or entry.get('updated_parsed')
            if published:
                published_dt = datetime(*published[:6])
            else:
                published_dt = datetime.now()
            
            # Źródło
            source_name = self._extract_source_name(source_url)
            
            return {
                'title': title,
                'link': link,
                'description': description,
                'published': published_dt,
                'source': source_name,
                'source_url': source_url
            }
            
        except Exception as e:
            self.logger.error(f"Failed to parse RSS entry: {e}")
            return None
    
    def _extract_source_name(self, url):
        """
        Wyciąga nazwę źródła z URL.
        
        Args:
            url (str): URL RSS
        
        Returns:
            str: Nazwa źródła
        """
        # Prosty mapping
        if 'ign.com' in url:
            return 'IGN'
        elif 'pcgamer.com' in url:
            return 'PC Gamer'
        elif 'gamespot.com' in url:
            return 'GameSpot'
        elif 'polygon.com' in url:
            return 'Polygon'
        else:
            # Wyciągnij domenę
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            return domain.replace('www.', '').split('.')[0].title()
    
    def get_cached_news(self):
        """
        Zwraca cache'owane newsy bez pobierania.
        
        Returns:
            list: Lista newsów
        
        AI Note: Szybkie - bez zapytań sieciowych
        """
        return self.news_cache
    
    def add_feed(self, url):
        """
        Dodaje nowy feed RSS.
        
        Args:
            url (str): URL RSS feeda
        
        AI Note: Użytkownik może dodać własne źródła
        """
        if url not in self.feed_urls:
            self.feed_urls.append(url)
            self.logger.info(f"Added RSS feed: {url}")
            # Odśwież newsy
            self.fetch_news(force=True)
    
    def remove_feed(self, url):
        """
        Usuwa feed RSS.
        
        Args:
            url (str): URL do usunięcia
        """
        if url in self.feed_urls:
            self.feed_urls.remove(url)
            self.logger.info(f"Removed RSS feed: {url}")