# Game Launcher - Główny plik aplikacji

import os
import sys
import json
import time
import datetime
import logging
import importlib
import re
import shutil
import subprocess
import threading
import queue
import tempfile
import mimetypes
import urllib.parse
import zipfile
import shlex
import random
import uuid
import socket

import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog, colorchooser
from PIL import Image, ImageTk, ImageDraw, ImageFont, UnidentifiedImageError
import winreg
from io import BytesIO
import webbrowser

from ui.components import ToolTip


class _LazyModule:
    def __init__(self, module_path: str):
        self._module_path = module_path
        self._loaded_module = None

    def _load(self):
        if self._loaded_module is None:
            self._loaded_module = importlib.import_module(self._module_path)
        return self._loaded_module

    def __getattr__(self, item):
        return getattr(self._load(), item)


_LAUNCHER_MODULE_ALIASES = {
    "gl_server_selection": "launcher.server_selection",
    "gl_chat_auth": "launcher.chat_auth",
    "gl_chat_socket": "launcher.chat_socket",
    "gl_chat_ui": "launcher.chat_ui",
    "gl_chat_messaging": "launcher.chat_messaging",
    "gl_chat_dashboard": "launcher.chat_dashboard",
    "gl_chat_history": "launcher.chat_history",
    "gl_chat_data": "launcher.chat_data",
    "gl_chat_render": "launcher.chat_render",
    "gl_chat_interactions": "launcher.chat_interactions",
    "gl_chat_navigation": "launcher.chat_navigation",
    "gl_chat_message_actions": "launcher.chat_message_actions",
    "gl_chat_emoji": "launcher.chat_emoji",
    "gl_chat_server_settings": "launcher.chat_server_settings",
    "gl_chat_layout": "launcher.chat_layout",
    "gl_chat_rooms": "launcher.chat_rooms",
    "gl_chat_user_profile": "launcher.chat_user_profile",
    "gl_chat_context_actions": "launcher.chat_context_actions",
    "gl_chat_blocking": "launcher.chat_blocking",
    "gl_overlay_runtime": "launcher.overlay_runtime",
    "gl_overlay_controls": "launcher.overlay_controls",
    "gl_hotkey_capture": "launcher.hotkey_capture",
    "gl_hotkey_runtime": "launcher.hotkey_runtime",
    "gl_hotkey_input": "launcher.hotkey_input",
    "gl_library_view": "launcher.library_view",
    "gl_library_header": "launcher.library_header",
    "gl_library_genres": "launcher.library_genres",
    "gl_window_ops": "launcher.window_ops",
    "gl_sidebar_ui": "launcher.sidebar_ui",
    "gl_stats_navigation": "launcher.stats_navigation",
    "gl_stats_controls": "launcher.stats_controls",
    "gl_stats_page": "launcher.stats_page",
    "gl_stats_data": "launcher.stats_data",
    "gl_stats_chart": "launcher.stats_chart",
    "gl_stats_runtime": "launcher.stats_runtime",
    "gl_usage_runtime": "launcher.usage_runtime",
    "gl_music_navigation": "launcher.music_navigation",
    "gl_library_tags": "launcher.library_tags",
    "gl_app_navigation": "launcher.app_navigation",
    "gl_backup_restore": "launcher.backup_restore",
    "gl_scan_pipeline": "launcher.scan_pipeline",
    "gl_achievements_defs": "launcher.achievements_defs",
    "gl_updater_runtime": "launcher.updater_runtime",
    "gl_achievements_runtime": "launcher.achievements_runtime",
    "gl_achievements_page": "launcher.achievements_page",
    "gl_rawg_cover": "launcher.rawg_cover",
    "gl_library_lazy_load": "launcher.library_lazy_load",
    "gl_discord_runtime": "launcher.discord_runtime",
    "gl_settings_avatar": "launcher.settings_avatar",
    "gl_library_tile_actions": "launcher.library_tile_actions",
    "gl_library_list_context": "launcher.library_list_context",
    "gl_rawg_settings": "launcher.rawg_settings",
    "gl_library_grid_runtime": "launcher.library_grid_runtime",
    "gl_remote_server_runtime": "launcher.remote_server_runtime",
    "gl_screenshot_scan_runtime": "launcher.screenshot_scan_runtime",
    "gl_duplicates_ui": "launcher.duplicates_ui",
    "gl_advanced_filter_eval": "launcher.advanced_filter_eval",
    "gl_library_list_sort": "launcher.library_list_sort",
    "gl_file_ops_runtime": "launcher.file_ops_runtime",
    "gl_roadmap_archive_runtime": "launcher.roadmap_archive_runtime",
    "gl_game_process_runtime": "launcher.game_process_runtime",
    "gl_settings_page_content": "launcher.settings_page_content",
    "gl_init_constructor_runtime": "launcher.init_constructor_runtime",
    "gl_theme_runtime": "launcher.services.theme_runtime",
    "gl_closing_runtime": "launcher.closing_runtime",
    "gl_cloud_github_runtime": "launcher.cloud_github_runtime",
    "gl_rawg_fetch_runtime": "launcher.rawg_fetch_runtime",
    "gl_emulator_settings_runtime": "launcher.emulator_settings_runtime",
    "gl_home_page_runtime": "launcher.home_page_runtime",
    "gl_news_runtime": "launcher.news_runtime",
    "gl_initial_setup_runtime": "launcher.initial_setup_runtime",
    "gl_autosave_runtime": "launcher.autosave_runtime",
    "gl_session_monitor_runtime": "launcher.session_monitor_runtime",
    "gl_game_crud_runtime": "launcher.game_crud_runtime",
    "gl_tray_runtime": "launcher.tray_runtime",
    "gl_playtime_stats_runtime": "launcher.playtime_stats_runtime",
    "gl_gamepad_runtime": "launcher.gamepad_runtime",
    "gl_reminders_runtime": "launcher.reminders_runtime",
    "gl_library_groups_runtime": "launcher.library_groups_runtime",
    "gl_settings_runtime": "launcher.settings_runtime",
}

globals().update(
    {
        alias_name: _LazyModule(module_path)
        for alias_name, module_path in _LAUNCHER_MODULE_ALIASES.items()
    }
)
from launcher.config_store import (
    load_local_settings as config_load_local_settings,
    save_local_settings as config_save_local_settings,
    load_config as config_load_config,
)
from launcher.utils import (
    THEMES, PROGRAM_VERSION, CONFIG_FILE, GAMES_FOLDER, IMAGES_FOLDER, 
    INTERNAL_MUSIC_DIR, CUSTOM_THEMES_DIR, LOCAL_SETTINGS_FILE,
    DEFAULT_MUSIC_HOTKEYS, RESAMPLING, get_contrast_color,
    MONTH_COLORS, MONTH_NAMES_PL,
    create_default_cover, load_photoimage_from_path,
    _load_theme_from_file, save_config, DummyTranslator
)


def load_local_settings():
    return config_load_local_settings()


def save_local_settings(data):
    return config_save_local_settings(data)


# Wczytanie istniejących danych lub utworzenie nowego pliku, jeśli nie istnieje
def load_config():
    return config_load_config()


class GameLauncher:
    def __init__(self, root):
        gl_init_constructor_runtime.initialize(self, root)

    def record_startup_time(self, checkpoint_name: str):
        """Rejestruje czas (od startu aplikacji) dla danego punktu kontrolnego."""
        if not hasattr(self, "_startup_initial_time"):
            self._startup_initial_time = (
                time.monotonic()
            )  # Referencyjny punkt zero (czas startu GameLauncher)

        elapsed = (
            time.monotonic() - self._startup_initial_time
        ) * 1000  # Czas w milisekundach
        self.start_up_time_points[checkpoint_name] = elapsed
        logging.debug(f"STARTUP TIME CHECKPOINT: {checkpoint_name} -> {elapsed:.2f} ms")

    # Zmień nazwę metody i dodaj ikony przycisków
    def _load_icons(self):  # Zmieniono nazwę
        """Ładuje ikony używane w menu i na przyciskach do cache."""
        icon_defs = {
            # Ikony Menu (16x16)
            "play_menu": "icons/play_16.png",  # Inna nazwa dla menu
            "edit": "icons/edit_16.png",
            "folder_open": "icons/folder_open_16.png",
            "save_disk": "icons/save_disk_16.png",
            "mods": "icons/mods_16.png",
            "reset": "icons/reset_16.png",
            "group_add": "icons/group_add_16.png",
            "group_remove": "icons/group_remove_16.png",
            "delete": "icons/delete_16.png",
            "checklist": "icons/checklist_16.png",
            "screenshot": "icons/screenshot_16.png",
            # Ikony Przycisków (mogą być większe, np. 20x20 lub 16x16)
            "play_btn": "icons/play_16.png",  # Możesz użyć tej samej lub innej ikony
            "stop_btn": "icons/stop_16.png",  # Potrzebna ikona stop
            "save_btn": "icons/save_disk_16.png",  # Ikona dla przycisku "Zapisy"
            "profile_menu_btn": "icons/down_arrow_16.png",  # Ikona dla menu profili
        }
        # self._menu_icons = {} # Usuń osobny słownik menu
        icon_size_menu = (16, 16)
        icon_size_button = (16, 16)  # Ustaw rozmiar dla ikon przycisków

        for key, path in icon_defs.items():
            if key not in self._button_icons:  # Użyj jednego cache
                try:
                    size = icon_size_button if "_btn" in key else icon_size_menu
                    img = Image.open(path).resize(size, RESAMPLING)
                    if img.mode != "RGBA":
                        img = img.convert("RGBA")
                    self._button_icons[key] = ImageTk.PhotoImage(
                        img
                    )  # Zapisz w self._button_icons
                except FileNotFoundError:
                    logging.warning(f"Nie znaleziono ikony: {path}")
                    self._button_icons[key] = None
                except Exception as e:
                    logging.error(f"Błąd ładowania ikony {path}: {e}")
                    self._button_icons[key] = None
        logging.info(
            f"Załadowano {len([icon for icon in self._button_icons.values() if icon])} ikon."
        )


    def prompt_initial_setup_choice(self):
        return gl_initial_setup_runtime.prompt_initial_setup_choice(self)

    def _on_root_resize(self, event):
        return gl_window_ops._on_root_resize(self, event)

    def _get_pynput_key_string(self, key):
        return gl_hotkey_input._get_pynput_key_string(self, key)

    def _build_hotkey_string_from_set(self, pressed_keys_set: set) -> str | None:
        return gl_hotkey_input._build_hotkey_string_from_set(self, pressed_keys_set)

    def _get_pynput_internal_representation(self, key) -> str:
        return gl_hotkey_input._get_pynput_internal_representation(self, key)

    def _on_press_for_new_hotkey(self, key):
        return gl_hotkey_input._on_press_for_new_hotkey(self, key)

    def _center_window(self, root, width, height):
        return gl_window_ops._center_window(self, root, width, height)


    def _on_release_for_new_hotkey(self, key):
        return gl_hotkey_input._on_release_for_new_hotkey(self, key)

    def _initialize_track_overlay_from_settings(self):  # Zmieniona nazwa
        return gl_overlay_controls._initialize_track_overlay_from_settings(self)

    def _toggle_track_overlay_setting(self):
        return gl_overlay_controls._toggle_track_overlay_setting(self)

    def show_track_overlay(self):
        return gl_overlay_controls.show_track_overlay(self)

    def hide_track_overlay(self):
        return gl_overlay_controls.hide_track_overlay(self)

    def show_chat_page(self):
        return gl_chat_navigation.show_chat_page(self)

    def _restore_last_chat_partner(self, partner_id_to_restore):
        return gl_chat_interactions._restore_last_chat_partner(
            self,
            partner_id_to_restore,
        )

    def _select_chat_partner_silently(self, partner_id: int):
        return gl_chat_interactions._select_chat_partner_silently(
            self,
            partner_id,
        )

    # W _try_auto_chat_login, użyj danych dla aktywnego serwera
    def _try_auto_chat_login(self):
        return gl_chat_auth._try_auto_chat_login(self)


    def _create_chat_page_content(self):
        return gl_chat_layout._create_chat_page_content(self)


    def _open_chat_server_settings_dialog(self):
        return gl_chat_server_settings._open_chat_server_settings_dialog(self)


    def _open_emoji_picker(self):
        return gl_chat_emoji._open_emoji_picker(self)

    def _close_emoji_picker_if_focus_lost(self, event):
        return gl_chat_emoji._close_emoji_picker_if_focus_lost(self, event)

    def _insert_emoji(self, emoji_char):
        return gl_chat_emoji._insert_emoji(self, emoji_char)

    def _on_room_member_list_right_click(self, event):
        return gl_chat_context_actions._on_room_member_list_right_click(self, event)

    def _confirm_self_leave_room(self, room_id: int, room_name: str):
        return gl_chat_context_actions._confirm_self_leave_room(self, room_id, room_name)

    def _execute_self_leave_room(self, room_id: int, room_name_for_log: str):
        return gl_chat_context_actions._execute_self_leave_room(
            self,
            room_id,
            room_name_for_log,
        )


    def _admin_remove_user_from_room_action(
        self, room_id: int, user_id_to_remove: int, username_to_remove: str
    ):
        return gl_chat_context_actions._admin_remove_user_from_room_action(
            self,
            room_id,
            user_id_to_remove,
            username_to_remove,
        )


    def _start_private_chat_from_room_context(
        self, target_user_id: int, target_username: str
    ):
        return gl_chat_context_actions._start_private_chat_from_room_context(
            self,
            target_user_id,
            target_username,
        )

    def _get_active_server_data(self) -> dict | None:
        return gl_server_selection._get_active_server_data(self)


    def _block_chat_user(self, user_id_to_block: int, username_to_block: str):
        return gl_chat_blocking._block_chat_user(
            self,
            user_id_to_block,
            username_to_block,
        )

    def _unblock_chat_user(self, user_id_to_unblock: int, username_to_unblock: str):
        return gl_chat_blocking._unblock_chat_user(
            self,
            user_id_to_unblock,
            username_to_unblock,
        )

    def _on_chat_list_right_click(self, event):
        return gl_chat_context_actions._on_chat_list_right_click(self, event)

    def _initiate_chat_from_context_menu(self, item_iid_to_select: str):
        return gl_chat_context_actions._initiate_chat_from_context_menu(
            self,
            item_iid_to_select,
        )


    def _handle_leave_room_success(
        self, success_message: str, room_id_left: int, user_id_left: int
    ):
        return gl_chat_rooms._handle_leave_room_success(
            self,
            success_message,
            room_id_left,
            user_id_left,
        )


    def _join_room_dialog(self, room_id: int):
        return gl_chat_rooms._join_room_dialog(self, room_id)


    def _handle_join_room_success(self, success_message: str, room_id_joined: int):
        return gl_chat_rooms._handle_join_room_success(
            self,
            success_message,
            room_id_joined,
        )

    def _leave_room_action(self, room_id: int):
        return gl_chat_rooms._leave_room_action(self, room_id)


    def _fetch_room_members_and_store(self, room_id: int):
        return gl_chat_rooms._fetch_room_members_and_store(self, room_id)


    def _create_room_dialog(self):
        return gl_chat_rooms._create_room_dialog(self)

    def _handle_create_room_success(self, data: dict, dialog_window: tk.Toplevel):
        return gl_chat_rooms._handle_create_room_success(self, data, dialog_window)


    def _fetch_more_chat_history(self):
        return gl_chat_history._fetch_more_chat_history(self)

    def _edit_chat_username_dialog(self):
        return gl_chat_user_profile._edit_chat_username_dialog(self)

    def _handle_username_update_success(self, data: dict, dialog_window: tk.Toplevel):
        return gl_chat_user_profile._handle_username_update_success(
            self,
            data,
            dialog_window,
        )

    def _confirm_delete_chat_account(self):
        return gl_chat_user_profile._confirm_delete_chat_account(self)

    def _handle_account_deletion_response(
        self, data: dict | None, error_message: str | None
    ):
        return gl_chat_user_profile._handle_account_deletion_response(
            self,
            data,
            error_message,
        )

    def _update_reply_preview_ui(self):
        return gl_chat_message_actions._update_reply_preview_ui(self)


    def _cancel_reply_mode(self):
        return gl_chat_message_actions._cancel_reply_mode(self)


    def _parse_text_for_links(self, text_content):
        return gl_chat_render._parse_text_for_links(self, text_content)


    def _create_chat_message_tags_if_needed(self):
        return gl_chat_render._create_chat_message_tags_if_needed(self)


    def _check_and_mark_read(self):
        return gl_chat_interactions._check_and_mark_read(self)


    def _on_chat_message_search_change(self, *args):
        return gl_chat_interactions._on_chat_message_search_change(self, *args)


    def _clear_chat_message_search(self):
        return gl_chat_interactions._clear_chat_message_search(self)

    def _apply_chat_message_filter(self):
        return gl_chat_interactions._apply_chat_message_filter(self)


    def _select_and_upload_chat_file(self):
        return gl_chat_messaging._select_and_upload_chat_file(self)

    def _upload_file_thread(self, files_payload, progress_window_ref, file_to_close=None):
        return gl_chat_messaging._upload_file_thread(self, files_payload, progress_window_ref, file_to_close=file_to_close)


    def _handle_file_upload_response(self, upload_data, error_message):
        return gl_chat_messaging._handle_file_upload_response(self, upload_data, error_message)


    def _chat_login(self):
        return gl_chat_auth._chat_login(self)


    def _on_remember_me_toggle(self):
        return gl_chat_auth._on_remember_me_toggle(self)


    def _on_auto_login_toggle(self):
        return gl_chat_auth._on_auto_login_toggle(self)


    def _chat_register(self):
        return gl_chat_auth._chat_register(self)


    def _chat_logout(self):
        return gl_chat_auth._chat_logout(self)


    def _on_chat_display_resize(self, event=None):
        return gl_chat_ui._on_chat_display_resize(self, event=event)

    def _update_chat_ui_state(self):
        return gl_chat_auth._update_chat_ui_state(self)


    def _is_user_blocked(self, user_id_to_check: int) -> bool:
        return gl_chat_blocking._is_user_blocked(self, user_id_to_check)

    def _update_chat_ui_for_blocked_status(self):
        return gl_chat_auth._update_chat_ui_for_blocked_status(self)


    def _on_message_edited_event(self, updated_message_data: dict):
        return gl_chat_message_actions._on_message_edited_event(
            self,
            updated_message_data,
        )

    def _filter_chat_users(self):
        return gl_chat_ui._filter_chat_users(self)

    def _reset_chat_search_field(self):
        return gl_chat_ui._reset_chat_search_field(self)


    def _connect_to_chat_server(self):
        return gl_chat_socket._connect_to_chat_server(self)


    def _update_typing_indicator(self):
        return gl_chat_ui._update_typing_indicator(self)


    def _on_chat_input_key_press(self, event=None):
        return gl_chat_messaging._on_chat_input_key_press(self, event=event)


    def _handle_typing_start_logic(self):
        return gl_chat_messaging._handle_typing_start_logic(self)


    def _check_typing_status_timeout(self):
        return gl_chat_messaging._check_typing_status_timeout(self)


    def _send_typing_stop_event(self):
        return gl_chat_messaging._send_typing_stop_event(self)


    def _select_chat_attachment_dialog(self):
        return gl_chat_messaging._select_chat_attachment_dialog(self)


    def _clear_pending_chat_attachment(self):
        return gl_chat_messaging._clear_pending_chat_attachment(self)


    def _update_pending_attachment_ui(self):
        return gl_chat_messaging._update_pending_attachment_ui(self)


    def _on_chat_user_select(self, event=None):
        return gl_chat_interactions._on_chat_user_select(self, event=event)


    def _reset_to_chat_dashboard(self):
        return gl_chat_dashboard._reset_to_chat_dashboard(self)


    def _load_and_display_room_members(self, room_id: int):
        return gl_chat_data._load_and_display_room_members(self, room_id)


    def _update_chat_partner_details(self, partner_id_to_update: int):
        return gl_chat_dashboard._update_chat_partner_details(self, partner_id_to_update)


    def _refresh_chat_dashboard_if_visible(self):
        return gl_chat_dashboard._refresh_chat_dashboard_if_visible(self)


    def _show_or_hide_room_members_panel(self, show: bool):
        return gl_chat_data._show_or_hide_room_members_panel(self, show)


    def _show_chat_dashboard(self):
        return gl_chat_dashboard._show_chat_dashboard(self)


    def _display_chat_messages_from_history(self, partner_id):
        return gl_chat_dashboard._display_chat_messages_from_history(self, partner_id)


    # --- ZMIANY W _display_chat_message dla obsługi załączników ---

    # --- ZMIANY W _display_chat_message dla obsługi załączników ---
    # --- ZMIANY W _display_chat_message dla obsługi załączników ---


    def _display_chat_message(
        self,
        message_text_with_timestamp,
        msg_type="normal",
        attachment_data=None,
        message_id=None,
        is_read_by_receiver=False,
        sender_id_for_read_status_check=None,
        replied_to_message_preview=None,
        message_data=None,
    ):
        return gl_chat_render._display_chat_message(
            self,
            message_text_with_timestamp,
            msg_type=msg_type,
            attachment_data=attachment_data,
            message_id=message_id,
            is_read_by_receiver=is_read_by_receiver,
            sender_id_for_read_status_check=sender_id_for_read_status_check,
            replied_to_message_preview=replied_to_message_preview,
            message_data=message_data,
        )


    def _on_message_read_update(
        self, data
    ):  # Upewnij się, że nazwa jest poprawna i bindowana
        return gl_chat_message_actions._on_message_read_update(self, data)

    def _show_chat_message_context_menu(
        self, event, message_id, message_bubble_container
    ):
        return gl_chat_message_actions._show_chat_message_context_menu(
            self,
            event,
            message_id,
            message_bubble_container,
        )

    def _edit_chat_message_dialog(self, message_data_to_edit: dict):
        return gl_chat_message_actions._edit_chat_message_dialog(
            self,
            message_data_to_edit,
        )


    def _confirm_and_delete_chat_message(self, message_id_to_delete):
        return gl_chat_message_actions._confirm_and_delete_chat_message(
            self,
            message_id_to_delete,
        )

    # Metoda do obsługi potwierdzenia usunięcia wiadomości z serwera
    # Będzie bindowana do eventu SocketIO
    def _on_message_deleted_event(self, data):
        return gl_chat_message_actions._on_message_deleted_event(self, data)

    def _go_to_server_selection_from_chat_auth(self):
        return gl_chat_auth._go_to_server_selection_from_chat_auth(self)


    def _go_to_server_selection_from_chat_main(self):
        return gl_chat_auth._go_to_server_selection_from_chat_main(self)


    def _apply_chat_message_tags_and_alignment(self):
        return gl_chat_render._apply_chat_message_tags_and_alignment(self)

    def _load_and_display_chat_image_thumbnail(self, image_url, target_label_widget, message_id_for_cache=None):
        return gl_chat_render._load_and_display_chat_image_thumbnail(self, image_url, target_label_widget, message_id_for_cache=message_id_for_cache)


    def _update_image_label(self, label_widget, photo_image, original_url, log_prefix_outer=""):
        return gl_chat_render._update_image_label(self, label_widget, photo_image, original_url, log_prefix_outer=log_prefix_outer)


    def _display_active_chat_history(self, partner_id):
        return gl_chat_history._display_active_chat_history(self, partner_id)

    def _update_send_button_state(self):
        return gl_chat_interactions._update_send_button_state(self)


    def _jump_to_message(self, target_message_id: int):
        return gl_chat_render._jump_to_message(self, target_message_id)


    def _highlight_message_widget(self, widget_to_highlight):
        return gl_chat_render._highlight_message_widget(self, widget_to_highlight)


    def _reset_widget_bg_after_highlight(self, widget, original_main_bg, children_colors):
        return gl_chat_render._reset_widget_bg_after_highlight(self, widget, original_main_bg, children_colors)


    def _format_chat_date(self, chat_date: datetime.date) -> str:
        return gl_chat_dashboard._format_chat_date(self, chat_date)


    def _fetch_chat_users(self):
        return gl_chat_data._fetch_chat_users(self)


    def _load_and_display_chat_history(self, current_user_id, partner_or_room_id, chat_type=None):
        return gl_chat_history._load_and_display_chat_history(self, current_user_id, partner_or_room_id, chat_type=chat_type)


    def _display_join_room_prompt(self, room_name: str, room_id: int):
        return gl_chat_message_actions._display_join_room_prompt(
            self,
            room_name,
            room_id,
        )


    def _add_message_to_history(
        self, message_data: dict, is_sent_by_me: bool, message_context: str
    ):  # Dodano message_context
        return gl_chat_history._add_message_to_history(
            self,
            message_data,
            is_sent_by_me,
            message_context,
        )


    def _set_reply_mode(self, message_data_to_quote: dict):
        return gl_chat_message_actions._set_reply_mode(self, message_data_to_quote)


    def _notify_new_chat_message(
        self, source_id, sender_username, message_content, message_context
    ):
        return gl_chat_history._notify_new_chat_message(
            self, source_id, sender_username, message_content, message_context
        )


    def _clear_new_message_notification(self, partner_or_room_id, chat_type: str | None = None):
        return gl_chat_data._clear_new_message_notification(self, partner_or_room_id, chat_type=chat_type)


    def _load_saved_chat_credentials(self):
        return gl_chat_navigation._load_saved_chat_credentials(self)


    def _send_chat_message(self, event=None):
        return gl_chat_messaging._send_chat_message(self, event=event)


    def _emit_chat_message(self, payload: dict):
        return gl_chat_messaging._emit_chat_message(self, payload)


    def show_server_selection_page(self):
        return gl_server_selection.show_server_selection_page(self)


    def _create_server_selection_page_content(self):
        return gl_server_selection._create_server_selection_page_content(self)


    def _load_chat_servers_to_treeview(self):
        return gl_server_selection._load_chat_servers_to_treeview(self)


    def _add_edit_chat_server_dialog(self, edit_mode=False):
        return gl_server_selection._add_edit_chat_server_dialog(self, edit_mode=edit_mode)


    def _delete_chat_server_dialog(self):
        return gl_server_selection._delete_chat_server_dialog(self)


    # Potrzebna nowa metoda pomocnicza do aktualizacji ustawień po zmianie aktywnego serwera
    def _update_active_server_dependent_settings(self):
        return gl_server_selection._update_active_server_dependent_settings(self)


    def _connect_to_selected_server(self):
        return gl_server_selection._connect_to_selected_server(self)


    def _save_auto_connect_setting(self):
        return gl_server_selection._save_auto_connect_setting(self)


    # --- Metoda do cyklicznej aktualizacji overlay'a z GameLauncher ---
    def _update_overlay_regularly(self):
        return gl_overlay_runtime._update_overlay_regularly(self)

    def _set_music_hotkey_dialog(
        self,
        action_key: str,
        string_var_to_update: tk.StringVar,
        entry_widget_to_update: ttk.Entry,
    ):
        return gl_hotkey_capture._set_music_hotkey_dialog(
            self,
            action_key,
            string_var_to_update,
            entry_widget_to_update,
        )

    def _cancel_hotkey_capture(self):
        return gl_hotkey_capture._cancel_hotkey_capture(self)

    def _music_action_callback(self, action_key):
        return gl_hotkey_runtime._music_action_callback(self, action_key)

    def _register_music_hotkeys(self):
        return gl_hotkey_runtime._register_music_hotkeys(self)

    def _reregister_all_global_hotkeys(self):
        return gl_hotkey_runtime._reregister_all_global_hotkeys(self)

    def _music_control_stop(self):
        return gl_hotkey_runtime._music_control_stop(self)

    def _music_control_volume_up(self):
        return gl_hotkey_runtime._music_control_volume_up(self)

    def _music_control_volume_down(self):
        return gl_hotkey_runtime._music_control_volume_down(self)

    def toggle_library_view(self):  # POPRAWNE WCIĘCIE
        return gl_library_view.toggle_library_view(self)

    def _capture_initial_root_size(self):
        return gl_library_view._capture_initial_root_size(self)


    def update_view_mode_button_text(self):  # POPRAWNE WCIĘCIE
        return gl_library_view.update_view_mode_button_text(self)


    def toggle_fullscreen(self):
        return gl_library_view.toggle_fullscreen(self)

    def ask_for_username(self):
        return gl_window_ops.ask_for_username(self)

    def create_sidebar(self):
        return gl_sidebar_ui.create_sidebar(self)

    def create_header(self):
        return gl_library_header.create_header(self)


    def show_statistics_page(self):
        return gl_stats_navigation.show_statistics_page(self)


    def create_statistics_page(self):
        return gl_stats_page.create_statistics_page(self)

    # Zaktualizuj _on_period_change, aby poprawnie umieszczał custom_range_frame

    def _on_period_change(self, event=None):
        return gl_stats_controls._on_period_change(self, event=event)

    def _get_time_period_dates(self):
        return gl_stats_controls._get_time_period_dates(self)

    def _update_launcher_usage_display(self):
        return gl_usage_runtime._update_launcher_usage_display(self)


    def reset_launcher_usage_time(self):
        return gl_usage_runtime.reset_launcher_usage_time(self)

    def _prepare_chart_data(self):
        return gl_stats_data._prepare_chart_data(self)

    def _generate_matplotlib_figure(self, chart_data, view_type_display):
        return gl_stats_chart._generate_matplotlib_figure(
            self,
            chart_data,
            view_type_display,
        )


    def _on_refresh_stats_threaded(self):
        return gl_stats_runtime._on_refresh_stats_threaded(self)

    def _generate_stats_in_thread(self):
        return gl_stats_runtime._generate_stats_in_thread(self)

    def _check_stats_queue(self):
        return gl_stats_runtime._check_stats_queue(self)

    def _update_stats_chart(self, figure):
        return gl_stats_runtime._update_stats_chart(self, figure)

    def _show_total_playtime_details(self):
        return gl_stats_runtime._show_total_playtime_details(self)

    def show_music_page(self):
        return gl_music_navigation.show_music_page(self)

    def _on_chart_click(self, event):
        return gl_stats_runtime._on_chart_click(self, event)

    def _show_daily_games_details(self, games_set):
        return gl_stats_runtime._show_daily_games_details(self, games_set)

    def get_all_tags(self):
        return gl_library_tags.get_all_tags(self)

    def _update_current_session_time_display(self):
        return gl_usage_runtime._update_current_session_time_display(self)


    def update_tag_filter_options(self):
        return gl_library_tags.update_tag_filter_options(self)

    def reset_and_update_grid(self, *_args):
        """Resetuje paginację i odświeża siatkę."""
        self.reset_pagination()
        self.update_game_grid()

    def change_language(self, selected_language):
        self.settings["language"] = selected_language
        save_config(self.config)
        self.translator.set_language(selected_language)
        # Odśwież interfejs
        self.refresh_ui()

    def refresh_ui(self):
        return gl_app_navigation.refresh_ui(self)

    def get_all_genres(self):
        genres = set()
        for game in self.games.values():
            genres.update(game.get("genres", []))
        genres.update(self.settings.get("custom_genres", []))
        return sorted(genres)

    def update_genre_menu(self):
        return gl_library_genres.update_genre_menu(self)

    def manage_genres(self):
        from ui.manage_genres_window import ManageGenresWindow

        ManageGenresWindow(self.root, self)

    def _monitor_discord_connection(self):
        return gl_discord_runtime._monitor_discord_connection(self)

    def _load_achievement_definitions(self):
        return gl_achievements_defs._load_achievement_definitions(self)

    def delete_group(self):
        return gl_library_groups_runtime.delete_group(self)

    def setup_key_bindings(self):
        self.root.bind_all("<Up>", self.focus_prev_widget)
        self.root.bind_all("<Down>", self.focus_next_widget)
        self.root.bind_all("<Left>", self.focus_prev_widget)
        self.root.bind_all("<Right>", self.focus_next_widget)
        self.root.bind_all("<Return>", self.activate_focused_widget)

    def activate_focused_widget(self, event):
        widget = self.root.focus_get()
        if isinstance(widget, ttk.Button):
            widget.invoke()
        elif isinstance(widget, ttk.Entry):
            widget.event_generate("<Return>")
        return "break"

    # ------------------------------------------------------------------
    # ===  BIG-PICTURE / PAD-ONLY  =====================================
    # ------------------------------------------------------------------

    def _enter_big_picture_mode(self):
        if getattr(self, "big_picture_mode", False):
            return  # już włączone
        self.big_picture_mode = True
        logging.info("→ Włączono tryb Big-picture")
        # 1) większe kafelki
        self.local_settings["tiles_per_row"] = 3
        self.current_tile_width = 300
        # 2) powiększona domyślna czcionka
        ttk.Style(self.root).configure("TLabel", font=("Segoe UI", 11))
        ttk.Style(self.root).configure("Tile.TButton", font=("Segoe UI", 9))
        # 3) odśwież widok
        self.reset_and_update_grid()

    def _exit_big_picture_mode(self):
        if not getattr(self, "big_picture_mode", False):
            return
        self.big_picture_mode = False
        logging.info("← Wyłączono tryb Big-picture")
        self.local_settings["tiles_per_row"] = 5
        self.current_tile_width = 200
        ttk.Style(self.root).configure("TLabel", font=("Segoe UI", 9))
        ttk.Style(self.root).configure("Tile.TButton", font=("Segoe UI", 7))
        self.reset_and_update_grid()

    # ------------------------------------------------------------------
    def controller_listener(self):
        return gl_gamepad_runtime.controller_listener(self)

    # ------------------------------------------------------------------
    # Zamieniamy domyślne metody focusa na wersję poziomą,
    # jeśli big-picture włączony.
    def focus_next_widget(self, event):
        if getattr(self, "big_picture_mode", False):
            # w poziomie → cały czas Right
            self.root.event_generate("<Right>")
        else:
            event.widget.tk_focusNext().focus()
        return "break"

    def focus_prev_widget(self, event):
        if getattr(self, "big_picture_mode", False):
            self.root.event_generate("<Left>")
        else:
            event.widget.tk_focusPrev().focus()
        return "break"

    def create_home_page(self):
        return gl_home_page_runtime.create_home_page(self)

    def _bind_details_resize(self):
        """Podpina <Configure> tylko raz – unikamy wielokrotnego bindowania."""
        if not getattr(self, "_details_resize_bound", False):
            self.details_frame.bind("<Configure>", self._on_details_frame_resize)
            self._details_resize_bound = True

    def _on_details_frame_resize(self, event):
        """
        Dynamicznie skaluje kolumny Treeview, aby zawsze mieściły się w oknie.
        Góra i dół statystyk NIEWZRUSZONE – zmieniamy jedynie szerokość kolumn.
        """
        try:
            # Całkowita szerokość ramki z tabelką (bez paska przewijania)
            total = self.details_frame.winfo_width()

            col2_w = 100  # „Czas w okresie” – stałe ~100 px
            col1_w = max(
                150, total - col2_w - 20
            )  # 20 px zapasu na padding + scrollbar

            # Pierwsza kolumna rozciąga się, druga nie
            self.details_tree.column("Col1", width=col1_w, stretch=True, anchor="w")
            self.details_tree.column("Col2", width=col2_w, stretch=False, anchor="e")
        except tk.TclError:
            # okno w trakcie niszczenia – ignorujemy
            pass


    def create_statistics(self, parent):
        most_played_games = sorted(
            self.games.items(), key=lambda x: x[1].get("play_time", 0), reverse=True
        )
        num_most_played = min(
            10, len(most_played_games)
        )  # Możesz zmienić 10 na dowolną liczbę
        frame = ttk.LabelFrame(parent, text="Statystyki Ogólne")
        frame.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")

        # Najdłużej grane gry
        ttk.Label(
            frame, text="Najdłużej Grane Gry:", font=("Helvetica", 12, "bold")
        ).grid(row=0, column=0, sticky="w")
        for idx, (game_name, game_data) in enumerate(
            most_played_games[:num_most_played]
        ):
            play_time = self.format_play_time(game_data.get("play_time", 0))
            ttk.Label(frame, text=f"{idx + 1}. {game_name} - {play_time}").grid(
                row=idx + 1, column=0, sticky="w"
            )
        # Możesz dodać więcej statystyk według potrzeb

    def _create_or_overwrite_autosave(self, game_name):
        return gl_autosave_runtime._create_or_overwrite_autosave(self, game_name)

    def _copy_with_progress_thread(self, src, dst, total_files):
        return gl_autosave_runtime._copy_with_progress_thread(
            self, src, dst, total_files
        )

    def _update_copy_progress_ui(self, percent, text):
        """Aktualizuje pasek postępu i etykietę (wywoływane przez root.after)."""
        if hasattr(self, "progress_window") and self.progress_window.winfo_exists():
            if (
                self.progress_bar["mode"] == "indeterminate"
            ):  # Zmień na deterministyczny, jeśli trzeba
                self.progress_bar.stop()
                self.progress_bar["mode"] = "determinate"
            self.progress_bar["value"] = percent
            self.progress_label.config(text=text)
            # self.progress_window.update_idletasks() # Niekonieczne w root.after

    def _destroy_progress_window(self):
        return gl_backup_restore._destroy_progress_window(self)

    def monitor_game_sessions(self):
        return gl_session_monitor_runtime.monitor_game_sessions(self)

    def prompt_checklist_update(self, game_name):
        """Sprawdza checklistę i pyta użytkownika, czy chce ją zaktualizować."""
        game_data = self.games.get(game_name)
        if not game_data:
            return

        checklist = game_data.get("checklist", [])
        # Sprawdź, czy lista istnieje i czy są na niej NIEUKOŃCZONE zadania
        has_pending_tasks = any(not item.get("done", False) for item in checklist)

        if (
            checklist and has_pending_tasks
        ):  # Pytaj tylko, jeśli lista istnieje i ma coś do zrobienia
            logging.info(f"Gra '{game_name}' ma nieukończone zadania na checkliście.")
            if messagebox.askyesno(
                "Checklista Zadań",
                f"Zakończyłeś sesję w '{game_name}'.\nCzy chcesz teraz przejrzeć/zaktualizować checklistę zadań dla tej gry?",
                parent=self.root,  # Użyj głównego okna jako rodzica
            ):
                logging.info(f"Użytkownik chce otworzyć checklistę dla '{game_name}'.")
                self._show_game_details_and_select_tab(game_name, "Checklista")

    def _show_game_details_and_select_tab(self, game_name, tab_text):
        """Otwiera (lub podnosi) okno szczegółów gry i aktywuje określoną zakładkę."""
        from ui.game_details import GameDetailsWindow

        details_window = None
        details_title = f"Szczegóły Gry - {game_name}"

        # Sprawdź, czy okno już istnieje
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Toplevel) and widget.title() == details_title:
                if isinstance(
                    widget, GameDetailsWindow
                ):  # Upewnij się, że to właściwy typ okna
                    details_window = widget
                    break

        if details_window and details_window.winfo_exists():
            logging.debug(
                f"Okno szczegółów dla '{game_name}' już otwarte. Podnoszenie i zmiana zakładki."
            )
            details_window.lift()
            details_window.focus_force()
        else:
            logging.debug(
                f"Tworzenie nowego okna szczegółów dla '{game_name}', aby pokazać zakładkę '{tab_text}'."
            )
            details_window = GameDetailsWindow(
                self.root, self, game_name
            )  # Utwórz nowe okno, jeśli nie ma

        # Wybierz zakładkę (po krótkiej chwili, aby UI zdążyło się zainicjować)
        if details_window and hasattr(details_window, "notebook"):
            self.root.after(
                100,
                lambda dw=details_window, txt=tab_text: self._select_notebook_tab(
                    dw, txt
                ),
            )
        else:
            logging.error(
                "Nie można wybrać zakładki - okno szczegółów lub notebook nie istnieje."
            )

    def _select_notebook_tab(self, details_window, tab_text):
        """Pomocnicza funkcja do wybierania zakładki w Notebooku."""
        try:
            if details_window.winfo_exists():  # Sprawdź ponownie przed operacją
                tab_id = None
                for i, text in enumerate(details_window.notebook.tabs()):
                    if details_window.notebook.tab(i, "text") == tab_text:
                        tab_id = (
                            text  # tabs() zwraca identyfikatory widgetów, nie tekst
                        )
                        break
                if tab_id:
                    details_window.notebook.select(tab_id)
                    logging.debug(f"Wybrano zakładkę '{tab_text}'.")
                else:
                    logging.warning(f"Nie znaleziono zakładki o tekście '{tab_text}'.")
        except tk.TclError as e:
            logging.warning(
                f"Błąd TclError podczas wybierania zakładki '{tab_text}': {e}"
            )
        except Exception as e:
            logging.exception(f"Nieoczekiwany błąd podczas wybierania zakładki: {e}")

    def _update_button_on_game_close(self, game_name):
        return gl_game_process_runtime._update_button_on_game_close(self, game_name)

    def prompt_completion(self, game_name):
        """Pyta użytkownika o procent ukończenia gry po jej zakończeniu."""
        completion = simpledialog.askinteger(
            "Procent ukończenia",
            f"Ile procent gry '{game_name}' ukończyłeś?",
            minvalue=0,
            maxvalue=100,
        )
        if completion is not None:
            self.games[game_name]["completion"] = completion
        else:
            self.games[game_name]["completion"] = self.games[game_name].get(
                "completion", 0
            )
        save_config(self.config)
        self.check_and_unlock_achievements()
        self.update_game_grid()
        self.update_time_stats()
        self.create_home_page()  # Odświeżenie strony głównej

    def create_recently_played(self, parent, row=0, column=0):
        frame = ttk.LabelFrame(parent, text="Ostatnio Grane")
        frame.grid(row=row, column=column, padx=10, pady=10, sticky="nsew")
        parent.rowconfigure(row, weight=1)
        parent.columnconfigure(column, weight=1)

        # Ostatnie 5 granych gier
        recent_games = sorted(
            [g for g in self.games.values() if g.get("last_played")],
            key=lambda x: x["last_played"],
            reverse=True,
        )[:5]

        for idx, game in enumerate(recent_games):
            game_name = [name for name, data in self.games.items() if data == game][0]
            btn = ttk.Button(
                frame, text=game_name, command=lambda gn=game_name: self.launch_game(gn)
            )
            btn.grid(row=idx, column=0, padx=5, pady=5, sticky="w")

    def create_time_stats(self, parent, row: int = 0, column: int = 1) -> None:
        return gl_playtime_stats_runtime.create_time_stats(
            self, parent, row=row, column=column
        )

    def update_time_stats(self, *_):
        return gl_playtime_stats_runtime.update_time_stats(self, *_)

    def get_total_play_time(
        self,
        period: str = "week",
        game_type: str | None = None,  # "pc" / "emulator" / None-=-oba
        emulator_name: str | None = None,  # gdy chcesz sumę tylko danego emulatora
    ) -> float:
        return gl_playtime_stats_runtime.get_total_play_time(
            self,
            period=period,
            game_type=game_type,
            emulator_name=emulator_name,
        )

    def create_random_games(self, parent, row=1, column=0):
        frame = ttk.LabelFrame(parent, text="Losowe Gry")
        frame.grid(row=row, column=column, padx=10, pady=10, sticky="nsew")
        parent.rowconfigure(row, weight=1)
        parent.columnconfigure(column, weight=1)

        # Wybierz do 10 losowych gier
        if self.games:
            num_random_games = min(
                10, len(self.games)
            )  # Możesz zmienić 10 na dowolną liczbę
            random_games = random.sample(list(self.games.keys()), num_random_games)
            for idx, game_name in enumerate(random_games):
                btn = ttk.Button(
                    frame,
                    text=game_name,
                    command=lambda gn=game_name: self.launch_game(gn),
                )
                btn.grid(row=idx, column=0, padx=5, pady=5, sticky="w")
        else:
            ttk.Label(frame, text="Brak gier w bibliotece.").grid(
                row=0, column=0, padx=5, pady=5
            )

    def create_game_grid(self):
        return gl_library_grid_runtime.create_game_grid(self)

    def on_mouse_wheel(self, event):
        """Przewijanie za pomocą kółka myszy."""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def format_play_time(self, seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

    def _save_and_apply_font_setting(self, event=None):
        return gl_theme_runtime._save_and_apply_font_setting(self, event=event)

    def _update_home_lists(self, *_):
        """Przelicza ile przycisków zmieści się w danej wysokości
        i odświeża obie listy bez scroll-barów."""
        if not (self.home_frame.winfo_exists() and self.recent_frame.winfo_exists()):
            return

        self.recent_frame.update_idletasks()
        self.random_frame.update_idletasks()

        # wysokość przycisku ≈ 30 px  (u Ciebie może być inna – dostosuj!)
        btn_h = 30
        pad = 8
        avail_recent = max(1, (self.recent_frame.winfo_height() // (btn_h + pad)) - 1)
        avail_random = max(1, (self.random_frame.winfo_height() // (btn_h + pad)) - 1)

        self._populate_recently_played(avail_recent)
        self._populate_random_games(avail_random)

    def _populate_recently_played(self, limit: int):
        for w in self.recent_frame.winfo_children():
            w.destroy()

        recent_games = sorted(
            (g for g in self.games.values() if g.get("last_played")),
            key=lambda d: d["last_played"],
            reverse=True,
        )[:limit]

        for g in recent_games:
            name = next(k for k, v in self.games.items() if v is g)
            ttk.Button(
                self.recent_frame, text=name, command=lambda n=name: self.launch_game(n)
            ).pack(anchor="w", padx=5, pady=4, fill="x")

    def _populate_random_games(self, limit: int):
        for w in self.random_frame.winfo_children():
            w.destroy()

        if not self.games:
            ttk.Label(self.random_frame, text="Brak gier.").pack(
                anchor="w", padx=5, pady=4
            )
            return

        sample = random.sample(list(self.games.keys()), min(limit, len(self.games)))
        for name in sample:
            ttk.Button(
                self.random_frame, text=name, command=lambda n=name: self.launch_game(n)
            ).pack(anchor="w", padx=5, pady=4, fill="x")

    def apply_font_settings(self, selected_font=None):
        return gl_theme_runtime.apply_font_settings(self, selected_font=selected_font)

    def _reset_single_achievement_progress(self, ach_id: str) -> None:
        """
        Usuwa z self.user['achievements'] wpis dotyczący wskazanego osiągnięcia
        (czyli: zeruje postęp i status „unlocked”), a następnie zapisuje config.
        """
        self.user.setdefault("achievements", {}).pop(ach_id, None)
        save_config(self.config)

    def launch_game(self, game_name, profile=None):
        return gl_game_process_runtime.launch_game(self, game_name, profile=profile)

    def track_play_time(self, game_name):
        start_time = time.time()
        while self.is_game_running(game_name):
            time.sleep(1)
        end_time = time.time()
        elapsed = end_time - start_time
        self.games[game_name]["play_time"] += elapsed

        # Loguj sesję
        self.games[game_name].setdefault("play_sessions", []).append(
            {"start": start_time, "end": end_time}
        )

        save_config(self.config)
        # Schedule GUI update in the main thread
        self.root.after(0, self.update_after_game, game_name)

    def update_after_game(self, game_name):
        # Zapytaj o procent ukończenia gry
        completion = simpledialog.askinteger(
            "Procent ukończenia", f"Ile procent gry '{game_name}' ukończyłeś?"
        )
        if completion is not None:
            self.games[game_name]["completion"] = completion
        else:
            self.games[game_name]["completion"] = self.games[game_name].get(
                "completion", 0
            )
        save_config(self.config)
        self.update_game_grid()
        self.update_time_stats()
        self.create_home_page()  # Odświeżenie strony głównej

    def is_game_running(self, game_name):
        return gl_game_process_runtime.is_game_running(self, game_name)

    def close_game(self, game_name):
        return gl_game_process_runtime.close_game(self, game_name)

    def reset_stats(self, game_name):
        confirm = messagebox.askyesno(
            "Resetuj Statystyki",
            f"Czy na pewno chcesz zresetować statystyki gry '{game_name}'?",
        )
        if confirm:
            self.games[game_name]["play_time"] = 0
            self.games[game_name]["completion"] = 0
            self.games[game_name]["play_sessions"] = []
            save_config(self.config)
            self.update_game_grid()
            self.update_time_stats()

    def manage_saves(self, game_name):
        from ui.save_manager import SaveManager

        save_manager = SaveManager(self.root, game_name, self.games[game_name], self)
        self.root.wait_window(save_manager.top)

    def _load_emulators_list(self):
        return gl_emulator_settings_runtime._load_emulators_list(self)

    def _add_edit_emulator(self, edit_mode=False):
        return gl_emulator_settings_runtime._add_edit_emulator(
            self, edit_mode=edit_mode
        )

    def _select_emulator_exe(self, string_var, parent_dialog):
        return gl_emulator_settings_runtime._select_emulator_exe(
            self, string_var, parent_dialog
        )

    def _delete_emulator(self):
        return gl_emulator_settings_runtime._delete_emulator(self)

    def add_game(self):
        return gl_game_crud_runtime.add_game(self)

    def _export_custom_theme_dialog(self):
        return gl_theme_runtime._export_custom_theme_dialog(self)

    def _import_custom_theme_dialog(self):
        return gl_theme_runtime._import_custom_theme_dialog(self)

    def _process_theme_import(self, json_string, parent_window):
        return gl_theme_runtime._process_theme_import(self, json_string, parent_window)

    def edit_game(self, game_name):
        return gl_game_crud_runtime.edit_game(self, game_name)

    def _force_refresh_tile(self, game_name):
        return gl_game_crud_runtime._force_refresh_tile(self, game_name)

    def delete_game(self, game_name):
        return gl_game_crud_runtime.delete_game(self, game_name)

    def add_group(self):
        return gl_library_groups_runtime.add_group(self)

    def add_to_group(self, game_name):
        groups = list(self.groups.keys())
        if not groups:
            messagebox.showwarning(
                "Błąd", "Nie utworzono żadnych grup. Najpierw dodaj grupę."
            )
            return

        selected_group = simpledialog.askstring(
            "Dodaj do Grupy",
            f"Wybierz grupę dla gry '{game_name}':\n" + "\n".join(groups),
        )
        if selected_group in groups:
            if game_name not in self.groups[selected_group]:
                self.groups[selected_group].append(game_name)
                save_config(self.config)
                messagebox.showinfo(
                    "Sukces",
                    f"Gra '{game_name}' została dodana do grupy '{selected_group}'.",
                )
            else:
                messagebox.showwarning(
                    "Błąd",
                    f"Gra '{game_name}' już znajduje się w grupie '{selected_group}'.",
                )
        else:
            messagebox.showwarning("Błąd", "Wybrana grupa nie istnieje.")

    def remove_from_group(self, game_name):
        group = self.group_var.get()
        if group != "Wszystkie Gry":
            if game_name in self.groups.get(group, []):
                self.groups[group].remove(game_name)
                save_config(self.config)
                messagebox.showinfo(
                    "Sukces", f"Gra '{game_name}' została usunięta z grupy '{group}'."
                )
                # self.update_game_grid() # Zamiast tego:
                self.reset_and_update_grid()  # Odśwież widok bieżącej grupy (teraz bez tej gry)
            else:
                messagebox.showwarning(
                    "Błąd", f"Gra '{game_name}' nie znajduje się w grupie '{group}'."
                )

    def show_home(self):
        return gl_app_navigation.show_home(self)


    def show_mod_manager(self):
        return gl_app_navigation.show_mod_manager(self)

    # Dodaj metodę _show_developer_console w klasie GameLauncher
    def _show_developer_console(self):
        return gl_app_navigation._show_developer_console(self)

    def _post_init_heavy_jobs(self):
        return gl_init_constructor_runtime._post_init_heavy_jobs(self)

    def show_library(self):
        return gl_app_navigation.show_library(self)

    def preload_library_view(self):
        return gl_app_navigation.preload_library_view(self)

    def preload_roadmap_view(self):
        return gl_app_navigation.preload_roadmap_view(self)

    def preload_music_page(self):
        return gl_app_navigation.preload_music_page(self)

    def get_all_available_themes(self):
        return gl_theme_runtime.get_all_available_themes(self)

    def change_theme(self, selected_theme_name):  # Zmieniono argument na nazwę
        return gl_theme_runtime.change_theme(self, selected_theme_name)

    def apply_theme(self, theme_def):  # Argument to teraz słownik definicji
        return gl_theme_runtime.apply_theme(self, theme_def)

    def _update_main_theme_selector(self):
        return gl_theme_runtime._update_main_theme_selector(self)

    def _load_custom_themes_list(self):
        return gl_theme_runtime._load_custom_themes_list(self)

    def _add_custom_theme(self):
        return gl_theme_runtime._add_custom_theme(self)

    def _edit_custom_theme(self):
        return gl_theme_runtime._edit_custom_theme(self)

    def _delete_custom_theme(self):
        return gl_theme_runtime._delete_custom_theme(self)

    def select_background_image(self):
        path = filedialog.askopenfilename(filetypes=[("Obrazy", "*.png;*.jpg;*.jpeg")])
        if path:
            self.background_image_var.set(path)
            self.settings["background_image"] = path
            save_config(self.config)
            self.apply_background_image(path)

    def apply_background_image(self, image_path):
        if os.path.exists(image_path):
            bg_image = Image.open(image_path)
            bg_photo = ImageTk.PhotoImage(bg_image)
            self.root.background_label = tk.Label(self.root, image=bg_photo)
            self.root.background_label.image = bg_photo
            self.root.background_label.place(x=0, y=0, relwidth=1, relheight=1)
            self.root.background_label.lower()  # Umieść tło za innymi widgetami
        else:
            if hasattr(self.root, "background_label"):
                self.root.background_label.destroy()

    def _open_folder(self, folder_path):
        return gl_app_navigation._open_folder(self, folder_path)

    def show_settings(self):
        return gl_settings_runtime.show_settings(self)

    def toggle_show_token(self):
        if self.github_token_entry["show"] == "*":
            self.github_token_entry["show"] = ""
        else:
            self.github_token_entry["show"] = "*"

    def save_github_token(self):
        token = self.github_token_entry.get().strip()
        if token:
            self.local_settings["github_token"] = token
            save_local_settings(self.local_settings)
            messagebox.showinfo("Sukces", "Token GitHub został zapisany.")
        else:
            messagebox.showwarning("Błąd", "Token GitHub nie może być pusty.")

    def show_github_token_help(self):
        message = (
            "Jak uzyskać GitHub Personal Access Token:\n\n"
            "1. Przejdź na stronę GitHub: https://github.com/settings/tokens\n"
            "2. Kliknij 'Personal access tokens', wybieramy 'Tokens (classic)' i klikamy 'Generate new token' wybierając 'Generate new token (classic)'.\n"
            "3. Nadaj tokenowi nazwę i ustaw odpowiednie uprawnienia:\n"
            "   - Dla tego programu potrzebujesz uprawnień 'repo'.\n"
            "4. Skopiuj wygenerowany token i wprowadź go w polu tokena w ustawieniach programu.\n\n"
            "**Pamiętaj, aby nie udostępniać swojego tokena publicznie!**"
        )
        messagebox.showinfo("Pomoc - GitHub Token", message)

    def show_progress_window(self, title):
        return gl_backup_restore.show_progress_window(self, title)

    def update_cloud_services(self):
        self.settings["cloud_service_google_drive"] = self.cloud_services[
            "Google Drive"
        ].get()
        self.settings["cloud_service_github"] = self.cloud_services["GitHub"].get()
        save_config(self.config)

    def toggle_autostart(self):
        if self.autostart_var.get():
            # Dodaj do rejestru
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            )
            winreg.SetValueEx(
                key,
                "GameLauncher",
                0,
                winreg.REG_SZ,
                sys.executable + " " + os.path.abspath(__file__),
            )
            winreg.CloseKey(key)
        else:
            # Usuń z rejestru
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0,
                    winreg.KEY_ALL_ACCESS,
                )
                winreg.DeleteValue(key, "GameLauncher")
                winreg.CloseKey(key)
            except FileNotFoundError:
                pass

        self.settings["autostart"] = self.autostart_var.get()
        save_config(self.config)

    def change_username(self):
        username = simpledialog.askstring(
            "Zmień Nazwę Użytkownika", "Podaj nową nazwę użytkownika:"
        )
        if username:
            self.user["username"] = username
            save_config(self.config)
            messagebox.showinfo("Sukces", "Nazwa użytkownika została zmieniona.")
            self.create_home_page()  # Odświeżenie strony głównej
            # Zaktualizuj etykietę w ustawieniach, jeśli istnieje
            if (
                hasattr(self, "settings_username_label")
                and self.settings_username_label.winfo_exists()
            ):
                self.settings_username_label.config(text=f"Nazwa: {username}")
        else:
            messagebox.showwarning("Błąd", "Nazwa użytkownika nie może być pusta.")

    def setup_google_drive(self):
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        import pickle

        SCOPES = ["https://www.googleapis.com/auth/drive.file"]
        creds = None
        if os.path.exists("token_google_drive.pickle"):
            with open("token_google_drive.pickle", "rb") as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists("credentials.json"):
                    messagebox.showerror(
                        "Błąd", "Brak pliku credentials.json dla Google Drive."
                    )
                    return
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open("token_google_drive.pickle", "wb") as token:
                pickle.dump(creds, token)
        self.google_drive_creds = creds
        messagebox.showinfo("Sukces", "Google Drive zostało skonfigurowane.")

    def setup_github(self):
        token = self.local_settings.get("github_token")
        if not token:
            token = simpledialog.askstring(
                "GitHub Token", "Podaj swój GitHub Personal Access Token:", show="*"
            )
            if token:
                self.local_settings["github_token"] = token
                save_local_settings(self.local_settings)
                messagebox.showinfo("Sukces", "GitHub został skonfigurowany.")
            else:
                messagebox.showwarning("Błąd", "Token GitHub jest wymagany.")
        else:
            messagebox.showinfo("Informacja", "GitHub jest już skonfigurowany.")

    def upload_to_cloud(self):
        services = []
        if self.settings.get("cloud_service_google_drive"):
            services.append("Google Drive")
        if self.settings.get("cloud_service_github"):
            services.append("GitHub")
        if not services:
            messagebox.showwarning("Błąd", "Nie wybrano żadnej usługi chmurowej.")
            return

        # Sprawdź, czy token GitHub jest dostępny przed rozpoczęciem wątku
        if "GitHub" in services:
            token = self.local_settings.get("github_token")
            if not token:
                self.setup_github()
                token = self.local_settings.get("github_token")
                if not token:
                    messagebox.showwarning("Błąd", "Brak tokenu GitHub.")
                    return

        # Tworzenie okna paska postępu
        self.show_progress_window("Przesyłanie do chmury")

        # Rozpocznij wątek roboczy
        threading.Thread(
            target=self.upload_to_cloud_thread, args=(services,), daemon=True
        ).start()

        # Rozpocznij sprawdzanie kolejki z postępem
        self.check_progress_queue()

    def _save_remote_port(self):
        return gl_remote_server_runtime._save_remote_port(self)

    def update_filter_group_menu(self):
        return gl_library_groups_runtime.update_filter_group_menu(self)

    def _on_filter_or_group_selected(self, selected_value):
        return gl_library_groups_runtime._on_filter_or_group_selected(
            self, selected_value
        )

    def _music_control_play_pause(self):
        """Wywołuje play/pause w odtwarzaczu muzyki, jeśli jest dostępny."""
        if (
            hasattr(self, "music_player_page_instance")
            and self.music_player_page_instance
        ):
            # Użyj after, aby upewnić się, że wykonuje się w głównym wątku GUI
            self.root.after(0, self.music_player_page_instance._toggle_play_pause)
            logging.info("Polecenie Play/Pause wysłane do odtwarzacza z zasobnika.")
        else:
            logging.warning(
                "Próba sterowania muzyką z zasobnika, ale instancja odtwarzacza nie istnieje."
            )
            # Można opcjonalnie poinformować użytkownika lub otworzyć stronę muzyki
            # self.show_window()
            # self.show_music_page()
        self.root.after(
            100, self._update_overlay_regularly
        )  # Wymuś aktualizację overlay'a

    def _music_control_next_track(self):
        """Wywołuje następny utwór w odtwarzaczu muzyki, jeśli jest dostępny."""
        if (
            hasattr(self, "music_player_page_instance")
            and self.music_player_page_instance
        ):
            self.root.after(0, self.music_player_page_instance._next_track)
            logging.info("Polecenie Następny Utwór wysłane do odtwarzacza z zasobnika.")
        else:
            logging.warning(
                "Próba sterowania muzyką z zasobnika (następny), ale instancja odtwarzacza nie istnieje."
            )
        self.root.after(100, self._update_overlay_regularly)

    def _music_control_prev_track(self):
        """Wywołuje poprzedni utwór w odtwarzaczu muzyki, jeśli jest dostępny."""
        if (
            hasattr(self, "music_player_page_instance")
            and self.music_player_page_instance
        ):
            self.root.after(0, self.music_player_page_instance._prev_track)
            logging.info(
                "Polecenie Poprzedni Utwór wysłane do odtwarzacza z zasobnika."
            )
        else:
            logging.warning(
                "Próba sterowania muzyką z zasobnika (poprzedni), ale instancja odtwarzacza nie istnieje."
            )
        self.root.after(100, self._update_overlay_regularly)

    def show_music_page_from_tray(self):
        return gl_app_navigation.show_music_page_from_tray(self)

    def download_from_cloud(self):
        services = []
        if self.settings.get("cloud_service_google_drive"):
            services.append("Google Drive")
        if self.settings.get("cloud_service_github"):
            services.append("GitHub")
        if not services:
            messagebox.showwarning("Błąd", "Nie wybrano żadnej usługi chmurowej.")
            return
        for service in services:
            if service == "Google Drive":
                self.download_from_google_drive()
            elif service == "GitHub":
                self.download_from_github()

    def upload_to_google_drive(self):
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        if not hasattr(self, "google_drive_creds"):
            self.setup_google_drive()
        service = build("drive", "v3", credentials=self.google_drive_creds)
        file_metadata = {"name": os.path.basename(CONFIG_FILE)}
        media = MediaFileUpload(CONFIG_FILE, mimetype="application/json")
        file = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        messagebox.showinfo("Sukces", "Plik został przesłany do Google Drive.")


    def check_and_unlock_achievements(self):
        return gl_achievements_runtime.check_and_unlock_achievements(self)

    def download_from_google_drive(self):
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload
        import io

        if not hasattr(self, "google_drive_creds"):
            self.setup_google_drive()
        service = build("drive", "v3", credentials=self.google_drive_creds)
        # Wyszukaj plik
        results = (
            service.files()
            .list(
                q=f"name='{os.path.basename(CONFIG_FILE)}'",
                spaces="drive",
                fields="files(id, name)",
            )
            .execute()
        )
        items = results.get("files", [])
        if not items:
            messagebox.showwarning("Błąd", "Nie znaleziono pliku w Google Drive.")
            return
        file_id = items[0]["id"]
        request = service.files().get_media(fileId=file_id)
        fh = io.FileIO(CONFIG_FILE, "wb")
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        fh.close()
        self.config = load_config()
        self.games = self.config.setdefault("games", {})
        self.settings = self.config.setdefault("settings", {})
        self.groups = self.config.setdefault("groups", {})
        self.user = self.config.setdefault("user", {})
        self.update_game_grid()
        self.create_home_page()
        messagebox.showinfo("Sukces", "Plik został pobrany z Google Drive.")

    def _upload_single_file_to_github(self, repo, local_path, repo_path):
        return gl_cloud_github_runtime._upload_single_file_to_github(
            self, repo, local_path, repo_path
        )

    def do_upload_to_github(self):
        return gl_cloud_github_runtime.do_upload_to_github(self)

    def upload_folder_to_github(self, repo, local_folder, repo_folder):
        return gl_cloud_github_runtime.upload_folder_to_github(
            self, repo, local_folder, repo_folder
        )

    def _download_single_file_from_github(self, repo, repo_path, local_path):
        return gl_cloud_github_runtime._download_single_file_from_github(
            self, repo, repo_path, local_path
        )

    def download_from_github(self):
        return gl_cloud_github_runtime.download_from_github(self)

    def download_folder_from_github(
        self, repo, repo_folder, local_folder, progress_callback=None
    ):
        return gl_cloud_github_runtime.download_folder_from_github(
            self,
            repo,
            repo_folder,
            local_folder,
            progress_callback=progress_callback,
        )

    def disable_event(self):
        pass

    def update_progress(self, percent):
        if hasattr(self, "progress_bar") and self.progress_bar.winfo_exists():
            self.progress_bar["value"] = percent
            self.progress_label.config(text=f"{percent}%")
            self.progress_window.update_idletasks()

    def upload_to_cloud_thread(self, services):
        for service in services:
            if service == "Google Drive":
                self.do_upload_to_google_drive()
            elif service == "GitHub":
                self.do_upload_to_github()
        # Wskaźnik zakończenia
        self.progress_queue.put("DONE")

    def check_progress_queue(self):
        try:
            while True:
                item = self.progress_queue.get_nowait()
                if item == "DONE":
                    self.progress_window.destroy()
                    messagebox.showinfo("Sukces", "Pliki zostały przesłane do chmury.")
                    return
                elif str(item).startswith("ERROR:"):
                    self.progress_window.destroy()
                    messagebox.showerror("Błąd", item[6:])
                    return
                else:
                    percent = item
                    self.update_progress(percent)
        except queue.Empty:
            pass
        # Harmonogram następnego sprawdzenia
        self.root.after(100, self.check_progress_queue)

    def start_fetch_details_thread(self, game_name, details_window, force=False):
        return gl_rawg_fetch_runtime.start_fetch_details_thread(
            self, game_name, details_window, force=force
        )

    def open_advanced_filter_manager(self):
        """Otwiera okno zarządzania filtrami zaawansowanymi."""
        # Sprawdź, czy okno już nie jest otwarte
        if (
            hasattr(self, "_filter_manager_window")
            and self._filter_manager_window.winfo_exists()
        ):
            self._filter_manager_window.lift()
            self._filter_manager_window.focus_force()
        else:
            from ui.filters import AdvancedFilterManager

            self._filter_manager_window = AdvancedFilterManager(self.root, self)

    def fetch_rawg_game_details(self, game_name, api_key, callback, force=False):
        return gl_rawg_fetch_runtime.fetch_rawg_game_details(
            self,
            game_name,
            api_key,
            callback,
            force=force,
        )

    def select_avatar(self):
        path = filedialog.askopenfilename(filetypes=[("Obrazy", "*.png;*.jpg;*.jpeg")])
        if path:
            try:
                os.makedirs(IMAGES_FOLDER, exist_ok=True)
                destination = os.path.join(IMAGES_FOLDER, "avatar.png")
                shutil.copy(path, destination)
                self.avatar_var.set(destination)  # Zaktualizuj pole Entry
                self.user["avatar"] = destination
                save_config(self.config)
                self.create_home_page()  # Odśwież stronę główną
                self._load_and_display_settings_avatar()  # Odśwież podgląd w ustawieniach
                messagebox.showinfo("Sukces", "Awatar został ustawiony.")
            except Exception as e:
                messagebox.showerror("Błąd", f"Nie udało się ustawić awatara: {e}")

    def create_news_page(self):
        return gl_news_runtime.create_news_page(self)

    def load_news(self, content_widget):
        return gl_news_runtime.load_news(self, content_widget)


    def show_news(self):
        return gl_news_runtime.show_news(self)

    def show_reminders(self):
        self.reminders_frame.grid()
        self.reminders_frame.tkraise()
        self.current_frame = self.reminders_frame

        if not self._reminders_initialized:
            logging.info(
                "Tworzenie zawartości strony Przypomnienia po raz pierwszy (lazy init)."
            )
            self.create_reminders_page()  # To buduje UI
            self._reminders_initialized = True
        else:
            self.load_reminders()  # Jeśli już zbudowana, tylko załaduj/odśwież dane

        self.current_section = "Sprawdza Przypomnienia"
        self._update_discord_status(
            status_type="browsing", activity_details=self.current_section
        )
        self.load_reminders()  # Wczytaj przypomnienia po pokazaniu strony (było wcześniej)

    def load_reminders(self):
        return gl_reminders_runtime.load_reminders(self)

    def add_reminder(self):
        return gl_reminders_runtime.add_reminder(self)

    def create_game_tile(
        self, parent, game_name, game_data, tile_width=200, tile_height=300
    ):
        return gl_library_grid_runtime.create_game_tile(
            self, parent, game_name, game_data, tile_width=tile_width, tile_height=tile_height
        )

    def delete_avatar(self):
        avatar_path = self.user.get("avatar", "")
        if avatar_path and os.path.exists(avatar_path):
            try:
                os.remove(avatar_path)
                self.user["avatar"] = ""
                self.avatar_var.set("")  # Wyczyść pole Entry
                save_config(self.config)
                self.create_home_page()  # Odśwież stronę główną
                self._load_and_display_settings_avatar()  # Odśwież podgląd (pokaże domyślny)
                messagebox.showinfo("Sukces", "Awatar został usunięty.")
            except Exception as e:
                messagebox.showerror("Błąd", f"Nie udało się usunąć awatara: {e}")
        else:
            messagebox.showwarning("Błąd", "Nie ma ustawionego awatara do usunięcia.")


    def update_game_grid(self):
        return gl_library_grid_runtime.update_game_grid(self)

    def _update_canvas_scrollregion(self):
        return gl_library_grid_runtime._update_canvas_scrollregion(self)

    def show_home_from_tray(self):
        self.show_window()
        self.show_home()

    def show_library_from_tray(self):
        self.show_window()
        self.show_library()

    def exit_program(self, icon=None, item=None):
        self.on_closing()  # zapisze czas, ustawi flagi, wyłączy RPC itp.

    def minimize_to_tray(self):
        self.root.withdraw()
        self.create_system_tray_icon()

    def create_default_icon(self):
        image = Image.new("RGB", (64, 64), color="blue")
        draw = ImageDraw.Draw(image)
        draw.text((10, 20), "GL", fill="white")
        return image

    def show_roadmap_from_tray(self):
        self.show_window()
        self.show_roadmap()

    def show_mods_from_tray(self):
        self.show_window()
        self.show_mod_manager()

    def show_achievements_from_tray(self):
        self.show_window()
        self.show_achievements_page()

    def show_news_from_tray(self):
        self.show_window()
        self.show_news()

    def show_settings_from_tray(self):
        self.show_window()
        self.show_settings()

    def show_statistics_from_tray(self):
        return gl_tray_runtime.show_statistics_from_tray(self)

    def show_window(self):
        return gl_tray_runtime.show_window(self)

    def on_minimize(self, event):
        return gl_tray_runtime.on_minimize(self, event)


    def on_closing(self):
        return gl_closing_runtime.on_closing(self)

    def create_system_tray_icon(self):
        return gl_tray_runtime.create_system_tray_icon(self)

    def create_reminders_page(self):
        return gl_reminders_runtime.create_reminders_page(self)

    def delete_reminder(self):
        return gl_reminders_runtime.delete_reminder(self)

    def monitor_reminders(self):
        return gl_reminders_runtime.monitor_reminders(self)

    def add_rss_feed(self):
        return gl_news_runtime.add_rss_feed(self)

    def remove_rss_feed(self):
        return gl_news_runtime.remove_rss_feed(self)

    def update_post_limit(self):
        return gl_news_runtime.update_post_limit(self)

    def load_news_threaded(self):
        return gl_news_runtime.load_news_threaded(self)

    def create_roadmap_page(self, show_frame=True):
        return gl_roadmap_archive_runtime.create_roadmap_page(self, show_frame=show_frame)

    def create_current_games_ui(self, parent_frame):
        return gl_roadmap_archive_runtime.create_current_games_ui(self, parent_frame)

    def create_archive_ui(self, parent_frame):
        return gl_roadmap_archive_runtime.create_archive_ui(self, parent_frame)


    def load_archive(self):
        return gl_roadmap_archive_runtime.load_archive(self)

    def update_archive_calendar(self):
        return gl_roadmap_archive_runtime.update_archive_calendar(self)

    def create_archive_legend(self, parent_frame):
        return gl_roadmap_archive_runtime.create_archive_legend(self, parent_frame)

    def load_roadmap(self):
        return gl_roadmap_archive_runtime.load_roadmap(self)

    def _hide_library_components(self):
        """Ukrywa komponenty specyficzne dla widoku Biblioteki."""
        if hasattr(self, "canvas") and self.canvas.winfo_ismapped():
            self.canvas.grid_remove()
        if hasattr(self, "scrollbar") and self.scrollbar.winfo_ismapped():
            self.scrollbar.grid_remove()
        if hasattr(self, "pagination_frame") and self.pagination_frame.winfo_ismapped():
            self.pagination_frame.grid_remove()
        if hasattr(self, "list_view_frame") and self.list_view_frame.winfo_ismapped():
            self.list_view_frame.grid_remove()

    def mark_calendar_dates(self, game):
        return gl_roadmap_archive_runtime.mark_calendar_dates(self, game)

    def update_calendar(self):
        return gl_roadmap_archive_runtime.update_calendar(self)

    def load_screenshot_ignored_folders(self):
        return gl_screenshot_scan_runtime.load_screenshot_ignored_folders(self)

    def save_screenshot_ignored_folders(self):
        return gl_screenshot_scan_runtime.save_screenshot_ignored_folders(self)

    def create_add_game_section(self, parent_frame):
        return gl_roadmap_archive_runtime.create_add_game_section(self, parent_frame)

    def create_roadmap_tree(self, parent_frame):
        return gl_roadmap_archive_runtime.create_roadmap_tree(self, parent_frame)

    def create_roadmap_buttons(self, parent_frame):
        return gl_roadmap_archive_runtime.create_roadmap_buttons(self, parent_frame)


    def _copy_or_delete_with_progress(
        self,
        operation_type,
        source_path,
        dest_path,
        operation_title,
        parent_window=None,
        callback_on_success=None,
    ):  # Dodano callback
        return gl_file_ops_runtime._copy_or_delete_with_progress(
            self,
            operation_type,
            source_path,
            dest_path,
            operation_title,
            parent_window=parent_window,
            callback_on_success=callback_on_success,
        )

    def load_autoscan_folders_list(self):
        return gl_screenshot_scan_runtime.load_autoscan_folders_list(self)

    def start_scan_screenshots_thread(self, game_to_scan=None):
        return gl_screenshot_scan_runtime.start_scan_screenshots_thread(
            self, game_to_scan=game_to_scan
        )

    def _on_view_change(self, event=None):
        selected_display_view = self.stats_view_var.get()
        view_key = self.TRANSLATED_TO_STATS_VIEW.get(
            selected_display_view, "Playtime per Day"
        )

        # Najpierw ukryj wszystkie dynamiczne kontrolki
        self.stats_game_select_frame.pack_forget()  # Używamy pack wewnątrz dynamic_controls_frame
        self.show_time_details_button.grid_remove()
        self.dynamic_controls_frame.grid_remove()  # Ukryj całą ramkę dynamicznych kontrolek

        # Pokaż odpowiednie kontrolki
        if view_key == "Playtime per Game (Selected)":
            self.dynamic_controls_frame.grid(
                row=0, column=4, padx=5, pady=5, sticky="w"
            )  # Pokaż ramkę
            self.stats_game_select_frame.pack(side=tk.LEFT)  # Pokaż wybór gry
        elif view_key == "Playtime per Day":
            # Przycisk szczegółów czasu umieszczamy bezpośrednio w controls_frame
            self.show_time_details_button.grid(
                row=0, column=5, padx=5, pady=5, sticky="e"
            )  # Dopasuj kolumnę
        # Można dodać inne warunki, jeśli inne widoki wymagają specjalnych kontrolek

        # Ukryj ramkę detali, jeśli widok jej nie używa
        if view_key not in ["Games Played per Day", "Playtime per Day"]:
            if hasattr(self, "details_frame") and self.details_frame.winfo_ismapped():
                self.details_frame.grid_remove()
                if (
                    hasattr(self, "chart_container")
                    and self.chart_container.winfo_exists()
                ):
                    self.chart_container.master.columnconfigure(0, weight=1)
                    self.chart_container.master.columnconfigure(1, weight=0)

    def _scan_for_screenshots_thread(self, game_to_scan=None):
        return gl_screenshot_scan_runtime._scan_for_screenshots_thread(
            self, game_to_scan=game_to_scan
        )

    def _refresh_details_window_if_open(self, game_name):
        return gl_screenshot_scan_runtime._refresh_details_window_if_open(
            self, game_name
        )


    def _get_local_ip(self):
        """Próbuje znaleźć lokalny adres IP komputera."""
        s = None
        try:
            # Spróbuj połączyć się z publicznym adresem DNS, aby system wybrał odpowiedni interfejs
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.1)  # Unikaj długiego czekania
            s.connect(("8.8.8.8", 1))  # Nie wysyła danych, tylko ustala trasę
            ip = s.getsockname()[0]
            return ip
        except Exception as e:
            logging.error(f"Nie można automatycznie wykryć lokalnego IP: {e}")
            # Spróbuj hostname jako fallback (może nie działać poprawnie z IP)
            try:
                return socket.gethostbyname(socket.gethostname())
            except socket.gaierror:
                logging.error("Nie można pobrać IP nawet przez hostname.")
                return "127.0.0.1"  # Ostateczny fallback
        finally:
            if s:
                s.close()

    def _flask_server_target(self, port):  # Dodano argument port
        return gl_remote_server_runtime._flask_server_target(self, port)


    def _start_flask_server(self):
        return gl_remote_server_runtime._start_flask_server(self)

    def _stop_flask_server(self):
        return gl_remote_server_runtime._stop_flask_server(self)

    # W _update_server_status_ui używaj self.remote_server_port
    def _update_server_status_ui(self, is_running, ip_address=None):
        return gl_remote_server_runtime._update_server_status_ui(
            self, is_running, ip_address=ip_address
        )

    def _toggle_remote_server(self):
        return gl_remote_server_runtime._toggle_remote_server(self)


    def add_autoscan_folder(self):
        return gl_screenshot_scan_runtime.add_autoscan_folder(self)

    def remove_autoscan_folder(self):
        return gl_screenshot_scan_runtime.remove_autoscan_folder(self)

    def _save_autoscan_startup_setting(self):
        return gl_screenshot_scan_runtime._save_autoscan_startup_setting(self)

    def _perform_file_operation_thread(
        self, operation_type, src, dst, total_files, callback_on_success=None
    ):
        return gl_file_ops_runtime._perform_file_operation_thread(
            self,
            operation_type,
            src,
            dst,
            total_files,
            callback_on_success=callback_on_success,
        )

    def add_to_roadmap(self):
        return gl_roadmap_archive_runtime.add_to_roadmap(self)

    def _check_game_against_rules(self, game_data, rules):
        return gl_advanced_filter_eval._check_game_against_rules(
            self, game_data, rules
        )

    def mark_as_completed(self):
        return gl_roadmap_archive_runtime.mark_as_completed(self)

    def _ensure_cover(self, game_name: str, game_data: dict, size: tuple):
        """
        Gwarantuje, że gra ma fizyczny plik okładki.
        Jeśli go nie ma – tworzy domyślną, zapisuje w configu i zwraca ścieżkę.
        """
        cover_path = game_data.get("cover_image") or ""
        if not os.path.isfile(cover_path):
            cover_path = create_default_cover(game_name, size=size)
            game_data["cover_image"] = cover_path
            game_data["_auto_cover"] = True  # zapisz w pamięci
            save_config(self.config)  # zapisz na dysku
            load_photoimage_from_path.cache_clear()  # odśwież mini‑cache
            logging.info(f"Utworzono domyślną okładkę dla '{game_name}': {cover_path}")
        return cover_path

    def delete_from_roadmap(self):
        return gl_roadmap_archive_runtime.delete_from_roadmap(self)

    def monitor_roadmap(self):
        return gl_roadmap_archive_runtime.monitor_roadmap(self)


    def show_roadmap(self):
        """Pokazuje kartę Roadmapy, tworząc UI tylko raz."""
        # Utwórz UI tylko jeśli ramka nie istnieje
        if not hasattr(self, "roadmap_frame") or not self.roadmap_frame.winfo_exists():
            self.create_roadmap_page()  # Stworzy UI i zaplanuje ładowanie danych
        # Zawsze podnoś ramkę do góry
        self.roadmap_frame.grid(
            row=0, column=1, sticky="nsew"
        )  # Upewnij się, że ramka Roadmapy jest w poprawnym miejscu
        self.roadmap_frame.tkraise()
        self.current_frame = self.roadmap_frame
        self.current_section = "Sprawdza Roadmapę"
        self._update_discord_status(
            status_type="browsing", activity_details=self.current_section
        )

    def perform_update_check(self):
        return gl_updater_runtime.perform_update_check(self)

    def check_for_updates(self):
        return gl_updater_runtime.check_for_updates(self)

    def _ensure_mod_manager(self):
        """Tworzy instancję ExtendedModManager, jeśli jeszcze nie istnieje."""
        if self.extended_mod_manager is None:
            from ui.mod_manager import ExtendedModManager

            logging.info("Leniwa inicjalizacja ExtendedModManager...")
            self.extended_mod_manager = ExtendedModManager(self, self.root)
            # Opcjonalnie: Upewnij się, że ramka jest pod spodem na początku
            self.extended_mod_manager.frame.lower()
        # Jeśli już istnieje, nic nie rób

    def _load_achievement_def_list(self):
        return gl_achievements_defs._load_achievement_def_list(self)


    def _delete_achievement_def(self):
        return gl_achievements_defs._delete_achievement_def(self)

    def _save_achievement_definitions_to_file(self):
        return gl_achievements_defs._save_achievement_definitions_to_file(self)

    def prompt_update(self, update_info):
        return gl_updater_runtime.prompt_update(self, update_info)

    def download_and_update(self, download_url):
        return gl_updater_runtime.download_and_update(self, download_url)

    def manual_check_updates(self):
        return gl_updater_runtime.manual_check_updates(self)

    def fix_user_in_path(self, old_path: str) -> str:
        """
        Zamienia fragment 'C:/Users/<ktoś>' w old_path
        na ścieżkę do aktualnie zalogowanego użytkownika
        (os.path.expanduser("~")), zachowując resztę ścieżki.
        Jeśli old_path nie zaczyna się od 'C:/Users/...',
        pozostaje bez zmian.
        """
        user_home = os.path.expanduser("~")  # np. C:/Users/TwojaNazwa
        # Zawsze pracuj na slashach /, żeby re.match było prostsze:
        old_fixed = old_path.replace("\\", "/")

        pattern = r"^([A-Z]:/Users/[^/]+)(.*)$"
        match = re.match(pattern, old_fixed, re.IGNORECASE)
        if match:
            # remainder = np. "/Documents/Gra" – czyli wszystko po "C:/Users/<ktoś>"
            remainder = match.group(2)
            user_home_slash = user_home.replace("\\", "/")
            new_path_slash = user_home_slash + remainder
            # Przywracamy slashe Windowsowe (jeśli trzeba):
            new_path = new_path_slash.replace("/", os.sep)
            return new_path
        else:
            return old_path

    def repair_save_paths(self):
        """
        Przykładowa metoda, która iteruje po wszystkich grach
        i poprawia ścieżki zapisów (save_path).
        """
        for game_name, game_data in self.games.items():
            old_path = game_data.get("save_path")
            if not old_path:
                continue

            # WAŻNE: Wywołanie przez self.fix_user_in_path
            new_path = self.fix_user_in_path(old_path)

            if new_path != old_path:
                game_data["save_path"] = new_path

            # Możesz też utworzyć folder, jeśli go nie ma:
            try:
                os.makedirs(new_path, exist_ok=True)
            except Exception as e:
                print(
                    f"Nie udało się utworzyć folderu {new_path} dla gry '{game_name}': {e}"
                )

        # Na koniec zapisz config, jeśli chcesz
        # save_config(self.config)


    def backup_to_local_folder(self):
        return gl_backup_restore.backup_to_local_folder(self)

    def load_local_backup(self):
        return gl_backup_restore.load_local_backup(self)

    def _update_restore_progress(
        self,
        next_step_description=None,
        increment_value=None,
        file_details=None,
        file_progress_percent=None,
    ):
        return gl_backup_restore._update_restore_progress(
            self,
            next_step_description=next_step_description,
            increment_value=increment_value,
            file_details=file_details,
            file_progress_percent=file_progress_percent,
        )

    def _perform_backup_restore_thread(self, backup_dir):
        return gl_backup_restore._perform_backup_restore_thread(self, backup_dir)

    def _save_tiles_per_row_setting(self):
        """Zapisuje ustawienie liczby kafelków i odświeża siatkę, jeśli trzeba."""
        try:
            value = self.tiles_per_row_var.get()
            if 2 <= value <= 8:  # Walidacja zakresu
                if self.local_settings.get("tiles_per_row") != value:
                    self.local_settings["tiles_per_row"] = value
                    save_local_settings(self.local_settings)
                    logging.info(f"Zmieniono liczbę kafelków w rzędzie na: {value}")
                    # Odśwież siatkę, jeśli aktualnie wyświetlana jest biblioteka w trybie kafelków
                    if (
                        self.current_frame == self.main_frame
                        and self.library_view_mode.get() == "tiles"
                    ):
                        self.reset_and_update_grid()
            else:
                # Przywróć poprzednią wartość w razie błędu
                self.tiles_per_row_var.set(self.local_settings.get("tiles_per_row", 4))
                logging.warning(
                    f"Nieprawidłowa wartość dla kafelków w rzędzie: {value}"
                )
        except tk.TclError:  # Jeśli wartość w Spinboxie jest chwilowo niepoprawna
            self.tiles_per_row_var.set(self.local_settings.get("tiles_per_row", 4))
            logging.warning("Błąd odczytu wartości ze Spinboxa kafelków.")
        except Exception as e:
            logging.exception(f"Błąd podczas zapisywania ustawienia kafelków: {e}")
            self.tiles_per_row_var.set(
                self.local_settings.get("tiles_per_row", 4)
            )  # Przywróć na wszelki wypadek

    def load_scan_folders_list(self):
        return gl_scan_pipeline.load_scan_folders_list(self)

    def add_scan_folder(self):
        return gl_scan_pipeline.add_scan_folder(self)

    def remove_scan_folder(self):
        return gl_scan_pipeline.remove_scan_folder(self)

    def save_scan_settings(self):
        return gl_scan_pipeline.save_scan_settings(self)

    def guess_game_name_from_folder(self, folder_name):
        return gl_scan_pipeline.guess_game_name_from_folder(self, folder_name)

    def find_likely_executable(self, game_folder_path, guessed_name=""):
        return gl_scan_pipeline.find_likely_executable(
            self, game_folder_path, guessed_name
        )

    find_likely_executable.ignore_dirs = {
        "_commonredist",
        "directx",
        "dotnet",
        "redist",
        "tools",
        "benchmark",
        "support",
        "data",
        "profiles",
        "config",
        "save",
        "logs",
    }
    find_likely_executable.ignore_files = {
        "setup.exe",
        "uninstall.exe",
        "unins000.exe",
        "unins001.exe",
        "launcher.exe",
        "crashreporter.exe",
        "configtool.exe",
        "activation.exe",
    }
    find_likely_executable.preferred_keywords = [
        "game",
        "shipping",
        "retail",
    ]

    def start_scan_thread(self):
        return gl_scan_pipeline.start_scan_thread(self)

    def scan_folders_for_games(self):
        return gl_scan_pipeline.scan_folders_for_games(self)

    def show_scan_verification_window(self, potential_games):
        return gl_scan_pipeline.show_scan_verification_window(self, potential_games)

    def update_scan_progress(self, percent, current_folder):
        return gl_scan_pipeline.update_scan_progress(self, percent, current_folder)

    def stop_scan_progress(self):
        return gl_scan_pipeline.stop_scan_progress(self)

    def parse_folder_name_metadata(self, folder_name):
        return gl_scan_pipeline.parse_folder_name_metadata(self, folder_name)

    def parse_nfo_file(self, game_folder_path):
        return gl_scan_pipeline.parse_nfo_file(self, game_folder_path)


    def _add_edit_achievement_def(self, edit_mode=False, parent_window=None):
        return gl_achievements_defs._add_edit_achievement_def(
            self, edit_mode=edit_mode, parent_window=parent_window
        )

    def create_achievements_page(self):
        return gl_achievements_page.create_achievements_page(self)

    def _reload_definitions_and_refresh_ui(self):
        return gl_achievements_runtime._reload_definitions_and_refresh_ui(self)

    def show_achievements_page(self):
        return gl_achievements_runtime.show_achievements_page(self)

    def _download_and_save_rawg_cover(self, game_name, image_url):
        return gl_rawg_cover._download_and_save_rawg_cover(self, game_name, image_url)

    def _on_search_change(self, *args):
        return gl_library_lazy_load._on_search_change(self, *args)

    def on_canvas_configure_and_lazy_load(self, event):
        return gl_library_lazy_load.on_canvas_configure_and_lazy_load(self, event)

    def _on_mouse_wheel_and_lazy_load(self, event):
        return gl_library_lazy_load._on_mouse_wheel_and_lazy_load(self, event)

    def _trigger_lazy_load(self, event=None):
        return gl_library_lazy_load._trigger_lazy_load(self, event)

    def _load_visible_tiles(self):
        return gl_library_lazy_load._load_visible_tiles(self)


    def _create_tile_placeholder(
        self,
        parent,
        game_name,
        row,
        col,
        padx_config,
        pady_config,
        tile_width,
        tile_height,
    ):
        return gl_library_lazy_load._create_tile_placeholder(
            self,
            parent,
            game_name,
            row,
            col,
            padx_config,
            pady_config,
            tile_width,
            tile_height,
        )

    def _start_discord_rpc(self):
        return gl_discord_runtime._start_discord_rpc(self)

    def _handle_rpc_connection_error(
        self, error_message: str, is_critical: bool = True
    ):
        return gl_discord_runtime._handle_rpc_connection_error(
            self, error_message=error_message, is_critical=is_critical
        )

    def _toggle_discord_rpc(self):
        return gl_discord_runtime._toggle_discord_rpc(self)


    def _update_discord_status(
        self,
        status_type="idle",
        game_name=None,
        profile_name=None,
        start_time=None,
        activity_details=None,
    ):
        return gl_discord_runtime._update_discord_status(
            self,
            status_type=status_type,
            game_name=game_name,
            profile_name=profile_name,
            start_time=start_time,
            activity_details=activity_details,
        )


    def _stop_discord_rpc(self):  # Poprzednio _stop_discord_rpc_quietly
        return gl_discord_runtime._stop_discord_rpc(self)


    def _save_discord_settings(self):
        return gl_discord_runtime._save_discord_settings(self)


    def _load_and_display_settings_avatar(self, size_tuple=None):
        return gl_settings_avatar._load_and_display_settings_avatar(
            self, size_tuple=size_tuple
        )

    def _populate_game_tile(
        self, tile_frame, game_name, game_data, tile_width, tile_height
    ):
        return gl_library_tile_actions._populate_game_tile(
            self, tile_frame, game_name, game_data, tile_width, tile_height
        )

    def _show_tile_context_menu(self, event, game_name):
        return gl_library_tile_actions._show_tile_context_menu(self, event, game_name)

    def _remove_from_group_from_menu(self, game_name, group_name):
        return gl_library_tile_actions._remove_from_group_from_menu(
            self, game_name, group_name
        )


    def _show_mods_for_game_from_context(self, game_name):
        return gl_library_tile_actions._show_mods_for_game_from_context(self, game_name)

    def _clear_launch_button_ref(self, game_name):
        return gl_library_tile_actions._clear_launch_button_ref(self, game_name)

    def update_pagination_controls(self, total_items):
        return gl_library_grid_runtime.update_pagination_controls(self, total_items)

    def prev_page(self):
        return gl_library_grid_runtime.prev_page(self)

    def next_page(self):
        return gl_library_grid_runtime.next_page(self)

    def reset_pagination(self):
        return gl_library_grid_runtime.reset_pagination(self)

    def _populate_roadmap_and_archive_data(self):
        return gl_roadmap_archive_runtime._populate_roadmap_and_archive_data(self)


    def _create_settings_page_content(self):
        return gl_settings_page_content._create_settings_page_content(self)

    def _save_and_refresh_avatar_size(self):
        """Zapisuje wybraną wielkość awatara i odświeża podglądy."""
        try:
            new_size = self.avatar_size_var.get()  # Spinbox zwraca int
            current_size = self.local_settings.get("avatar_display_size", 48)

            if new_size != current_size:
                self.local_settings["avatar_display_size"] = new_size
                save_local_settings(self.local_settings)
                logging.info(
                    f"Zmieniono rozmiar wyświetlania awatara na: {new_size}x{new_size}"
                )

                # Odśwież awatary w UI
                self._load_and_display_settings_avatar()  # W ustawieniach
                self.create_home_page()  # Przebuduj stronę główną (najprostszy sposób na odświeżenie awatara tam)
            else:
                logging.debug("Rozmiar awatara nie został zmieniony.")
        except tk.TclError:
            logging.error("Błąd TclError podczas odczytu rozmiaru awatara ze Spinboxa.")
            # Przywróć poprzednią wartość, jeśli coś poszło nie tak
            self.avatar_size_var.set(self.local_settings.get("avatar_display_size", 48))
        except Exception as e:
            logging.exception(
                f"Nieoczekiwany błąd podczas zapisywania/odświeżania rozmiaru awatara: {e}"
            )

    def populate_rss_management_frame(self):
        return gl_settings_runtime.populate_rss_management_frame(self)

    def add_rss_feed_from_settings(self):
        return gl_settings_runtime.add_rss_feed_from_settings(self)

    def _toggle_music_hotkeys_enabled(self):
        """Zapisuje stan włączenia/wyłączenia skrótów i je (re)rejestruje oraz aktualizuje UI."""
        enabled = self.music_hotkeys_enabled_var.get()
        self.local_settings["music_hotkeys_enabled"] = enabled
        save_local_settings(self.local_settings)
        logging.info(
            f"Globalne skróty muzyczne {'włączone' if enabled else 'wyłączone'}."
        )

        if enabled:
            self._register_music_hotkeys()
        else:
            if self.global_hotkeys_listener and self.global_hotkeys_listener.is_alive():
                self.global_hotkeys_listener.stop()
                self.global_hotkeys_listener = None
                logging.info("Zatrzymano listenera GlobalHotKeys (skróty wyłączone).")

        # Zaktualizuj stan kontrolek w UI
        new_state = tk.NORMAL if enabled else tk.DISABLED

        for action_key, entry_widget in self.music_hotkey_entries.items():
            if entry_widget.winfo_exists():
                entry_widget.config(
                    state="readonly" if enabled else tk.DISABLED
                )  # Entry jest readonly lub disabled

        if hasattr(self, "music_hotkey_set_buttons"):  # Sprawdź, czy słownik istnieje
            for action_key, button_widget in self.music_hotkey_set_buttons.items():
                if button_widget.winfo_exists():
                    button_widget.config(state=new_state)

        if hasattr(self, "reset_hotkeys_btn") and self.reset_hotkeys_btn.winfo_exists():
            self.reset_hotkeys_btn.config(state=new_state)

    def _reset_music_hotkeys(self):
        """Przywraca domyślne skróty klawiszowe dla odtwarzacza muzyki."""
        if messagebox.askyesno(
            "Resetuj Skróty",
            "Czy na pewno chcesz przywrócić domyślne skróty klawiszowe dla odtwarzacza?\n"
            "Nowe skróty zaczną działać natychmiast.",
            parent=(
                self.settings_page_frame
                if hasattr(self, "settings_page_frame")
                else self.root
            ),
        ):

            self.local_settings["music_hotkeys"] = DEFAULT_MUSIC_HOTKEYS.copy()
            save_local_settings(self.local_settings)

            # Odśwież pola Entry w UI
            for action_key, string_var in self.music_hotkey_vars.items():
                string_var.set(
                    self.local_settings["music_hotkeys"].get(action_key, "")
                )  # Użyj .get() dla bezpieczeństwa

            logging.info("Przywrócono domyślne skróty klawiszowe dla muzyki.")

            self.root.after(
                10, self._reregister_all_global_hotkeys
            )  # Użyj after dla bezpieczeństwa

            messagebox.showinfo(
                "Przywrócono Domyślne",
                "Domyślne skróty klawiszowe zostały przywrócone i powinny być aktywne.",
                parent=(
                    self.settings_page_frame
                    if hasattr(self, "settings_page_frame")
                    else self.root
                ),
            )

    def remove_specific_rss_feed(self, feed_to_remove):
        return gl_news_runtime.remove_specific_rss_feed(self, feed_to_remove)

    # Upewnij się, że update_rss_feeds używa self.rss_vars
    def update_rss_feeds(self):
        return gl_news_runtime.update_rss_feeds(self)

    def _save_chat_server_url(self):
        return gl_chat_server_settings._save_chat_server_url(self)

    def _normalize_game_name_for_duplicates(self, name):
        return gl_duplicates_ui._normalize_game_name_for_duplicates(self, name)

    def start_duplicate_scan_thread(self):
        return gl_duplicates_ui.start_duplicate_scan_thread(self)

    def _save_auto_backup_setting(self):
        """Zapisuje ustawienie automatycznego backupu."""
        self.settings["auto_backup_on_exit"] = self.auto_backup_var.get()
        save_config(self.config)
        logging.info(
            f"Ustawienie auto-backup zmienione na: {self.auto_backup_var.get()}"
        )

    def find_potential_duplicates(self):
        return gl_duplicates_ui.find_potential_duplicates(self)

    # Metoda do aktualizacji etykiety paska postępu (jeśli chcesz)
    # def update_progress_label(self, text):
    #     if hasattr(self, 'progress_label') and self.progress_label.winfo_exists():
    #         self.progress_label.config(text=text)
    #         self.progress_window.update_idletasks()


    def _show_lastfm_key_help(self):
        message = (
            "Jak uzyskać klucz API Last.fm:\n\n"
            "1. Zaloguj się lub załóż konto na [https://www.last.fm](https://www.last.fm)\n"
            "2. Przejdź na stronę [https://www.last.fm/api/account/create](https://www.last.fm/api/account/create)\n"
            "3. Wypełnij formularz (nazwa aplikacji, opis itp.). Nie musisz podawać 'Callback URL', jeśli nie tworzysz aplikacji webowej.\n"
            "4. Po zaakceptowaniu, otrzymasz swój API Key oraz API Secret (Secret nie będzie nam na razie potrzebny do pobierania okładek, ale zachowaj go).\n"
            "5. Skopiuj API Key i wklej go w polu w ustawieniach launchera.\n\n"
            "Klucz API jest wymagany do automatycznego pobierania okładek albumów."
        )
        messagebox.showinfo(
            "Pomoc - Klucz API Last.fm",
            message,
            parent=(
                self.settings_page_frame
                if hasattr(self, "settings_page_frame")
                else self.root
            ),
        )

    def _save_lastfm_api_key(self):
        if hasattr(self, "lastfm_api_key_entry"):
            key = self.lastfm_api_key_entry.get().strip()
            if key:
                self.local_settings["lastfm_api_key"] = key
                save_local_settings(self.local_settings)
                messagebox.showinfo(
                    "Sukces",
                    "Klucz API Last.fm został zapisany.",
                    parent=(
                        self.settings_page_frame
                        if hasattr(self, "settings_page_frame")
                        else self.root
                    ),
                )
            else:
                if "lastfm_api_key" in self.local_settings:
                    del self.local_settings["lastfm_api_key"]
                    save_local_settings(self.local_settings)
                    messagebox.showinfo(
                        "Usunięto",
                        "Klucz API Last.fm został usunięty.",
                        parent=(
                            self.settings_page_frame
                            if hasattr(self, "settings_page_frame")
                            else self.root
                        ),
                    )
                else:
                    messagebox.showwarning(
                        "Brak klucza",
                        "Pole klucza API Last.fm jest puste.",
                        parent=(
                            self.settings_page_frame
                            if hasattr(self, "settings_page_frame")
                            else self.root
                        ),
                    )

    def show_duplicate_results(self, duplicate_groups):
        return gl_duplicates_ui.show_duplicate_results(self, duplicate_groups)

    def _update_duplicate_selection_count(self, event=None):
        return gl_duplicates_ui._update_duplicate_selection_count(self, event=event)

    # Metoda _sort_duplicate_tree pozostaje bez zmian
    # Metoda _open_selected_duplicate_location pozostaje bez zmian

    def _sort_duplicate_tree(self, column_name):
        return gl_duplicates_ui._sort_duplicate_tree(self, column_name)

    def _open_selected_duplicate_location(self):
        return gl_duplicates_ui._open_selected_duplicate_location(self)

    def load_ignored_folders(self):
        """Wczytuje listę ignorowanych folderów do pola Text w ustawieniach."""
        if (
            hasattr(self, "ignored_folders_text")
            and self.ignored_folders_text.winfo_exists()
        ):
            ignored_list = self.settings.get(
                "scan_ignore_folders", []
            )  # Nowy klucz w settings
            # Wyczyść stare dane
            self.ignored_folders_text.delete("1.0", tk.END)
            # Wstaw nowe, każda nazwa w nowej linii
            self.ignored_folders_text.insert("1.0", "\n".join(ignored_list))

    def save_ignored_folders(self):
        """Pobiera nazwy z pola Text, czyści je i zapisuje do konfiguracji."""
        if (
            hasattr(self, "ignored_folders_text")
            and self.ignored_folders_text.winfo_exists()
        ):
            # Pobierz cały tekst
            raw_text = self.ignored_folders_text.get("1.0", tk.END)
            # Podziel na linie, usuń białe znaki z każdej i odfiltruj puste linie
            ignored_list = [
                line.strip().lower() for line in raw_text.splitlines() if line.strip()
            ]
            # Zapisz unikalne wartości (konwersja na set i z powrotem na listę)
            unique_ignored_list = sorted(list(set(ignored_list)))

            self.settings["scan_ignore_folders"] = unique_ignored_list
            save_config(self.config)
            # Przeładuj, aby pokazać posortowaną i oczyszczoną listę
            self.load_ignored_folders()
            messagebox.showinfo(
                "Zapisano", "Lista ignorowanych folderów została zapisana."
            )
            logging.info(f"Zapisano ignorowane foldery: {unique_ignored_list}")

    def _sort_list_view_by_column(self, column_name):
        return gl_library_list_sort._sort_list_view_by_column(self, column_name)

    def _on_list_view_double_click(self, event):
        """Obsługuje podwójne kliknięcie na elemencie listy."""
        item_iid = self.list_view_tree.focus()
        if item_iid and item_iid in self.games:
            logging.info(f"Podwójne kliknięcie na: {item_iid}")
            # Zamiast: self.launch_game(item_iid)
            self.show_game_details(item_iid)  # Otwórz okno szczegółów
        else:
            logging.warning(f"Podwójne kliknięcie na nieznany element: {item_iid}")

    def show_game_details(self, game_name):
        """Otwiera okno ze szczegółami wybranej gry."""
        # Sprawdź, czy okno dla tej gry już nie jest otwarte (proste sprawdzenie po tytule)
        details_title = f"Szczegóły Gry - {game_name}"
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Toplevel) and widget.title() == details_title:
                logging.debug(
                    f"Okno szczegółów dla '{game_name}' już otwarte. Podnoszenie."
                )
                widget.lift()
                widget.focus_force()
                return  # Nie twórz nowego

        logging.info(f"Otwieranie okna szczegółów dla: {game_name}")
        from ui.game_details import GameDetailsWindow

        GameDetailsWindow(self.root, self, game_name)  # Utwórz nowe okno


    def _apply_overlay_position_from_settings(self):
        return gl_overlay_controls._apply_overlay_position_from_settings(self)

    def _reset_overlay_position(self):
        return gl_overlay_controls._reset_overlay_position(self)

    def _on_list_view_right_click(self, event):
        return gl_library_list_context._on_list_view_right_click(self, event)

    # Metoda pomocnicza dla menu kontekstowego
    def _add_to_group_from_menu(self, game_name, group_name):
        return gl_library_list_context._add_to_group_from_menu(
            self, game_name, group_name
        )

    def toggle_show_key(self, entry_widget, show_var):
        return gl_rawg_settings.toggle_show_key(self, entry_widget, show_var)

    def save_rawg_api_key(self):
        return gl_rawg_settings.save_rawg_api_key(self)

    def show_rawg_key_help(self):
        return gl_rawg_settings.show_rawg_key_help(self)


                # Już NIE wywołujemy self.update_saves_list() tutaj bezpośrednio.
            # Błąd inicjalizacji jest już obsługiwany w _copy_or_delete_with_progress


# Główna część programu
if __name__ == "__main__":
    root = tk.Tk()
    try:
        # Użyj ścieżki względnej lub bezwzględnej do ikony
        icon_path = "icon.ico"  # Zakładamy, że plik jest w tym samym folderze co skrypt
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
        else:
            logging.warning(f"Plik ikony '{icon_path}' nie został znaleziony.")
            # Można spróbować załadować z innego miejsca lub pominąć
    except tk.TclError as e:
        logging.error(f"Nie można ustawić ikony okna: {e}")
    except Exception as e:
        logging.error(f"Nieoczekiwany błąd podczas ustawiania ikony: {e}")
    app = GameLauncher(root)
    root.mainloop()

