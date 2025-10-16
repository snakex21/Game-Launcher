# plugins/settings/view.py
import customtkinter as ctk
from tkinter import filedialog, messagebox
from .theme_editor_window import ThemeEditorWindow

class SettingsView(ctk.CTkFrame):
    def __init__(self, parent, app_context):
        super().__init__(parent, fg_color="transparent")
        self.app_context = app_context
        self.editor_window = None
        self.pack_propagate(False)
        
        # --- KLUCZOWA POPRAWKA: Inicjalizacja brakującej zmiennej ---
        self.is_pat_visible = False 
        # --- KONIEC POPRAWKI ---

        self.app_context.event_manager.subscribe("cloud_status_update", self._update_cloud_status_thread_safe)

        scrollable_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scrollable_container.pack(fill="both", expand=True)

        # --- SEKCJA PROFILU UŻYTKOWNIKA ---
        profile_frame = ctk.CTkFrame(scrollable_container)
        profile_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(profile_frame, text="Profil Użytkownika", font=("Roboto", 16, "bold")).pack(pady=(5, 10))
        
        username_frame = ctk.CTkFrame(profile_frame, fg_color="transparent")
        username_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(username_frame, text="Nazwa:", width=100, anchor="w").pack(side="left")
        self.username_entry = ctk.CTkEntry(username_frame)
        self.username_entry.pack(side="left", fill="x", expand=True)

        avatar_frame = ctk.CTkFrame(profile_frame, fg_color="transparent")
        avatar_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(avatar_frame, text="Awatar:", width=100, anchor="w").pack(side="left")
        self.avatar_entry = ctk.CTkEntry(avatar_frame, state="readonly")
        self.avatar_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(avatar_frame, text="Przeglądaj...", width=100, command=self._browse_avatar).pack(side="left")
        
        ctk.CTkButton(profile_frame, text="Zapisz zmiany w profilu", command=self._save_profile).pack(pady=10)

        # --- SEKCJA USTAWIEŃ SYSTEMOWYCH ---
        system_frame = ctk.CTkFrame(scrollable_container)
        system_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(system_frame, text="Ustawienia Systemowe", font=("Roboto", 16, "bold")).pack(pady=5)
        
        self.autostart_switch = ctk.CTkSwitch(system_frame, text="Uruchamiaj z systemem Windows")
        self.autostart_switch.pack(anchor="w", padx=10, pady=5)
        
        self.tray_switch = ctk.CTkSwitch(system_frame, text="Minimalizuj do zasobnika systemowego (tray)")
        self.tray_switch.pack(anchor="w", padx=10, pady=5)
        
        ctk.CTkButton(system_frame, text="Zapisz ustawienia systemowe", command=self._save_system_settings).pack(pady=10)
        
        # --- SEKCJA BACKUP I PRZYWRACANIE ---
        backup_frame = ctk.CTkFrame(scrollable_container)
        backup_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(backup_frame, text="Backup i Przywracanie", font=("Roboto", 16, "bold")).pack(pady=5)
        
        backup_controls = ctk.CTkFrame(backup_frame, fg_color="transparent")
        backup_controls.pack(fill="x", padx=10, pady=10)
        backup_controls.grid_columnconfigure((0, 1), weight=1)
        
        ctk.CTkButton(backup_controls, text="Utwórz lokalny backup", command=self._create_backup).grid(row=0, column=0, padx=(0, 5), sticky="ew")
        ctk.CTkButton(backup_controls, text="Przywróć z backupu...", command=self._restore_backup).grid(row=0, column=1, padx=(5, 0), sticky="ew")

        # --- SEKCJA SYNCHRONIZACJI Z CHMURĄ ---
        cloud_frame = ctk.CTkFrame(scrollable_container)
        cloud_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(cloud_frame, text="Synchronizacja z Chmurą", font=("Roboto", 16, "bold")).pack(pady=5)
        
        provider_frame = ctk.CTkFrame(cloud_frame, fg_color="transparent")
        provider_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(provider_frame, text="Dostawca:").pack(side="left")
        self.provider_selector = ctk.CTkOptionMenu(provider_frame, values=["Google Drive", "GitHub"], command=self.on_provider_change)
        self.provider_selector.pack(side="left", padx=10)
        
        self.github_frame = ctk.CTkFrame(cloud_frame, fg_color="transparent")
        ctk.CTkLabel(self.github_frame, text="GitHub Personal Access Token:").pack(anchor="w", padx=10, pady=(5,0))
        
        pat_input_frame = ctk.CTkFrame(self.github_frame, fg_color="transparent")
        pat_input_frame.pack(fill="x", padx=10)
        
        self.github_pat_entry = ctk.CTkEntry(pat_input_frame, show="*")
        self.github_pat_entry.pack(side="left", fill="x", expand=True)
        
        self.pat_visibility_button = ctk.CTkButton(pat_input_frame, text="👁", font=("Segoe UI Emoji", 14), width=35, command=self._toggle_pat_visibility)
        self.pat_visibility_button.pack(side="left", padx=(5, 0))

        ctk.CTkButton(self.github_frame, text="Zapisz Token", command=self._save_github_pat).pack(pady=5)
        
        self.cloud_status_label = ctk.CTkLabel(cloud_frame, text="Status: Niepołączono")
        self.cloud_status_label.pack(pady=5)
        
        cloud_controls = ctk.CTkFrame(cloud_frame, fg_color="transparent")
        cloud_controls.pack(fill="x", padx=10, pady=10)
        cloud_controls.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.connect_button = ctk.CTkButton(cloud_controls, text="Połącz / Zaloguj", command=self._connect_to_drive)
        self.connect_button.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        self.upload_button = ctk.CTkButton(cloud_controls, text="Wyślij do chmury", command=self._upload_to_drive, state="disabled")
        self.upload_button.grid(row=0, column=1, padx=(5, 5), sticky="ew")
        self.download_button = ctk.CTkButton(cloud_controls, text="Pobierz z chmury", command=self._download_from_drive, state="disabled")
        self.download_button.grid(row=0, column=2, padx=(5, 0), sticky="ew")

        # --- SEKCJA INTEGRACJI ---
        integrations_frame = ctk.CTkFrame(scrollable_container)
        integrations_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(integrations_frame, text="Integracje", font=("Roboto", 16, "bold")).pack(pady=5)
        
        self.discord_switch = ctk.CTkSwitch(integrations_frame, text="Włącz integrację z Discord Rich Presence", command=self._save_integrations_settings)
        self.discord_switch.pack(anchor="w", padx=10, pady=(5, 10))

        # --- SEKCJA WYGLĄDU ---
        theme_frame = ctk.CTkFrame(scrollable_container)
        theme_frame.pack(fill="x", padx=10, pady=10, expand=False)
        ctk.CTkLabel(theme_frame, text="Wygląd Aplikacji", font=("Roboto", 16, "bold")).pack(pady=5)
        
        theme_controls = ctk.CTkFrame(theme_frame, fg_color="transparent")
        theme_controls.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(theme_controls, text="Aktywny motyw:").pack(side="left")
        self.theme_selector = ctk.CTkOptionMenu(theme_controls, command=self._change_theme)
        self.theme_selector.pack(side="left", padx=10)
        ctk.CTkButton(theme_controls, text="Otwórz Edytor Motywów...", command=self._open_theme_editor).pack(side="left")

        self.refresh_view()

    def _toggle_pat_visibility(self):
        self.is_pat_visible = not self.is_pat_visible
        if self.is_pat_visible:
            self.github_pat_entry.configure(show="")
            self.pat_visibility_button.configure(text="🙈")
        else:
            self.github_pat_entry.configure(show="*")
            self.pat_visibility_button.configure(text="👁")

    def refresh_view(self):
        self._load_settings()
        self._populate_theme_selector()

    def _load_settings(self):
        settings_data = self.app_context.data_manager.get_plugin_data("settings")
        
        self.username_entry.delete(0, 'end'); self.username_entry.insert(0, settings_data.get("username", ""))
        self.avatar_entry.configure(state="normal"); self.avatar_entry.delete(0, 'end'); self.avatar_entry.insert(0, settings_data.get("avatar_path", "")); self.avatar_entry.configure(state="readonly")
        
        if settings_data.get("autostart_enabled", False): self.autostart_switch.select()
        else: self.autostart_switch.deselect()
        if settings_data.get("tray_minimize_enabled", False): self.tray_switch.select()
        else: self.tray_switch.deselect()

        if settings_data.get("discord_rpc_enabled", False): self.discord_switch.select()
        else: self.discord_switch.deselect()

        provider = settings_data.get("cloud_provider", "Google Drive")
        self.provider_selector.set(provider)
        self.on_provider_change(provider, initial_load=True)
        self.github_pat_entry.delete(0, 'end'); self.github_pat_entry.insert(0, settings_data.get("github_pat", ""))

    def on_provider_change(self, provider_name, initial_load=False):
        if not initial_load:
            self.app_context.cloud_service.set_provider(provider_name)
        
        if provider_name == "GitHub":
            self.github_frame.pack(fill="x", padx=10, pady=5)
            self.connect_button.configure(text="Połącz z GitHub")
        else:
            self.github_frame.pack_forget()
            self.connect_button.configure(text="Połącz z Google Drive")
        self._update_cloud_status_ui("Niepołączono")

    def _save_github_pat(self):
        settings_data = self.app_context.data_manager.get_plugin_data("settings")
        settings_data["github_pat"] = self.github_pat_entry.get()
        self.app_context.data_manager.save_plugin_data("settings", settings_data)
        messagebox.showinfo("Sukces", "Token GitHub został zapisany.")

    def _populate_theme_selector(self):
        themes = self.app_context.theme_service.get_available_themes()
        self.theme_selector.configure(values=themes)
        settings_data = self.app_context.data_manager.get_plugin_data("settings")
        current_theme = settings_data.get("last_used_theme", "Dark")
        if current_theme in themes:
            self.theme_selector.set(current_theme)

    def _browse_avatar(self):
        filepath = filedialog.askopenfilename(title="Wybierz awatar", filetypes=(("Obrazy", "*.png *.jpg *.jpeg"),))
        if filepath:
            self.avatar_entry.configure(state="normal"); self.avatar_entry.delete(0, "end"); self.avatar_entry.insert(0, filepath); self.avatar_entry.configure(state="readonly")

    def _save_profile(self):
        settings_data = self.app_context.data_manager.get_plugin_data("settings")
        settings_data["username"] = self.username_entry.get()
        settings_data["avatar_path"] = self.avatar_entry.get()
        self.app_context.data_manager.save_plugin_data("settings", settings_data)
        self.app_context.event_manager.emit("profile_updated")

    def _save_system_settings(self):
        settings_data = self.app_context.data_manager.get_plugin_data("settings")
        settings_data["autostart_enabled"] = self.autostart_switch.get() == 1
        settings_data["tray_minimize_enabled"] = self.tray_switch.get() == 1
        self.app_context.data_manager.save_plugin_data("settings", settings_data)
        self.app_context.system_handler.set_autostart(settings_data["autostart_enabled"])

    def _create_backup(self):
        success, message = self.app_context.backup_service.create_backup()
        messagebox.showinfo("Sukces" if success else "Błąd", message)

    def _restore_backup(self):
        filepath = filedialog.askopenfilename(title="Wybierz plik backupu", initialdir="backups", filetypes=[("Pliki JSON", "*.json")])
        if not filepath: return
        if messagebox.askyesno("Potwierdzenie", "Przywrócenie backupu nadpisze aktualną konfigurację. Kontynuować?"):
            success, message = self.app_context.backup_service.restore_from_backup(filepath)
            messagebox.showinfo("Sukces" if success else "Błąd", message)

    def _connect_to_drive(self):
        self._update_cloud_status_ui("Otwieranie przeglądarki...")
        self.app_context.cloud_service.authenticate_async()

    def _update_cloud_status_thread_safe(self, status):
        self.after(0, self._update_cloud_status_ui, status)

    def _update_cloud_status_ui(self, status):
        self.cloud_status_label.configure(text=f"Status: {status}")
        if "Połączono" in status:
            self.upload_button.configure(state="normal")
            self.download_button.configure(state="normal")
        elif "Błąd" in status or "Niepołączono" in status:
            self.upload_button.configure(state="disabled")
            self.download_button.configure(state="disabled")

    def _upload_to_drive(self):
        self.app_context.cloud_service.upload_database_async()

    def _download_from_drive(self):
        if messagebox.askyesno("Potwierdzenie", "Pobranie danych z chmury nadpisze Twoje lokalne zmiany. Kontynuować?"):
            self.app_context.cloud_service.download_database_async()

    def _save_integrations_settings(self):
        settings_data = self.app_context.data_manager.get_plugin_data("settings")
        settings_data["discord_rpc_enabled"] = self.discord_switch.get() == 1
        self.app_context.data_manager.save_plugin_data("settings", settings_data)
        print("Zapisano ustawienia integracji z Discordem.")

    def _change_theme(self, new_theme_name):
        self.app_context.theme_service.apply_theme(new_theme_name)

    def _open_theme_editor(self):
        if self.editor_window is None or not self.editor_window.winfo_exists():
            self.editor_window = ThemeEditorWindow(self, self.app_context, on_save_callback=self.refresh_view)
        else:
            self.editor_window.focus()