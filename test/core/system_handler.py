# core/system_handler.py
import os
import sys
import threading
from PIL import Image

# Te biblioteki działają głównie na Windows
try:
    import winshell
    from pystray import Icon as TrayIcon, MenuItem as item
    IS_WINDOWS = True
except ImportError:
    IS_WINDOWS = False

class SystemHandler:
    def __init__(self, app_context):
        self.app_context = app_context
        self.tray_icon = None
        self.tray_thread = None

        if IS_WINDOWS:
            self.startup_folder = winshell.startup()
            # Użyj ścieżki do pythonw.exe, aby unikać okna konsoli przy autostarcie
            self.python_executable = sys.executable.replace("python.exe", "pythonw.exe")
            self.script_path = os.path.abspath(sys.argv[0])
            self.shortcut_path = os.path.join(self.startup_folder, "Game-Launcher.lnk")

    def set_autostart(self, enabled: bool):
        if not IS_WINDOWS:
            print("Autostart jest wspierany tylko w systemie Windows.")
            return

        try:
            if enabled:
                if not os.path.exists(self.shortcut_path):
                    with winshell.shortcut(self.shortcut_path) as shortcut:
                        shortcut.path = self.python_executable
                        shortcut.arguments = f'"{self.script_path}"'
                        shortcut.working_directory = os.path.dirname(self.script_path)
                    print("Dodano skrót do autostartu.")
            else:
                if os.path.exists(self.shortcut_path):
                    os.remove(self.shortcut_path)
                    print("Usunięto skrót z autostartu.")
        except Exception as e:
            print(f"Błąd podczas ustawiania autostartu: {e}")

    def run_in_tray(self, main_window):
        if not IS_WINDOWS: return
        
        main_window.withdraw() # Ukryj główne okno
        
        icon_path = "assets/icons/app_icon.png"
        image = Image.open(icon_path) if os.path.exists(icon_path) else Image.new('RGB', (64, 64))

        menu = (item('Pokaż', lambda: self._show_window(main_window)), item('Zamknij', lambda: self._quit_app(main_window)))
        self.tray_icon = TrayIcon("Game-Launcher", image, "Game-Launcher", menu)
        
        # Uruchomienie ikony w osobnym wątku, aby nie blokować aplikacji
        if self.tray_thread is None or not self.tray_thread.is_alive():
            self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            self.tray_thread.start()
        print("Aplikacja zminimalizowana do zasobnika systemowego.")

    def _show_window(self, main_window):
        if self.tray_icon:
            self.tray_icon.stop()
        main_window.after(0, main_window.deiconify) # Pokaż główne okno
        print("Przywrócono aplikację z zasobnika.")

    def _quit_app(self, main_window):
        if self.tray_icon:
            self.tray_icon.stop()
        
        self.app_context.shutdown_event.set() # <-- 3. USTAW FLAGĘ RÓWNIEŻ TUTAJ

        print("Zamknięto aplikację z poziomu zasobnika.")
        self.app_context.reminder_service.stop()
        main_window.destroy()
        main_window.shutdown()