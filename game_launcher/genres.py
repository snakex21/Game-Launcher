from __future__ import annotations

from .shared_imports import *


class ManageGenresWindow:
    def __init__(self, parent_root, launcher_instance):
        self.top = tk.Toplevel(parent_root)
        self.top.title("Zarządzaj Gatunkami Niestandardowymi")
        self.top.configure(bg="#1e1e1e")
        self.top.grab_set()
        self.top.minsize(300, 300)

        self.launcher = launcher_instance # Referencja do głównej aplikacji

        ttk.Label(self.top, text="Gatunki Niestandardowe:", font=("Helvetica", 12)).pack(pady=10)

        # Ramka dla Listboxa i Scrollbara
        listbox_frame = ttk.Frame(self.top)
        listbox_frame.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        listbox_frame.rowconfigure(0, weight=1)
        listbox_frame.columnconfigure(0, weight=1)

        self.custom_genres_listbox = tk.Listbox(listbox_frame)
        self.custom_genres_listbox.grid(row=0, column=0, sticky='nsew')

        scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.custom_genres_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.custom_genres_listbox.config(yscrollcommand=scrollbar.set)

        self.load_custom_genres()

        # Ramka dla przycisków
        button_frame = ttk.Frame(self.top)
        button_frame.pack(pady=10)

        add_btn = ttk.Button(button_frame, text="Dodaj Gatunek", command=self.add_custom_genre)
        add_btn.pack(side=tk.LEFT, padx=5)
        remove_btn = ttk.Button(button_frame, text="Usuń Zaznaczony", command=self.remove_custom_genre)
        remove_btn.pack(side=tk.LEFT, padx=5)
        close_btn = ttk.Button(button_frame, text="Zamknij", command=self.close_window)
        close_btn.pack(side=tk.LEFT, padx=5)

    def load_custom_genres(self):
        """Ładuje niestandardowe gatunki do listboxa."""
        self.custom_genres_listbox.delete(0, tk.END)
        custom_genres = self.launcher.settings.get("custom_genres", [])
        for genre in sorted(custom_genres): # Sortujemy dla porządku
            self.custom_genres_listbox.insert(tk.END, genre)

    def add_custom_genre(self):
        """Dodaje nowy niestandardowy gatunek."""
        new_genre = simpledialog.askstring("Nowy Gatunek", "Podaj nazwę nowego gatunku niestandardowego:")
        if new_genre:
            new_genre = new_genre.strip()
            custom_genres = self.launcher.settings.setdefault("custom_genres", [])
            if new_genre and new_genre not in custom_genres:
                # Sprawdźmy też w gatunkach gier, żeby nie dublować
                all_game_genres = set()
                for game in self.launcher.games.values():
                     all_game_genres.update(game.get("genres", []))
                if new_genre in all_game_genres:
                     messagebox.showwarning("Uwaga", f"Gatunek '{new_genre}' już istnieje jako gatunek przypisany do gry.")
                     # Mimo wszystko dodajemy go do custom, aby można było go wybrać
                     # jeśli nie ma gier z tym gatunkiem.
                custom_genres.append(new_genre)
                save_config(self.launcher.config)
                self.load_custom_genres() # Odśwież listę w tym oknie
                self.launcher.update_genre_menu() # Odśwież menu w głównym oknie
                logging.info(f"Dodano niestandardowy gatunek: {new_genre}")
            elif not new_genre:
                 messagebox.showwarning("Błąd", "Nazwa gatunku nie może być pusta.")
            else:
                 messagebox.showwarning("Błąd", f"Gatunek '{new_genre}' już istnieje na liście niestandardowej.")


    def remove_custom_genre(self):
        """Usuwa zaznaczony niestandardowy gatunek."""
        selected_indices = self.custom_genres_listbox.curselection()
        if selected_indices:
            index = selected_indices[0]
            genre_to_remove = self.custom_genres_listbox.get(index)
            custom_genres = self.launcher.settings.get("custom_genres", [])
            if genre_to_remove in custom_genres:
                custom_genres.remove(genre_to_remove)
                save_config(self.launcher.config)
                self.load_custom_genres() # Odśwież listę w tym oknie
                self.launcher.update_genre_menu() # Odśwież menu w głównym oknie
                logging.info(f"Usunięto niestandardowy gatunek: {genre_to_remove}")
            else:
                # To nie powinno się zdarzyć, jeśli listbox pokazuje tylko custom_genres
                messagebox.showerror("Błąd", "Wybrany gatunek nie znajduje się na liście niestandardowej.")
        else:
            messagebox.showwarning("Błąd", "Nie wybrano gatunku do usunięcia.")

    def close_window(self):
        """Zamyka okno i odświeża listę gatunków w formularzu, jeśli jest otwarty."""
        # Sprawdź, czy okno GameForm istnieje
        for widget in self.launcher.root.winfo_children():
             if isinstance(widget, tk.Toplevel):
                 # Proste sprawdzenie po tytule (można ulepszyć)
                 if "Dodaj Grę" in widget.title() or "Edytuj Grę" in widget.title():
                     # Znajdź instancję GameForm (trochę naokoło, ale powinno działać)
                     # Zakładamy, że GameForm ma atrybut 'genres_listbox'
                     game_form_instance = None
                     # Szukamy po referencji (jeśli GameLauncher ją trzyma) lub po widgetach
                     # To jest trudniejsze bez bezpośredniej referencji.
                     # Bezpieczniej będzie, jeśli GameForm samo odświeży listę przy zamknięciu ManageGenresWindow
                     # Ale na razie spróbujmy tak:
                     try:
                         # Załóżmy, że GameForm jest ostatnim otwartym Toplevel
                         # To nie jest niezawodne!
                         potential_game_form = widget
                         if hasattr(potential_game_form, 'genres_listbox'):
                             # Odśwież listę gatunków w GameForm
                             potential_game_form.all_genres = self.launcher.get_all_genres()
                             potential_game_form.genres_listbox.delete(0, tk.END)
                             selected_genres = potential_game_form.genres # Zapamiętaj zaznaczone
                             for genre in potential_game_form.all_genres:
                                 potential_game_form.genres_listbox.insert(tk.END, genre)
                             # Przywróć zaznaczenie (jeśli gatunek nadal istnieje)
                             for i, genre in enumerate(potential_game_form.all_genres):
                                 if genre in selected_genres:
                                     potential_game_form.genres_listbox.selection_set(i)
                             logging.info("Odświeżono listę gatunków w otwartym formularzu gry.")
                     except Exception as e:
                         logging.error(f"Nie udało się odświeżyć listy gatunków w GameForm: {e}")
                     break
        self.top.destroy()
from .shared_imports import tk, ttk, simpledialog, messagebox, logging
from .utils import save_config


