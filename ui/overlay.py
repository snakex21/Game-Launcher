import logging
import tkinter as tk
from tkinter import ttk


class TrackOverlayWindow(tk.Toplevel):
    def __init__(
        self,
        parent,
        initial_x=None,
        initial_y=None,
        launcher_instance=None,
        save_settings_callback=None,
    ):
        super().__init__(parent)
        self.parent = parent
        self.launcher = launcher_instance
        self.save_settings_callback = save_settings_callback

        self.overrideredirect(True)
        self.wm_attributes("-topmost", True)

        self.transparent_color = "lime green"
        try:
            self.attributes("-transparentcolor", self.transparent_color)
            self.configure(bg=self.transparent_color)
        except tk.TclError:
            fallback_bg = "#212121"
            self.configure(bg=fallback_bg)
            self.transparent_color = fallback_bg

        self.width = 300
        self.height = 70

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        default_x = screen_w - self.width - 20
        default_y = screen_h - self.height - 60

        temp_x = initial_x
        temp_y = initial_y

        if temp_x is None:
            temp_x = default_x
        if temp_y is None:
            temp_y = default_y

        self.x_pos = int(temp_x)
        self.y_pos = int(temp_y)

        self.geometry(f"{self.width}x{self.height}+{int(self.x_pos)}+{int(self.y_pos)}")

        self.drag_frame = ttk.Frame(self, style="Overlay.TFrame")
        self.drag_frame.pack(fill=tk.BOTH, expand=True)
        s = ttk.Style()
        s.configure("Overlay.TFrame", background=self.transparent_color)

        self.drag_frame.columnconfigure(0, weight=1)
        self.drag_frame.rowconfigure(0, weight=0)
        self.drag_frame.rowconfigure(1, weight=0)
        self.drag_frame.rowconfigure(2, weight=0)

        self.track_name_label = ttk.Label(
            self.drag_frame,
            text="Nic nie gra...",
            font=("Segoe UI", 9, "bold"),
            wraplength=self.width - 15,
            justify="left",
            anchor="nw",
            style="Overlay.TLabel",
        )
        self.track_name_label.grid(row=0, column=0, sticky="ew", padx=5, pady=(3, 0))

        self.progress_bar = ttk.Progressbar(
            self.drag_frame,
            orient="horizontal",
            length=self.width - 10,
            mode="determinate",
        )
        s.configure(
            "Overlay.Horizontal.TProgressbar",
            troughcolor="#404040",
            background="#C0C0C0",
            thickness=4,
            borderwidth=0,
        )
        self.progress_bar.config(style="Overlay.Horizontal.TProgressbar")
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=5, pady=(1, 1))

        self.time_label = ttk.Label(
            self.drag_frame,
            text="0:00 / 0:00",
            font=("Segoe UI", 8),
            anchor="e",
            style="Overlay.TLabel",
        )
        self.time_label.grid(row=2, column=0, sticky="ew", padx=5, pady=(0, 3))

        s.configure(
            "Overlay.TLabel", background=self.transparent_color, foreground="#E0E0E0"
        )

        self._offset_x = 0
        self._offset_y = 0
        self.drag_frame.bind("<ButtonPress-1>", self._on_overlay_press)
        self.drag_frame.bind("<ButtonRelease-1>", self._on_overlay_release)
        self.drag_frame.bind("<B1-Motion>", self._on_overlay_motion)
        self.track_name_label.bind("<ButtonPress-1>", self._on_overlay_press)
        self.track_name_label.bind("<ButtonRelease-1>", self._on_overlay_release)
        self.track_name_label.bind("<B1-Motion>", self._on_overlay_motion)
        self.time_label.bind("<ButtonPress-1>", self._on_overlay_press)
        self.time_label.bind("<ButtonRelease-1>", self._on_overlay_release)
        self.time_label.bind("<B1-Motion>", self._on_overlay_motion)

        self.withdraw()

    def _on_overlay_press(self, event):
        self._offset_x = event.x
        self._offset_y = event.y

    def _on_overlay_release(self, event):
        self.x_pos = self.winfo_x()
        self.y_pos = self.winfo_y()
        if self.launcher and hasattr(self.launcher, "local_settings"):
            self.launcher.local_settings["overlay_x_pos"] = self.x_pos
            self.launcher.local_settings["overlay_y_pos"] = self.y_pos
            if self.save_settings_callback:
                self.save_settings_callback(self.launcher.local_settings)
            logging.debug(
                f"Overlay: Zapisano nowa pozycje: x={self.x_pos}, y={self.y_pos}"
            )

    def _on_overlay_motion(self, event):
        new_x = self.winfo_x() + (event.x - self._offset_x)
        new_y = self.winfo_y() + (event.y - self._offset_y)
        self.geometry(f"+{int(new_x)}+{int(new_y)}")

    def update_display(
        self,
        track_name: str | None,
        current_time_sec: float,
        total_time_sec: float,
        is_active: bool,
    ):
        if not self.winfo_exists():
            return

        current_time_sec = max(0, current_time_sec)
        total_time_sec = max(0, total_time_sec)

        if track_name:
            self.track_name_label.config(text=track_name[:60])
        else:
            self.track_name_label.config(text="Nic nie gra...")

        if is_active and total_time_sec > 0:
            if self.progress_bar["mode"] == "indeterminate":
                self.progress_bar.stop()
            self.progress_bar.config(mode="determinate")
            self.progress_bar["maximum"] = total_time_sec
            self.progress_bar["value"] = min(current_time_sec, total_time_sec)

            current_m, current_s = divmod(int(current_time_sec), 60)
            total_m, total_s = divmod(int(total_time_sec), 60)
            self.time_label.config(
                text=f"{current_m:02d}:{current_s:02d} / {total_m:02d}:{total_s:02d}"
            )

        elif is_active and total_time_sec == 0:
            if self.progress_bar["mode"] != "indeterminate":
                self.progress_bar.config(mode="indeterminate")
            self.progress_bar.start(15)
            self.time_label.config(text="??:?? / ??:??")

        else:
            if self.progress_bar["mode"] == "indeterminate":
                self.progress_bar.stop()
            self.progress_bar.config(mode="determinate")
            self.progress_bar["maximum"] = 1
            self.progress_bar["value"] = 0
            self.time_label.config(text="00:00 / 00:00")

    def show_overlay(self):
        if not self.winfo_exists():
            logging.warning("Proba pokazania overlay'a, ktory nie istnieje.")
            return
        self.geometry(f"{self.width}x{self.height}+{self.x_pos}+{self.y_pos}")
        self.deiconify()
        self.lift()

    def hide_overlay(self):
        if self.winfo_exists():
            self.withdraw()
