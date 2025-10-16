# core/backup_service.py
import os
import shutil
from datetime import datetime

class BackupService:
    def __init__(self, app_context):
        self.app_context = app_context
        self.db_path = 'data/database.json'
        self.backups_dir = 'backups'
        os.makedirs(self.backups_dir, exist_ok=True)

    def create_backup(self):
        """Tworzy kopię zapasową pliku database.json z unikalną nazwą."""
        if not os.path.exists(self.db_path):
            return False, "Plik bazy danych nie istnieje. Nie ma czego zbackupować."
        
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            backup_filename = f"backup_{timestamp}.json"
            destination_path = os.path.join(self.backups_dir, backup_filename)
            
            shutil.copy(self.db_path, destination_path)
            
            print(f"Utworzono backup: {destination_path}")
            return True, f"Kopia zapasowa została pomyślnie utworzona w folderze 'backups'!"
        except Exception as e:
            print(f"Błąd podczas tworzenia backupu: {e}")
            return False, f"Wystąpił błąd: {e}"

    def restore_from_backup(self, backup_path):
        """Przywraca bazę danych z wybranego pliku backupu."""
        if not os.path.exists(backup_path):
            return False, "Wybrany plik backupu nie istnieje."
        
        try:
            shutil.copy(backup_path, self.db_path)
            print(f"Przywrócono bazę danych z pliku: {backup_path}")
            return True, "Baza danych została pomyślnie przywrócona. Uruchom ponownie aplikację, aby zobaczyć zmiany."
        except Exception as e:
            print(f"Błąd podczas przywracania backupu: {e}")
            return False, f"Wystąpił błąd: {e}"