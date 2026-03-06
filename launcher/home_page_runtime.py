import logging
import os
import random
from tkinter import ttk

from PIL import Image, ImageDraw, ImageFont, ImageTk

from launcher.utils import RESAMPLING


def create_home_page(self):
    """Buduje stronę startową i podpina automatyczne skalowanie."""
    for w in self.home_frame.winfo_children():
        w.destroy()

    head = ttk.Frame(self.home_frame)
    head.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
    head.columnconfigure(0, weight=0)
    head.columnconfigure(1, weight=1)

    avatar_s = self.local_settings.get("avatar_display_size", 48)
    avatar_size_home = (avatar_s, avatar_s)
    avatar_label = ttk.Label(
        head, width=avatar_size_home[0] // 8 if avatar_size_home[0] >= 48 else 6
    )
    avatar_label.grid(row=0, column=0, rowspan=3, padx=(5, 10), pady=5, sticky="w")

    avatar_path = self.user.get("avatar")
    if avatar_path and os.path.exists(avatar_path):
        try:
            with Image.open(avatar_path) as img:
                img.thumbnail(avatar_size_home, RESAMPLING)
                avatar_photo = ImageTk.PhotoImage(img)
                avatar_label.config(image=avatar_photo)
                avatar_label.image = avatar_photo
        except Exception as e:
            logging.error(f"... {e}")
            avatar_label.config(text="Błąd", font=("Segoe UI", 7))
    else:
        try:
            default_avatar = Image.new("RGB", avatar_size_home, color="#444444")
            draw = ImageDraw.Draw(default_avatar)
            username_initial = (
                self.user.get("username", "G")[0].upper()
                if self.user.get("username")
                else "G"
            )
            try:
                font = ImageFont.truetype("arialbd.ttf", avatar_size_home[0] // 2)
            except IOError:
                font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), username_initial, font=font)
            text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text(
                ((avatar_size_home[0] - text_w) // 2, (avatar_size_home[1] - text_h) // 2 - 2),
                username_initial,
                fill="white",
                font=font,
            )
            default_avatar_photo = ImageTk.PhotoImage(default_avatar)
            avatar_label.config(image=default_avatar_photo)
            avatar_label.image = default_avatar_photo
        except Exception as e_def:
            logging.error(f"Nie można stworzyć domyślnego awatara: {e_def}")
            avatar_label.config(text="Brak\navatara", font=("Segoe UI", 7))

    greetings = [
        f"Witaj, {self.user.get('username', 'Graczu')}!",
        f"Co dzisiaj gramy, {self.user.get('username', 'Graczu')}?",
        f"Jak się masz, {self.user.get('username', 'Graczu')}?",
        f"Miło Cię widzieć, {self.user.get('username', 'Graczu')}!",
        f"Gotowy na nowe wyzwania, {self.user.get('username', 'Graczu')}?",
    ]
    ttk.Label(head, text=random.choice(greetings), font=("Helvetica", 14)).grid(
        row=0, column=1, sticky="w", pady=10
    )

    self.launcher_usage_label_home = ttk.Label(
        head, text="Czas sesji: 00:00:00", font=("Segoe UI", 9), anchor="w"
    )
    self.launcher_usage_label_home.grid(row=1, column=1, sticky="w", pady=(0, 0))

    self.total_launcher_usage_label_home = ttk.Label(
        head, text="Łączny czas: Ładowanie...", font=("Segoe UI", 9), anchor="w"
    )
    self.total_launcher_usage_label_home.grid(row=2, column=1, sticky="w", pady=(0, 5))

    body = ttk.Frame(self.home_frame)
    body.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
    self.home_frame.rowconfigure(1, weight=1)
    self.home_frame.columnconfigure(0, weight=1)
    body.columnconfigure((0, 1), weight=1)
    body.rowconfigure((0, 1), weight=1)
    self.recent_frame = ttk.LabelFrame(body, text="Ostatnio grane")
    self.recent_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
    self.random_frame = ttk.LabelFrame(body, text="Losowe gry")
    self.random_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
    self.stats_frame = ttk.Frame(body)
    self.stats_frame.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=5, pady=5)
    self.stats_frame.columnconfigure(0, weight=1)
    self.stats_frame.rowconfigure((0, 1, 2), weight=1)
    self.create_time_stats(self.stats_frame, row=0, column=0)
    self.create_statistics(self.stats_frame)
    self.home_frame.bind("<Configure>", self._update_home_lists)
    self._update_home_lists()
    self._update_current_session_time_display()
    self._update_launcher_usage_display()


__all__ = ["create_home_page"]
