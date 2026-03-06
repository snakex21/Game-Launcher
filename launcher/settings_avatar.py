import logging
import os

from PIL import Image, ImageDraw, ImageFont, ImageTk

from launcher.utils import RESAMPLING


def _load_and_display_settings_avatar(self, size_tuple=None):
    """Ładuje i wyświetla awatar w sekcji Ustawienia."""
    if not hasattr(self, "settings_avatar_label") or not self.settings_avatar_label.winfo_exists():
        return

    if size_tuple is None:
        s = self.local_settings.get("avatar_display_size", 48)
        size_tuple = (s, s)

    avatar_path = self.user.get("avatar")
    loaded_photo = None

    if avatar_path and os.path.exists(avatar_path):
        try:
            with Image.open(avatar_path) as img:
                img.thumbnail(size_tuple, RESAMPLING)
                loaded_photo = ImageTk.PhotoImage(img)
        except Exception as e:
            logging.error(f"Nie można załadować awatara (Ustawienia) '{avatar_path}': {e}")
            loaded_photo = None

    if loaded_photo:
        self.settings_avatar_label.config(image=loaded_photo, text="")
        self.settings_avatar_label.image = loaded_photo
    else:
        try:
            default_avatar = Image.new("RGB", size_tuple, color="#444444")
            draw = ImageDraw.Draw(default_avatar)
            username_initial = (
                self.user.get("username", "G")[0].upper()
                if self.user.get("username")
                else "G"
            )
            try:
                font = ImageFont.truetype("arialbd.ttf", size_tuple[0] // 2)
            except IOError:
                font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), username_initial, font=font)
            text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text(
                ((size_tuple[0] - text_w) // 2, (size_tuple[1] - text_h) // 2 - 2),
                username_initial,
                fill="white",
                font=font,
            )
            default_photo = ImageTk.PhotoImage(default_avatar)
            self.settings_avatar_label.config(image=default_photo, text="")
            self.settings_avatar_label.image = default_photo
        except Exception as e_def:
            logging.error(f"Nie można stworzyć domyślnego awatara (Ustawienia): {e_def}")
            self.settings_avatar_label.config(image=None, text="")


__all__ = ["_load_and_display_settings_avatar"]
