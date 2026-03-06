import logging
import re
import threading
import tkinter as tk
import webbrowser
from io import BytesIO
from tkinter import ttk

from ui.components import ToolTip
from launcher.utils import THEMES

def _parse_text_for_links(self, text_content):
        """
        Analizuje tekst w poszukiwaniu linków URL.
        Zwraca listę krotek: (fragment_tekstu, typ_segmentu),
        gdzie typ_segmentu to "text" lub "link".
        """
        # Bardzo prosty regex do wykrywania URL. Można go znacznie ulepszyć.
        # Ten regex łapie http://, https:// oraz www. (z opcjonalnym / na końcu)
        # UWAGA: Ten regex jest uproszczony i może nie łapać wszystkich poprawnych URL
        # ani poprawnie obsługiwać wszystkich przypadków brzegowych (np. URL w nawiasach).
        url_pattern = re.compile(
            r'((?:https?://|www\.)[^\s<>"\'(){}|\\^`]+(?:[^\s<>"\'(){}|\\^`\.])?)'
            # Wyjaśnienie regexu:
            # (?:https?://|www\.)  - Zaczyna się od http://, https:// lub www.
            # [^\s<>"\'(){}|\\^`]+ - Jeden lub więcej znaków, które nie są spacją ani niektórymi znakami specjalnymi
            # (?:[^\s<>"\'(){}|\\^`\.])? - Opcjonalny ostatni znak, który nie jest kropką (aby uniknąć łapania kropki na końcu zdania)
            # Całość w grupie przechwytującej (...)
        )

        segments = []
        last_end = 0
        for match in url_pattern.finditer(text_content):
            start, end = match.span()
            link_url = match.group(1)

            # Dodaj tekst przed linkiem (jeśli jest)
            if start > last_end:
                segments.append((text_content[last_end:start], "text"))

            # Dodaj link
            segments.append((link_url, "link"))
            last_end = end

        # Dodaj tekst po ostatnim linku (jeśli jest)
        if last_end < len(text_content):
            segments.append((text_content[last_end:], "text"))

        if not segments and text_content:  # Jeśli nie znaleziono linków, ale jest tekst
            segments.append((text_content, "text"))

        return segments

def _create_chat_message_tags_if_needed(self):
        """Pomocnicza metoda do jednorazowego tworzenia tagów dla wiadomości czatu."""
        if (
            hasattr(self, "_chat_message_tags_created")
            and self._chat_message_tags_created
        ):
            return

        # Definicje tagów dla stylów tekstu i linków
        theme_def = self.get_all_available_themes().get(
            self.settings.get("theme", "Dark"), THEMES["Dark"]
        )

        # Dla zwykłego tekstu w dymkach (jeśli nie używamy tk.Label dla tekstu)
        # self.chat_message_display.tag_config("my_message_text_tag", foreground=theme_def.get('link_foreground', 'lightblue'))
        # self.chat_message_display.tag_config("other_message_text_tag", foreground=theme_def.get('foreground', 'lightgreen'))

        # Dla linków
        link_fg_color = theme_def.get("link_foreground", "lightblue")  # Kolor z motywu
        self.chat_message_display.tag_config(
            "chat_link_tag", foreground=link_fg_color, underline=True
        )
        self.chat_message_display.tag_bind(
            "chat_link_tag",
            "<Enter>",
            lambda e: self.chat_message_display.config(cursor="hand2"),
        )
        self.chat_message_display.tag_bind(
            "chat_link_tag",
            "<Leave>",
            lambda e: self.chat_message_display.config(cursor=""),
        )
        # Bindowanie kliknięcia do otwierania linku będzie dodawane dynamicznie

        # Ustawienia tagów dla wyrównania dymków (jak poprzednio)
        # Możemy to zrefaktoryzować do _on_chat_display_resize
        # bubble_margin_percent = 0.15 # np. 15% marginesu z jednej strony
        # chat_width = self.chat_message_display.winfo_width()
        # if chat_width < 50: chat_width = 500 # Domyślna szerokość, jeśli widget jeszcze nie ma rozmiaru
        # l_margin = int(chat_width * bubble_margin_percent)
        # r_margin = 10

        # self.chat_message_display.tag_config("my_message_bubble_align_tag",
        #                                      justify='left', # Tekst w dymku od lewej
        #                                      lmargin1=r_margin, # Mały lewy margines dla dymka
        #                                      rmargin1=l_margin)  # Duży prawy margines dla dymka (dymek po lewej)
        # self.chat_message_display.tag_config("other_message_bubble_align_tag",
        #                                      justify='left', # Tekst w dymku od lewej
        #                                      lmargin1=l_margin,  # Duży lewy margines dla dymka
        #                                      rmargin1=r_margin)   # Mały prawy margines dla dymka (dymek po prawej)

        setattr(self, "_chat_message_tags_created", True)

def _apply_chat_message_tags_and_alignment(self):
        """Stosuje tagi wyrównania do dymków wiadomości w oknie czatu.
        Powinno być wywoływane po wstawieniu wszystkich wiadomości
        lub przy zmianie rozmiaru okna, jeśli wyrównanie od tego zależy.
        """
        if (
            not hasattr(self, "chat_message_display")
            or not self.chat_message_display.winfo_exists()
        ):
            return

        # Marginesy dla dymków (symulacja wyrównania)
        display_width_px = self.chat_message_display.winfo_width()
        bubble_margin = int(display_width_px * 0.30)  # Np. dymek zajmuje 70% szerokości

        self.chat_message_display.tag_config(
            "my_message_bubble_align_tag",
            justify="right",
            lmargin1=bubble_margin,
            rmargin1=10,
        )  # Moje - duży lewy margines
        self.chat_message_display.tag_config(
            "other_message_bubble_align_tag",
            justify="left",
            lmargin1=10,
            rmargin1=bubble_margin,
        )

def _load_and_display_chat_image_thumbnail(
        self, image_url, target_label_widget, message_id_for_cache=None
    ):
        """
        Pobiera obraz z URL i wyświetla go jako miniaturkę w podanym ttk.Label.
        Działa w tle. Używa cache'u.
        """
        log_prefix = f"ChatImgLoad (ID: {message_id_for_cache}, URL: {image_url}): "
        logging.debug(f"{log_prefix}Rozpoczęto próbę załadowania miniaturki.")

        import requests
        from PIL import Image, ImageTk, UnidentifiedImageError

        if not target_label_widget.winfo_exists():
            logging.warning(
                f"{log_prefix}Label docelowy już nie istnieje. Przerywanie."
            )
            return

        if not hasattr(self, "_chat_image_thumbnail_cache"):
            self._chat_image_thumbnail_cache = {}

        thumbnail_max_width = 200
        thumbnail_max_height = 150
        cache_key = f"{image_url}_{thumbnail_max_width}x{thumbnail_max_height}"

        if cache_key in self._chat_image_thumbnail_cache:
            cached_photo = self._chat_image_thumbnail_cache[cache_key]
            if cached_photo:
                logging.debug(
                    f"{log_prefix}Miniaturka znaleziona w cache. Aktualizowanie UI."
                )
                self.root.after(
                    0,
                    lambda: self._update_image_label(
                        target_label_widget, cached_photo, image_url, log_prefix
                    ),
                )
                return
            else:
                logging.debug(
                    f"{log_prefix}Miniaturka była w cache jako None (poprzedni błąd). Próba ponownego załadowania."
                )

        # Ustawienie tekstu "Ładowanie..." przed próbą pobrania
        self.root.after(
            0, lambda: target_label_widget.config(text="[Ładowanie podglądu...]")
        )

        try:
            logging.debug(f"{log_prefix}Pobieranie danych obrazu z serwera...")
            response = requests.get(image_url, stream=True, timeout=20)
            response.raise_for_status()
            logging.debug(f"{log_prefix}Odpowiedź serwera: {response.status_code}")

            image_data_bytes = response.content  # Pobierz całą zawartość od razu
            logging.debug(
                f"{log_prefix}Pobrano {len(image_data_bytes)} bajtów danych obrazu."
            )

            if not image_data_bytes:
                logging.error(f"{log_prefix}Pobrane dane obrazu są puste.")
                raise ValueError("Puste dane obrazu")

            image_data_io = BytesIO(image_data_bytes)

            logging.debug(
                f"{log_prefix}Próba otwarcia obrazu z BytesIO za pomocą Pillow..."
            )
            with Image.open(image_data_io) as img:
                logging.debug(
                    f"{log_prefix}Obraz otwarty. Format: {img.format}, Rozmiar: {img.size}, Tryb: {img.mode}"
                )
                img.thumbnail(
                    (thumbnail_max_width, thumbnail_max_height),
                    Image.Resampling.LANCZOS,
                )
                logging.debug(
                    f"{log_prefix}Miniaturka utworzona. Nowy rozmiar: {img.size}"
                )
                photo_image = ImageTk.PhotoImage(img)
                logging.debug(f"{log_prefix}ImageTk.PhotoImage utworzony.")

            self._chat_image_thumbnail_cache[cache_key] = photo_image
            self.root.after(
                0,
                lambda: self._update_image_label(
                    target_label_widget, photo_image, image_url, log_prefix
                ),
            )
            logging.info(
                f"{log_prefix}Miniaturka pomyślnie załadowana i zaplanowano aktualizację UI."
            )

        except requests.exceptions.RequestException as e:
            logging.error(f"{log_prefix}Błąd sieciowy: {e}")
            self._chat_image_thumbnail_cache[cache_key] = None
            self.root.after(0, lambda: target_label_widget.config(text="[Błąd sieci]"))
        except UnidentifiedImageError:
            logging.error(
                f"{log_prefix}Nie można zidentyfikować obrazka (nieprawidłowy format?)"
            )
            self._chat_image_thumbnail_cache[cache_key] = None
            self.root.after(
                0, lambda: target_label_widget.config(text="[Zły format obrazka]")
            )
        except ValueError as ve:  # Dla pustych danych obrazu
            logging.error(f"{log_prefix}Błąd wartości (np. puste dane): {ve}")
            self._chat_image_thumbnail_cache[cache_key] = None
            self.root.after(
                0, lambda: target_label_widget.config(text="[Błąd danych obrazka]")
            )
        except Exception:
            logging.exception(f"{log_prefix}Nieoczekiwany błąd")
            self._chat_image_thumbnail_cache[cache_key] = None
            self.root.after(
                0, lambda: target_label_widget.config(text="[Błąd ładowania]")
            )

def _update_image_label(
        self, label_widget, photo_image, original_url, log_prefix_outer=""
    ):
        """Aktualizuje etykietę obrazkiem (wywoływane przez root.after)."""
        log_prefix = f"{log_prefix_outer}UpdateImgLabel: "
        if label_widget.winfo_exists():
            logging.debug(f"{log_prefix}Aktualizowanie widgetu Label obrazkiem.")
            label_widget.config(image=photo_image, text="")
            label_widget.image = photo_image
            label_widget.unbind("<Button-1>")
            label_widget.bind(
                "<Button-1>", lambda e, url=original_url: webbrowser.open(url)
            )
            ToolTip(label_widget, "Kliknij, aby otworzyć pełny obraz")
            logging.debug(f"{log_prefix}Widget Label zaktualizowany.")
        else:
            logging.warning(
                f"{log_prefix}Widget Label już nie istnieje. Pominięto aktualizację."
            )

def _display_chat_message(
        self,
        message_text_with_timestamp,
        msg_type="normal",
        attachment_data=None,
        message_id=None,
        is_read_by_receiver=False,
        sender_id_for_read_status_check=None,
        replied_to_message_preview=None,  # Istniejący parametr
        message_data=None,
    ):  # --- NOWE ZMIANY: Dodaj pełne dane wiadomości ---
        """
        Renderuje jedną wiadomość w oknie czatu z opcjonalnymi załącznikami i cytatem.
        """
        # Utwórz tagi do linków tylko raz
        self._create_chat_message_tags_if_needed()
        # Brak widgetu? wyjdź
        if (
            not hasattr(self, "chat_message_display")
            or not self.chat_message_display.winfo_exists()
        ):
            return
        self.chat_message_display.config(state=tk.NORMAL)
        # Clear
        if msg_type == "clear":
            self.chat_message_display.delete("1.0", tk.END)
            self._chat_bubble_containers = []
            self.chat_message_display.config(state=tk.DISABLED)
            return

        line_container = None
        bubble_container = None

        if msg_type in ("my_message", "other_message"):
            theme = self.get_all_available_themes().get(
                self.settings.get("theme", "Dark"), THEMES["Dark"]
            )
            bubble_bg = "#004e92" if msg_type == "my_message" else "#2e2e2e"
            text_fg = (
                theme.get("link_foreground", "lightblue")
                if msg_type == "my_message"
                else theme.get("foreground", "lightgreen")
            )
            line_bg = self.chat_message_display.cget("bg")
            line_container = tk.Frame(self.chat_message_display, bg=line_bg)
            bubble_container = tk.Frame(
                line_container,
                bg=bubble_bg,
                padx=8,
                pady=4,
                relief="solid",
                borderwidth=1,
            )
            if message_id is not None:
                self._rendered_message_widgets[message_id] = (
                    bubble_container  # Zapisz referencję do dymka
                )
                bubble_container._original_bg = (
                    bubble_bg  # Zapisz oryginalny kolor tła do resetu
                )
                # Dodaj to samo do wewnętrznych ramek i labelek w dymku
                bubble_container._bubble_children_colors = {}

            # Bind right-click on bubble
            bubble_container.bind(
                "<Button-3>",
                lambda e, msg_id=message_id, cont=bubble_container: self._show_chat_message_context_menu(
                    e, msg_id, cont
                ),
            )
            if not hasattr(self, "_chat_bubble_containers"):
                self._chat_bubble_containers = []
            self._chat_bubble_containers.append(bubble_container)
            if message_id is not None:
                bubble_container._chat_message_id = message_id

            content_frame = tk.Frame(bubble_container, bg=bubble_bg)
            content_frame.pack(fill=tk.X, expand=True)
            if message_id is not None:
                bubble_container._bubble_children_colors[content_frame] = (
                    content_frame.cget("bg")
                )

            # Cytat (replied_to_message_preview)
            if replied_to_message_preview:
                q_bg = theme.get("entry_background", "#3a3a3a")
                q_fg = theme.get("foreground", "gray")
                q_border = theme.get("tree_heading", "#555555")
                quote = tk.Frame(
                    content_frame,
                    bg=q_bg,
                    bd=1,
                    relief="solid",
                    highlightbackground=q_border,
                    highlightcolor=q_border,
                    highlightthickness=1,
                )
                quote.pack(fill=tk.X, anchor="w", pady=(0, 5))
                if message_id is not None:
                    bubble_container._bubble_children_colors[quote] = quote.cget("bg")
                q_text = replied_to_message_preview.get(
                    "content"
                ) or replied_to_message_preview.get(
                    "attachment_original_filename", "[Załącznik]"
                )

                # Użyj tk.Label, aby można było kontrolować kursor i bindowanie
                quote_label = tk.Label(
                    quote,
                    text=f"\"{q_text[:50]}{'...' if len(q_text)>50 else ''}\"",
                    wraplength=300,
                    justify=tk.LEFT,
                    font=("Segoe UI", 8, "italic"),
                    background=q_bg,
                    foreground=q_fg,
                    cursor="hand2",
                )  # Kursor ręki
                quote_label.pack(fill=tk.X)
                if message_id is not None:
                    bubble_container._bubble_children_colors[quote_label] = (
                        quote_label.cget("bg")
                    )

                # Bind kliknięcia do funkcji przeskoku
                quote_label.bind(
                    "<Button-1>",
                    lambda e, target_msg_id=replied_to_message_preview.get(
                        "id"
                    ): self._jump_to_message(target_msg_id),
                )

            # Tekst z linkami
            if message_text_with_timestamp:
                seg_frame = tk.Frame(content_frame, bg=bubble_bg)
                seg_frame.pack(fill=tk.X, pady=(0, 3))
                if message_id is not None:
                    bubble_container._bubble_children_colors[seg_frame] = (
                        seg_frame.cget("bg")
                    )
                for txt, typ in self._parse_text_for_links(message_text_with_timestamp):
                    if typ == "link":
                        lbl = tk.Label(
                            seg_frame,
                            text=txt,
                            fg=theme.get("link_foreground", "lightblue"),
                            bg=bubble_bg,
                            cursor="hand2",
                            font=("Segoe UI", 9, "underline"),
                        )
                        lbl.pack(side=tk.LEFT)
                        if message_id is not None:
                            bubble_container._bubble_children_colors[lbl] = lbl.cget(
                                "bg"
                            )
                        lbl.bind(
                            "<Button-1>",
                            lambda e, url=txt: webbrowser.open(
                                url if url.startswith("http") else "http://" + url
                            ),
                        )
                        lbl.bind(
                            "<Button-3>",
                            lambda e, msg_id=message_id, cont=bubble_container: self._show_chat_message_context_menu(
                                e, msg_id, cont
                            ),
                        )
                    else:
                        lbl = tk.Label(
                            seg_frame,
                            text=txt,
                            fg=text_fg,
                            bg=bubble_bg,
                            font=("Segoe UI", 9),
                        )
                        lbl.pack(side=tk.LEFT)
                        if message_id is not None:
                            bubble_container._bubble_children_colors[lbl] = lbl.cget(
                                "bg"
                            )
                        lbl.bind(
                            "<Button-3>",
                            lambda e, msg_id=message_id, cont=bubble_container: self._show_chat_message_context_menu(
                                e, msg_id, cont
                            ),
                        )

            if message_data and message_data.get("edited_at"):
                edited_indicator_frame = tk.Frame(content_frame, bg=bubble_bg)
                edited_indicator_frame.pack(
                    fill=tk.X, anchor="e", pady=(0, 0), padx=(0, 0)
                )
                if message_id is not None:
                    bubble_container._bubble_children_colors[edited_indicator_frame] = (
                        edited_indicator_frame.cget("bg")
                    )
                edited_label = ttk.Label(
                    edited_indicator_frame,
                    text="(edytowano)",
                    font=("Segoe UI", 7, "italic"),
                    foreground=theme.get("chart_axis_color", "gray"),
                    background=bubble_bg,
                )
                edited_label.pack(side=tk.RIGHT, anchor="se", padx=(0, 0), pady=(0, 0))
                if message_id is not None:
                    bubble_container._bubble_children_colors[edited_label] = (
                        edited_label.cget("bg")
                    )
                edited_label.bind(
                    "<Button-3>",
                    lambda e, msg_id=message_id, cont=bubble_container: self._show_chat_message_context_menu(
                        e, msg_id, cont
                    ),
                )

        # Załączniki
        if attachment_data and bubble_container:
            fn = attachment_data.get("server_filename")
            orig = attachment_data.get("original_filename", "plik")
            mimetype = attachment_data.get(
                "attachment_mimetype", "application/octet-stream"
            )
            attach_bg = bubble_container.cget("bg")
            theme = self.get_all_available_themes().get(
                self.settings.get("theme", "Dark"), THEMES["Dark"]
            )
            link_color = theme.get("link_foreground", "lightblue")

            attach_frame = tk.Frame(bubble_container, bg=attach_bg)
            attach_frame.pack(fill=tk.X, anchor="w", pady=(3, 0))
            if message_id is not None:
                bubble_container._bubble_children_colors[attach_frame] = (
                    attach_frame.cget("bg")
                )
            # Bind right-click on attachment
            attach_frame.bind(
                "<Button-3>",
                lambda e, msg_id=message_id, cont=bubble_container: self._show_chat_message_context_menu(
                    e, msg_id, cont
                ),
            )

            if mimetype.startswith("image/"):
                preview = tk.Label(
                    attach_frame, text="Ładowanie podglądu...", bg=attach_bg
                )
                preview.pack(anchor="w", padx=5, pady=(5, 0))
                if message_id is not None:
                    bubble_container._bubble_children_colors[preview] = preview.cget(
                        "bg"
                    )
                threading.Thread(
                    target=self._load_and_display_chat_image_thumbnail,
                    args=(
                        f"{self.chat_server_url}/download_file/{fn}",
                        preview,
                        f"chat_img_{message_id}",
                    ),
                    daemon=True,
                ).start()
                # link do oryginału
                link = tk.Label(
                    attach_frame,
                    text=f"Pobierz oryginał: {orig}",
                    fg=link_color,
                    bg=attach_bg,
                    cursor="hand2",
                    font=("Segoe UI", 8, "underline"),
                )
                link.pack(anchor="w", padx=5, pady=(2, 0))
                if message_id is not None:
                    bubble_container._bubble_children_colors[link] = link.cget("bg")
                link.bind(
                    "<Button-1>",
                    lambda e, url=f"{self.chat_server_url}/download_file/{fn}": webbrowser.open(
                        url
                    ),
                )
                link.bind(
                    "<Button-3>",
                    lambda e, msg_id=message_id, cont=bubble_container: self._show_chat_message_context_menu(
                        e, msg_id, cont
                    ),
                )
            else:
                info = tk.Frame(attach_frame, bg=attach_bg)
                info.pack(fill=tk.X)
                if message_id is not None:
                    bubble_container._bubble_children_colors[info] = info.cget("bg")
                icon = tk.Label(info, text="📄", bg=attach_bg)
                icon.pack(side=tk.LEFT, padx=(0, 5))
                if message_id is not None:
                    bubble_container._bubble_children_colors[icon] = icon.cget("bg")
                link = tk.Label(
                    info,
                    text=orig,
                    fg=link_color,
                    bg=attach_bg,
                    cursor="hand2",
                    font=("Segoe UI", 9, "underline"),
                )
                link.pack(side=tk.LEFT)
                if message_id is not None:
                    bubble_container._bubble_children_colors[link] = link.cget("bg")
                link.bind(
                    "<Button-1>",
                    lambda e, url=f"{self.chat_server_url}/download_file/{fn}": webbrowser.open(
                        url
                    ),
                )
                link.bind(
                    "<Button-3>",
                    lambda e, msg_id=message_id, cont=bubble_container: self._show_chat_message_context_menu(
                        e, msg_id, cont
                    ),
                )

        # Wstawianie dymka lub tekstu
        if line_container and bubble_container:
            pos = tk.LEFT if msg_type == "my_message" else tk.RIGHT
            bubble_container.pack(side=pos, padx=5, pady=2)
            self.chat_message_display.insert(tk.END, "\n")
            if message_id is not None:  # Zapisz referencję również do line_container
                line_container._chat_message_id = message_id
                self._rendered_message_widgets[message_id] = (
                    line_container  # Użyj line_container jako głównej referencji do okna
                )
                line_container._original_bg = line_bg  # Zapisz oryginalne tło
                line_container._bubble_children_colors = (
                    bubble_container._bubble_children_colors
                )  # Przekaż info o kolorach dzieci
            self.chat_message_display.window_create(tk.END, window=line_container)
            self.chat_message_display.insert(tk.END, "\n\n")
        elif msg_type == "system":
            self.chat_message_display.insert(
                tk.END, f"{message_text_with_timestamp}\n", "system_tag"
            )
        elif msg_type == "error":
            self.chat_message_display.insert(
                tk.END, f"[BŁĄD] {message_text_with_timestamp}\n", "error_tag"
            )
        else:
            self.chat_message_display.insert(tk.END, f"{message_text_with_timestamp}\n")

        # Wskaźnik przeczytania
        if msg_type == "my_message" and is_read_by_receiver and bubble_container:
            rd = tk.Label(bubble_container, text="👁️", bg=bubble_bg, fg=text_fg)
            rd.pack(side=tk.RIGHT, anchor="se", padx=(0, 1), pady=(1, 0))
            if message_id is not None:
                bubble_container._bubble_children_colors[rd] = rd.cget("bg")

        self.chat_message_display.config(state=tk.DISABLED)

def _jump_to_message(self, target_message_id: int):
        """
        Przewija widok czatu do wiadomości o podanym ID i ją podświetla.
        Jeśli wiadomość nie jest aktualnie renderowana, przeładuje historię.
        """
        if not target_message_id:
            logging.warning("Jump: Otrzymano puste ID wiadomości do przeskoku.")
            return

        # Spróbuj znaleźć widget wiadomości, jeśli jest już w pamięci i na ekranie
        target_widget = self._rendered_message_widgets.get(target_message_id)

        if target_widget and target_widget.winfo_exists():
            logging.info(
                f"Jump: Znaleziono wiadomość ID {target_message_id} już wyrenderowaną. Przewijanie..."
            )
            # `self.chat_message_display.index(widget)` zwraca indeks tekstu, gdzie widget został wstawiony.
            self.chat_message_display.see(
                self.chat_message_display.index(target_widget)
            )
            self._highlight_message_widget(target_widget)
        else:
            logging.info(
                f"Jump: Wiadomość ID {target_message_id} nie jest wyrenderowana. Przeładowywanie historii i przewijanie..."
            )
            # Ustaw flagę, aby po przeładowaniu historii przewinąć do tej wiadomości
            self._jump_target_message_id = target_message_id
            # Wymuś ponowne załadowanie i wyświetlenie historii dla aktywnego partnera
            # To spowoduje, że _display_active_chat_history zostanie ponownie wywołane i zobaczy _jump_target_message_id
            self._load_and_display_chat_history(self.active_chat_partner_id)

def _highlight_message_widget(self, widget_to_highlight):
        """
        Tymczasowo podświetla tło dymka wiadomości i jego wewnętrznych elementów.
        """
        if not widget_to_highlight or not widget_to_highlight.winfo_exists():
            return

        original_bg_main = getattr(widget_to_highlight, "_original_bg", None)
        if (
            not original_bg_main
        ):  # Jeśli nie ma zapisanego oryginalnego tła, użyj obecnego
            original_bg_main = widget_to_highlight.cget("bg")
            widget_to_highlight._original_bg = original_bg_main  # Zapisz na przyszłość

        # Zmień tło głównego dymka
        widget_to_highlight.config(bg=self.MESSAGE_HIGHLIGHT_COLOR)

        # Zmień tło wewnętrznych dzieci dymka, które mają zapamiętane oryginalne kolory
        children_colors = getattr(widget_to_highlight, "_bubble_children_colors", {})
        for child_widget, original_child_bg in children_colors.items():
            if child_widget.winfo_exists():
                try:  # Nie wszystkie widgety mogą mieć 'background'
                    child_widget.config(bg=self.MESSAGE_HIGHLIGHT_COLOR)
                except tk.TclError:
                    pass  # Ignoruj, jeśli widget nie obsługuje 'background'

        # Zaplanuj przywrócenie oryginalnych kolorów po 1.5 sekundzie
        self.root.after(
            1500,
            lambda: self._reset_widget_bg_after_highlight(
                widget_to_highlight, original_bg_main, children_colors
            ),
        )

def _reset_widget_bg_after_highlight(
        self, widget, original_main_bg, children_colors
    ):
        """Przywraca oryginalne kolory tła po podświetleniu."""
        if widget.winfo_exists():
            widget.config(bg=original_main_bg)
            for child_widget, original_child_bg in children_colors.items():
                if child_widget.winfo_exists():
                    try:
                        child_widget.config(bg=original_child_bg)
                    except tk.TclError:
                        pass  # Ignoruj błędy
            logging.debug(
                f"Zresetowano podświetlenie dla wiadomości: {getattr(widget, '_chat_message_id', 'N/A')}"
            )

__all__ = [
    "_parse_text_for_links",
    "_create_chat_message_tags_if_needed",
    "_apply_chat_message_tags_and_alignment",
    "_load_and_display_chat_image_thumbnail",
    "_update_image_label",
    "_display_chat_message",
    "_jump_to_message",
    "_highlight_message_widget",
    "_reset_widget_bg_after_highlight",
]
