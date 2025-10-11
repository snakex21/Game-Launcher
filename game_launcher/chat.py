class ChatServerEditorDialog(tk.Toplevel):
    def __init__(self, parent, launcher_instance, existing_server_data=None):
        super().__init__(parent)
        self.launcher = launcher_instance
        self.result = None # Przechowa dane serwera {'id':..., 'name':..., 'url':..., 'is_default':...}
        
        self.is_edit_mode = existing_server_data is not None
        # --- NOWE ZMIANY: Zapisz existing_server_data jako atrybut instancji ---
        self.existing_server_data_for_edit = existing_server_data # Zapisujemy, aby mieć dostęp w _save
        # --- KONIEC NOWYCH ZMIAN ---
        self.original_server_id = existing_server_data.get("id") if self.is_edit_mode else None
        self.original_server_name = existing_server_data.get("name") if self.is_edit_mode else None

        title = "Edytuj Serwer Czatu" if self.is_edit_mode else "Dodaj Nowy Serwer Czatu"
        self.title(title)
        self.configure(bg=self.launcher.settings.get("background", "#1e1e1e"))
        self.grab_set()
        self.resizable(False, False)
        self.transient(parent)

        # --- Zmienne Tkinter ---
        self.server_name_var = tk.StringVar(value=existing_server_data.get("name", "") if self.is_edit_mode else "Nowy Serwer")
        self.server_url_var = tk.StringVar(value=existing_server_data.get("url", "http://") if self.is_edit_mode else "http://127.0.0.1:5000")
        self.is_default_var = tk.BooleanVar(value=existing_server_data.get("is_default", False) if self.is_edit_mode else False)

        # --- Główna Ramka ---
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(expand=True, fill=tk.BOTH)
        main_frame.columnconfigure(1, weight=1)

        ttk.Label(main_frame, text="Nazwa Serwera:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        name_entry = ttk.Entry(main_frame, textvariable=self.server_name_var, width=40)
        name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(main_frame, text="Adres URL Serwera:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        url_entry = ttk.Entry(main_frame, textvariable=self.server_url_var, width=40)
        url_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        default_check = ttk.Checkbutton(main_frame, text="Ustaw jako domyślny serwer", variable=self.is_default_var)
        default_check.grid(row=2, column=0, columnspan=2, padx=5, pady=10, sticky="w")

        # Przyciski
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10, sticky="e")
        ttk.Button(button_frame, text="Zapisz", command=self._save_server_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Anuluj", command=self.destroy).pack(side=tk.LEFT)

        name_entry.focus_set()
        if not self.is_edit_mode: # Zaznacz tekst tylko przy dodawaniu
            name_entry.selection_range(0, tk.END)
        
        self.wait_window(self)

    def _save_server_data(self):
        name = self.server_name_var.get().strip()
        url = self.server_url_var.get().strip()
        is_default = self.is_default_var.get()

        if not name:
            messagebox.showerror("Brak Nazwy", "Nazwa serwera nie może być pusta.", parent=self)
            return
        if not url:
            messagebox.showerror("Brak URL", "Adres URL serwera nie może być pusty.", parent=self)
            return
        if not (url.startswith("http://") or url.startswith("https://")):
            messagebox.showerror("Nieprawidłowy URL", "Adres URL serwera musi zaczynać się od http:// lub https://", parent=self)
            return

        # Sprawdź unikalność nazwy (poza edytowanym serwerem)
        for server in self.launcher.chat_servers_list:
            if self.is_edit_mode and server.get("id") == self.original_server_id:
                continue # Pomiń sprawdzanie samego siebie przy edycji
            if server.get("name", "").lower() == name.lower():
                messagebox.showerror("Nazwa Zajęta", f"Serwer o nazwie '{name}' już istnieje.", parent=self)
                return
        
        # Jeśli ustawiono jako domyślny, odznacz inne domyślne
        if is_default:
            for server in self.launcher.chat_servers_list:
                # --- NOWE ZMIANY: Poprawka warunku dla edycji przy ustawianiu is_default ---
                # Jeśli edytujemy i to jest ten sam serwer, nie odznaczaj go.
                # Inaczej, jeśli inny serwer ma być domyślny, odznacz ten.
                if self.is_edit_mode and server.get("id") == self.original_server_id:
                    pass # Nie modyfikujemy is_default dla edytowanego serwera tutaj, zrobimy to w self.result
                elif server.get("id") != (self.original_server_id if self.is_edit_mode else None): # Dla nowego, odznacz wszystkie inne
                    server["is_default"] = False
                # --- KONIEC NOWYCH ZMIAN ---

        # --- NOWE ZMIANY: Użyj self.existing_server_data_for_edit ---
        # Przygotuj dane do zwrócenia
        current_credentials = {}
        current_remember = False
        current_auto_login = False
        last_used_timestamp = None # Domyślnie None dla nowych

        if self.is_edit_mode and self.existing_server_data_for_edit: # Użyj zapisanego atrybutu
            current_credentials = self.existing_server_data_for_edit.get("credentials", {})
            current_remember = self.existing_server_data_for_edit.get("remember_credentials", False)
            current_auto_login = self.existing_server_data_for_edit.get("auto_login_to_server", False)
            last_used_timestamp = self.existing_server_data_for_edit.get("last_used") # Zachowaj last_used przy edycji

        # Jeśli zmieniono URL, najlepiej wyczyścić zapamiętane dane (lub zapytać użytkownika)
        # Na razie, jeśli URL się zmienił, a to edycja, wyczyścimy dane logowania, bo mogą nie pasować.
        if self.is_edit_mode and self.existing_server_data_for_edit and \
           self.existing_server_data_for_edit.get("url") != url:
            current_credentials = {}
            current_remember = False
            current_auto_login = False
            logging.info(f"URL serwera '{name}' zmieniony. Wyczyszczono zapamiętane dane logowania dla tego serwera.")


        self.result = {
            "id": self.original_server_id if self.is_edit_mode else str(uuid.uuid4()),
            "name": name,
            "url": url,
            "is_default": is_default,
            "last_used": last_used_timestamp,
            "credentials": current_credentials,
            "remember_credentials": current_remember,
            "auto_login_to_server": current_auto_login
        }
        # --- KONIEC NOWYCH ZMIAN ---
        self.destroy()
from .shared_imports import tk, ttk, messagebox, logging, uuid


