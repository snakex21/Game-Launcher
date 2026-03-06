import logging
import os
import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageDraw, ImageFont, ImageTk

from launcher.utils import load_photoimage_from_path, save_config
from ui.components import ToolTip


def _populate_game_tile(self, tile_frame, game_name, game_data, tile_width, tile_height):
    """Wypełnia ramkę o STAŁYM rozmiarze zawartością kafelka gry."""
    logging.debug(f"Populating tile for {game_name} with size {tile_width}x{tile_height}")

    target_image_height = int(tile_height * 0.60)
    target_image_size = (tile_width, target_image_height)
    _target_info_height = int(tile_height * 0.18)

    _original_cover_path = self.games[game_name].get("cover_image")
    cover_path_to_load = self._ensure_cover(game_name, self.games[game_name], target_image_size)

    photo = load_photoimage_from_path(cover_path_to_load, target_image_size)

    for widget in tile_frame.winfo_children():
        widget.destroy()

    tile_frame.rowconfigure(0, weight=0)
    tile_frame.rowconfigure(1, weight=0)
    tile_frame.rowconfigure(2, weight=1)
    tile_frame.columnconfigure(0, weight=1)

    cover_label = ttk.Label(tile_frame, anchor=tk.CENTER)
    if photo:
        cover_label.config(image=photo)
        cover_label.image = photo
    else:
        try:
            placeholder_img = Image.new("RGB", target_image_size, color="#555555")
            draw = ImageDraw.Draw(placeholder_img)
            try:
                font = ImageFont.truetype("arial.ttf", 12)
            except IOError:
                font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), "Brak\nOkładki", font=font)
            text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text(
                ((target_image_size[0] - text_w) // 2, (target_image_size[1] - text_h) // 2),
                "Brak\nOkładki",
                fill="white",
                font=font,
                align="center",
            )
            placeholder_photo = ImageTk.PhotoImage(placeholder_img)
            cover_label.config(image=placeholder_photo)
            cover_label.image = placeholder_photo
        except Exception as e_placeholder:
            logging.error(f"Nie można nawet utworzyć placeholdera obrazu: {e_placeholder}")
            cover_label.config(text="Brak\nOkładki", image="")

    cover_label.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 0))
    cover_label.bind("<Button-1>", lambda event, gn=game_name: self.show_game_details(gn))
    tile_frame.bind(
        "<Button-3>",
        lambda event, gn=game_name: self._show_tile_context_menu(event, gn),
    )
    cover_label.bind(
        "<Button-3>",
        lambda event, gn=game_name: self._show_tile_context_menu(event, gn),
    )

    target_info_height = 60
    info_font_size = 9
    info_font = ("Segoe UI", info_font_size)

    info_frame = ttk.Frame(tile_frame, height=target_info_height)
    info_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=2)
    info_frame.columnconfigure(0, weight=1)
    info_frame.rowconfigure(0, weight=1)

    completion = game_data.get("completion", 0)
    game_version = game_data.get("version", "")
    game_tags = ", ".join(game_data.get("tags", []))

    game_type = game_data.get("game_type", "pc")
    type_info = ""
    if game_type == "emulator":
        emulator_name = game_data.get("emulator_name", "Nieznany Emu")
        type_info = f" [{emulator_name}]"
    elif game_type == "pc":
        type_info = " [PC]"

    label_text = f"{game_name}{type_info}\n"

    details = []
    details.append(f"Czas: {self.format_play_time(game_data.get('play_time', 0))}")
    details.append(f"Ukoń.: {completion}%")
    if game_version:
        details.append(f"Ver: {game_version}")
    if game_tags:
        max_tag_len = tile_width // 9
        if len(game_tags) > max_tag_len:
            game_tags = game_tags[:max_tag_len] + "..."
        details.append(f"Tagi: {game_tags}")
    label_text += " | ".join(details)

    name_label = ttk.Label(
        info_frame,
        text=label_text,
        anchor="nw",
        wraplength=tile_width - 15,
        justify=tk.LEFT,
        font=info_font,
    )
    name_label.grid(sticky="nsew")
    name_label.bind(
        "<Button-3>",
        lambda event, gn=game_name: self._show_tile_context_menu(event, gn),
    )
    info_frame.bind(
        "<Button-3>",
        lambda event, gn=game_name: self._show_tile_context_menu(event, gn),
    )

    key_buttons_frame = ttk.Frame(tile_frame)
    key_buttons_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=(0, 5))
    key_buttons_frame.columnconfigure((0, 1), weight=1)

    launch_area_frame = ttk.Frame(key_buttons_frame)
    launch_area_frame.grid(row=0, column=0, padx=(0, 1), pady=1, sticky="nsew")

    profiles = game_data.get("launch_profiles", [])
    if not profiles:
        profiles = [{"name": "Default", "exe_path": None, "arguments": ""}]
    default_profile = profiles[0]

    if len(profiles) == 1 and default_profile.get("name", "").lower() == "default":
        tooltip_text_base = "Uruchom"
    else:
        tooltip_text_base = f"Uruchom: {default_profile.get('name', 'Profil')}"

    if self.is_game_running(game_name):
        button_image = self._button_icons.get("stop_btn")
        button_style = "Red.TButton"
        button_command = lambda: self.close_game(game_name)
        tooltip_text = "Zamknij"
    else:
        button_image = self._button_icons.get("play_btn")
        button_style = "Green.TButton"
        button_command = lambda p=default_profile: self.launch_game(game_name, profile=p)
        tooltip_text = tooltip_text_base

    if button_image:
        launch_btn = ttk.Button(
            launch_area_frame,
            image=button_image,
            style=button_style,
            command=button_command,
        )
        launch_btn.image = button_image
        launch_btn.tooltip = ToolTip(launch_btn, tooltip_text)
    else:
        fallback_text = (
            "Zamknij" if self.is_game_running(game_name) else tooltip_text_base.split(":")[0]
        )
        launch_btn = ttk.Button(
            launch_area_frame,
            text=fallback_text,
            style=button_style,
            command=button_command,
        )
        launch_btn.tooltip = ToolTip(launch_btn, tooltip_text)

    self._launch_buttons[game_name] = launch_btn

    if len(profiles) > 1:
        launch_btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        profile_menu_icon = self._button_icons.get("profile_menu_btn")
        if profile_menu_icon:
            profile_menu_btn = ttk.Menubutton(
                launch_area_frame, image=profile_menu_icon, style="Toolbutton"
            )
            profile_menu_btn.image = profile_menu_icon
            ToolTip(profile_menu_btn, "Wybierz profil")
        else:
            profile_menu_btn = ttk.Menubutton(
                launch_area_frame, text="▼", width=2, style="Toolbutton"
            )
        profile_menu_btn.pack(side=tk.LEFT, fill=tk.Y)
        self._launch_buttons[f"{game_name}_profile_menu"] = profile_menu_btn
        profile_menu = tk.Menu(
            profile_menu_btn, tearoff=0, background="#2e2e2e", foreground="white"
        )
        profile_menu_btn["menu"] = profile_menu
        for profile in profiles:
            profile_name = profile.get("name", "Brak Nazwy")
            cmd = lambda p=profile, gn=game_name: self.launch_game(gn, profile=p)
            profile_menu.add_command(label=profile_name, command=cmd)
    else:
        launch_btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    save_icon_tk = self._button_icons.get("save_btn")
    if save_icon_tk:
        saves_btn = ttk.Button(
            key_buttons_frame,
            image=save_icon_tk,
            style="Toolbutton",
            command=lambda gn=game_name: self.manage_saves(gn),
        )
        saves_btn.image = save_icon_tk
        ToolTip(saves_btn, "Zarządzaj Zapisami")
    else:
        saves_btn = ttk.Button(
            key_buttons_frame,
            text="Zapisy",
            style="Tile.TButton",
            command=lambda gn=game_name: self.manage_saves(gn),
        )
    saves_btn.grid(row=0, column=1, padx=(1, 0), pady=1, sticky="nsew")

    info_frame.grid_propagate(False)


def _show_tile_context_menu(self, event, game_name):
    """Wyświetla menu kontekstowe dla kafelka gry (z ikonami i opcją Uruchom)."""
    if game_name not in self.games:
        return

    game_data = self.games[game_name]
    save_path = game_data.get("save_path")
    is_save_path_valid = save_path and os.path.isdir(save_path)

    context_menu = tk.Menu(self.root, tearoff=0, background="#2e2e2e", foreground="white")

    profiles = game_data.get("launch_profiles", [])
    play_icon = self._button_icons.get("play_menu")

    if profiles:
        if len(profiles) == 1 and profiles[0].get("name", "").lower() == "default":
            context_menu.add_command(
                label="Uruchom",
                command=lambda gn=game_name: self.launch_game(gn),
                image=play_icon,
                compound=tk.LEFT,
            )
        else:
            launch_menu = tk.Menu(
                context_menu, tearoff=0, background="#2e2e2e", foreground="white"
            )
            context_menu.add_cascade(
                label="Uruchom z profilem...",
                menu=launch_menu,
                image=play_icon,
                compound=tk.LEFT,
            )
            for profile in profiles:
                profile_name = profile.get("name", "Brak nazwy")
                cmd = lambda p=profile, gn=game_name: self.launch_game(gn, profile=p)
                launch_menu.add_command(label=profile_name, command=cmd)
    else:
        context_menu.add_command(
            label="Uruchom",
            command=lambda gn=game_name: self.launch_game(gn),
            image=play_icon,
            compound=tk.LEFT,
        )
    context_menu.add_separator()

    context_menu.add_command(
        label="Edytuj dane",
        command=lambda gn=game_name: self.edit_game(gn),
        image=self._button_icons.get("edit"),
        compound=tk.LEFT,
    )
    context_menu.add_command(
        label="Otwórz folder z zapisami",
        command=lambda p=save_path: self._open_folder(p),
        state=tk.NORMAL if is_save_path_valid else tk.DISABLED,
        image=self._button_icons.get("folder_open"),
        compound=tk.LEFT,
    )
    context_menu.add_command(
        label="Zarządzaj zapisami",
        command=lambda gn=game_name: self.manage_saves(gn),
        image=self._button_icons.get("save_disk"),
        compound=tk.LEFT,
    )
    context_menu.add_command(
        label="Pokaż Checklistę",
        command=lambda gn=game_name: self._show_game_details_and_select_tab(gn, "Checklista"),
        image=self._button_icons.get("checklist"),
        compound=tk.LEFT,
    )
    context_menu.add_command(
        label="Pokaż Screenshoty",
        command=lambda gn=game_name: self._show_game_details_and_select_tab(gn, "Screenshoty"),
        image=self._button_icons.get("screenshot"),
        compound=tk.LEFT,
    )
    if hasattr(self, "extended_mod_manager"):
        context_menu.add_command(
            label="Mody",
            command=lambda gn=game_name: self._show_mods_for_game_from_context(gn),
            image=self._button_icons.get("mods"),
            compound=tk.LEFT,
        )

    context_menu.add_separator()
    context_menu.add_command(
        label="Resetuj statystyki",
        command=lambda gn=game_name: self.reset_stats(gn),
        image=self._button_icons.get("reset"),
        compound=tk.LEFT,
    )

    if self.groups:
        group_menu_add = tk.Menu(
            context_menu, tearoff=0, background="#2e2e2e", foreground="white"
        )
        context_menu.add_cascade(
            label="Dodaj do grupy...",
            menu=group_menu_add,
            image=self._button_icons.get("group_add"),
            compound=tk.LEFT,
        )
        can_add_to_any = False
        for group_name in sorted(self.groups.keys()):
            is_in_group = game_name in self.groups.get(group_name, [])
            state = tk.DISABLED if is_in_group else tk.NORMAL
            cmd = lambda gn=game_name, grp=group_name: self._add_to_group_from_menu(gn, grp)
            group_menu_add.add_command(label=group_name, command=cmd, state=state)
            if not is_in_group:
                can_add_to_any = True
        if not can_add_to_any:
            context_menu.entryconfig("Dodaj do grupy...", state=tk.DISABLED)

        groups_game_is_in = [grp for grp, games in self.groups.items() if game_name in games]
        if groups_game_is_in:
            remove_group_menu = tk.Menu(
                context_menu, tearoff=0, background="#2e2e2e", foreground="white"
            )
            context_menu.add_cascade(
                label="Usuń z grupy...",
                menu=remove_group_menu,
                image=self._button_icons.get("group_remove"),
                compound=tk.LEFT,
            )
            for group_name in sorted(groups_game_is_in):
                cmd = lambda gn=game_name, grp=group_name: self._remove_from_group_from_menu(
                    gn, grp
                )
                remove_group_menu.add_command(label=group_name, command=cmd)

    context_menu.add_separator()
    context_menu.add_command(
        label="Usuń grę",
        command=lambda gn=game_name: self.delete_game(gn),
        image=self._button_icons.get("delete"),
        compound=tk.LEFT,
    )

    context_menu.post(event.x_root, event.y_root)


def _remove_from_group_from_menu(self, game_name, group_name):
    """Usuwa grę z wybranej grupy (wywołane z menu kontekstowego)."""
    if group_name in self.groups and game_name in self.groups[group_name]:
        self.groups[group_name].remove(game_name)
        save_config(self.config)
        messagebox.showinfo("Sukces", f"Gra '{game_name}' została usunięta z grupy '{group_name}'.")
        if self.group_var.get() == group_name or self.group_var.get() == "Wszystkie Gry":
            self.reset_and_update_grid()
    else:
        messagebox.showwarning("Błąd", f"Gra '{game_name}' nie znajduje się w grupie '{group_name}'.")
        logging.warning(
            f"Błąd logiki: próba usunięcia gry '{game_name}' z grupy '{group_name}', w której jej nie ma (menu kontekstowe)."
        )


def _show_mods_for_game_from_context(self, game_name):
    """Pokazuje menedżera modów i wybiera grę."""
    self.show_mod_manager()
    self.root.after(100, lambda: self.extended_mod_manager.select_game_in_manager(game_name))


def _clear_launch_button_ref(self, game_name):
    """Usuwa referencję do przycisku Uruchom/Zamknij, gdy kafelek jest niszczony."""
    if game_name in self._launch_buttons:
        del self._launch_buttons[game_name]


__all__ = [
    "_populate_game_tile",
    "_show_tile_context_menu",
    "_remove_from_group_from_menu",
    "_show_mods_for_game_from_context",
    "_clear_launch_button_ref",
]
