import time
import tkinter as tk
from tkinter import ttk


def create_time_stats(self, parent, row: int = 0, column: int = 1) -> None:
    frame = ttk.LabelFrame(parent, text="Czas spędzony w grach")
    frame.grid(row=row, column=column, padx=10, pady=10, sticky="nsew")
    parent.rowconfigure(row, weight=1)
    parent.columnconfigure(column, weight=1)

    self.time_unit_var = tk.StringVar(value="godziny")
    ttk.OptionMenu(
        frame,
        self.time_unit_var,
        self.time_unit_var.get(),
        *["godziny", "dni", "miesiące", "lata"],
        command=self.update_time_stats,
    ).grid(row=0, column=0, padx=5, pady=5, sticky="w")

    self.time_labels: dict[str, ttk.Label] = {}
    labels_order = ["Wszystkie gry", "Gry PC", "Emulatory – łącznie"]
    for i, txt in enumerate(labels_order, start=1):
        lbl = ttk.Label(frame, text="")
        lbl.grid(row=i, column=0, sticky="w", padx=5, pady=2)
        self.time_labels[txt] = lbl

    self._time_stats_emulator_rows: list[tuple[str, ttk.Label]] = []
    self.update_time_stats()


def update_time_stats(self, *_):
    unit = self.time_unit_var.get()
    to_unit = {
        "godziny": 3600,
        "dni": 3600 * 24,
        "miesiące": 3600 * 24 * 30,
        "lata": 3600 * 24 * 365,
    }[unit]

    def _fmt(sec: float) -> str:
        return f"{sec/to_unit:.2f} {unit}"

    for _, lbl in self._time_stats_emulator_rows:
        lbl.destroy()
    self._time_stats_emulator_rows.clear()

    self.time_labels["Wszystkie gry"].config(
        text=f"Łącznie: {_fmt(self.get_total_play_time('all'))}"
    )
    self.time_labels["Gry PC"].config(
        text=f"Gry PC: {_fmt(self.get_total_play_time('all', game_type='pc'))}"
    )

    emu_total = self.get_total_play_time("all", game_type="emulator")
    self.time_labels["Emulatory – łącznie"].config(
        text=f"Emulatory (razem): {_fmt(emu_total)}"
    )

    row_start = len(self.time_labels) + 1
    emulators = sorted(
        set(
            g.get("emulator_name")
            for g in self.games.values()
            if g.get("game_type") == "emulator"
        )
    )
    for i, emu in enumerate(emulators, start=row_start):
        secs = self.get_total_play_time("all", emulator_name=emu)
        lbl = ttk.Label(
            self.time_labels["Wszystkie gry"].master,
            text=f"  ↳ {emu}: {_fmt(secs)}",
        )
        lbl.grid(row=i, column=0, sticky="w", padx=20, pady=1)
        self._time_stats_emulator_rows.append((emu, lbl))


def get_total_play_time(
    self,
    period: str = "week",
    game_type: str | None = None,
    emulator_name: str | None = None,
) -> float:
    seconds_in = {
        "week": 60 * 60 * 24 * 7,
        "month": 60 * 60 * 24 * 30,
        "year": 60 * 60 * 24 * 365,
        "all": 10**12,
    }[period]

    now = time.time()
    total = 0.0
    for g in self.games.values():
        if game_type and g.get("game_type", "pc") != game_type:
            continue
        if emulator_name and g.get("emulator_name") != emulator_name:
            continue

        for sess in g.get("play_sessions", []):
            if now - sess["end"] <= seconds_in:
                total += sess["end"] - sess["start"]
    return total


__all__ = ["create_time_stats", "update_time_stats", "get_total_play_time"]
