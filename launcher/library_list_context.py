import logging
import os
import tkinter as tk
from tkinter import messagebox

from launcher.utils import save_config


def _on_list_view_right_click(self, event):
    """Wyświetla menu kontekstowe dla widoku listy (z ikonami)."""
    item_iid = self.list_view_tree.identify_row(event.y)
    if not item_iid:
        return

    if item_iid not in self.list_view_tree.selection():
        self.list_view_tree.selection_set(item_iid)
    self.list_view_tree.focus(item_iid)

    if item_iid in self.games:
        game_name = item_iid
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
                    command=lambda: self.launch_game(game_name),
                    image=play_icon,
                    compound=tk.LEFT,
                )
            else:
                launch_menu = tk.Menu(
                    context_menu,
                    tearoff=0,
                    background="#2e2e2e",
                    foreground="white",
                )
                context_menu.add_cascade(
                    label="Uruchom z profilem...",
                    menu=launch_menu,
                    image=play_icon,
                    compound=tk.LEFT,
                )
                for profile in profiles:
                    profile_name = profile.get("name", "Brak nazwy")
                    cmd = lambda p=profile: self.launch_game(game_name, profile=p)
                    launch_menu.add_command(label=profile_name, command=cmd)
            context_menu.add_separator()
        else:
            context_menu.add_command(
                label="Uruchom",
                command=lambda: self.launch_game(game_name),
                image=play_icon,
                compound=tk.LEFT,
            )
            context_menu.add_separator()

        context_menu.add_command(
            label="Edytuj dane",
            command=lambda: self.edit_game(game_name),
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
            command=lambda: self.manage_saves(game_name),
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
                cmd = lambda gn=game_name, grp=group_name: self._add_to_group_from_menu(
                    gn, grp
                )
                group_menu_add.add_command(label=group_name, command=cmd, state=state)
                if not is_in_group:
                    can_add_to_any = True
            if not can_add_to_any:
                context_menu.entryconfig("Dodaj do grupy...", state=tk.DISABLED)

            groups_game_is_in = [grp for grp, games in self.groups.items() if game_name in games]
            if groups_game_is_in:
                remove_group_menu = tk.Menu(
                    context_menu,
                    tearoff=0,
                    background="#2e2e2e",
                    foreground="white",
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

        context_menu.add_command(
            label="Resetuj statystyki",
            command=lambda: self.reset_stats(game_name),
            image=self._button_icons.get("reset"),
            compound=tk.LEFT,
        )
        context_menu.add_separator()
        context_menu.add_command(
            label="Usuń grę",
            command=lambda: self.delete_game(game_name),
            image=self._button_icons.get("delete"),
            compound=tk.LEFT,
        )

        context_menu.post(event.x_root, event.y_root)
    else:
        logging.warning(f"Kliknięto prawym na nieznany element listy: {item_iid}")


def _add_to_group_from_menu(self, game_name, group_name):
    """Dodaje grę do grupy wybranej z menu kontekstowego."""
    if game_name not in self.groups[group_name]:
        self.groups[group_name].append(game_name)
        save_config(self.config)
        messagebox.showinfo(
            "Sukces", f"Gra '{game_name}' została dodana do grupy '{group_name}'."
        )
    else:
        messagebox.showwarning(
            "Błąd", f"Gra '{game_name}' już znajduje się w grupie '{group_name}'."
        )


__all__ = ["_on_list_view_right_click", "_add_to_group_from_menu"]
