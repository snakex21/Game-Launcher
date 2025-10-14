"""Legacy component extracted from the monolithic launcher."""
from __future__ import annotations

from .base import *  # noqa: F401,F403
from .constants import *  # noqa: F401,F403
from .utils import *  # noqa: F401,F403

class ThemeEditorWindow(tk.Toplevel):
    """Okno dialogowe do dodawania/edycji niestandardowego motywu."""
# W klasie ThemeEditorWindow

    def __init__(self, parent, launcher_instance, theme_name=None, theme_data=None):
        super().__init__(parent)
        self.launcher = launcher_instance
        self.result = None
        self.original_name = theme_name

        # --- NOWE: Zapisz oryginalne ustawienia TScrollbar ---
        self.original_scrollbar_settings = {}
        try:
            active_theme_name_main = self.launcher.settings.get('theme', 'Dark')
            all_themes_main = self.launcher.get_all_available_themes()
            active_theme_def_main = all_themes_main.get(active_theme_name_main, THEMES.get('Dark', {}))

            # Klucze, które chcemy zapisać i przywrócić dla TScrollbar
            scrollbar_keys_to_save = ['background', 'troughcolor', 'bordercolor', 'arrowcolor']
            # UWAGA: 'background' w ttk.Scrollbar to kolor suwaka, 'troughcolor' to tło
            # Musimy mapować klucze z naszego motywu na opcje stylu TScrollbar
            # 'scrollbar_slider' -> 'background' w stylu
            # 'scrollbar_trough' -> 'troughcolor' w stylu
            # 'background' (ogólne tło) -> 'bordercolor' w stylu
            # 'foreground' (ogólny tekst) -> 'arrowcolor' w stylu

            self.original_scrollbar_settings['background'] = active_theme_def_main.get('scrollbar_slider', '#555555')
            self.original_scrollbar_settings['troughcolor'] = active_theme_def_main.get('scrollbar_trough', '#1e1e1e')
            self.original_scrollbar_settings['bordercolor'] = active_theme_def_main.get('background', '#1e1e1e')
            self.original_scrollbar_settings['arrowcolor'] = active_theme_def_main.get('foreground', 'white')
            logging.debug(f"Zapisano oryginalne ustawienia TScrollbar: {self.original_scrollbar_settings}")
        except Exception as e:
            logging.error(f"Błąd przy zapisywaniu oryginalnych ustawień TScrollbar: {e}")
        # --- KONIEC NOWEGO ---

        is_edit = theme_name is not None and theme_data is not None
        title = f"Edytuj Motyw: {theme_name}" if is_edit else "Dodaj Nowy Motyw"
        self.title(title)
        self.configure(bg="#1e1e1e")
        # --- ZMIANA: Zwiększ wysokość okna ---
        # Poprzednio było 550x780, spróbujmy np. 550x820 lub nawet więcej
        # Dostosuj tę wartość, aby pasowała do Twojego ekranu i liczby pól kolorów
        self.geometry("550x840") # Przykładowa nowa wysokość
        self.minsize(500, 750)  # Odpowiednio zwiększ minimalną wysokość
        # --- KONIEC ZMIANY ---
        self.grab_set()
        self.transient(parent)

        # --- Słownik tłumaczeń dla kluczy kolorów ---
        self.COLOR_KEY_TRANSLATIONS = {
            'background': 'Tło Główne',
            'foreground': 'Tekst Główny',
            'button_background': 'Tło Przycisku',
            'button_foreground': 'Tekst Przycisku',
            'entry_background': 'Tło Pola Tekst.',
            'tree_background': 'Tło Listy/Drzewa',
            'tree_heading': 'Nagłówek Listy',
            'scrollbar_trough': 'Tło Paska Przew.',
            'scrollbar_slider': 'Suwak Paska Przew.',
            'link_foreground': 'Kolor Linku',
            # --- NOWE TŁUMACZENIA ---
            'chart_bar_color': 'Kolor Słupków Wykresu',
            'chart_axis_color': 'Kolor Osi Wykresu',
            # --- KONIEC NOWYCH ---
        }
        # --- Koniec słownika tłumaczeń ---

        # Pobierz kolor tła Entry z aktywnego motywu
        active_theme_name = self.launcher.settings.get('theme', 'Dark')
        all_themes = self.launcher.get_all_available_themes()
        active_theme_def = all_themes.get(active_theme_name, THEMES.get('Dark', {}))
        active_entry_bg_color = active_theme_def.get('entry_background', '#2e2e2e')
        hardcoded_fg_color = '#ffffff'

        # Styl dla Entry
        self.hex_entry_style_name = f"HexInput{id(self)}.TEntry"
        style = ttk.Style()
        style.configure(
            self.hex_entry_style_name,
            fieldbackground=active_entry_bg_color,
            foreground=hardcoded_fg_color,
            insertcolor=hardcoded_fg_color
        )

        # --- Główny kontener ---
        content_container = ttk.Frame(self, style="TFrame")
        content_container.pack(fill="both", expand=True, padx=5, pady=5)
        content_container.rowconfigure(1, weight=0)
        content_container.rowconfigure(2, weight=1)
        content_container.columnconfigure(0, weight=1)

        # --- Pole Nazwy Motywu ---
        name_frame = ttk.Frame(content_container, style="TFrame")
        name_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        name_frame.columnconfigure(1, weight=1)
        ttk.Label(name_frame, text="Nazwa Motywu:").grid(row=0, column=0, padx=5)
        self.name_var = tk.StringVar(value=theme_name if is_edit else "Mój Motyw")
        self.name_entry = ttk.Entry(name_frame, textvariable=self.name_var)
        self.name_entry.grid(row=0, column=1, sticky="ew")

        # --- Ramka na pola kolorów ---
        scrollable_frame = ttk.Frame(content_container, style="TFrame")
        scrollable_frame.grid(row=1, column=0, sticky="nsew")

        # --- Pola Edycji Kolorów ---
        self.color_vars = {}
        template_theme = THEMES.get('Dark', {})
        current_theme_data = theme_data if is_edit else template_theme
        colors_frame = ttk.LabelFrame(scrollable_frame, text=" Kolory (format HEX: #RRGGBB) ", padding=10)
        colors_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        colors_frame.columnconfigure(1, weight=1)
        colors_frame.columnconfigure(2, weight=0)

        row_idx = 0
        for key in template_theme.keys():
            # --- ZMIANA: Użyj polskiej nazwy dla etykiety ---
            display_name = self.COLOR_KEY_TRANSLATIONS.get(key, key) # Pobierz tłumaczenie lub użyj klucza
            ttk.Label(colors_frame, text=f"{display_name}:").grid(row=row_idx, column=0, padx=5, pady=3, sticky="w")
            # --- KONIEC ZMIANY ---

            default_color = template_theme.get(key, "#ffffff")
            initial_value_raw = current_theme_data.get(key, default_color)
            initial_value = "#ffffff" if initial_value_raw == "white" else initial_value_raw

            color_var = tk.StringVar(value=initial_value)
            color_entry = ttk.Entry(colors_frame, textvariable=color_var, width=10, style=self.hex_entry_style_name)
            color_entry.grid(row=row_idx, column=1, padx=5, pady=3, sticky="ew")

            color_button = tk.Button(
                colors_frame, text=" ", bg=initial_value, width=3, relief="solid",
                borderwidth=1,
                # --- ZMIANA: Przekaż polską nazwę do _choose_color ---
                command=lambda k=key, var=color_var, dn=display_name: self._choose_color(k, var, dn)
                # --- KONIEC ZMIANY ---
            )
            color_button.grid(row=row_idx, column=2, padx=5, pady=3)

            color_var.trace_add("write", lambda name, index, mode, var=color_var, button=color_button: self._update_color_preview(var, button))
            # --- ZMIANA: Zapisz też polską nazwę ---
            self.color_vars[key] = {"var": color_var, "entry": color_entry, "button": color_button, "display_name": display_name}
            # --- KONIEC ZMIANY ---
            row_idx += 1
        
        # --- NOWY PRZYCISK: Losuj Kolory (obok etykiety LabelFrame) ---
        randomize_btn = ttk.Button(colors_frame, text="Losuj Wszystkie", command=self._randomize_colors)
        # Umieśćmy go np. w prawym górnym rogu LabelFrame lub pod listą kolorów
        # Dla prostoty na razie pod listą:
        randomize_btn.grid(row=row_idx, column=0, columnspan=3, pady=10, sticky="ew") # Rozciągnij na wszystkie kolumny
        # --- KONIEC NOWEGO PRZYCISKU ---

        # --- Ramka podglądu ---
        self.preview_frame = ttk.LabelFrame(content_container, text=" Podgląd na Żywo ", padding=10)
        self.preview_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(5, 10))
        self.preview_frame.columnconfigure(0, weight=1)
        # --- NOWE: Kolumna dla scrollbara ---
        self.preview_frame.columnconfigure(2, weight=0) # Dodano kolumnę 2
        # --- KONIEC NOWEGO ---

        # Widgety podglądu
        self.preview_style_prefix = f"Preview{id(self)}."
        # ... (kod tworzenia preview_label, preview_button, preview_entry, preview_link) ...
        self.preview_label = ttk.Label(self.preview_frame, text="Przykładowa etykieta", style=self.preview_style_prefix + "TLabel")
        self.preview_label.grid(row=0, column=0, pady=3, sticky="w")
        self.preview_button = ttk.Button(self.preview_frame, text="Przycisk", style=self.preview_style_prefix + "TButton")
        self.preview_button.grid(row=1, column=0, pady=3, sticky="w")
        self.preview_entry = ttk.Entry(self.preview_frame, style=self.preview_style_prefix + "TEntry")
        self.preview_entry.insert(0, "Pole tekstowe")
        self.preview_entry.grid(row=2, column=0, pady=3, sticky="ew")
        self.preview_link = ttk.Button(self.preview_frame, text="Link", style=self.preview_style_prefix + "Link.TButton")
        self.preview_link.grid(row=0, column=1, pady=3, padx=10, sticky="w")


        # Podgląd Treeview
        preview_tree_frame = ttk.Frame(self.preview_frame)
        # --- ZMIANA: Umieść w kolumnie 0, columnspan=2 ---
        preview_tree_frame.grid(row=3, column=0, columnspan=2, pady=5, sticky="ew")
        # --- KONIEC ZMIANY ---
        preview_tree_frame.columnconfigure(0, weight=1)
        self.preview_tree = ttk.Treeview(preview_tree_frame, columns=("col1",), height=2, style=self.preview_style_prefix + "Treeview")
        self.preview_tree.heading("col1", text="Nagłówek")
        self.preview_tree.column("col1", width=100)
        self.preview_tree.insert("", "end", text="Item 1", values=("Wartość 1",))
        self.preview_tree.insert("", "end", text="Item 2", values=("Wartość 2",))
        self.preview_tree.grid(row=0, column=0, sticky="ew")

        # --- NOWE: Dodanie podglądu Scrollbar ---
        # Usuwamy opcję style=...
        self.preview_scrollbar = ttk.Scrollbar(self.preview_frame, orient="vertical")
        self.preview_scrollbar.grid(row=3, column=2, pady=5, padx=(2,0), sticky="ns")
        # --- KONIEC ZMIANY ---

        # --- Przyciski na Dole Okna ---
        button_frame = ttk.Frame(self, style="TFrame")
        button_frame.pack(fill="x", pady=10, side="bottom")
        button_frame.columnconfigure((0, 1), weight=1)
        save_btn = ttk.Button(button_frame, text="Zapisz Motyw", command=self._save)
        save_btn.grid(row=0, column=0, padx=10, sticky="e")
        cancel_btn = ttk.Button(button_frame, text="Anuluj", command=self._on_close_editor)
        cancel_btn.grid(row=0, column=1, padx=10, sticky="w")

        # --- NOWE: Bindowanie do własnej metody zamykania ---
        self.protocol("WM_DELETE_WINDOW", self._on_close_editor)
        # --- KONIEC NOWEGO ---

        # --- Finalizacja ---
        self.name_entry.focus_set()
        self._apply_preview_styles()
        self.wait_window(self)

    # --- NOWA METODA: Aplikuje style do widgetów podglądu ---
    def _apply_preview_styles(self):
        """Odczytuje kolory z pól i aktualizuje style widgetów podglądu."""
        preview_style = ttk.Style()
        theme = {}
        valid_theme = True
        for key, data in self.color_vars.items():
            color_code = data["var"].get().strip()
            if self._is_valid_hex_color(color_code):
                theme[key] = color_code
            else:
                theme[key] = THEMES['Dark'].get(key, "#ffffff")
                valid_theme = False
                # Nie oznaczamy już błędu w Entry tutaj, bo _update_color_preview tego nie robi

        if not valid_theme:
            logging.warning("Wykryto nieprawidłowe kody HEX w edytorze motywów. Podgląd używa częściowo domyślnych wartości.")

        prefix = self.preview_style_prefix

        try:
            # ... (style Label, Button, Entry, Link bez zmian) ...
            preview_style.configure(prefix + "TLabel", background=theme.get('background', '#1e1e1e'), foreground=theme.get('foreground', 'white'))
            self.preview_label.configure(style=prefix + "TLabel")
            preview_style.configure(prefix + "TButton", background=theme.get('button_background', '#2e2e2e'), foreground=theme.get('button_foreground', 'white'))
            self.preview_button.configure(style=prefix + "TButton")
            preview_style.configure(prefix + "TEntry", fieldbackground=theme.get('entry_background', '#2e2e2e'), foreground=theme.get('foreground', 'white'), insertbackground=theme.get('foreground', 'white'))
            self.preview_entry.configure(style=prefix + "TEntry")
            preview_style.configure(prefix + "Link.TButton", foreground=theme.get('link_foreground', '#66b3ff'), background=theme.get('background', '#1e1e1e'), padding=0, relief="flat", borderwidth=0)
            preview_style.map(prefix + "Link.TButton", underline=[('active', 1)])
            self.preview_link.configure(style=prefix + "Link.TButton")

            # Styl Treeview (bez zmian)
            preview_style.configure(prefix + "Treeview", background=theme.get('tree_background', '#2e2e2e'), foreground=theme.get('foreground', 'white'), fieldbackground=theme.get('tree_background', '#2e2e2e'))
            preview_style.map(prefix + "Treeview", background=[('selected', '#0078d7')])
            preview_style.configure(prefix + "Treeview.Heading", background=theme.get('tree_heading', '#3e3e3e'), foreground=theme.get('foreground', 'white'))
            self.preview_tree.configure(style=prefix + "Treeview")

            # --- ZMIANA: Konfiguruj globalny styl TScrollbar dla tego okna ---
            preview_style.configure(
                "TScrollbar", # Zamiast prefix + "TScrollbar"
                background=theme.get('scrollbar_slider', '#555555'),
                troughcolor=theme.get('scrollbar_trough', '#1e1e1e'),
                bordercolor=theme.get('background', '#1e1e1e'),
                arrowcolor=theme.get('foreground', 'white')
            )
            # Usunięto: self.preview_scrollbar.configure(style=...)
            # Styl zostanie zastosowany automatycznie do wszystkich TScrollbar w tym oknie
            # --- KONIEC ZMIANY ---

            self.preview_frame.config(style="TFrame")

        except tk.TclError as e:
            logging.error(f"Błąd TclError podczas stosowania stylów podglądu: {e}")
        except Exception as e:
             logging.exception("Nieoczekiwany błąd podczas stosowania stylów podglądu.")

    # --- KONIEC NOWEJ METODY ---

    # --- ZMIANA: Aktualizuje tło przycisku ---
    # Zmień sygnaturę, aby przyjmowała domyślny kolor tekstu (fg)
# W klasie ThemeEditorWindow
    # --- NOWA METODA ---
    def _randomize_colors(self):
        """Generuje losowe kolory HEX dla wszystkich pól motywu."""
        logging.info("Losowanie kolorów motywu...")
        for key, data in self.color_vars.items():
            # Generuj 6 losowych cyfr szesnastkowych
            random_hex = ''.join([random.choice('0123456789abcdef') for _ in range(6)])
            random_color_code = f"#{random_hex}"

            # Ustaw nową wartość w StringVar (to wywoła _update_color_preview i _apply_preview_styles)
            data["var"].set(random_color_code)
        messagebox.showinfo("Losowanie Zakończone", "Kolory zostały wylosowane! Sprawdź podgląd.", parent=self)
    # --- KONIEC NOWEJ METODY ---
# W klasie ThemeEditorWindow

    # Zaktualizowana metoda - usuwa parametr color_entry i logikę z nim związaną
    def _update_color_preview(self, color_var, color_button):
        """Aktualizuje kolor tła przycisku podglądu i odświeża cały podgląd."""
        color_code = color_var.get()
        is_valid = self._is_valid_hex_color(color_code)

        try:
            # Ustaw tło przycisku (nawet jeśli kod jest zły, użyje koloru zastępczego)
            color_button.config(bg=color_code if is_valid else "SystemButtonFace")
            # Usunięto logikę zmiany koloru tekstu Entry
        except tk.TclError:
            color_button.config(bg="SystemButtonFace")
            # Usunięto logikę zmiany koloru tekstu Entry

        # Odśwież cały podgląd, aby zobaczyć efekt w innych widgetach
        self._apply_preview_styles()

    def _is_valid_hex_color(self, color_code):
        """Sprawdza prostym regexem, czy string to poprawny kod HEX."""
        return re.match(r'^#[0-9a-fA-F]{6}$', color_code)

    # --- NOWA METODA: Otwiera selektor kolorów ---
    # Dodano argument display_name
    def _choose_color(self, key, color_var, display_name):
        """Otwiera systemowy selektor kolorów i aktualizuje zmienną oraz przycisk."""
        current_color = color_var.get()
        # --- ZMIANA: Użyj display_name w tytule ---
        color_info = colorchooser.askcolor(initialcolor=current_color, title=f"Wybierz kolor dla: {display_name}", parent=self)
        # --- KONIEC ZMIANY ---

        chosen_color_hex = color_info[1]

        if chosen_color_hex:
            logging.debug(f"Wybrano kolor dla '{key}': {chosen_color_hex}")
            color_var.set(chosen_color_hex)
        else:
            logging.debug(f"Anulowano wybór koloru dla '{key}'.")

    def _save(self):
        """Waliduje dane i zapisuje wynik."""
        new_name = self.name_var.get().strip()
        if not new_name:
            messagebox.showerror("Błąd", "Nazwa motywu nie może być pusta.", parent=self)
            return

        # Sprawdź, czy nazwa nie koliduje (poza sobą, jeśli edytujemy)
        # --- ZMIANA: Użyj globalnego THEMES ---
        all_builtin_themes = list(THEMES.keys())
        # --- KONIEC ZMIANY ---
        all_custom_themes = list(self.launcher.config.get("settings", {}).get("custom_themes", {}).keys())

        if new_name in all_builtin_themes:
            messagebox.showerror("Błąd Nazwy", f"Nazwa '{new_name}' jest zarezerwowana dla motywu wbudowanego.", parent=self)
            return
        if new_name != self.original_name and new_name in all_custom_themes:
            messagebox.showerror("Błąd Nazwy", f"Motyw niestandardowy o nazwie '{new_name}' już istnieje.", parent=self)
            return

        # Zbierz i zwaliduj kolory
        theme_def = {}
        has_error = False
        for key, data in self.color_vars.items():
            color_code = data["var"].get().strip()
            if self._is_valid_hex_color(color_code):
                theme_def[key] = color_code
                data["entry"].config(foreground="SystemWindowText") # Resetuj kolor tekstu
            else:
                messagebox.showerror("Błąd Koloru", f"Nieprawidłowy format kodu HEX dla '{key}': {color_code}\nOczekiwano formatu #RRGGBB.", parent=self)
                data["entry"].config(foreground="red") # Oznacz błędne pole
                has_error = True
                # Nie przerywamy, żeby oznaczyć wszystkie błędy
                # return

        if has_error:
            return # Przerwij, jeśli były błędy w kolorach

        # Zwróć wynik
        self.result = {"name": new_name, "theme_def": theme_def}

        # --- NOWE: Po zapisie, zastosuj styl aktywnego motywu launchera ---
        # To jest ważne, jeśli edytowany motyw nie stał się od razu aktywny
        # lub jeśli anulujemy zmiany w motywie, który był aktywny.
        try:
            active_theme_name_launcher = self.launcher.settings.get('theme', 'Dark')
            all_themes_launcher = self.launcher.get_all_available_themes()
            active_theme_def_launcher = all_themes_launcher.get(active_theme_name_launcher, THEMES.get('Dark', {}))

            # Klucze dla TScrollbar
            bg_slider = active_theme_def_launcher.get('scrollbar_slider', '#555555')
            bg_trough = active_theme_def_launcher.get('scrollbar_trough', '#1e1e1e')
            bg_border = active_theme_def_launcher.get('background', '#1e1e1e')
            fg_arrow = active_theme_def_launcher.get('foreground', 'white')

            main_style = ttk.Style()
            main_style.configure(
                "TScrollbar",
                background=bg_slider,
                troughcolor=bg_trough,
                bordercolor=bg_border,
                arrowcolor=fg_arrow
            )
            logging.info("Zastosowano styl TScrollbar aktywnego motywu launchera po zapisie.")
            self.launcher.root.update_idletasks()
        except Exception as e:
            logging.error(f"Błąd przy stosowaniu stylu TScrollbar aktywnego motywu po zapisie: {e}")
        # --- KONIEC NOWEGO ---

        self.destroy()
    # --- NOWA METODA ---
    def _on_close_editor(self):
        """Przywraca oryginalny styl TScrollbar przed zamknięciem edytora."""
        logging.debug("Zamykanie ThemeEditorWindow, przywracanie oryginalnego TScrollbar...")
        try:
            # Zastosuj zapisane oryginalne ustawienia do globalnego stylu TScrollbar
            # używanego przez główną aplikację.
            # Musimy odwołać się do instancji stylu launchera,
            # ale `ttk.Style()` powinno dać nam tę samą instancję.
            main_style = ttk.Style() # Powinno dać referencję do globalnego stylu
            if self.original_scrollbar_settings:
                main_style.configure(
                    "TScrollbar", # Konfigurujemy globalny styl TScrollbar
                    background=self.original_scrollbar_settings.get('background'),
                    troughcolor=self.original_scrollbar_settings.get('troughcolor'),
                    bordercolor=self.original_scrollbar_settings.get('bordercolor'),
                    arrowcolor=self.original_scrollbar_settings.get('arrowcolor')
                )
                logging.info("Przywrócono oryginalny styl TScrollbar dla głównego okna.")
                # Wymuś odświeżenie UI launchera, aby zmiana była widoczna
                self.launcher.root.update_idletasks()
            else:
                logging.warning("Brak zapisanych oryginalnych ustawień TScrollbar do przywrócenia.")
        except Exception as e:
            logging.error(f"Błąd przy przywracaniu oryginalnego stylu TScrollbar: {e}")
        finally:
            self.destroy() # Zamknij okno edytora
