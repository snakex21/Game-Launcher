"""Legacy component extracted from the monolithic launcher."""
from __future__ import annotations

from .base import *  # noqa: F401,F403
from .constants import *  # noqa: F401,F403
from .utils import *  # noqa: F401,F403

class AddProfileDialog(tk.Toplevel):
    """Małe okno dialogowe do dodawania/edycji profilu uruchomieniowego w oknie weryfikacji."""
    def __init__(self, parent, game_folder, existing_profiles, callback, initial_data=None):
        super().__init__(parent)
        self.parent = parent # Rodzicem jest ScanVerificationWindow
        self.game_folder = game_folder
        self.existing_profiles = existing_profiles # Lista profili już dodanych dla tej gry w oknie weryfikacji
        self.callback = callback # Funkcja do wywołania po zapisaniu
        self.result = None # Przechowa dane profilu

        is_edit = initial_data is not None
        title = "Edytuj Profil Uruchomieniowy" if is_edit else "Dodaj Profil Uruchomieniowy"
        self.title(title)
        self.configure(bg="#1e1e1e")
        self.grab_set()
        self.resizable(False, False)
        self.transient(parent) # Ustaw jako okno zależne od rodzica

        # Pola
        ttk.Label(self, text="Nazwa profilu:", background="#1e1e1e", foreground="white").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.name_var = tk.StringVar(value=initial_data['name'] if is_edit else f"Profil {len(existing_profiles) + 1}")
        self.name_entry = ttk.Entry(self, textvariable=self.name_var, width=40)
        self.name_entry.grid(row=0, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

        ttk.Label(self, text="Plik .exe:", background="#1e1e1e", foreground="white").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.exe_var = tk.StringVar(value=initial_data['exe_path'] if is_edit and initial_data.get('exe_path') else "")
        self.exe_entry = ttk.Entry(self, textvariable=self.exe_var, width=40, state='readonly') # Tylko do odczytu, zmieniane przez przycisk
        self.exe_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        exe_btn = ttk.Button(self, text="Wybierz...", command=self._select_exe)
        exe_btn.grid(row=1, column=2, padx=5, pady=5)

        ttk.Label(self, text="Argumenty:", background="#1e1e1e", foreground="white").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.args_var = tk.StringVar(value=initial_data['arguments'] if is_edit else "")
        self.args_entry = ttk.Entry(self, textvariable=self.args_var, width=40)
        self.args_entry.grid(row=2, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

        # Przyciski
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=15)
        save_button = ttk.Button(btn_frame, text="Zapisz", command=self._save)
        save_button.pack(side=tk.LEFT, padx=10)
        cancel_button = ttk.Button(btn_frame, text="Anuluj", command=self.destroy)
        cancel_button.pack(side=tk.LEFT, padx=10)

        self.name_entry.focus_set()
        self.wait_window(self) # Czekaj na zamknięcie tego okna

    def _select_exe(self):
        """Otwiera dialog wyboru pliku .exe w folderze gry."""
        path = filedialog.askopenfilename(
            title="Wybierz plik wykonywalny dla profilu",
            filetypes=[("Pliki wykonywalne", "*.exe"), ("Wszystkie pliki", "*.*")],
            initialdir=self.game_folder, # Zaczynaj w folderze gry
            parent=self # Rodzicem jest to okno dialogowe
        )
        if path:
            # Sprawdź, czy wybrany plik jest w folderze gry lub jego podfolderze
            if os.path.commonpath([self.game_folder, path]) == self.game_folder:
                 self.exe_var.set(path)
            else:
                 messagebox.showerror("Błąd ścieżki", "Plik wykonywalny musi znajdować się w folderze gry lub jego podfolderze.", parent=self)


    def _save(self):
        """Waliduje i zapisuje dane profilu."""
        name = self.name_var.get().strip()
        exe_path = self.exe_var.get().strip() or None # Zapisz None, jeśli puste (oznacza użycie głównego exe)
        arguments = self.args_var.get().strip()

        if not name:
            messagebox.showerror("Błąd", "Nazwa profilu jest wymagana.", parent=self)
            return
        if not exe_path:
            messagebox.showerror("Błąd", "Ścieżka pliku .exe jest wymagana dla dodatkowego profilu.", parent=self)
            return

        # Sprawdź unikalność nazwy wśród istniejących (w tej sesji weryfikacji)
        # Pomijamy sprawdzanie, jeśli edytujemy (bo initial_data będzie miało starą nazwę)
        # Trzeba by przekazać indeks edytowanego profilu, aby to zaimplementować poprawnie.
        # Na razie uproszczenie - zakładamy, że użytkownik nie stworzy duplikatu ręcznie.
        # is_edit = initial_data is not None ...

        self.result = {"name": name, "exe_path": exe_path, "arguments": arguments}
        self.callback(self.result) # Wywołaj callback z wynikiem
        self.destroy()
