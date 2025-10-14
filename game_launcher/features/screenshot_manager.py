"""Screenshot Manager - Obsługa zrzutów ekranu.

Moduł zapewnia niewielką warstwę abstrakcji nad wykonywaniem zrzutów
ekranu oraz zarządzaniem istniejącymi plikami.  W projekcie pojawiały się
odwołania konfiguracyjne do katalogu ``data/screenshots``, natomiast sam
moduł był pusty – brakowało więc implementacji faktycznie realizującej
funkcjonalność.  Poniższa klasa udostępnia trzy podstawowe operacje:

* wykonanie zrzutu ekranu (metoda :meth:`capture_screenshot`),
* listowanie dostępnych plików (:meth:`list_screenshots`),
* usuwanie wskazanego pliku (:meth:`delete_screenshot`).

Kod stara się być maksymalnie odporny na błędy środowiskowe.  Na
platformach, na których ``PIL.ImageGrab`` nie jest dostępny (np. linuxowy
serwer bez środowiska graficznego) metoda wykonująca zrzut nie zgłosi
wyjątku dalej – błąd zostanie zalogowany, a metoda zwróci ``None``.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

try:  # Pillow może być niedostępne w środowisku testowym
    from PIL import ImageGrab  # type: ignore
except Exception:  # pragma: no cover - fallback na brak środowiska GUI
    ImageGrab = None  # type: ignore

from utils.helpers import ensure_dir, sanitize_filename
from utils.logger import get_logger


class ScreenshotManager:
    """Obsługa zrzutów ekranu wykonywanych przez launcher.

    Parametry ścieżki bazowej są pobierane z konfiguracji aplikacji, ale
    klasę można wykorzystać również niezależnie od niej (np. w testach).
    Wszystkie ścieżki są normalizowane do obiektu :class:`pathlib.Path`.
    """

    def __init__(self, screenshots_dir: Path | str = "data/screenshots") -> None:
        self.logger = get_logger()
        self.screenshots_dir = ensure_dir(screenshots_dir)

    # ------------------------------------------------------------------
    def capture_screenshot(
        self,
        name: Optional[str] = None,
        region: Optional[Tuple[int, int, int, int]] = None,
        timestamp: Optional[datetime] = None,
    ) -> Optional[Path]:
        """Wykonuje zrzut ekranu i zapisuje go w katalogu screenshotów.

        Args:
            name: Opcjonalna nazwa pliku.  Jeśli nie zostanie podana,
                wykorzystany zostanie znacznik czasu (``YYYYMMDD_HHMMSS``).
            region: Krotka ``(lewo, góra, prawo, dół)`` określająca obszar
                ekranu do przechwycenia.  Brak wartości oznacza pełny ekran.
            timestamp: Własny moment czasowy – przydatne w testach, gdzie
                deterministyczna nazwa pliku upraszcza asercje.

        Returns:
            Ścieżka do zapisanego pliku lub ``None`` jeśli przechwycenie się
            nie powiodło (np. brak środowiska graficznego).
        """

        if ImageGrab is None:  # pragma: no cover - brak środowiska graficznego
            self.logger.error("Pillow ImageGrab not available – screenshot skipped")
            return None

        ts = timestamp or datetime.now()
        safe_name = sanitize_filename(name or ts.strftime("screenshot_%Y%m%d_%H%M%S"))
        file_path = self.screenshots_dir / f"{safe_name}.png"

        try:
            image = ImageGrab.grab(bbox=region)
            image.save(file_path, format="PNG")
            self.logger.info(f"Screenshot saved to {file_path}")
            return file_path
        except Exception as exc:  # pragma: no cover - zależne od środowiska
            self.logger.error(f"Failed to capture screenshot: {exc}")
            return None

    # ------------------------------------------------------------------
    def list_screenshots(self, limit: Optional[int] = None) -> List[Path]:
        """Zwraca listę zrzutów ekranu posortowaną malejąco po czasie."""

        screenshots: Iterable[Path] = self.screenshots_dir.glob("*.png")
        sorted_files = sorted(
            screenshots,
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if limit is not None:
            return sorted_files[:limit]
        return sorted_files

    # ------------------------------------------------------------------
    def delete_screenshot(self, path: Path | str) -> bool:
        """Usuwa wskazany zrzut ekranu.

        Funkcja zwraca ``True`` jeśli plik został usunięty, natomiast w
        przypadku błędu (np. plik nie istnieje) loguje problem i zwraca
        ``False``.
        """

        file_path = Path(path)
        try:
            file_path.unlink()
            self.logger.info(f"Screenshot removed: {file_path}")
            return True
        except FileNotFoundError:
            self.logger.warning(f"Screenshot not found: {file_path}")
        except Exception as exc:  # pragma: no cover - trudne do odtworzenia
            self.logger.error(f"Failed to delete screenshot {file_path}: {exc}")
        return False

