import logging
import time
import tkinter as tk
from tkinter import messagebox, ttk

from ui.dialogs import ChatServerEditorDialog
from launcher.config_store import save_local_settings

def _get_active_server_data(self) -> dict | None:
        """Zwraca słownik danych dla aktywnego serwera lub None."""
        if self.active_chat_server_id and self.chat_servers_list:
            for server_data in self.chat_servers_list:
                if server_data.get("id") == self.active_chat_server_id:
                    return server_data
        elif self.chat_servers_list:
            self.active_chat_server_id = self.chat_servers_list[0].get("id")
            logging.warning(
                "Brak active_chat_server_id, ustawiono pierwszy serwer z listy jako aktywny."
            )
            return self.chat_servers_list[0]
        return None

def show_server_selection_page(self):
        """Pokazuje stronę zarządzania serwerami czatu."""
        self._hide_library_components()  # Jeśli jest taka metoda do ukrywania specyficznych rzeczy

        self.server_selection_page_frame.grid()
        self.server_selection_page_frame.tkraise()
        self.current_frame = self.server_selection_page_frame

        if not self._server_selection_initialized:
            logging.info(
                "Tworzenie zawartości strony wyboru serwera czatu po raz pierwszy."
            )
            self._create_server_selection_page_content()
            self._server_selection_initialized = True
        else:
            # Jeśli strona była już inicjalizowana, odśwież listę serwerów
            if hasattr(self, "_load_chat_servers_to_treeview"):
                self._load_chat_servers_to_treeview()

        self.current_section = "Zarządza Serwerami Czatu"  # Lub podobnie
        self._update_discord_status(
            status_type="browsing", activity_details=self.current_section
        )

def _create_server_selection_page_content(self):
        """Tworzy interfejs użytkownika dla strony zarządzania serwerami czatu."""
        for widget in self.server_selection_page_frame.winfo_children():
            widget.destroy()

        self.server_selection_page_frame.columnconfigure(0, weight=1)
        self.server_selection_page_frame.rowconfigure(
            1, weight=1
        )  # Pozwól Treeview rosnąć

        # Nagłówek
        header_frame_servers = ttk.Frame(self.server_selection_page_frame)
        header_frame_servers.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        header_frame_servers.columnconfigure(0, weight=1)  # Wyśrodkowanie etykiety
        ttk.Label(
            header_frame_servers,
            text="Zarządzanie Serwerami Czatu",
            font=("Helvetica", 16, "bold"),
        ).pack(pady=5)

        # Ramka dla Treeview i Scrollbara
        tree_frame_servers = ttk.Frame(self.server_selection_page_frame)
        tree_frame_servers.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        tree_frame_servers.columnconfigure(0, weight=1)
        tree_frame_servers.rowconfigure(0, weight=1)

        columns = ("name", "url", "default")
        self.servers_tree = ttk.Treeview(
            tree_frame_servers, columns=columns, show="headings", selectmode="browse"
        )
        self.servers_tree.heading("name", text="Nazwa Serwera")
        self.servers_tree.heading("url", text="Adres URL")
        self.servers_tree.heading("default", text="Domyślny?")

        self.servers_tree.column("name", width=200, anchor=tk.W)
        self.servers_tree.column("url", width=300, anchor=tk.W)
        self.servers_tree.column("default", width=80, anchor=tk.CENTER, stretch=False)

        servers_scrollbar = ttk.Scrollbar(
            tree_frame_servers, orient="vertical", command=self.servers_tree.yview
        )
        self.servers_tree.configure(yscrollcommand=servers_scrollbar.set)

        self.servers_tree.grid(row=0, column=0, sticky="nsew")
        servers_scrollbar.grid(row=0, column=1, sticky="ns")

        # TODO: Bindowanie <Double-1> do "Połącz" i <Button-3> do menu kontekstowego

        # Ramka na przyciski zarządzania listą serwerów
        buttons_frame_servers = ttk.Frame(self.server_selection_page_frame)
        buttons_frame_servers.grid(row=2, column=0, pady=10, sticky="ew")
        # Wyśrodkowanie przycisków
        buttons_frame_servers.columnconfigure(0, weight=1)
        buttons_frame_servers.columnconfigure(1, weight=1)
        buttons_frame_servers.columnconfigure(2, weight=1)
        buttons_frame_servers.columnconfigure(3, weight=1)  # Dla Połącz

        # Umieść przyciski w wewnętrznej ramce, aby były obok siebie, a potem wyśrodkuj ramkę
        inner_buttons_frame = ttk.Frame(buttons_frame_servers)
        inner_buttons_frame.grid(
            row=0, column=0, columnspan=4
        )  # columnspan, aby ramka mogła się centrować

        ttk.Button(
            inner_buttons_frame,
            text="➕ Dodaj Serwer",
            command=self._add_edit_chat_server_dialog,
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            inner_buttons_frame,
            text="✏️ Edytuj Zaznaczony",
            command=lambda: self._add_edit_chat_server_dialog(edit_mode=True),
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            inner_buttons_frame,
            text="❌ Usuń Zaznaczony",
            command=self._delete_chat_server_dialog,
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            inner_buttons_frame,
            text="🔗 Połącz z Zaznaczonym",
            style="Green.TButton",
            command=self._connect_to_selected_server,
        ).pack(side=tk.LEFT, padx=15)

        # Ramka dla opcji globalnych (np. auto-connect)
        global_options_frame = ttk.Frame(self.server_selection_page_frame)
        global_options_frame.grid(row=3, column=0, pady=(10, 5), padx=10, sticky="w")

        auto_connect_check = ttk.Checkbutton(
            global_options_frame,
            text="Automatycznie łącz z domyślnym serwerem przy starcie launchera",
            variable=self.chat_auto_connect_to_default_var,
            command=self._save_auto_connect_setting,
        )
        auto_connect_check.pack(side=tk.LEFT)

        # Wczytaj dane do Treeview
        self._load_chat_servers_to_treeview()

def _load_chat_servers_to_treeview(self):
        """Wczytuje listę serwerów z self.chat_servers_list do Treeview."""
        if not hasattr(self, "servers_tree") or not self.servers_tree.winfo_exists():
            return

        for item in self.servers_tree.get_children():
            self.servers_tree.delete(item)

        # Sortuj listę serwerów np. alfabetycznie po nazwie, z domyślnym na górze
        sorted_servers = sorted(
            self.chat_servers_list,
            key=lambda s: (not s.get("is_default", False), s.get("name", "").lower()),
        )

        for server_data in sorted_servers:
            server_id = server_data.get("id")
            name = server_data.get("name", "Brak Nazwy")
            url = server_data.get("url", "Brak URL")
            is_default_str = "Tak" if server_data.get("is_default") else "Nie"

            tags = []
            if server_data.get("id") == self.active_chat_server_id:
                tags.append("active_server")  # Tag dla aktywnego serwera

            self.servers_tree.insert(
                "", "end", iid=server_id, values=(name, url, is_default_str), tags=tags
            )

        # Konfiguracja tagu dla aktywnego serwera (np. pogrubienie)
        self.servers_tree.tag_configure(
            "active_server", font=("Segoe UI", 9, "bold"), foreground="lightgreen"
        )

def _add_edit_chat_server_dialog(self, edit_mode=False):
        """Otwiera dialog do dodawania lub edycji serwera czatu."""
        server_data_to_edit = None
        if edit_mode:
            selection = self.servers_tree.selection()
            if not selection:
                messagebox.showwarning(
                    "Brak Zaznaczenia",
                    "Zaznacz serwer, który chcesz edytować.",
                    parent=self.server_selection_page_frame,
                )
                return
            selected_server_id = selection[0]
            server_data_to_edit = next(
                (
                    s
                    for s in self.chat_servers_list
                    if s.get("id") == selected_server_id
                ),
                None,
            )
            if not server_data_to_edit:
                messagebox.showerror(
                    "Błąd",
                    "Nie można znaleźć danych dla wybranego serwera.",
                    parent=self.server_selection_page_frame,
                )
                return

        dialog = ChatServerEditorDialog(
            self.server_selection_page_frame, self, server_data_to_edit
        )

        if dialog.result:
            new_server_data = dialog.result

            if new_server_data.get("is_default"):
                # Jeśli ten serwer jest ustawiany jako domyślny,
                # odznacz wszystkie inne serwery jako domyślne.
                for s_iter in self.chat_servers_list:
                    if s_iter.get("id") != new_server_data.get(
                        "id"
                    ):  # Nie odznaczaj właśnie edytowanego/dodanego
                        s_iter["is_default"] = False
            # Jeśli ten serwer NIE jest ustawiany jako domyślny (is_default = False w new_server_data)
            # a był to JEDYNY domyślny serwer, to musimy ustawić inny jako domyślny (np. pierwszy z listy).
            elif (
                not new_server_data.get("is_default")
                and server_data_to_edit
                and server_data_to_edit.get("is_default")
                and not any(
                    s.get("is_default")
                    for s in self.chat_servers_list
                    if s.get("id") != new_server_data.get("id")
                )
            ):
                # Jeśli odznaczyliśmy jedyny domyślny serwer, i lista nie jest pusta po tej operacji,
                # ustaw pierwszy serwer na liście jako domyślny.
                # Najpierw zaktualizuj/dodaj wpis, potem znajdź nowy domyślny.
                pass  # Logika poniżej to obsłuży

            if edit_mode and server_data_to_edit:
                updated_list_after_edit = False
                for i, server in enumerate(self.chat_servers_list):
                    if server.get("id") == server_data_to_edit.get("id"):
                        self.chat_servers_list[i] = new_server_data
                        updated_list_after_edit = True
                        break
                if (
                    not updated_list_after_edit
                ):  # Na wszelki wypadek, gdyby ID się zmieniło w dialogu (nie powinno)
                    self.chat_servers_list.append(new_server_data)
            else:
                self.chat_servers_list.append(new_server_data)

            if self.chat_servers_list and not any(
                s.get("is_default") for s in self.chat_servers_list
            ):
                self.chat_servers_list[0][
                    "is_default"
                ] = True  # Ustaw pierwszy jako domyślny

            self.local_settings["chat_servers"] = self.chat_servers_list
            save_local_settings(self.local_settings)
            self._load_chat_servers_to_treeview()

def _delete_chat_server_dialog(self):
        """Usuwa zaznaczony serwer czatu z listy."""
        selection = self.servers_tree.selection()
        if not selection:
            messagebox.showwarning(
                "Brak Zaznaczenia",
                "Zaznacz serwer, który chcesz usunąć.",
                parent=self.server_selection_page_frame,
            )
            return
        selected_server_id = selection[0]
        server_to_delete = next(
            (s for s in self.chat_servers_list if s.get("id") == selected_server_id),
            None,
        )

        if not server_to_delete:
            messagebox.showerror(
                "Błąd",
                "Nie można znaleźć wybranego serwera do usunięcia.",
                parent=self.server_selection_page_frame,
            )
            return

        if len(self.chat_servers_list) <= 1:
            messagebox.showwarning(
                "Ostrzeżenie",
                "Nie można usunąć ostatniego serwera z listy.",
                parent=self.server_selection_page_frame,
            )
            return

        if messagebox.askyesno(
            "Potwierdź Usunięcie",
            f"Czy na pewno chcesz usunąć serwer:\n'{server_to_delete.get('name')}' ({server_to_delete.get('url')})?",
            icon="warning",
            parent=self.server_selection_page_frame,
        ):

            self.chat_servers_list = [
                s for s in self.chat_servers_list if s.get("id") != selected_server_id
            ]

            # Jeśli usunięto aktywny serwer, ustaw inny jako aktywny (np. pierwszy lub domyślny)
            if self.active_chat_server_id == selected_server_id:
                if self.sio and self.sio.connected:
                    self._chat_logout()  # Rozłącz, jeśli był połączony

                new_active_server = next(
                    (s for s in self.chat_servers_list if s.get("is_default")), None
                )
                if not new_active_server and self.chat_servers_list:
                    new_active_server = self.chat_servers_list[0]

                self.active_chat_server_id = (
                    new_active_server.get("id") if new_active_server else None
                )
                self.local_settings["active_chat_server_id"] = (
                    self.active_chat_server_id
                )
                # Zaktualizuj używany URL itp.
                self._update_active_server_dependent_settings()

            # Jeśli usunięto domyślny serwer, a lista nie jest pusta, ustaw inny jako domyślny
            if server_to_delete.get("is_default") and self.chat_servers_list:
                # Sprawdź, czy jest już inny domyślny
                if not any(s.get("is_default") for s in self.chat_servers_list):
                    self.chat_servers_list[0][
                        "is_default"
                    ] = True  # Ustaw pierwszy jako domyślny

            self.local_settings["chat_servers"] = self.chat_servers_list
            save_local_settings(self.local_settings)
            self._load_chat_servers_to_treeview()
            logging.info(f"Usunięto serwer czatu: {server_to_delete.get('name')}")

def _update_active_server_dependent_settings(self):
        """Aktualizuje self.chat_server_url i inne zmienne na podstawie aktywnego serwera."""
        active_data = self._get_active_server_data()
        if active_data:
            self.chat_server_url = active_data.get("url", "http://127.0.0.1:5000")
            creds = active_data.get("credentials", {})
            self.current_server_credentials["email"] = creds.get("email", "")
            self.current_server_credentials["password"] = creds.get("password", "")
            self.current_server_remember_credentials = active_data.get(
                "remember_credentials", False
            )
            self.current_server_auto_login = active_data.get(
                "auto_login_to_server", False
            )

            if hasattr(self, "chat_server_url_var"):
                self.chat_server_url_var.set(self.chat_server_url)
            if hasattr(self, "chat_remember_me_var"):
                self.chat_remember_me_var.set(self.current_server_remember_credentials)
            if hasattr(self, "chat_auto_login_var"):
                self.chat_auto_login_var.set(self.current_server_auto_login)

            # Wyczyść pola logowania, jeśli "remember_me" nie jest ustawione dla nowego aktywnego serwera
            if hasattr(self, "chat_email_var") and hasattr(self, "chat_password_var"):
                if not self.current_server_remember_credentials:
                    self.chat_email_var.set("")
                    self.chat_password_var.set("")
                else:  # Załaduj dane, jeśli są zapamiętane
                    self.chat_email_var.set(self.current_server_credentials["email"])
                    self.chat_password_var.set(
                        self.current_server_credentials["password"]
                    )

            logging.info(
                f"Przełączono na serwer: {active_data.get('name')} ({self.chat_server_url})"
            )
        else:  # Brak serwerów na liście
            self.chat_server_url = "http://127.0.0.1:5000"  # Fallback
            # Wyczyść wszystkie powiązane zmienne
            if hasattr(self, "chat_server_url_var"):
                self.chat_server_url_var.set(self.chat_server_url)
            if hasattr(self, "chat_remember_me_var"):
                self.chat_remember_me_var.set(False)
            if hasattr(self, "chat_auto_login_var"):
                self.chat_auto_login_var.set(False)
            if hasattr(self, "chat_email_var"):
                self.chat_email_var.set("")
            if hasattr(self, "chat_password_var"):
                self.chat_password_var.set("")
            logging.warning("Brak zdefiniowanych serwerów czatu.")

def _connect_to_selected_server(self):
        """Łączy z serwerem wybranym w Treeview na stronie zarządzania serwerami."""
        if not hasattr(self, "servers_tree") or not self.servers_tree.winfo_exists():
            logging.error("Próba połączenia, ale Treeview serwerów nie istnieje.")
            return

        selection = self.servers_tree.selection()
        if not selection:
            messagebox.showwarning(
                "Brak Zaznaczenia",
                "Zaznacz serwer z listy, z którym chcesz się połączyć.",
                parent=self.server_selection_page_frame,
            )
            return

        selected_server_id = selection[0]
        server_data_to_connect = next(
            (s for s in self.chat_servers_list if s.get("id") == selected_server_id),
            None,
        )

        if not server_data_to_connect:
            messagebox.showerror(
                "Błąd Wewnętrzny",
                "Nie można znaleźć danych dla wybranego serwera.",
                parent=self.server_selection_page_frame,
            )
            self._load_chat_servers_to_treeview()  # Odśwież listę na wszelki wypadek
            return

        new_url = server_data_to_connect.get("url")
        new_name = server_data_to_connect.get("name")

        if not new_url:
            messagebox.showerror(
                "Brak URL",
                f"Wybrany serwer '{new_name}' nie ma zdefiniowanego adresu URL.",
                parent=self.server_selection_page_frame,
            )
            return

        logging.info(f"Próba połączenia z wybranym serwerem: '{new_name}' ({new_url})")

        # 1. Rozłącz z obecnym serwerem, jeśli jesteś połączony
        if self.sio and self.sio.connected:
            if (
                self.chat_server_url == new_url
            ):  # Próba połączenia z tym samym serwerem, z którym już jesteśmy połączeni
                messagebox.showinfo(
                    "Informacja",
                    f"Jesteś już połączony z serwerem '{new_name}'.",
                    parent=self.server_selection_page_frame,
                )
                self.show_chat_page()  # Po prostu przejdź do strony czatu
                return
            else:  # Łączenie z innym serwerem
                self._chat_logout()  # To rozłączy i zresetuje stan czatu

        # 2. Ustaw nowy serwer jako aktywny i zaktualizuj ustawienia
        self.active_chat_server_id = selected_server_id
        self.local_settings["active_chat_server_id"] = (
            selected_server_id  # Zapisz jako ostatnio używany/aktywny
        )

        # Aktualizuj last_used dla wybranego serwera
        for server in self.chat_servers_list:
            if server.get("id") == selected_server_id:
                server["last_used"] = time.time()
                break
        self.local_settings["chat_servers"] = self.chat_servers_list
        save_local_settings(self.local_settings)

        self._update_active_server_dependent_settings()  # To ustawi self.chat_server_url, creds, etc.
        self._load_chat_servers_to_treeview()  # Odśwież Treeview, aby pokazać nowy aktywny serwer

        # 3. Przejdź do strony czatu (która spróbuje się połączyć i ewentualnie auto-zalogować)
        messagebox.showinfo(
            "Przełączanie Serwera",
            f"Przełączono na serwer '{new_name}'.\nPrzechodzenie do strony logowania/czatu...",
            parent=self.server_selection_page_frame,
        )

        self.show_chat_page()

def _save_auto_connect_setting(self):
        self.local_settings["chat_auto_connect_to_default"] = (
            self.chat_auto_connect_to_default_var.get()
        )
        save_local_settings(self.local_settings)
        logging.info(
            f"Ustawienie auto-connect to default server: {self.chat_auto_connect_to_default_var.get()}"
        )

__all__ = [
    "_get_active_server_data",
    "show_server_selection_page",
    "_create_server_selection_page_content",
    "_load_chat_servers_to_treeview",
    "_add_edit_chat_server_dialog",
    "_delete_chat_server_dialog",
    "_update_active_server_dependent_settings",
    "_connect_to_selected_server",
    "_save_auto_connect_setting",
]
