import logging
import os
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from launcher.utils import RESAMPLING, THEMES
from ui.components import ToolTip


def _create_chat_page_content(self):
    # usuń poprzednią zawartość ramki
    for widget in self.chat_page_frame.winfo_children():
        widget.destroy()

    self.chat_page_frame.columnconfigure(0, weight=1)
    self.chat_page_frame.rowconfigure(0, weight=1)

    # ---------- PANEL LOGOWANIA ----------
    self.chat_auth_panel = ttk.Frame(self.chat_page_frame, padding=20)
    self.chat_auth_panel.columnconfigure(1, weight=1)
    self.chat_auth_panel.columnconfigure(2, weight=0)

    current_auth_panel_row = 0

    ttk.Label(
        self.chat_auth_panel,
        text="Logowanie / Rejestracja do Czatu",
        font=("Helvetica", 14, "bold"),
    ).grid(row=current_auth_panel_row, column=0, columnspan=3, pady=(0, 10))
    current_auth_panel_row += 1

    ttk.Label(self.chat_auth_panel, text="Adres E-mail:").grid(
        row=current_auth_panel_row, column=0, sticky="w", pady=5
    )
    ttk.Entry(self.chat_auth_panel, textvariable=self.chat_email_var).grid(
        row=current_auth_panel_row, column=1, sticky="ew", pady=5
    )
    current_auth_panel_row += 1

    ttk.Label(self.chat_auth_panel, text="Hasło:").grid(
        row=current_auth_panel_row, column=0, sticky="w", pady=5
    )
    ttk.Entry(
        self.chat_auth_panel, textvariable=self.chat_password_var, show="*"
    ).grid(row=current_auth_panel_row, column=1, sticky="ew", pady=5)
    current_auth_panel_row += 1

    ttk.Button(self.chat_auth_panel, text="Zaloguj", command=self._chat_login).grid(
        row=current_auth_panel_row,
        column=0,
        columnspan=2,
        pady=(10, 2),
        sticky="ew",
    )
    current_auth_panel_row += 1

    remember_me_check = ttk.Checkbutton(
        self.chat_auth_panel,
        text="Zapamiętaj dane logowania",
        variable=self.chat_remember_me_var,
        command=self._on_remember_me_toggle,
    )
    remember_me_check.grid(
        row=current_auth_panel_row,
        column=0,
        columnspan=2,
        sticky="w",
        padx=0,
        pady=(0, 0),
    )
    current_auth_panel_row += 1

    auto_login_check = ttk.Checkbutton(
        self.chat_auth_panel,
        text="Automatyczne logowanie",
        variable=self.chat_auto_login_var,
        command=self._on_auto_login_toggle,
    )
    auto_login_check.grid(
        row=current_auth_panel_row,
        column=0,
        columnspan=2,
        sticky="w",
        padx=0,
        pady=(0, 10),
    )
    current_auth_panel_row += 1

    ttk.Label(self.chat_auth_panel, text="--- Brak konta? ---").grid(
        row=current_auth_panel_row, column=0, columnspan=2, pady=(5, 5)
    )
    current_auth_panel_row += 1

    ttk.Label(self.chat_auth_panel, text="Nazwa Użytkownika:").grid(
        row=current_auth_panel_row, column=0, sticky="w", pady=5
    )
    ttk.Entry(self.chat_auth_panel, textvariable=self.chat_username_var).grid(
        row=current_auth_panel_row, column=1, sticky="ew", pady=5
    )
    current_auth_panel_row += 1

    ttk.Button(
        self.chat_auth_panel, text="Zarejestruj", command=self._chat_register
    ).grid(
        row=current_auth_panel_row,
        column=0,
        columnspan=2,
        pady=(10, 5),
        sticky="ew",
    )
    current_auth_panel_row += 1

    server_list_btn_auth_panel = ttk.Button(
        self.chat_auth_panel,
        text="🌐 Wybierz/Zarządzaj Serwerami Czatu",
        command=self._go_to_server_selection_from_chat_auth,
        style="Toolbutton.TButton",
    )
    server_list_btn_auth_panel.grid(
        row=current_auth_panel_row,
        column=0,
        columnspan=2,
        pady=(15, 5),
        sticky="ew",
    )
    ToolTip(
        server_list_btn_auth_panel, "Pokaż listę serwerów czatu i zarządzaj nimi"
    )
    # current_auth_panel_row +=1 # Nie potrzebujemy już inkrementować, bo to ostatni element w tej sekcji

    # ---------- PANEL GŁÓWNY CZATU ----------
    self.chat_main_panel = ttk.Frame(self.chat_page_frame)
    self.chat_main_panel.columnconfigure(0, weight=1)
    self.chat_main_panel.rowconfigure(0, weight=1)

    self.chat_paned_window = ttk.PanedWindow(self.chat_main_panel, orient=tk.HORIZONTAL)
    self.chat_paned_window.grid(row=0, column=0, sticky="nsew")

    # -------- LEWY: lista użytkowników --------
    self.chat_users_panel = ttk.Frame(self.chat_paned_window)
    self.chat_paned_window.add(
        self.chat_users_panel, weight=1
    )  # Zmieniamy wagę na 1 (proporcjonalnie mniejszy)
    self.chat_users_panel.columnconfigure(0, weight=1)
    self.chat_users_panel.rowconfigure(1, weight=0)  # Wiersz dla labela użytkownika
    self.chat_users_panel.rowconfigure(2, weight=0)  # Wiersz dla przycisku edycji
    self.chat_users_panel.rowconfigure(3, weight=0)  # Nowy wiersz dla przycisku "Utwórz Pokój"
    self.chat_users_panel.rowconfigure(
        4, weight=1
    )  # Wiersz dla pola wyszukiwarki i Treeview

    self.chat_connection_status_label = ttk.Label(
        self.chat_users_panel,
        text="Status: Rozłączono",
        font=("Segoe UI", 8, "italic"),
        anchor="w",
    )
    self.chat_connection_status_label.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 0))

    # Ramka na etykietę nazwy użytkownika i przycisk edycji
    user_info_frame = ttk.Frame(self.chat_users_panel)
    user_info_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(5, 0))
    user_info_frame.columnconfigure(
        0, weight=1
    )  # Etykieta nazwy użytkownika rozciąga się

    self.chat_current_user_label = ttk.Label(
        user_info_frame,
        text="Zalogowano jako: Nieznany",
        font=("Segoe UI", 9, "bold"),
    )
    self.chat_current_user_label.grid(row=0, column=0, sticky="w")

    edit_username_btn = ttk.Button(
        user_info_frame,
        text="Edytuj",
        command=self._edit_chat_username_dialog,
        width=6,
    )
    edit_username_btn.grid(row=0, column=1, sticky="e", padx=(5, 0))

    # Przycisk "Utwórz Pokój"
    self.create_room_btn = ttk.Button(
        self.chat_users_panel,
        text="➕ Utwórz Pokój",
        command=self._create_room_dialog,
    )
    self.create_room_btn.grid(row=2, column=0, sticky="ew", padx=5, pady=(5, 0))
    ToolTip(self.create_room_btn, "Stwórz nowy pokój czatu (opcjonalnie z hasłem)")

    self.chat_user_search_var = tk.StringVar()
    self.chat_user_search_var.trace_add("write", lambda *args: self._filter_chat_users())
    self.chat_user_search_entry = ttk.Entry(
        self.chat_users_panel, textvariable=self.chat_user_search_var, width=20
    )
    self.chat_user_search_entry.grid(row=3, column=0, sticky="ew", padx=5, pady=(5, 0))
    ToolTip(self.chat_user_search_entry, "Wyszukaj użytkowników...")

    self.chat_users_tree = ttk.Treeview(
        self.chat_users_panel,
        columns=("username", "unread_count"),
        show="headings",
        selectmode="browse",
    )
    self.chat_users_tree.heading("username", text="Nazwa")
    self.chat_users_tree.heading("unread_count", text="Nowe")
    self.chat_users_tree.column("username", width=120, anchor="w")
    self.chat_users_tree.column("unread_count", width=40, anchor="center", stretch=False)

    self.chat_users_tree.grid(row=4, column=0, sticky="nsew", padx=5, pady=(0, 5))

    self.chat_users_tree.tag_configure(
        "user_chat_item", foreground="white", background="#2e2e2e"
    )
    self.chat_users_tree.tag_configure(
        "room_chat_item",
        font=("Segoe UI", 9, "bold"),
        foreground="cyan",
        background="#3a3a3a",
    )
    self.chat_users_tree.tag_configure(
        "room_member_tag", foreground="cyan", font=("Segoe UI", 9, "bold")
    )
    self.chat_users_tree.tag_configure(
        "room_non_member_tag", foreground="gray", font=("Segoe UI", 9, "italic")
    )
    self.chat_users_tree.tag_configure(
        "room_has_password_tag", font=("Segoe UI Symbol", 9), foreground="yellow"
    )

    self.chat_users_tree.tag_configure("user_online_tag", foreground="lightgreen")
    self.chat_users_tree.tag_configure("user_offline_tag", foreground="gray")
    self.chat_users_tree.tag_configure(
        "new_message_tag", foreground="yellow", font=("Segoe UI", 9, "bold")
    )

    self.chat_users_tree.tag_configure(
        "system_header_tag", foreground="lightgray", font=("Segoe UI", 9, "italic")
    )

    self.chat_users_tree.bind("<<TreeviewSelect>>", self._on_chat_user_select)
    self.chat_users_tree.bind("<Button-3>", self._on_chat_list_right_click)

    users_scrollbar = ttk.Scrollbar(
        self.chat_users_panel, orient="vertical", command=self.chat_users_tree.yview
    )
    users_scrollbar.grid(row=4, column=1, sticky="ns", pady=(0, 5))
    self.chat_users_tree.config(yscrollcommand=users_scrollbar.set)

    theme_def = self.get_all_available_themes().get(
        self.settings.get("theme", "Dark"), THEMES["Dark"]
    )
    new_message_fg = "yellow"
    normal_user_fg = theme_def.get("foreground", "white")
    normal_user_bg = theme_def.get("tree_background", "#2e2e2e")

    self.chat_users_tree.tag_configure(
        "new_message", foreground=new_message_fg, font=("Segoe UI", 9, "bold")
    )
    self.chat_users_tree.tag_configure(
        "normal_user_chat_tree",
        foreground=normal_user_fg,
        background=normal_user_bg,
    )

    online_fg = "lightgreen"
    offline_fg = "gray"

    self.chat_users_tree.tag_configure(
        "online_user_chat_tree", foreground=online_fg, background=normal_user_bg
    )
    self.chat_users_tree.tag_configure(
        "offline_user_chat_tree", foreground=offline_fg, background=normal_user_bg
    )

    # -------- PRAWY: okno wiadomości --------
    self.chat_messages_panel = ttk.Frame(self.chat_paned_window)
    self.chat_paned_window.add(self.chat_messages_panel, weight=3)
    self.chat_messages_panel.columnconfigure(0, weight=1)

    self.chat_messages_panel.rowconfigure(0, weight=0)
    self.chat_messages_panel.rowconfigure(1, weight=0)
    self.chat_messages_panel.rowconfigure(2, weight=0)
    self.chat_messages_panel.rowconfigure(3, weight=1)
    self.chat_messages_panel.rowconfigure(4, weight=0)
    self.chat_messages_panel.rowconfigure(5, weight=0)
    self.chat_messages_panel.rowconfigure(6, weight=0)
    self.chat_messages_panel.rowconfigure(7, weight=0)
    self.chat_messages_panel.rowconfigure(8, weight=0)

    self.chat_active_partner_label = ttk.Label(
        self.chat_messages_panel,
        text="Wybierz partnera czatu",
        font=("Segoe UI", 10, "bold"),
        anchor="w",
    )
    self.chat_active_partner_label.grid(row=0, column=0, sticky="ew", padx=10, pady=(5, 0))

    self.chat_typing_indicator_label = ttk.Label(
        self.chat_messages_panel,
        text="",
        font=("Segoe UI", 8, "italic"),
        foreground="gray",
        anchor="w",
    )
    self.chat_typing_indicator_label.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 5))

    chat_message_search_frame = ttk.Frame(self.chat_messages_panel)
    chat_message_search_frame.grid(
        row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(5, 0)
    )
    chat_message_search_frame.columnconfigure(0, weight=1)

    self.chat_message_search_var = tk.StringVar()
    self.chat_message_search_var.trace_add(
        "write", lambda *args: self._on_chat_message_search_change()
    )

    chat_message_search_entry = ttk.Entry(
        chat_message_search_frame, textvariable=self.chat_message_search_var
    )
    chat_message_search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 2))
    ToolTip(chat_message_search_entry, "Wyszukaj w wiadomościach tego czatu...")

    clear_message_search_btn = ttk.Button(
        chat_message_search_frame,
        text="✖",
        command=self._clear_chat_message_search,
        width=3,
        style="Toolbutton.TButton",
    )
    clear_message_search_btn.grid(row=0, column=1, sticky="e")

    self.chat_message_display = tk.Text(
        self.chat_messages_panel,
        wrap=tk.WORD,
        state=tk.DISABLED,
        height=10,
        bg="#2e2e2e",
        fg="white",
    )
    self.chat_message_display.grid(row=3, column=0, sticky="nsew", padx=10, pady=5)

    messages_scrollbar = ttk.Scrollbar(
        self.chat_messages_panel,
        orient="vertical",
        command=self.chat_message_display.yview,
    )
    messages_scrollbar.grid(row=3, column=1, sticky="ns", pady=5)

    def _on_chat_scroll(lower, upper):
        messages_scrollbar.set(lower, upper)
        if (
            float(lower) <= 0.02
            and self.chat_history_has_more
            and not self.chat_history_loading
        ):
            self._fetch_more_chat_history()

    self.chat_message_display.config(yscrollcommand=_on_chat_scroll)

    theme_def = self.get_all_available_themes().get(
        self.settings.get("theme", "Dark"), THEMES["Dark"]
    )
    my_msg_fg = theme_def.get("link_foreground", "lightblue")
    other_msg_fg = theme_def.get("foreground", "lightgreen")
    system_msg_fg = theme_def.get("chart_axis_color", "gray")
    error_msg_fg = "red"

    self.chat_message_display.tag_config(
        "system_tag",
        foreground=system_msg_fg,
        font=("Segoe UI", 9, "italic"),
        justify="center",
        lmargin1=10,
        lmargin2=10,
        rmargin=10,
        spacing1=5,
        spacing2=2,
    )
    self.chat_message_display.tag_config(
        "error_tag",
        foreground=error_msg_fg,
        font=("Segoe UI", 9, "bold"),
        justify="center",
        spacing1=5,
        spacing2=2,
    )

    self.chat_message_display.tag_config(
        "my_message_tag",
        foreground=my_msg_fg,
        background="#004e92",
        borderwidth=5,
        relief="solid",
        justify="right",
        lmargin1=10,
        lmargin2=10,
        rmargin=10,
        spacing1=8,
        spacing2=4,
        spacing3=8,
    )

    self.chat_message_display.tag_config(
        "other_message_tag",
        foreground=other_msg_fg,
        background="#2e2e2e",
        borderwidth=5,
        relief="solid",
        justify="left",
        lmargin1=10,
        lmargin2=10,
        rmargin=10,
        spacing1=8,
        spacing2=4,
        spacing3=8,
    )

    s = ttk.Style()
    theme_fg = self.chat_message_display.cget("fg")

    pending_attachment_frame_bg = theme_def.get("entry_background", "#282828")
    s.configure(
        "ChatPendingAttachment.TFrame",
        background=pending_attachment_frame_bg,
        borderwidth=1,
        relief="groove",
    )
    s.configure(
        "ChatPendingAttachment.TLabel",
        background=pending_attachment_frame_bg,
        foreground=theme_fg,
        font=("Segoe UI", 8),
    )
    s.configure(
        "ChatPendingAttachment.Toolbutton.TButton",
        background=pending_attachment_frame_bg,
        foreground=theme_fg,
        relief="flat",
        padding=(1, 0),
        font=("Segoe UI Symbol", 9, "bold"),
    )
    s.map(
        "ChatPendingAttachment.Toolbutton.TButton",
        foreground=[("active", "red"), ("hover", "red")],
        background=[("active", pending_attachment_frame_bg), ("hover", pending_attachment_frame_bg)],
    )

    self.chat_message_display.bind("<Configure>", self._on_chat_display_resize)

    self.chat_input_var = tk.StringVar()
    self.chat_input_entry = ttk.Entry(self.chat_messages_panel, textvariable=self.chat_input_var)
    self.chat_input_entry.grid(row=4, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
    self.chat_input_entry.bind("<Key>", self._on_chat_input_key_press)
    self.chat_input_entry.bind("<Return>", self._send_chat_message)
    self.attach_file_icon = None

    self.chat_reply_preview_frame = tk.Frame(self.chat_messages_panel, relief="solid", bd=1)
    self.chat_reply_preview_frame.columnconfigure(0, weight=1)

    self.reply_preview_label = ttk.Label(
        self.chat_reply_preview_frame,
        text="",
        wraplength=300,
        justify=tk.LEFT,
        font=("Segoe UI", 8, "italic"),
    )
    self.reply_preview_label.grid(row=0, column=0, sticky="ew")

    self.cancel_reply_button = ttk.Button(
        self.chat_reply_preview_frame,
        text="✖",
        command=self._cancel_reply_mode,
        width=2,
        style="Toolbutton.TButton",
    )
    self.cancel_reply_button.grid(row=0, column=1, sticky="e", padx=(5, 0))
    ToolTip(self.cancel_reply_button, "Anuluj odpowiadanie")

    self.chat_pending_attachment_frame = ttk.Frame(
        self.chat_messages_panel, style="ChatPendingAttachment.TFrame"
    )
    self.chat_pending_attachment_icon_label = ttk.Label(
        self.chat_pending_attachment_frame,
        text="📄",
        font=("Segoe UI Symbol", 10),
        style="ChatPendingAttachment.TLabel",
    )
    self.chat_pending_attachment_name_label = ttk.Label(
        self.chat_pending_attachment_frame,
        text="",
        wraplength=200,
        style="ChatPendingAttachment.TLabel",
    )
    self.remove_pending_attachment_button = ttk.Button(
        self.chat_pending_attachment_frame,
        text="✖",
        command=self._clear_pending_chat_attachment,
        width=2,
        style="ChatPendingAttachment.Toolbutton.TButton",
    )
    ToolTip(self.remove_pending_attachment_button, "Usuń załącznik")
    self.chat_pending_attachment_icon_label.pack(side=tk.LEFT, padx=(5, 2))
    self.chat_pending_attachment_name_label.pack(
        side=tk.LEFT, padx=(0, 5), expand=True, fill=tk.X
    )
    self.remove_pending_attachment_button.pack(side=tk.RIGHT, padx=(2, 5))

    self.chat_action_buttons_frame = ttk.Frame(self.chat_messages_panel)
    self.chat_action_buttons_frame.grid(row=7, column=0, columnspan=2, pady=5, sticky="ew")
    self.chat_action_buttons_frame.columnconfigure(0, weight=1)
    self.chat_action_buttons_frame.columnconfigure(1, weight=0)
    self.chat_action_buttons_frame.columnconfigure(2, weight=0)

    self.chat_send_button = ttk.Button(
        self.chat_action_buttons_frame, text="Wyślij", command=self._send_chat_message
    )
    self.chat_send_button.grid(row=0, column=0, sticky="ew", padx=(0, 5))

    attach_file_icon_path = "icons/attach_16.png"
    icon_size = (20, 20)
    if os.path.exists(attach_file_icon_path):
        try:
            img = Image.open(attach_file_icon_path).resize(icon_size, RESAMPLING)
            self.attach_file_icon = ImageTk.PhotoImage(img)
        except Exception as e:
            logging.error(
                f"Nie można załadować ikony dołączania pliku ({attach_file_icon_path}): {e}"
            )

    if self.attach_file_icon:
        self.chat_attach_button = ttk.Button(
            self.chat_action_buttons_frame,
            text=" Dołącz",
            image=self.attach_file_icon,
            compound=tk.LEFT,
            command=self._select_chat_attachment_dialog,
            style="Toolbutton.TButton",
            width=8,
        )
        ToolTip(self.chat_attach_button, "Dołącz plik (maks. 10MB)")
    else:
        self.chat_attach_button = ttk.Button(
            self.chat_action_buttons_frame,
            text="📎 Dołącz Plik",
            command=self._select_chat_attachment_dialog,
            width=12,
        )
        ToolTip(self.chat_attach_button, "Dołącz plik (maks. 10MB)")
    self.chat_attach_button.grid(row=0, column=1, sticky="e", padx=(5, 0))

    self.emoji_button = ttk.Button(
        self.chat_action_buttons_frame,
        text="😊",
        command=self._open_emoji_picker,
        width=3,
        style="Toolbutton.TButton",
    )
    self.emoji_button.grid(row=0, column=2, sticky="e", padx=(5, 0))
    ToolTip(self.emoji_button, "Wstaw Emoji")

    self.chat_logout_button = ttk.Button(
        self.chat_messages_panel, text="Wyloguj z Czatu", command=self._chat_logout
    )
    self.chat_logout_button.grid(row=8, column=0, columnspan=2, pady=(5, 10), sticky="ew")

    change_server_btn_main_panel = ttk.Button(
        self.chat_messages_panel,
        text="🌐 Zmień Serwer",
        command=self._go_to_server_selection_from_chat_main,
        style="Toolbutton.TButton",
    )
    change_server_btn_main_panel.grid(row=9, column=0, columnspan=2, pady=(2, 10), sticky="ew")
    ToolTip(
        change_server_btn_main_panel,
        "Wróć do listy serwerów (rozłączy obecne połączenie)",
    )

    self.chat_messages_panel.rowconfigure(0, weight=0)
    self.chat_messages_panel.rowconfigure(1, weight=0)
    self.chat_messages_panel.rowconfigure(2, weight=0)
    self.chat_messages_panel.rowconfigure(3, weight=1)
    self.chat_messages_panel.rowconfigure(4, weight=0)
    self.chat_messages_panel.rowconfigure(5, weight=0)
    self.chat_messages_panel.rowconfigure(6, weight=0)
    self.chat_messages_panel.rowconfigure(7, weight=0)
    self.chat_messages_panel.rowconfigure(8, weight=0)

    self.chat_room_members_panel = ttk.Frame(self.chat_paned_window, width=150)

    self.chat_room_members_panel.columnconfigure(0, weight=1)
    self.chat_room_members_panel.rowconfigure(1, weight=1)

    members_header_label = ttk.Label(
        self.chat_room_members_panel,
        text="Członkowie Pokoju:",
        font=("Segoe UI", 9, "bold"),
    )
    members_header_label.grid(row=0, column=0, padx=5, pady=(5, 0), sticky="ew")

    self.room_members_listbox = tk.Listbox(
        self.chat_room_members_panel, bg="#2a2a2a", fg="lightgray", height=10
    )
    self.room_members_listbox.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
    members_list_scrollbar = ttk.Scrollbar(
        self.chat_room_members_panel,
        orient="vertical",
        command=self.room_members_listbox.yview,
    )
    members_list_scrollbar.grid(row=1, column=1, sticky="ns", pady=5)
    self.room_members_listbox.config(yscrollcommand=members_list_scrollbar.set)
    self.room_members_listbox.bind("<Button-3>", self._on_room_member_list_right_click)
    self._room_members_panel_visible = False


__all__ = ["_create_chat_page_content"]
