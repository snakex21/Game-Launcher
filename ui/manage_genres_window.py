import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import logging
from utils import config_manager  # Potrzebne do zapisu konfiguracji


class ManageGenresWindow:
    """Okno do zarządzania niestandardowymi gatunkami gier."""

    def __init__(self, parent_root, launcher_instance):
        self.top = tk.Toplevel(parent_root)
        self.top.title("Zarządzaj Gatunkami Niestandardowymi")
        # Prosta konfiguracja stylu (można rozbudować o przekazywanie motywu)
        self.top.configure(bg="#1e1e1e")
        style = ttk.Style(self.top)
        style.configure("TLabel", background="#1e1e1e", foreground="white")
        style.configure("TButton", background="#2e2e2e", foreground="white", padding=6)
        style.configure("TFrame", background="#1e1e1e")
        # Można dodać konfigurację Listbox i Scrollbar, jeśli domyślna nie pasuje

        self.top.grab_set()  # Blokuje interakcję z głównym oknem
        self.top.minsize(300, 300)

        self.launcher = launcher_instance  # Referencja do głównej aplikacji

        ttk.Label(
            self.top, text="Gatunki Niestandardowe:", font=("Helvetica", 12)
        ).pack(pady=10)

        # Ramka dla Listboxa i Scrollbara
        listbox_frame = ttk.Frame(self.top)
        listbox_frame.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        listbox_frame.rowconfigure(0, weight=1)
        listbox_frame.columnconfigure(0, weight=1)

        self.custom_genres_listbox = tk.Listbox(
            listbox_frame,
            bg="#2e2e2e",
            fg="white",
            selectbackground="#555",
            selectforeground="white",
            borderwidth=0,
            highlightthickness=0,
        )
        self.custom_genres_listbox.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            listbox_frame, orient="vertical", command=self.custom_genres_listbox.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.custom_genres_listbox.config(yscrollcommand=scrollbar.set)

        self.load_custom_genres()

        # Ramka dla przycisków
        button_frame = ttk.Frame(self.top)
        button_frame.pack(pady=10)

        add_btn = ttk.Button(
            button_frame, text="Dodaj Gatunek", command=self.add_custom_genre
        )
        add_btn.pack(side=tk.LEFT, padx=5)
        remove_btn = ttk.Button(
            button_frame, text="Usuń Zaznaczony", command=self.remove_custom_genre
        )
        remove_btn.pack(side=tk.LEFT, padx=5)
        close_btn = ttk.Button(button_frame, text="Zamknij", command=self.close_window)
        close_btn.pack(side=tk.LEFT, padx=5)

        # Wyśrodkowanie okna
        self.top.update_idletasks()
        parent_x = parent_root.winfo_rootx()
        parent_y = parent_root.winfo_rooty()
        parent_width = parent_root.winfo_width()
        parent_height = parent_root.winfo_height()
        win_width = self.top.winfo_width()
        win_height = self.top.winfo_height()
        x = parent_x + (parent_width - win_width) // 2
        y = parent_y + (parent_height - win_height) // 2
        self.top.geometry(f"+{x}+{y}")

    def load_custom_genres(self):
        """Ładuje niestandardowe gatunki do listboxa."""
        self.custom_genres_listbox.delete(0, tk.END)
        # Używamy self.launcher.settings, bo mamy referencję
        custom_genres = self.launcher.settings.get("custom_genres", [])
        for genre in sorted(custom_genres):  # Sortujemy dla porządku
            self.custom_genres_listbox.insert(tk.END, genre)

    def add_custom_genre(self):
        """Dodaje nowy niestandardowy gatunek."""
        new_genre = simpledialog.askstring(
            "Nowy Gatunek",
            "Podaj nazwę nowego gatunku niestandardowego:",
            parent=self.top,
        )
        if new_genre:
            new_genre = new_genre.strip()
            custom_genres = self.launcher.settings.setdefault("custom_genres", [])
            if new_genre and new_genre not in custom_genres:
                # Sprawdźmy też w gatunkach gier, żeby nie dublować
                all_game_genres = set()
                for game in self.launcher.games.values():
                    all_game_genres.update(game.get("genres", []))
                if new_genre in all_game_genres:
                    messagebox.showwarning(
                        "Uwaga",
                        f"Gatunek '{new_genre}' już istnieje jako gatunek przypisany do gry.",
                        parent=self.top,
                    )
                    # Mimo wszystko dodajemy go do custom, aby można było go wybrać
                    # jeśli nie ma gier z tym gatunkiem.
                custom_genres.append(new_genre)
                config_manager.save_config(
                    self.launcher.config
                )  # Używamy funkcji z modułu
                self.load_custom_genres()  # Odśwież listę w tym oknie
                self.launcher.update_genre_menu()  # Odśwież menu w głównym oknie
                logging.info(f"Dodano niestandardowy gatunek: {new_genre}")
            elif not new_genre:
                messagebox.showwarning(
                    "Błąd", "Nazwa gatunku nie może być pusta.", parent=self.top
                )
            else:
                messagebox.showwarning(
                    "Błąd",
                    f"Gatunek '{new_genre}' już istnieje na liście niestandardowej.",
                    parent=self.top,
                )

    def remove_custom_genre(self):
        """Usuwa zaznaczony niestandardowy gatunek."""
        selected_indices = self.custom_genres_listbox.curselection()
        if selected_indices:
            index = selected_indices[0]
            genre_to_remove = self.custom_genres_listbox.get(index)
            if messagebox.askyesno(
                "Potwierdzenie",
                f"Czy na pewno chcesz usunąć gatunek '{genre_to_remove}' z listy niestandardowej?",
                parent=self.top,
            ):
                custom_genres = self.launcher.settings.get("custom_genres", [])
                if genre_to_remove in custom_genres:
                    custom_genres.remove(genre_to_remove)
                    config_manager.save_config(
                        self.launcher.config
                    )  # Używamy funkcji z modułu
                    self.load_custom_genres()  # Odśwież listę w tym oknie
                    self.launcher.update_genre_menu()  # Odśwież menu w głównym oknie
                    logging.info(f"Usunięto niestandardowy gatunek: {genre_to_remove}")
                else:
                    # To nie powinno się zdarzyć, jeśli listbox pokazuje tylko custom_genres
                    messagebox.showerror(
                        "Błąd",
                        "Wybrany gatunek nie znajduje się na liście niestandardowej.",
                        parent=self.top,
                    )
        else:
            messagebox.showwarning(
                "Błąd", "Nie wybrano gatunku do usunięcia.", parent=self.top
            )

    def close_window(self):
        """Zamyka okno."""
        # Odświeżanie listy w GameForm jest teraz problematyczne bez bezpośredniej referencji.
        # Lepszym podejściem byłoby, gdyby GameForm samo nasłuchiwało na zamknięcie tego okna
        # lub odświeżało listę przy aktywacji. Na razie pomijamy ten krok.
        # Można by ewentualnie przekazać callback do GameForm, jeśli istnieje.
        self.top.destroy()
