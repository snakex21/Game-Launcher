# plugins/library/mod_handler.py
import os
import shutil

class ModHandler:
    DISABLED_EXTENSION = ".disabled"

    def _get_game_mods_path(self, game_path):
        """Zwraca ścieżkę do folderu _mods dla danej gry."""
        game_dir = os.path.dirname(game_path)
        return os.path.join(game_dir, "_mods")

    def discover_mods(self, game_path):
        """Skanuje folder _mods i zwraca listę znalezionych modów."""
        mods_path = self._get_game_mods_path(game_path)
        if not os.path.exists(mods_path):
            os.makedirs(mods_path)
            print(f"Utworzono folder modów dla gry: {mods_path}")
        
        found_mods = []
        for item_name in os.listdir(mods_path):
            is_active = not item_name.endswith(self.DISABLED_EXTENSION)
            mod_name = item_name.replace(self.DISABLED_EXTENSION, "") if not is_active else item_name
            
            found_mods.append({
                "name": mod_name,
                "path": os.path.join(mods_path, item_name),
                "is_active": is_active
            })
        return found_mods

    def set_mod_status(self, mod_path, activate: bool):
        """Aktywuje lub dezaktywuje mod poprzez zmianę nazwy."""
        try:
            is_currently_disabled = mod_path.endswith(self.DISABLED_EXTENSION)
            
            if activate and is_currently_disabled:
                # Aktywacja: usuń .disabled
                new_path = mod_path[:-len(self.DISABLED_EXTENSION)]
                os.rename(mod_path, new_path)
                print(f"Aktywowano mod: {os.path.basename(new_path)}")
                return True
            elif not activate and not is_currently_disabled:
                # Dezaktywacja: dodaj .disabled
                new_path = mod_path + self.DISABLED_EXTENSION
                os.rename(mod_path, new_path)
                print(f"Dezaktywowano mod: {os.path.basename(mod_path)}")
                return True
        except Exception as e:
            print(f"Błąd podczas zmiany statusu moda {mod_path}: {e}")
            return False
        return False # Nie było potrzeby zmiany

    def add_mod(self, game_path, source_path):
        """Kopiuje mod z wybranego folderu do folderu _mods gry."""
        mods_path = self._get_game_mods_path(game_path)
        mod_name = os.path.basename(source_path)
        destination_path = os.path.join(mods_path, mod_name)

        if os.path.exists(destination_path):
            print(f"Mod o nazwie '{mod_name}' już istnieje.")
            return False, f"Mod o nazwie '{mod_name}' już istnieje."
        
        try:
            print(f"Kopiowanie moda z {source_path} do {destination_path}")
            shutil.copytree(source_path, destination_path)
            return True, f"Mod '{mod_name}' został pomyślnie dodany."
        except Exception as e:
            print(f"Błąd podczas dodawania moda: {e}")
            return False, f"Błąd: {e}"

    def remove_mod(self, mod_path):
        """Usuwa folder/plik moda."""
        try:
            if os.path.isdir(mod_path):
                shutil.rmtree(mod_path)
            else:
                os.remove(mod_path)
            print(f"Usunięto mod: {mod_path}")
            return True
        except Exception as e:
            print(f"Błąd podczas usuwania moda: {e}")
            return False