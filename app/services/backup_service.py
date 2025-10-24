"""Automatyczne tworzenie kopii zapasowych."""
from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class BackupService:
    def __init__(self, data_manager, event_bus) -> None:  # type: ignore[no-untyped-def]
        self.data_manager = data_manager
        self.event_bus = event_bus
        # Pobierz lokalizację z ustawień lub użyj domyślnej
        backup_location = data_manager.get_nested("settings", "backup_location", default="backups")
        self.backup_dir = Path(backup_location)
        self.backup_dir.mkdir(exist_ok=True)

    def create_backup(self, reason: str = "manual") -> Path | None:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"config_backup_{reason}_{timestamp}.json"
            backup_path = self.backup_dir / backup_name
            
            config_path = Path(self.data_manager.config_file)
            if config_path.exists():
                shutil.copy2(config_path, backup_path)
                logger.info("Utworzono backup: %s", backup_path)
                self.event_bus.emit("backup_created", path=str(backup_path))
                
                self._cleanup_old_backups()
                return backup_path
            else:
                logger.warning("Plik konfiguracji nie istnieje")
                return None
        except Exception as e:
            logger.error("Błąd tworzenia backupu: %s", e)
            return None

    def _cleanup_old_backups(self, keep_count: int = 10) -> None:
        backups = sorted(self.backup_dir.glob("config_backup_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        
        for backup in backups[keep_count:]:
            try:
                backup.unlink()
                logger.info("Usunięto stary backup: %s", backup.name)
            except Exception as e:
                logger.error("Błąd usuwania backupu %s: %s", backup.name, e)

    def list_backups(self) -> list[dict[str, str]]:
        backups = []
        for backup in sorted(self.backup_dir.glob("config_backup_*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            backups.append({
                "name": backup.name,
                "path": str(backup),
                "size": f"{backup.stat().st_size / 1024:.2f} KB",
                "date": datetime.fromtimestamp(backup.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })
        return backups

    def restore_backup(self, backup_path: str) -> bool:
        try:
            backup = Path(backup_path)
            if not backup.exists():
                logger.error("Backup nie istnieje: %s", backup_path)
                return False
            
            config_path = Path(self.data_manager.config_file)
            shutil.copy2(backup, config_path)
            self.data_manager.load()
            
            logger.info("Przywrócono backup: %s", backup_path)
            self.event_bus.emit("backup_restored", path=backup_path)
            return True
        except Exception as e:
            logger.error("Błąd przywracania backupu: %s", e)
            return False
