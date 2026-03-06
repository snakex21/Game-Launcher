import logging


def show_chat_page(self):
    remembered_partner = self._last_open_chat_partner_id

    self.chat_page_frame.grid()
    self.chat_page_frame.tkraise()
    self.current_frame = self.chat_page_frame

    if not getattr(self, "_chat_initialized", False):
        self._create_chat_page_content()
        self._chat_initialized = True

    if self.chat_remember_me_var.get():
        self._load_saved_chat_credentials()
    else:
        self.chat_email_var.set(self.local_settings.get("chat_last_email", ""))
        self.chat_password_var.set("")

    self._update_chat_ui_state()

    if not self.chat_logged_in_user:
        self._try_auto_chat_login()

    if remembered_partner and remembered_partner != self.chat_dashboard_placeholder_id:
        self.root.after(
            500,
            lambda pid=remembered_partner: self._restore_last_chat_partner(pid),
        )
    elif self.chat_logged_in_user and self.chat_authenticated:
        if not hasattr(self, "chat_users_tree") or not self.chat_users_tree.winfo_exists():
            self.root.after(100, self._show_chat_dashboard)
        elif self.chat_users_tree.exists(self.chat_dashboard_placeholder_id):
            self.chat_users_tree.selection_set(self.chat_dashboard_placeholder_id)
            self.chat_users_tree.focus(self.chat_dashboard_placeholder_id)
            self.root.after(50, self._show_chat_dashboard)

    self._reset_chat_search_field()
    self.current_section = "Czat"
    self._update_discord_status(
        status_type="browsing", activity_details=self.current_section
    )


def _load_saved_chat_credentials(self):
    active_server_data = self._get_active_server_data()
    if active_server_data and active_server_data.get("remember_credentials", False):
        creds = active_server_data.get("credentials", {})
        self.chat_email_var.set(creds.get("email", ""))
        self.chat_password_var.set(creds.get("password", ""))
        logging.debug(
            f"Chat: Wypełniono pola zapamiętanymi danymi dla serwera '{active_server_data.get('name')}'."
        )
    else:
        self.chat_email_var.set("")
        self.chat_password_var.set("")


__all__ = [
    "show_chat_page",
    "_load_saved_chat_credentials",
]
