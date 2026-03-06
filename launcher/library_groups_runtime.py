import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from launcher.utils import save_config


def delete_group(self):
    selected_item = self.filter_or_group_var.get()

    if selected_item in self.groups:
        group_to_delete = selected_item
        confirm = messagebox.askyesno(
            "Usuń Grupę Statyczną",
            f"Czy na pewno chcesz usunąć grupę '{group_to_delete}'?",
        )
        if confirm:
            del self.groups[group_to_delete]
            save_config(self.config)
            self.filter_or_group_var.set("Wszystkie Gry")
            self.update_filter_group_menu()
            self.reset_and_update_grid()
            messagebox.showinfo(
                "Sukces", f"Grupa statyczna '{group_to_delete}' została usunięta."
            )
    elif selected_item == "Wszystkie Gry":
        messagebox.showwarning("Błąd", "Nie można usunąć grupy 'Wszystkie Gry'.")
    elif selected_item in self.config.get("saved_filters", {}):
        messagebox.showwarning(
            "Błąd",
            f"'{selected_item}' to filtr zaawansowany, a nie grupa statyczna. Użyj 'Zarządzaj Filtrami'.",
        )
    else:
        messagebox.showwarning(
            "Błąd",
            f"Nie można usunąć wybranego elementu: '{selected_item}'. Wybierz grupę statyczną z listy.",
        )


def add_group(self):
    group_name = simpledialog.askstring(
        "Dodaj Grupę Statyczną", "Podaj nazwę nowej grupy:"
    )
    if group_name:
        if group_name == "Wszystkie Gry" or group_name.startswith("---"):
            messagebox.showwarning("Błąd", f"Nazwa '{group_name}' jest zarezerwowana.")
            return
        if group_name in self.groups:
            messagebox.showwarning("Błąd", "Grupa statyczna o tej nazwie już istnieje.")
        elif group_name in self.config.get("saved_filters", {}):
            messagebox.showwarning(
                "Błąd", f"Istnieje już filtr zaawansowany o nazwie '{group_name}'."
            )
        else:
            self.groups[group_name] = []
            save_config(self.config)
            self.update_filter_group_menu()
            messagebox.showinfo("Sukces", f"Grupa statyczna '{group_name}' została dodana.")
            self.filter_or_group_var.set(group_name)
            self.reset_and_update_grid()


def update_filter_group_menu(self):
    """Tworzy lub aktualizuje OptionMenu z grupami statycznymi i filtrami zaawansowanymi."""
    if hasattr(self, "filter_group_menu") and self.filter_group_menu.winfo_exists():
        self.filter_group_menu.destroy()

    options = ["Wszystkie Gry"]
    static_groups = sorted(list(self.groups.keys()))
    if static_groups:
        options.append("--- Grupy Statyczne ---")
        options.extend(static_groups)

    saved_filters = sorted(list(self.config.get("saved_filters", {}).keys()))
    if saved_filters:
        options.append("--- Filtry Zaawansowane ---")
        options.extend(saved_filters)

    current_selection = self.filter_or_group_var.get()
    if current_selection not in options:
        self.filter_or_group_var.set("Wszystkie Gry")

    self.filter_group_menu = ttk.OptionMenu(
        self.header,
        self.filter_or_group_var,
        self.filter_or_group_var.get(),
        *options,
        command=self._on_filter_or_group_selected,
    )
    self.filter_group_menu.grid(row=0, column=3, padx=10, pady=10, sticky="ew")

    try:
        menu_widget = self.filter_group_menu["menu"]
        for i, option in enumerate(options):
            if option.startswith("---"):
                menu_widget.entryconfigure(i, state="disabled")
    except tk.TclError:
        pass


def _on_filter_or_group_selected(self, selected_value):
    if selected_value.startswith("---"):
        pass
    self.reset_and_update_grid()


__all__ = [
    "delete_group",
    "add_group",
    "update_filter_group_menu",
    "_on_filter_or_group_selected",
]
