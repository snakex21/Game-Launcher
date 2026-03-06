import logging
import tkinter as tk
from tkinter import ttk

from launcher.utils import DEFAULT_MUSIC_HOTKEYS, PROGRAM_VERSION


def _create_settings_page_content(self):
    """Tworzy zawartość strony ustawień w self.settings_page_frame."""
    logging.info("Rozpoczynanie tworzenia zawartości ustawień...")

    header_frame = ttk.Frame(self.settings_page_frame)
    header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(10, 5))
    header_frame.columnconfigure(0, weight=1)
    ttk.Label(
        header_frame, text="Ustawienia Aplikacji", font=("Helvetica", 18, "bold")
    ).grid(row=0, column=0, sticky="w")

    settings_canvas = tk.Canvas(self.settings_page_frame, bg="#1e1e1e", highlightthickness=0)
    settings_scrollbar = ttk.Scrollbar(
        self.settings_page_frame, orient="vertical", command=settings_canvas.yview
    )
    scrollable_frame = ttk.Frame(settings_canvas, style="TFrame")
    scrollable_frame_window_id = settings_canvas.create_window(
        (0, 0), window=scrollable_frame, anchor="nw"
    )

    def _on_canvas_configure(event):
        if settings_canvas.winfo_exists() and scrollable_frame.winfo_exists():
            canvas_width = event.width
            settings_canvas.itemconfig(scrollable_frame_window_id, width=canvas_width)
            bbox = settings_canvas.bbox("all")
            logging.debug(f"Settings Canvas Configure - bbox: {bbox}")
            settings_canvas.configure(scrollregion=bbox if bbox else (0, 0, 1, 1))

    settings_canvas.bind("<Configure>", _on_canvas_configure)
    scrollable_frame.bind(
        "<Configure>",
        lambda e: (
            settings_canvas.configure(scrollregion=settings_canvas.bbox("all"))
            if settings_canvas.winfo_exists()
            else None
        ),
    )

    def _on_settings_mousewheel(event):
        try:
            widget_under_cursor = self.root.winfo_containing(event.x_root, event.y_root)
        except (tk.TclError, KeyError) as e:
            logging.debug(f"Ignorowany błąd w winfo_containing (settings): {e}")
            widget_under_cursor = None

        is_settings_area = False
        curr = widget_under_cursor
        while curr is not None:
            if curr == settings_canvas or curr == scrollable_frame:
                is_settings_area = True
                break
            if curr == self.root:
                break
            try:
                curr = curr.master
            except tk.TclError:
                break
        if is_settings_area and settings_canvas.winfo_exists():
            scroll_val = -1 * int(event.delta / 120)
            view_start, view_end = settings_canvas.yview()
            if (scroll_val < 0 and view_start > 0.0) or (scroll_val > 0 and view_end < 1.0):
                settings_canvas.yview_scroll(scroll_val, "units")
                return "break"

    self.root.bind_all("<MouseWheel>", _on_settings_mousewheel, add="+")

    def _safe_scrollbar_set(first, last):
        try:
            settings_scrollbar.set(first, last)
        except tk.TclError:
            pass

    settings_canvas.configure(yscrollcommand=_safe_scrollbar_set)
    settings_canvas.grid(row=1, column=0, sticky="nsew")
    settings_scrollbar.grid(row=1, column=1, sticky="ns")
    scrollable_frame.columnconfigure(0, weight=1)

    current_row = 0
    logging.debug(f"--- Start sekcji --- current_row: {current_row}")

    appearance_frame = ttk.LabelFrame(scrollable_frame, text=" Wygląd ", padding=(10, 5))
    appearance_frame.grid(row=current_row, column=0, sticky="nsew", padx=20, pady=10)
    appearance_frame.columnconfigure(1, weight=1)

    appearance_current_row = 0

    ttk.Label(appearance_frame, text="Aktywny Motyw:").grid(
        row=appearance_current_row, column=0, padx=5, pady=5, sticky="w"
    )
    self.theme_var = tk.StringVar(value=self.settings.get("theme", "Dark"))
    self.theme_menu = ttk.OptionMenu(appearance_frame, self.theme_var, self.theme_var.get())
    self.theme_menu.grid(row=appearance_current_row, column=1, padx=5, pady=5, sticky="ew")
    self._update_main_theme_selector()
    appearance_current_row += 1

    ttk.Label(appearance_frame, text="Kafelki w rzędzie w Bibliotece:").grid(
        row=appearance_current_row, column=0, padx=5, pady=5, sticky="w"
    )
    self.tiles_per_row_var = tk.IntVar(value=self.local_settings.get("tiles_per_row", 4))
    tiles_spinbox = ttk.Spinbox(
        appearance_frame,
        from_=2,
        to=8,
        textvariable=self.tiles_per_row_var,
        width=5,
        command=self._save_tiles_per_row_setting,
        state="readonly",
    )
    tiles_spinbox.grid(row=appearance_current_row, column=1, padx=5, pady=5, sticky="w")
    appearance_current_row += 1

    ttk.Label(appearance_frame, text="Czcionka interfejsu:").grid(
        row=2, column=0, padx=5, pady=5, sticky="w"
    )
    available_fonts = ["Segoe UI", "Arial", "Verdana", "Tahoma", "Calibri", "System"]
    try:
        from tkinter import font

        system_fonts = list(font.families())
        sensible_system_fonts = [f for f in system_fonts if not f.startswith("@")] 
        available_fonts = sorted(
            list(set(available_fonts + sensible_system_fonts)), key=str.lower
        )
    except Exception:
        pass
    default_font = "Segoe UI" if "Segoe UI" in available_fonts else "System"
    self.font_var = tk.StringVar(value=self.local_settings.get("ui_font", default_font))
    font_combo = ttk.Combobox(
        appearance_frame,
        textvariable=self.font_var,
        values=available_fonts,
        state="readonly",
        width=30,
    )
    font_combo.grid(row=appearance_current_row, column=1, padx=5, pady=5, sticky="ew")
    font_combo.bind("<<ComboboxSelected>>", self._save_and_apply_font_setting)
    appearance_current_row += 1

    custom_theme_frame = ttk.LabelFrame(
        appearance_frame, text=" Zarządzanie Motywami Niestandardowymi ", padding=10
    )
    custom_theme_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=5, pady=10)
    custom_theme_frame.columnconfigure(0, weight=1)
    custom_theme_frame.rowconfigure(0, weight=1)

    ct_list_frame = ttk.Frame(custom_theme_frame)
    ct_list_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")
    ct_list_frame.columnconfigure(0, weight=1)
    ct_list_frame.rowconfigure(0, weight=1)

    self.custom_themes_listbox = tk.Listbox(ct_list_frame, height=5)
    self.custom_themes_listbox.grid(row=0, column=0, sticky="nsew")
    ct_scrollbar = ttk.Scrollbar(
        ct_list_frame, orient="vertical", command=self.custom_themes_listbox.yview
    )
    ct_scrollbar.grid(row=0, column=1, sticky="ns")
    self.custom_themes_listbox.config(yscrollcommand=ct_scrollbar.set)
    self._load_custom_themes_list()

    ct_buttons_frame = ttk.Frame(custom_theme_frame)
    ct_buttons_frame.grid(row=1, column=0, columnspan=2, pady=(5, 0))
    ttk.Button(ct_buttons_frame, text="Dodaj", command=self._add_custom_theme).pack(
        side=tk.LEFT, padx=2
    )
    ttk.Button(ct_buttons_frame, text="Edytuj", command=self._edit_custom_theme).pack(
        side=tk.LEFT, padx=2
    )
    ttk.Button(ct_buttons_frame, text="Usuń", command=self._delete_custom_theme).pack(
        side=tk.LEFT, padx=2
    )
    ttk.Button(
        ct_buttons_frame, text="Eksportuj", command=self._export_custom_theme_dialog
    ).pack(side=tk.LEFT, padx=2)
    ttk.Button(
        ct_buttons_frame, text="Importuj", command=self._import_custom_theme_dialog
    ).pack(side=tk.LEFT, padx=2)
    appearance_current_row += 1

    if not hasattr(self, "show_track_overlay_var"):
        self.show_track_overlay_var = tk.BooleanVar(
            value=self.local_settings.get("show_track_overlay", False)
        )
    overlay_check = ttk.Checkbutton(
        appearance_frame,
        text="Pokaż nakładkę 'Teraz Odtwarzane' na ekranie (globalnie)",
        variable=self.show_track_overlay_var,
        command=self._toggle_track_overlay_setting,
    )
    overlay_check.grid(
        row=appearance_current_row,
        column=0,
        columnspan=2,
        sticky="w",
        padx=5,
        pady=(10, 5),
    )
    appearance_current_row += 1

    overlay_position_frame = ttk.Frame(appearance_frame)
    overlay_position_frame.grid(
        row=appearance_current_row,
        column=0,
        columnspan=2,
        sticky="w",
        padx=5,
        pady=(5, 0),
    )

    ttk.Label(overlay_position_frame, text="Pozycja X nakładki:").grid(
        row=0, column=0, padx=(0, 5), pady=2
    )
    self.overlay_x_pos_var = tk.IntVar(value=self.local_settings.get("overlay_x_pos", 0))
    overlay_x_entry = ttk.Entry(
        overlay_position_frame, textvariable=self.overlay_x_pos_var, width=6
    )
    overlay_x_entry.grid(row=0, column=1, pady=2)

    ttk.Label(overlay_position_frame, text="Pozycja Y nakładki:").grid(
        row=1, column=0, padx=(0, 5), pady=2
    )
    self.overlay_y_pos_var = tk.IntVar(value=self.local_settings.get("overlay_y_pos", 0))
    overlay_y_entry = ttk.Entry(
        overlay_position_frame, textvariable=self.overlay_y_pos_var, width=6
    )
    overlay_y_entry.grid(row=1, column=1, pady=2)

    overlay_pos_buttons_frame = ttk.Frame(appearance_frame)
    overlay_pos_buttons_frame.grid(
        row=appearance_current_row + 1,
        column=0,
        columnspan=2,
        sticky="w",
        padx=5,
        pady=(0, 5),
    )

    apply_pos_btn = ttk.Button(
        overlay_pos_buttons_frame,
        text="Zastosuj Pozycję",
        command=self._apply_overlay_position_from_settings,
    )
    apply_pos_btn.pack(side=tk.LEFT, padx=(0, 5))

    reset_pos_btn = ttk.Button(
        overlay_pos_buttons_frame,
        text="Resetuj Pozycję",
        command=self._reset_overlay_position,
    )
    reset_pos_btn.pack(side=tk.LEFT)

    appearance_current_row += 2

    current_row += 1

    user_frame = ttk.LabelFrame(scrollable_frame, text=" Użytkownik ", padding=(10, 5))
    user_frame.grid(row=current_row, column=0, sticky="nsew", padx=20, pady=10)
    user_frame.columnconfigure(1, weight=1)

    user_display_frame = ttk.Frame(user_frame)
    user_display_frame.grid(row=0, column=0, columnspan=3, pady=5, sticky="w")
    avatar_size_settings = (
        self.local_settings.get("avatar_display_size", 48),
        self.local_settings.get("avatar_display_size", 48),
    )
    self.settings_avatar_label = ttk.Label(
        user_display_frame,
        width=avatar_size_settings[0] // 8 if avatar_size_settings[0] >= 48 else 6,
    )
    self.settings_avatar_label.pack(side=tk.LEFT, padx=5)
    self.settings_username_label = ttk.Label(
        user_display_frame,
        text=f"Nazwa: {self.user.get('username', 'Gracz')}",
        font=("Helvetica", 11, "bold"),
    )
    self.settings_username_label.pack(side=tk.LEFT, padx=10, anchor="w")
    self._load_and_display_settings_avatar()
    self._load_and_display_settings_avatar(avatar_size_settings)

    ttk.Button(user_frame, text="Zmień Nazwę Użytkownika", command=self.change_username).grid(
        row=1, column=0, columnspan=3, padx=5, pady=5, sticky="w"
    )

    ttk.Label(user_frame, text="Ścieżka Awatara:").grid(
        row=2, column=0, padx=5, pady=5, sticky="w"
    )
    self.avatar_var = tk.StringVar(value=self.user.get("avatar", ""))
    avatar_entry = ttk.Entry(user_frame, textvariable=self.avatar_var, width=40, state="readonly")
    avatar_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
    avatar_button = ttk.Button(user_frame, text="Wybierz...", command=self.select_avatar)
    avatar_button.grid(row=2, column=2, padx=5, pady=5)
    delete_avatar_btn = ttk.Button(user_frame, text="Usuń Awatar", command=self.delete_avatar)
    delete_avatar_btn.grid(row=3, column=1, columnspan=2, padx=5, pady=(0, 5), sticky="e")

    avatar_size_control_frame = ttk.Frame(user_frame)
    avatar_size_control_frame.grid(row=4, column=0, columnspan=3, padx=5, pady=(5, 10), sticky="w")

    ttk.Label(avatar_size_control_frame, text="Rozmiar Awatara:").pack(side=tk.LEFT, padx=(0, 5))
    self.avatar_size_var = tk.IntVar(value=self.local_settings.get("avatar_display_size", 48))
    avatar_size_options = [32, 48, 64, 96, 128]
    avatar_size_spinbox = ttk.Spinbox(
        avatar_size_control_frame,
        textvariable=self.avatar_size_var,
        values=avatar_size_options,
        width=5,
        command=self._save_and_refresh_avatar_size,
        state="readonly",
    )
    avatar_size_spinbox.pack(side=tk.LEFT)

    ttk.Button(
        user_frame,
        text="Usuń Konto Czatu",
        command=self._confirm_delete_chat_account,
        style="Red.TButton",
    ).grid(row=5, column=0, columnspan=3, padx=5, pady=(15, 5), sticky="ew")
    logging.debug(
        f"Po sekcji Użytkownik - grid_info: {user_frame.grid_info()}, current_row: {current_row}"
    )

    current_row += 1

    system_frame = ttk.LabelFrame(scrollable_frame, text=" System ", padding=(10, 5))
    system_frame.grid(row=current_row, column=0, sticky="nsew", padx=20, pady=10)

    self.autostart_var = tk.BooleanVar(value=self.settings.get("autostart", False))
    autostart_check = ttk.Checkbutton(
        system_frame,
        text="Uruchamiaj z systemem Windows",
        variable=self.autostart_var,
        command=self.toggle_autostart,
    )
    autostart_check.pack(anchor="w", pady=2)

    self.auto_backup_var = tk.BooleanVar(value=self.settings.get("auto_backup_on_exit", True))
    auto_backup_check = ttk.Checkbutton(
        system_frame,
        text="Automatycznie twórz backup zapisów przy zamknięciu gry (nadpisuje poprzedni)",
        variable=self.auto_backup_var,
        command=self._save_auto_backup_setting,
    )
    auto_backup_check.pack(anchor="w", pady=2)

    ttk.Button(
        system_frame,
        text="Resetuj licznik Launchera",
        command=self.reset_launcher_usage_time,
    ).pack(anchor="w", pady=2)

    logging.debug(
        f"Po sekcji System - grid_info: {system_frame.grid_info()}, current_row: {current_row}"
    )
    current_row += 1

    sync_api_frame = ttk.LabelFrame(
        scrollable_frame, text=" Klucze API i Synchronizacja ", padding=(10, 5)
    )
    sync_api_frame.grid(row=current_row, column=0, sticky="nsew", padx=20, pady=10)
    sync_api_frame.columnconfigure(0, weight=1)

    api_keys_subframe = ttk.Frame(sync_api_frame, style="TFrame")
    api_keys_subframe.grid(row=0, column=0, sticky="ew", pady=(0, 10))
    api_keys_subframe.columnconfigure(1, weight=1)

    github_token_frame = ttk.Frame(api_keys_subframe, style="TFrame")
    github_token_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
    github_token_frame.columnconfigure(1, weight=1)
    ttk.Label(github_token_frame, text="GitHub Token:").grid(row=0, column=0, sticky="w", padx=5)
    self.github_token_entry = ttk.Entry(github_token_frame, show="*", width=30)
    self.github_token_entry.grid(row=0, column=1, padx=5, sticky="ew")
    self.github_token_entry.insert(0, self.local_settings.get("github_token", ""))
    ttk.Button(github_token_frame, text="?", width=2, command=self.show_github_token_help).grid(
        row=0, column=2, padx=5
    )
    show_gh_token_var = tk.BooleanVar()
    ttk.Checkbutton(
        github_token_frame,
        text="Pokaż",
        variable=show_gh_token_var,
        command=lambda: self.toggle_show_key(self.github_token_entry, show_gh_token_var),
    ).grid(row=0, column=3, padx=5)

    rawg_subframe = ttk.Frame(api_keys_subframe, style="TFrame")
    rawg_subframe.grid(row=1, column=0, pady=(5, 0), sticky="ew")
    rawg_subframe.columnconfigure(1, weight=1)
    ttk.Label(rawg_subframe, text="RAWG.io API Key:").grid(row=0, column=0, sticky="w", padx=5)
    self.rawg_api_key_entry = ttk.Entry(rawg_subframe, show="*", width=30)
    self.rawg_api_key_entry.grid(row=0, column=1, padx=5, sticky="ew")
    self.rawg_api_key_entry.insert(0, self.local_settings.get("rawg_api_key", ""))
    ttk.Button(rawg_subframe, text="?", width=2, command=self.show_rawg_key_help).grid(
        row=0, column=2, padx=5
    )
    show_rawg_key_var = tk.BooleanVar()
    ttk.Checkbutton(
        rawg_subframe,
        text="Pokaż",
        variable=show_rawg_key_var,
        command=lambda: self.toggle_show_key(self.rawg_api_key_entry, show_rawg_key_var),
    ).grid(row=0, column=3, padx=5)

    lastfm_api_frame = ttk.Frame(api_keys_subframe, style="TFrame")
    lastfm_api_frame.grid(row=2, column=0, pady=(5, 0), sticky="ew")
    lastfm_api_frame.columnconfigure(1, weight=1)
    ttk.Label(lastfm_api_frame, text="Last.fm API Key:").grid(row=0, column=0, sticky="w", padx=5)
    self.lastfm_api_key_entry = ttk.Entry(lastfm_api_frame, show="*", width=30)
    self.lastfm_api_key_entry.grid(row=0, column=1, padx=5, sticky="ew")
    if hasattr(self, "local_settings"):
        self.lastfm_api_key_entry.insert(0, self.local_settings.get("lastfm_api_key", ""))
    ttk.Button(lastfm_api_frame, text="?", width=2, command=self._show_lastfm_key_help).grid(
        row=0, column=2, padx=5
    )
    show_lastfm_key_var = tk.BooleanVar()
    ttk.Checkbutton(
        lastfm_api_frame,
        text="Pokaż",
        variable=show_lastfm_key_var,
        command=lambda e=self.lastfm_api_key_entry, v=show_lastfm_key_var: self.toggle_show_key(e, v),
    ).grid(row=0, column=3, padx=5)

    api_save_buttons_frame = ttk.Frame(api_keys_subframe, style="TFrame")
    api_save_buttons_frame.grid(row=3, column=0, columnspan=4, pady=(10, 0), sticky="w")
    ttk.Button(
        api_save_buttons_frame,
        text="Zapisz GitHub Token",
        command=self.save_github_token,
    ).pack(side=tk.LEFT, padx=5)
    ttk.Button(
        api_save_buttons_frame,
        text="Zapisz RAWG Key",
        command=self.save_rawg_api_key,
    ).pack(side=tk.LEFT, padx=5)
    ttk.Button(
        api_save_buttons_frame,
        text="Zapisz Last.fm Key",
        command=self._save_lastfm_api_key,
    ).pack(side=tk.LEFT, padx=5)

    ttk.Separator(sync_api_frame, orient="horizontal").grid(
        row=1, column=0, sticky="ew", pady=15, padx=20
    )

    cloud_services_label = ttk.Label(sync_api_frame, text="Usługi Chmurowe do Synchronizacji:")
    cloud_services_label.grid(row=2, column=0, pady=(5, 2), sticky="w", padx=5)

    cloud_cb_frame = ttk.Frame(sync_api_frame, style="TFrame")
    cloud_cb_frame.grid(row=3, column=0, sticky="w", padx=5)
    self.cloud_services = {
        "Google Drive": tk.BooleanVar(
            value=self.settings.get("cloud_service_google_drive", False)
        ),
        "GitHub": tk.BooleanVar(value=self.settings.get("cloud_service_github", False)),
    }
    ttk.Checkbutton(
        cloud_cb_frame,
        text="Google Drive",
        variable=self.cloud_services["Google Drive"],
        command=self.update_cloud_services,
    ).pack(side=tk.LEFT, padx=5)
    ttk.Checkbutton(
        cloud_cb_frame,
        text="GitHub",
        variable=self.cloud_services["GitHub"],
        command=self.update_cloud_services,
    ).pack(side=tk.LEFT, padx=5)

    cloud_btn_frame = ttk.Frame(sync_api_frame, style="TFrame")
    cloud_btn_frame.grid(row=4, column=0, pady=5, sticky="w", padx=5)
    ttk.Button(cloud_btn_frame, text="Prześlij", command=self.upload_to_cloud).pack(
        side=tk.LEFT, padx=5
    )
    ttk.Button(cloud_btn_frame, text="Pobierz", command=self.download_from_cloud).pack(
        side=tk.LEFT, padx=5
    )

    ttk.Separator(sync_api_frame, orient="horizontal").grid(
        row=5, column=0, sticky="ew", pady=15, padx=20
    )

    local_backup_label = ttk.Label(sync_api_frame, text="Lokalny Backup:")
    local_backup_label.grid(row=6, column=0, pady=(5, 2), sticky="w", padx=5)

    local_btn_frame = ttk.Frame(sync_api_frame, style="TFrame")
    local_btn_frame.grid(row=7, column=0, pady=5, sticky="w", padx=5)
    ttk.Button(local_btn_frame, text="Zgraj Backup", command=self.backup_to_local_folder).pack(
        side=tk.LEFT, padx=5
    )
    ttk.Button(local_btn_frame, text="Wczytaj Backup", command=self.load_local_backup).pack(
        side=tk.LEFT, padx=5
    )

    logging.debug(
        f"Po sekcji Synchronizacja i API - grid_info: {sync_api_frame.grid_info()}, current_row: {current_row}"
    )
    current_row += 1

    screenshot_scan_frame = ttk.LabelFrame(
        scrollable_frame, text=" Skanowanie Screenshotów ", padding=(10, 5)
    )
    screenshot_scan_frame.grid(row=current_row, column=0, sticky="nsew", padx=20, pady=10)
    screenshot_scan_frame.columnconfigure(0, weight=1)

    ss_list_manage_frame = ttk.Frame(screenshot_scan_frame)
    ss_list_manage_frame.grid(row=0, column=0, sticky="nsew", pady=5, padx=5)
    ss_list_manage_frame.columnconfigure(0, weight=1)
    ss_list_manage_frame.rowconfigure(0, weight=1)

    ss_listbox_frame = ttk.Frame(ss_list_manage_frame)
    ss_listbox_frame.grid(row=0, column=0, sticky="nsew")
    ss_listbox_frame.rowconfigure(0, weight=1)
    ss_listbox_frame.columnconfigure(0, weight=1)

    self.autoscan_folders_listbox = tk.Listbox(ss_listbox_frame, height=4)
    self.autoscan_folders_listbox.grid(row=0, column=0, sticky="nsew")
    ss_scan_scrollbar = ttk.Scrollbar(
        ss_listbox_frame,
        orient="vertical",
        command=self.autoscan_folders_listbox.yview,
    )
    ss_scan_scrollbar.grid(row=0, column=1, sticky="ns")
    self.autoscan_folders_listbox.config(yscrollcommand=ss_scan_scrollbar.set)
    self.load_autoscan_folders_list()

    ss_buttons_frame = ttk.Frame(ss_list_manage_frame)
    ss_buttons_frame.grid(row=0, column=1, sticky="ns", padx=5)
    ttk.Button(ss_buttons_frame, text="Dodaj", command=self.add_autoscan_folder).pack(
        pady=2, fill="x"
    )
    ttk.Button(ss_buttons_frame, text="Usuń", command=self.remove_autoscan_folder).pack(
        pady=2, fill="x"
    )

    ss_ignore_label = ttk.Label(
        screenshot_scan_frame,
        text="Nazwy folderów do ignorowania podczas skanowania screenshotów (jedna na linię):",
    )
    ss_ignore_label.grid(row=2, column=0, columnspan=2, sticky="w", padx=5, pady=(15, 2))

    ss_ignore_text_frame = ttk.Frame(screenshot_scan_frame)
    ss_ignore_text_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=5, pady=2)
    ss_ignore_text_frame.columnconfigure(0, weight=1)
    ss_ignore_text_frame.rowconfigure(0, weight=1)

    self.ss_ignored_folders_text = tk.Text(
        ss_ignore_text_frame, height=4, wrap=tk.WORD, relief=tk.FLAT
    )
    style = ttk.Style()
    text_bg = style.lookup("TEntry", "fieldbackground")
    text_fg = style.lookup("TEntry", "foreground")
    self.ss_ignored_folders_text.config(
        background=text_bg, foreground=text_fg, relief=tk.SOLID, borderwidth=1
    )
    self.ss_ignored_folders_text.grid(row=0, column=0, sticky="nsew")

    ss_ignore_scrollbar = ttk.Scrollbar(
        ss_ignore_text_frame,
        orient="vertical",
        command=self.ss_ignored_folders_text.yview,
    )
    ss_ignore_scrollbar.grid(row=0, column=1, sticky="ns")
    self.ss_ignored_folders_text.config(yscrollcommand=ss_ignore_scrollbar.set)
    self.load_screenshot_ignored_folders()

    save_ss_ignore_btn = ttk.Button(
        screenshot_scan_frame,
        text="Zapisz Ignorowane Foldery Screenshotów",
        command=self.save_screenshot_ignored_folders,
    )
    save_ss_ignore_btn.grid(row=4, column=0, columnspan=2, pady=(5, 10))

    self.autoscan_on_startup_var = tk.BooleanVar(
        value=self.settings.get("autoscan_on_startup", False)
    )
    autoscan_startup_check = ttk.Checkbutton(
        screenshot_scan_frame,
        text="Skanuj screenshoty automatycznie przy uruchomieniu launchera",
        variable=self.autoscan_on_startup_var,
        command=self._save_autoscan_startup_setting,
    )
    autoscan_startup_check.grid(row=1, column=0, sticky="w", padx=5, pady=5)

    start_screenshot_scan_btn = ttk.Button(
        screenshot_scan_frame,
        text="Skanuj Screenshoty Teraz (Wszystkie Gry)",
        command=self.start_scan_screenshots_thread,
    )
    start_screenshot_scan_btn.grid(row=2, column=0, pady=10)

    current_row += 1

    logging.debug(f"--- Tworzenie sekcji Emulatorów --- current_row: {current_row}")
    emulators_frame = ttk.LabelFrame(scrollable_frame, text=" Emulatory ", padding=(10, 5))
    emulators_frame.grid(row=current_row, column=0, sticky="nsew", padx=20, pady=10)
    emulators_frame.columnconfigure(0, weight=1)
    emu_list_frame = ttk.Frame(emulators_frame)
    emu_list_frame.grid(row=0, column=0, sticky="ew", pady=5, padx=5)
    emu_list_frame.columnconfigure(0, weight=1)
    emu_cols = ("Nazwa", "Ścieżka")
    self.emulators_tree = ttk.Treeview(
        emu_list_frame,
        columns=emu_cols,
        show="headings",
        height=4,
        selectmode="browse",
    )
    self.emulators_tree.heading("Nazwa", text="Nazwa Emulatora")
    self.emulators_tree.heading("Ścieżka", text="Ścieżka do .exe")
    self.emulators_tree.column("Nazwa", width=200, anchor=tk.W)
    self.emulators_tree.column("Ścieżka", width=400, anchor=tk.W)
    emu_scrollbar = ttk.Scrollbar(emu_list_frame, orient="vertical", command=self.emulators_tree.yview)
    self.emulators_tree.configure(yscrollcommand=emu_scrollbar.set)
    self.emulators_tree.grid(row=0, column=0, sticky="nsew")
    emu_scrollbar.grid(row=0, column=1, sticky="ns")
    emu_buttons_frame = ttk.Frame(emulators_frame)
    emu_buttons_frame.grid(row=1, column=0, pady=(5, 10))
    ttk.Button(emu_buttons_frame, text="Dodaj Emulator", command=self._add_edit_emulator).pack(
        side=tk.LEFT, padx=5
    )
    ttk.Button(
        emu_buttons_frame,
        text="Edytuj Zaznaczony",
        command=lambda: self._add_edit_emulator(edit_mode=True),
    ).pack(side=tk.LEFT, padx=5)
    ttk.Button(emu_buttons_frame, text="Usuń Zaznaczony", command=self._delete_emulator).pack(
        side=tk.LEFT, padx=5
    )
    self._load_emulators_list()
    self.root.update_idletasks()
    logging.debug(
        f"Po sekcji Emulatory - grid_info: {emulators_frame.grid_info()}, current_row: {current_row}"
    )
    current_row += 1

    news_settings_frame = ttk.LabelFrame(scrollable_frame, text=" Newsy (RSS) ", padding=(10, 5))
    news_settings_frame.grid(row=current_row, column=0, sticky="nsew", padx=20, pady=10)
    news_settings_frame.columnconfigure(0, weight=1)
    ttk.Label(news_settings_frame, text="Zarządzanie Kanałami RSS:").grid(
        row=0, column=0, sticky="w", pady=5
    )
    rss_list_outer_frame = ttk.Frame(news_settings_frame)
    rss_list_outer_frame.grid(row=1, column=0, sticky="nsew", pady=5)
    rss_list_outer_frame.columnconfigure(0, weight=1)
    self.rss_management_frame = ttk.Frame(rss_list_outer_frame)
    self.rss_management_frame.grid(sticky="nsew")
    self.populate_rss_management_frame()
    rss_buttons_frame = ttk.Frame(news_settings_frame)
    rss_buttons_frame.grid(row=2, column=0, pady=5)
    ttk.Button(
        rss_buttons_frame,
        text="Dodaj Kanał RSS",
        command=self.add_rss_feed_from_settings,
    ).pack(side=tk.LEFT, padx=5)
    ttk.Separator(news_settings_frame, orient="horizontal").grid(
        row=3, column=0, sticky="ew", pady=10, padx=10
    )
    post_limit_frame = ttk.Frame(news_settings_frame)
    post_limit_frame.grid(row=4, column=0, pady=5)
    ttk.Label(post_limit_frame, text="Liczba wyświetlanych newsów:").pack(side=tk.LEFT, padx=5)
    self.post_limit_var = tk.IntVar(value=self.settings.get("news_post_limit", 10))
    ttk.Spinbox(
        post_limit_frame,
        from_=1,
        to=100,
        textvariable=self.post_limit_var,
        width=5,
        command=self.update_post_limit,
    ).pack(side=tk.LEFT)
    logging.debug(
        f"Po sekcji Newsy - grid_info: {news_settings_frame.grid_info()}, current_row: {current_row}"
    )
    current_row += 1

    tools_frame = ttk.LabelFrame(scrollable_frame, text=" Narzędzia Biblioteki ", padding=(10, 5))
    tools_frame.grid(row=current_row, column=0, sticky="nsew", padx=20, pady=10)
    ttk.Button(
        tools_frame,
        text="Znajdź Potencjalne Duplikaty",
        command=self.start_duplicate_scan_thread,
    ).pack(pady=5)
    logging.debug(
        f"Po sekcji Narzędzia - grid_info: {tools_frame.grid_info()}, current_row: {current_row}"
    )
    current_row += 1

    update_frame = ttk.LabelFrame(scrollable_frame, text=" Aktualizacje Aplikacji ", padding=(10, 5))
    update_frame.grid(row=current_row, column=0, sticky="nsew", padx=20, pady=10)
    ttk.Button(
        update_frame,
        text="Sprawdź Aktualizacje Teraz",
        command=self.manual_check_updates,
    ).pack(pady=5)
    ttk.Label(update_frame, text=f"Aktualna wersja: {PROGRAM_VERSION}").pack(pady=5)
    logging.debug(
        f"Po sekcji Aktualizacje - grid_info: {update_frame.grid_info()}, current_row: {current_row}"
    )
    current_row += 1

    discord_frame = ttk.LabelFrame(scrollable_frame, text=" Integracja z Discord ", padding=(10, 5))
    discord_frame.grid(row=current_row, column=0, sticky="nsew", padx=20, pady=10)
    discord_frame.columnconfigure(1, weight=1)

    self.discord_rpc_enabled_var = tk.BooleanVar(
        value=self.local_settings.get("discord_rpc_enabled", False)
    )
    discord_enable_check = ttk.Checkbutton(
        discord_frame,
        text="Włącz Discord Rich Presence (pokaż status w Discord)",
        variable=self.discord_rpc_enabled_var,
        command=self._toggle_discord_rpc,
    )
    discord_enable_check.grid(row=0, column=0, columnspan=2, sticky="w", padx=5, pady=5)

    ttk.Label(discord_frame, text="Tekst statusu (gdy w menu):").grid(
        row=1, column=0, padx=5, pady=5, sticky="w"
    )
    self.discord_status_text_var = tk.StringVar(
        value=self.local_settings.get("discord_status_text", "Korzysta z Game Launcher")
    )
    discord_status_entry = ttk.Entry(
        discord_frame, textvariable=self.discord_status_text_var, width=40
    )
    discord_status_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
    discord_status_entry.bind("<FocusOut>", lambda e: self._save_discord_settings())

    current_row += 1

    remote_frame = ttk.LabelFrame(
        scrollable_frame,
        text=" Zdalne Sterowanie (Telefon/Przeglądarka) ",
        padding=(10, 5),
    )
    remote_frame.grid(row=current_row, column=0, sticky="nsew", padx=20, pady=10)
    remote_frame.columnconfigure(1, weight=1)

    self.remote_server_enabled_var = tk.BooleanVar(
        value=self.local_settings.get("remote_control_enabled", False)
    )
    remote_enable_check = ttk.Checkbutton(
        remote_frame,
        text="Włącz zdalne sterowanie (uruchamianie gier przez przeglądarkę w sieci lokalnej)",
        variable=self.remote_server_enabled_var,
        command=self._toggle_remote_server,
    )
    remote_enable_check.grid(row=0, column=0, columnspan=3, sticky="w", padx=5, pady=5)

    ttk.Label(
        remote_frame,
        text="Adres do wpisania w przeglądarce telefonu (w tej samej sieci Wi-Fi):",
    ).grid(row=1, column=0, columnspan=3, sticky="w", padx=5, pady=(10, 0))
    self.remote_url_label = ttk.Label(
        remote_frame,
        text="Serwer wyłączony",
        font=("Segoe UI", 9, "bold"),
        foreground="gray",
        wraplength=450,
    )
    self.remote_url_label.grid(row=2, column=0, columnspan=3, sticky="w", padx=5, pady=(0, 10))

    port_frame = ttk.Frame(remote_frame)
    port_frame.grid(row=3, column=0, columnspan=3, sticky="w", padx=5, pady=5)

    ttk.Label(port_frame, text="Port serwera:").pack(side=tk.LEFT, padx=(0, 5))
    self.remote_port_var = tk.IntVar(value=self.local_settings.get("remote_control_port", 5000))
    port_entry = ttk.Entry(port_frame, textvariable=self.remote_port_var, width=6)
    port_entry.pack(side=tk.LEFT)
    save_port_btn = ttk.Button(port_frame, text="Zapisz Port", command=self._save_remote_port)
    save_port_btn.pack(side=tk.LEFT, padx=(10, 0))

    current_row += 1

    hotkeys_frame_outer = ttk.LabelFrame(
        scrollable_frame,
        text=" Skróty Klawiszowe Odtwarzacza Muzyki ",
        padding=(10, 5),
    )
    hotkeys_frame_outer.grid(row=current_row, column=0, sticky="nsew", padx=20, pady=10)
    hotkeys_frame_outer.columnconfigure(1, weight=1)

    if not hasattr(self, "music_hotkey_entries"):
        self.music_hotkey_entries = {}
    if not hasattr(self, "music_hotkey_vars"):
        self.music_hotkey_vars = {}

    self.hotkeys_frame_outer = hotkeys_frame_outer

    hotkey_row = 0

    self.music_hotkeys_enabled_var = tk.BooleanVar(
        value=self.local_settings.get("music_hotkeys_enabled", True)
    )
    enable_hotkeys_check = ttk.Checkbutton(
        hotkeys_frame_outer,
        text="Włącz globalne skróty klawiszowe dla odtwarzacza muzyki",
        variable=self.music_hotkeys_enabled_var,
        command=self._toggle_music_hotkeys_enabled,
    )
    enable_hotkeys_check.grid(
        row=hotkey_row, column=0, columnspan=3, pady=(0, 10), sticky="w", padx=5
    )
    hotkey_row += 1

    hotkey_actions = {
        "play_pause": "Odtwórz / Pauza",
        "next_track": "Następny utwór",
        "prev_track": "Poprzedni utwór",
        "stop_music": "Zatrzymaj",
        "volume_up": "Głośniej",
        "volume_down": "Ciszej",
    }
    if not hasattr(self, "hotkey_actions_display_names"):
        self.hotkey_actions_display_names = hotkey_actions.copy()

    current_hotkeys = self.local_settings.get("music_hotkeys", DEFAULT_MUSIC_HOTKEYS.copy())

    for action_key, display_name in hotkey_actions.items():
        ttk.Label(hotkeys_frame_outer, text=f"{display_name}:").grid(
            row=hotkey_row, column=0, padx=5, pady=3, sticky="w"
        )

        shortcut_var = tk.StringVar(value=current_hotkeys.get(action_key, ""))
        self.music_hotkey_vars[action_key] = shortcut_var

        shortcut_entry = ttk.Entry(
            hotkeys_frame_outer,
            textvariable=shortcut_var,
            state="readonly",
            width=25,
        )
        shortcut_entry.grid(row=hotkey_row, column=1, padx=5, pady=3, sticky="ew")
        self.music_hotkey_entries[action_key] = shortcut_entry

        set_button = ttk.Button(
            hotkeys_frame_outer,
            text="Ustaw",
            command=lambda k=action_key, v=shortcut_var, e=shortcut_entry: self._set_music_hotkey_dialog(
                k, v, e
            ),
        )
        set_button.grid(row=hotkey_row, column=2, padx=5, pady=3)
        if not hasattr(self, "music_hotkey_set_buttons"):
            self.music_hotkey_set_buttons = {}
        self.music_hotkey_set_buttons[action_key] = set_button
        hotkey_row += 1

    self.reset_hotkeys_btn = ttk.Button(
        hotkeys_frame_outer,
        text="Przywróć Domyślne Skróty",
        command=self._reset_music_hotkeys,
    )
    self.reset_hotkeys_btn.grid(row=hotkey_row, column=0, columnspan=3, pady=(10, 5))
    hotkey_row += 1

    self._toggle_music_hotkeys_enabled()

    current_row += 1

    developer_tools_frame = ttk.LabelFrame(
        scrollable_frame, text=" Narzędzia Deweloperskie ", padding=(10, 5)
    )
    developer_tools_frame.grid(row=current_row, column=0, sticky="nsew", padx=20, pady=10)
    developer_tools_frame.columnconfigure(0, weight=1)

    ttk.Button(
        developer_tools_frame,
        text="Pokaż Konsolę Deweloperską",
        command=self._show_developer_console,
    ).pack(pady=5)

    spacer_frame = ttk.Frame(scrollable_frame, height=20)
    spacer_frame.grid(row=current_row + 1, column=0)

    current_row += 2

    spacer_frame = ttk.Frame(scrollable_frame, height=20)
    spacer_frame.grid(row=current_row, column=0)
    logging.debug(
        f"Po Spacer - grid_info: {spacer_frame.grid_info()}, current_row: {current_row}"
    )
    current_row += 1

    logging.info("Zakończono tworzenie zawartości ustawień.")
    self.root.after(
        50,
        lambda: (
            settings_canvas.configure(scrollregion=settings_canvas.bbox("all"))
            if settings_canvas.winfo_exists()
            else None
        ),
    )


__all__ = ["_create_settings_page_content"]
