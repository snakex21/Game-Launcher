"""Legacy component extracted from the monolithic launcher."""
from __future__ import annotations

from .base import *  # noqa: F401,F403
from .constants import *  # noqa: F401,F403
from .utils import *  # noqa: F401,F403

class SaveManager:
    def __init__(self, parent, game_name, game_data, launcher_instance):
        self.top = tk.Toplevel(parent)
        self.top.title(f"Zarządzanie zapisami - {game_name}")
        self.top.configure(bg="#1e1e1e")
        self.top.grab_set()

        # --- NOWE: Zapisz referencję do launchera ---
        self.launcher = launcher_instance
        # --- KONIEC NOWEGO ---

        ttk.Label(self.top, text=f"Zarządzanie zapisami - {game_name}", font=("Helvetica", 14)).pack(pady=10)

        self.game_name = game_name
        self.save_path = game_data.get("save_path")
        self.backup_path = os.path.join(GAMES_FOLDER, game_name)

        # Sprawdź poprawność ścieżki do zapisów gry
        self.is_save_path_valid = self.save_path and os.path.isdir(self.save_path)

        # Lista zapisów (w backupie)
        # --- ZMIANA: Zamiast Listbox użyj Treeview ---
        list_frame = ttk.Frame(self.top)
        list_frame.pack(pady=5, fill=tk.BOTH, expand=True, padx=10) # Dodano expand=True, fill=tk.BOTH
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1) # Pozwól Treeview rosnąć

        # Definicja kolumn
        save_cols = ("Procent", "Data", "Godzina", "Nazwa Folderu")
        self.saves_tree = ttk.Treeview(list_frame, columns=save_cols, show="headings", height=8, selectmode="browse") # Ustaw wysokość

        # Nagłówki i szerokości kolumn
        self.saves_tree.heading("Procent", text="% Ukoń.")
        self.saves_tree.column("Procent", width=60, anchor='center', stretch=False)
        self.saves_tree.heading("Data", text="Data Zapisu")
        self.saves_tree.column("Data", width=100, anchor='center', stretch=False)
        self.saves_tree.heading("Godzina", text="Godzina")
        self.saves_tree.column("Godzina", width=70, anchor='center', stretch=False)
        self.saves_tree.heading("Nazwa Folderu", text="Nazwa Folderu (Techniczna)")
        self.saves_tree.column("Nazwa Folderu", width=200, anchor='w') # Pozostała szerokość

        # Scrollbar (bez zmian, ale dla Treeview)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.saves_tree.yview)
        self.saves_tree.configure(yscrollcommand=scrollbar.set)

        self.saves_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Bindowanie podwójnego kliknięcia do wczytania zapisu
        self.saves_tree.bind("<Double-1>", lambda e: self.load_save())

        # Zastąp self.saves_listbox nowym drzewem w innych miejscach, gdzie jest używane do pobrania zaznaczenia
        # np. w load_save, edit_save, delete_save użyj self.saves_tree.selection() i self.saves_tree.item(iid, 'values') lub iid

        self.update_saves_list() # Wypełnij nowe Treeview
        # --- KONIEC ZMIANY ---

        # Ramka na przyciski akcji
        button_frame = ttk.Frame(self.top)
        button_frame.pack(pady=10, fill=tk.X, padx=10)
        # Rozłóżmy przyciski w siatce dla lepszego układu
        button_frame.columnconfigure((0, 1), weight=1) # Dwie kolumny

        # Przyciski (rozmieszczone w gridzie)
        ttk.Button(button_frame, text="Utwórz Zapis", command=self.create_save,
                   state=tk.NORMAL if self.is_save_path_valid else tk.DISABLED).grid(row=0, column=0, padx=5, pady=3, sticky="ew")
        ttk.Button(button_frame, text="Wczytaj Zapis", command=self.load_save,
                   state=tk.NORMAL if self.is_save_path_valid else tk.DISABLED).grid(row=0, column=1, padx=5, pady=3, sticky="ew")
        ttk.Button(button_frame, text="Edytuj Zapis", command=self.edit_save).grid(row=1, column=0, padx=5, pady=3, sticky="ew") # Edycja nazwy backupu zawsze możliwa
        ttk.Button(button_frame, text="Usuń Zapis", command=self.delete_save).grid(row=1, column=1, padx=5, pady=3, sticky="ew") # Usuwanie backupu zawsze możliwe

        # --- NOWE: Przycisk Otwórz Folder Zapisów ---
        open_save_folder_btn = ttk.Button(
            button_frame,
            text="Otwórz Folder Zapisów Gry",
            command=lambda: self.launcher._open_folder(self.save_path), # Użyj metody z launchera
            state=tk.NORMAL if self.is_save_path_valid else tk.DISABLED # Stan zależny od poprawności ścieżki
        )
        open_save_folder_btn.grid(row=2, column=0, columnspan=2, padx=5, pady=8, sticky="ew") # Rozciągnij na dwie kolumny
        # --- KONIEC NOWEGO ---

        ttk.Button(button_frame, text="Zamknij", command=self.top.destroy).grid(row=3, column=0, columnspan=2, padx=5, pady=(15, 5), sticky="ew")

    def update_saves_list(self):
        """Wczytuje zapisy ręczne i automatyczne do Treeview, sortując je."""
        if not hasattr(self, 'saves_tree') or not self.saves_tree.winfo_exists(): return
        for item in self.saves_tree.get_children():
            self.saves_tree.delete(item)

        autosave_path = os.path.join(self.backup_path, '_autosave')
        if os.path.isdir(autosave_path):
            try:
                mtime = os.path.getmtime(autosave_path)
                autosave_date = datetime.datetime.fromtimestamp(mtime)
                self.saves_tree.insert("", 0, iid="_autosave_", values=(
                    "AUTO", 
                    autosave_date.strftime('%Y-%m-%d'), 
                    autosave_date.strftime('%H:%M:%S'), 
                    "Automatyczny Zapis" 
                ), tags=('autosave',))
                self.saves_tree.tag_configure('autosave', foreground='lightblue', font=('Segoe UI', 9, 'italic')) # Dodano font dla lepszej czytelności
            except Exception as e: 
                logging.error(f"Błąd odczytu daty modyfikacji dla auto-zapisu: {e}")


        saves_folder = os.path.join(self.backup_path, 'saves')
        manual_saves_data = []
        if os.path.exists(saves_folder):
            for save_name_folder in os.listdir(saves_folder):
                save_full_path = os.path.join(saves_folder, save_name_folder)
                if os.path.isdir(save_full_path):
                      try:
                           mtime = os.path.getmtime(save_full_path)
                           percent = 0
                           match = re.search(r'Save_(\d+)%', save_name_folder) # Szukaj procentu w nazwie folderu
                           if match: percent = int(match.group(1))
                           manual_saves_data.append({"name": save_name_folder, "mtime": mtime, "percent": percent})
                      except OSError: 
                           manual_saves_data.append({"name": save_name_folder, "mtime": 0, "percent": 0}) # Fallback

            manual_saves_data.sort(key=lambda item: (item["mtime"], item["percent"]), reverse=True)

            for save_data_item in manual_saves_data:
                 save_date_item = datetime.datetime.fromtimestamp(save_data_item["mtime"])
                 self.saves_tree.insert("", "end", iid=save_data_item["name"], values=(
                      f"{save_data_item['percent']}%", 
                      save_date_item.strftime('%Y-%m-%d'), 
                      save_date_item.strftime('%H:%M:%S'), 
                      save_data_item["name"] 
                 ))

        children_items = self.saves_tree.get_children()
        if children_items:
             self.saves_tree.focus(children_items[0])
             self.saves_tree.selection_set(children_items[0])


    def create_save(self):
        """Tworzy nowy nazwany zapis (z paskiem postępu)."""
        if not self.is_save_path_valid: # Użyj flagi sprawdzonej w __init__
            messagebox.showwarning("Błąd", "Ścieżka do zapisów gry jest nieprawidłowa lub nie istnieje.", parent=self.top)
            return

        percent = simpledialog.askinteger("Procent ukończenia", "Podaj procent ukończenia gry dla tego zapisu:", parent=self.top)
        if percent is not None:
            save_name = f"Save_{percent}%_{time.strftime('%Y%m%d_%H%M%S')}"
            destination = os.path.join(self.backup_path, 'saves', save_name)

            # Sprawdź, czy zapis o tej nazwie już istnieje (na wszelki wypadek)
            if os.path.exists(destination):
                 messagebox.showerror("Błąd", f"Zapis o nazwie '{save_name}' już istnieje.", parent=self.top)
                 return

            # Wywołaj kopiowanie z postępem
            success = self.launcher._copy_or_delete_with_progress(
                 operation_type='copy',
                 source_path=self.save_path,
                 dest_path=destination,
                 operation_title=f"Tworzenie zapisu '{save_name}'",
                 parent_window=self.top
            )

            if success:
                # Informuj użytkownika, że proces się rozpoczął
                messagebox.showinfo("Rozpoczęto", f"Rozpoczęto tworzenie zapisu '{save_name}'.", parent=self.top)
                # Odśwież listę zapisów od razu, aby pokazać nowy wpis (nawet jeśli kopiowanie trwa)
                # LUB lepiej - dodaj callback do wątku, który odświeży listę PO zakończeniu.
                # Na razie odświeżamy od razu:
                self.update_saves_list()
            # Jeśli success == False, błąd został już pokazany w _copy_or_delete_with_progress

    def _get_selected_save_info(self):
        """Pomocnicza funkcja do pobierania informacji o zaznaczonym zapisie."""
        selection = self.saves_tree.selection()
        if not selection: return None, None, False # Zwraca (ścieżka, nazwa dla logu, czy_autosave)

        selected_iid = selection[0]
        is_autosave = (selected_iid == "_autosave_")

        if is_autosave:
             source_path = os.path.join(self.backup_path, '_autosave')
             save_name_for_log = "Automatyczny Zapis"
        else:
             # iid to teraz nazwa folderu
             save_folder_name = selected_iid
             source_path = os.path.join(self.backup_path, 'saves', save_folder_name)
             save_name_for_log = save_folder_name

        return source_path, save_name_for_log, is_autosave

    def load_save(self):
        """Wczytuje zaznaczony zapis (ręczny lub automatyczny) z Treeview z paskiem postępu."""
        # --- NOWE ZMIANY: Użycie _get_selected_save_info ---
        source_path, save_name_for_log, _ = self._get_selected_save_info() # Nie potrzebujemy tu is_autosave osobno
        
        if not source_path: # Jeśli nic nie zaznaczono
            messagebox.showwarning("Błąd", "Nie wybrano żadnego zapisu.", parent=self.top)
            return
        # --- KONIEC NOWYCH ZMIAN ---

        if not os.path.isdir(source_path):
            messagebox.showerror("Błąd", f"Ścieżka źródłowa zapisu '{source_path}' nie istnieje lub nie jest folderem.", parent=self.top)
            self.update_saves_list() 
            return

        if not self.is_save_path_valid:
            messagebox.showerror("Błąd", "Ścieżka do zapisów gry jest nieprawidłowa.\nUstaw ją w edycji gry.", parent=self.top)
            return

        if messagebox.askyesno("Potwierdź Wczytanie", f"Czy na pewno chcesz wczytać zapis '{save_name_for_log}'?\nSpowoduje to nadpisanie aktualnych zapisów gry!", parent=self.top):
            success = self.launcher._copy_or_delete_with_progress(
                 operation_type='copy',
                 source_path=source_path,
                 dest_path=self.save_path, 
                 operation_title=f"Wczytywanie zapisu '{save_name_for_log}'",
                 parent_window=self.top
            )

            if success:
                messagebox.showinfo("Rozpoczęto", f"Rozpoczęto wczytywanie zapisu '{save_name_for_log}'.", parent=self.top)
                # Po zakończeniu wątku, można zamknąć okno jeśli chcemy, lub poinformować
                # Aktualnie okno postępu zamyka się samo w wątku.
            # Błąd jest już obsługiwany w _copy_or_delete_with_progress

    # Metoda edit_save - powinna działać tylko dla zapisów ręcznych
    def edit_save(self):
        """Edytuje nazwę/procent zaznaczonego zapisu RĘCZNEGO."""
        # --- NOWE ZMIANY: Użycie _get_selected_save_info ---
        selected_save_path, old_save_name_folder, is_autosave = self._get_selected_save_info()
        
        if not selected_save_path: # Nic nie zaznaczono
             messagebox.showwarning("Błąd", "Nie wybrano zapisu do edycji.", parent=self.top)
             return

        if is_autosave:
             messagebox.showinfo("Informacja", "Nie można zmienić nazwy automatycznego zapisu.", parent=self.top)
             return
        # --- KONIEC NOWYCH ZMIAN ---

        # old_save_name_folder to teraz bezpośrednio nazwa folderu zapisu (bez 'saves/')
        
        percent = simpledialog.askinteger("Edytuj Procent Ukończenia", "Podaj nowy procent ukończenia dla tego zapisu (tylko dla nazwy):", parent=self.top)
        if percent is not None:
            try:
                 parts = old_save_name_folder.split('_')
                 timestamp_part = f"{parts[-2]}_{parts[-1]}" if len(parts) >= 3 and parts[-2].isdigit() and parts[-1].isdigit() else time.strftime('%Y%m%d_%H%M%S')
                 new_save_folder_name = f"Save_{percent}%_{timestamp_part}"
                 
                 if new_save_folder_name == old_save_name_folder: return 

                 saves_base_folder = os.path.join(self.backup_path, 'saves')
                 new_full_path_check = os.path.join(saves_base_folder, new_save_folder_name)
                 
                 if os.path.exists(new_full_path_check):
                      messagebox.showerror("Błąd", f"Zapis o nazwie '{new_save_folder_name}' już istnieje.", parent=self.top)
                      return

                 old_full_path = os.path.join(saves_base_folder, old_save_name_folder) # To samo co selected_save_path
                 
                 os.rename(old_full_path, new_full_path_check)
                 messagebox.showinfo("Sukces", "Nazwa zapisu została zaktualizowana.", parent=self.top)
                 self.update_saves_list()
            except IndexError:
                 messagebox.showerror("Błąd Nazwy", "Nie można przetworzyć starej nazwy zapisu do zmiany procentu.", parent=self.top)
            except Exception as e:
                 logging.exception(f"Błąd podczas zmiany nazwy zapisu '{old_save_name_folder}': {e}")
                 messagebox.showerror("Błąd", f"Nie udało się zaktualizować nazwy zapisu:\n{e}", parent=self.top)

    def delete_save(self):
        """Usuwa zaznaczony zapis (ręczny lub automatyczny) z Treeview z paskiem postępu."""
        path_to_delete, save_name_for_log, _ = self._get_selected_save_info()
        
        if not path_to_delete:
             messagebox.showwarning("Błąd", "Nie wybrano zapisu do usunięcia.", parent=self.top)
             return

        if not os.path.isdir(path_to_delete):
             messagebox.showerror("Błąd", f"Folder zapisu '{save_name_for_log}' nie istnieje:\n{path_to_delete}", parent=self.top)
             self.update_saves_list()
             return

        if messagebox.askyesno("Potwierdź Usunięcie", f"Czy na pewno chcesz trwale usunąć zapis '{save_name_for_log}'?", parent=self.top):
            # --- NOWA ZMIANA: Przekazanie self.update_saves_list jako callbacku ---
            success = self.launcher._copy_or_delete_with_progress(
                 operation_type='delete',
                 source_path=path_to_delete, 
                 dest_path=None,             
                 operation_title=f"Usuwanie zapisu '{save_name_for_log}'",
                 parent_window=self.top,
                 callback_on_success=self.update_saves_list # <--- TUTAJ PRZEKAZUJEMY CALLBACK
            )
            # --- KONIEC NOWEJ ZMIANY ---

            if success: # Jeśli operacja została poprawnie zainicjowana (nie oznacza to jeszcze zakończenia wątku)
                 messagebox.showinfo("Rozpoczęto", f"Rozpoczęto usuwanie zapisu '{save_name_for_log}'.\nLista zostanie odświeżona po zakończeniu.", parent=self.top)
