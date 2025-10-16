# ui/main_window.py
import customtkinter as ctk
from PIL import Image
import os
from plugins.settings.user_setup_window import UserSetupWindow

class MainWindow(ctk.CTk):
    def __init__(self, app_context, plugins):
        super().__init__()
        self.app_context = app_context

        # --- KLUCZOWA POPRAWKA ---
        # Wczytaj i zastosuj ostatnio używany motyw PRZED zbudowaniem reszty UI.
        # To rozwiązuje problem "zawsze białego motywu" przy starcie.
        settings_data = self.app_context.data_manager.get_plugin_data("settings")
        last_theme = settings_data.get("last_used_theme", "System") # Użyj "System" jako bezpiecznego domyślnego
        self.app_context.theme_service.apply_theme(last_theme)
        # --- KONIEC POPRAWKI ---

        self.plugins = plugins
        self.views = {}

        # Subskrypcje zdarzeń
        self.app_context.event_manager.subscribe("setting_changed", self.on_setting_changed)
        self.app_context.event_manager.subscribe("reminder_triggered", self._show_reminder_notification)
        self.app_context.event_manager.subscribe("profile_updated", self._update_profile_display)
        self.app_context.event_manager.subscribe("song_changed", self._show_song_overlay)
        self.overlay_window = None # Do śledzenia okna nakładki

        self.title("Game-Launcher")
        self.geometry("1280x720")
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Panel boczny
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsw")
        self.sidebar_frame.grid_rowconfigure(1, weight=1)

        # Panel profilu
        self.profile_frame = ctk.CTkFrame(self.sidebar_frame, height=80, fg_color="transparent")
        self.profile_frame.grid(row=0, column=0, sticky="new", padx=10, pady=10)
        self.profile_frame.grid_columnconfigure(1, weight=1)
        self.avatar_label = ctk.CTkLabel(self.profile_frame, text="", width=64, height=64, fg_color="gray30", corner_radius=32)
        self.avatar_label.grid(row=0, column=0, rowspan=2)
        self.username_label = ctk.CTkLabel(self.profile_frame, text="...", font=("Roboto", 16, "bold"), anchor="sw")
        self.username_label.grid(row=0, column=1, sticky="nsew", padx=10)
        
        plugins.sort(key=lambda p: p.get_name() != "Strona Główna")
        
        # Kontener na przyciski
        self.buttons_container = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.buttons_container.grid(row=1, column=0, sticky="new")
        for plugin in self.plugins:
            button = ctk.CTkButton(self.buttons_container, text=plugin.get_name(), command=lambda p=plugin: self.switch_view(p))
            button.pack(pady=5, padx=10, fill="x")

        # Kontener na widoki
        self.main_view_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_view_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        if self.plugins:
            self.switch_view(self.plugins[0])

        self._update_profile_display()
        self.after(100, self._check_initial_setup)
        
        # Ustawienie obsługi zamykania
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def switch_view(self, plugin):
        plugin_name = plugin.get_name()
        for view in self.views.values():
            view.pack_forget()
        if plugin_name not in self.views:
            view = plugin.create_view(self.main_view_frame)
            self.views[plugin_name] = view
        
        plugin.on_view_enter(self.views[plugin_name])
        self.views[plugin_name].pack(fill="both", expand=True)

    def on_setting_changed(self, key, value):
        if key == "theme":
            ctk.set_appearance_mode(value)
            # Musimy też poinformować wykres w statystykach, że ma się przerysować
            self.app_context.event_manager.emit("theme_changed")

    def _show_reminder_notification(self, message):
        notification = ctk.CTkToplevel(self)
        notification.geometry("400x150")
        notification.title("Przypomnienie!")
        notification.transient(self)
        notification.grab_set()
        notification.after(250, lambda: notification.lift())

        ctk.CTkLabel(notification, text=message, font=("Roboto", 16), wraplength=380).pack(expand=True, padx=20, pady=10)
        ctk.CTkButton(notification, text="OK", command=notification.destroy).pack(pady=10)

    def _update_profile_display(self):
        settings_data = self.app_context.data_manager.get_plugin_data("settings")
        self.username_label.configure(text=settings_data.get("username", "Gość"))
        
        avatar_path = settings_data.get("avatar_path")
        if avatar_path and os.path.exists(avatar_path):
            try:
                img = ctk.CTkImage(Image.open(avatar_path), size=(64, 64))
                self.avatar_label.configure(image=img, text="")
            except Exception:
                self.avatar_label.configure(image=None, text="Błąd")
        else:
            self.avatar_label.configure(image=None, text="")

    def _check_initial_setup(self):
        settings_data = self.app_context.data_manager.get_plugin_data("settings")
        if not settings_data.get("username"):
            UserSetupWindow(self, self.app_context, on_save_callback=self._update_profile_display)

    def _on_closing(self):
        """Obsługuje zamykanie okna w zależności od ustawień."""
        settings_data = self.app_context.data_manager.get_plugin_data("settings")
        if settings_data.get("tray_minimize_enabled", False):
            self.app_context.system_handler.run_in_tray(self)
        else:
            self.shutdown() # Użyj nowej, bezpiecznej procedury

    def shutdown(self):
        """Centralna, bezpieczna procedura zamykania aplikacji."""
        print("Rozpoczęto procedurę bezpiecznego zamykania...")
        # Krok 1: Ustaw globalną flagę, aby wszystkie wątki natychmiast przestały wywoływać UI
        self.app_context.shutdown_event.set()
        
        # Krok 2: Zatrzymaj wszystkie serwisy działające w tle
        self.app_context.reminder_service.stop()
        self.app_context.discord_service.shutdown()
        if self.app_context.system_handler.tray_icon:
            self.app_context.system_handler.tray_icon.stop()
        
        # Krok 3: Dopiero teraz, gdy wszystko jest uciszone, zniszcz okno
        self.destroy()
        print("Aplikacja zamknięta.")

    # --- NOWA LOGIKA NAKŁADKI ---
    def _show_song_overlay(self, song_title):
        if self.overlay_window and self.overlay_window.winfo_exists():
            self.overlay_window.destroy()

        self.overlay_window = ctk.CTkToplevel(self)
        overlay = self.overlay_window
        overlay.overrideredirect(True) # Usuń ramki okna
        overlay.attributes("-alpha", 0.9) # Półprzezroczystość
        overlay.attributes("-topmost", True) # Zawsze na wierzchu

        label = ctk.CTkLabel(overlay, text=f"♫  {song_title.rsplit('.', 1)[0]}", font=("Roboto", 14), corner_radius=10, fg_color=("#333333", "#222222"))
        label.pack(ipadx=10, ipady=5, padx=5, pady=5)
        
        # Oblicz pozycję w prawym dolnym rogu ekranu
        overlay.update_idletasks()
        screen_w, screen_h = self.winfo_screenwidth(), self.winfo_screenheight()
        win_w, win_h = overlay.winfo_width(), overlay.winfo_height()
        x, y = screen_w - win_w - 20, screen_h - win_h - 40
        overlay.geometry(f"+{x}+{y}")
        
        # Automatyczne zniknięcie po 3 sekundach
        overlay.after(3000, overlay.destroy)