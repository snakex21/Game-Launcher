from .shared_imports import tk, os, logging
from .launcher import GameLauncher


def main() -> GameLauncher:
    root = tk.Tk()
    try:
        icon_path = "icon.ico"
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
        else:
            logging.warning("Plik ikony '%s' nie został znaleziony.", icon_path)
    except tk.TclError as error:
        logging.error("Nie można ustawić ikony okna: %s", error)
    except Exception as error:
        logging.error("Nieoczekiwany błąd podczas ustawiania ikony: %s", error)

    app = GameLauncher(root)
    root.mainloop()
    return app


__all__ = ["main", "GameLauncher"]
