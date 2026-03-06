import datetime
import logging
import time
from collections import defaultdict
from tkinter import messagebox


def _prepare_chart_data(self):
    start_date, end_date = self._get_time_period_dates()
    if start_date is None or end_date is None:
        return None

    selected_display_view = self.stats_view_var.get()
    view_type = self.TRANSLATED_TO_STATS_VIEW.get(
        selected_display_view, "Playtime per Day"
    )
    logging.info(
        f"Przygotowywanie danych dla widoku: '{view_type}', "
        f"okres: {start_date} - {end_date}"
    )

    dates_in_period = [
        start_date + datetime.timedelta(days=i)
        for i in range((end_date - start_date).days + 1)
    ]
    today = datetime.date.today()
    if start_date <= today <= end_date and today not in dates_in_period:
        dates_in_period.append(today)
        dates_in_period.sort()

    daily_playtime_seconds = defaultdict(float)
    daily_games_set = defaultdict(set)
    per_game_playtime_seconds = defaultdict(float)
    selected_game_daily_playtime = defaultdict(float)
    genre_playtime_seconds = defaultdict(float)
    tag_playtime_seconds = defaultdict(float)
    game_launch_counts = defaultdict(int)
    game_session_durations = defaultdict(list)
    total_sessions_count = 0
    total_sessions_duration = 0.0

    selected_game_name = None
    if view_type == "Playtime per Game (Selected)":
        selected_game_name = self.stats_game_var.get()
        if not selected_game_name or selected_game_name not in self.games:
            messagebox.showerror(
                "Błąd Gry",
                "Wybierz poprawną grę z listy.",
                parent=self.stats_page_frame,
            )
            return None

    for game_name, game_data in self.games.items():
        if view_type == "Playtime per Game (Selected)" and game_name != selected_game_name:
            continue

        game_genres = game_data.get("genres", [])
        game_tags = game_data.get("tags", [])

        for session in game_data.get("play_sessions", []):
            session_start_ts = session.get("start")
            session_end_ts = session.get("end")
            if not session_start_ts or not session_end_ts:
                continue

            session_duration = session_end_ts - session_start_ts
            try:
                session_start_date = datetime.date.fromtimestamp(session_start_ts)
                session_date_end = datetime.date.fromtimestamp(session_end_ts)
            except ValueError as e_date:
                logging.warning(
                    f"Nie można przekonwertować timestamp sesji na datę "
                    f"dla gry {game_name}: {e_date}"
                )
                continue

            if start_date <= session_start_date <= end_date:
                game_launch_counts[game_name] += 1

            current_check_date = start_date
            session_counted_for_avg = False
            while current_check_date <= end_date:
                if session_start_date <= current_check_date <= session_date_end:
                    day_start_ts = time.mktime(current_check_date.timetuple())
                    day_end_ts = day_start_ts + 86_400

                    overlap_start = max(session_start_ts, day_start_ts)
                    overlap_end = min(session_end_ts, day_end_ts)
                    duration_on_day = max(0, overlap_end - overlap_start)

                    if duration_on_day > 0:
                        daily_playtime_seconds[current_check_date] += duration_on_day
                        daily_games_set[current_check_date].add(game_name)
                        per_game_playtime_seconds[game_name] += duration_on_day
                        for genre in game_genres:
                            genre_playtime_seconds[genre] += duration_on_day
                        for tag in game_tags:
                            tag_playtime_seconds[tag] += duration_on_day

                        if game_name == selected_game_name:
                            selected_game_daily_playtime[current_check_date] += duration_on_day

                        if (
                            not session_counted_for_avg
                            and start_date <= session_start_date <= end_date
                        ):
                            game_session_durations[game_name].append(session_duration)
                            total_sessions_duration += session_duration
                            total_sessions_count += 1
                            session_counted_for_avg = True

                current_check_date += datetime.timedelta(days=1)

    launcher_usage_seconds = defaultdict(float)
    for iso_date, secs in self.local_settings.get(
        "launcher_daily_usage_seconds", {}
    ).items():
        try:
            launcher_usage_seconds[datetime.date.fromisoformat(iso_date)] += secs
        except ValueError:
            logging.warning(f"Zły klucz daty w launcher_daily_usage_seconds: {iso_date}")

    if start_date <= today <= end_date:
        launcher_usage_seconds[today] += time.time() - self.launcher_start_time

    chart_data = {
        "x_labels": [],
        "y_values": [],
        "details": None,
        "title": "",
        "y_label": "",
        "all_games_playtime": per_game_playtime_seconds,
    }

    if view_type == "Playtime per Day":
        chart_data["title"] = (
            f"Czas gry dziennie ({start_date:%Y-%m-%d} – {end_date:%Y-%m-%d})"
        )
        chart_data["y_label"] = "Czas gry (godziny)"
        for dt in dates_in_period:
            chart_data["x_labels"].append(dt.strftime("%m-%d"))
            chart_data["y_values"].append(round(daily_playtime_seconds[dt] / 3600, 2))

    elif view_type == "Games Played per Day":
        chart_data["title"] = (
            f"Liczba unikalnych gier dziennie "
            f"({start_date:%Y-%m-%d} – {end_date:%Y-%m-%d})"
        )
        chart_data["y_label"] = "Liczba gier"
        chart_data["details"] = daily_games_set
        for dt in dates_in_period:
            chart_data["x_labels"].append(dt.strftime("%m-%d"))
            chart_data["y_values"].append(len(daily_games_set[dt]))

    elif view_type == "Playtime per Game":
        chart_data["title"] = (
            f"Łączny czas gry per gra "
            f"({start_date:%Y-%m-%d} – {end_date:%Y-%m-%d})"
        )
        chart_data["y_label"] = "Czas gry (godziny)"
        sorted_games = sorted(
            per_game_playtime_seconds.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:20]
        for game_name, seconds in sorted_games:
            if seconds > 0:
                chart_data["x_labels"].append(game_name)
                chart_data["y_values"].append(round(seconds / 3600, 2))

    elif view_type == "Playtime per Game (Selected)" and selected_game_name:
        chart_data["title"] = (
            f"Czas gry dla '{selected_game_name}' dziennie "
            f"({start_date:%Y-%m-%d} – {end_date:%Y-%m-%d})"
        )
        chart_data["y_label"] = "Czas gry (godziny)"
        for dt in dates_in_period:
            chart_data["x_labels"].append(dt.strftime("%m-%d"))
            chart_data["y_values"].append(
                round(selected_game_daily_playtime[dt] / 3600, 2)
            )

    elif view_type == "Playtime by Genre (Pie)":
        chart_data["title"] = (
            f"Udział gatunków w czasie gry "
            f"({start_date:%Y-%m-%d} – {end_date:%Y-%m-%d})"
        )
        chart_data["y_label"] = ""
        sorted_genres = sorted(
            genre_playtime_seconds.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        limit = 8
        top_genres = sorted_genres[:limit]
        other_seconds = sum(item[1] for item in sorted_genres[limit:])

        chart_data["x_labels"] = [g for g, _ in top_genres]
        chart_data["y_values"] = [round(sec / 3600, 2) for _, sec in top_genres]
        if other_seconds > 0:
            chart_data["x_labels"].append("Inne")
            chart_data["y_values"].append(round(other_seconds / 3600, 2))

    elif view_type == "Most Launched Games":
        chart_data["title"] = (
            f"Najczęściej uruchamiane gry "
            f"({start_date:%Y-%m-%d} – {end_date:%Y-%m-%d})"
        )
        chart_data["y_label"] = "Liczba uruchomień"
        sorted_launches = sorted(
            game_launch_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:20]
        for game_name, count in sorted_launches:
            if count > 0:
                chart_data["x_labels"].append(game_name)
                chart_data["y_values"].append(count)

    elif view_type == "Launcher Usage per Day":
        chart_data["title"] = (
            f"Czas w launcherze dziennie "
            f"({start_date:%Y-%m-%d} – {end_date:%Y-%m-%d})"
        )
        chart_data["y_label"] = "Czas (godziny)"
        for dt in dates_in_period:
            chart_data["x_labels"].append(dt.strftime("%m-%d"))
            chart_data["y_values"].append(round(launcher_usage_seconds[dt] / 3600, 2))

    elif view_type == "Average Session Time":
        chart_data["title"] = (
            f"Średni czas sesji per gra "
            f"({start_date:%Y-%m-%d} – {end_date:%Y-%m-%d})"
        )
        chart_data["y_label"] = "Średni czas (minuty)"
        avg_session_times = {
            g: (sum(durs) / len(durs)) / 60
            for g, durs in game_session_durations.items()
            if durs
        }
        sorted_avg = sorted(
            avg_session_times.items(), key=lambda item: item[1], reverse=True
        )[:20]
        for game_name, minutes in sorted_avg:
            if minutes > 0:
                chart_data["x_labels"].append(game_name)
                chart_data["y_values"].append(round(minutes, 1))

    logging.info(
        f"Przygotowano dane dla '{view_type}': "
        f"X={len(chart_data['x_labels'])}, Y={len(chart_data['y_values'])}"
    )
    return chart_data


__all__ = [
    "_prepare_chart_data",
]
