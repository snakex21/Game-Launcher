from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from launcher.utils import THEMES, get_contrast_color


def _generate_matplotlib_figure(self, chart_data, view_type_display):
    view_type = self.TRANSLATED_TO_STATS_VIEW.get(view_type_display, "Playtime per Day")
    active_theme_name = self.settings.get("theme", "Dark")
    all_themes = self.get_all_available_themes()
    theme_def = all_themes.get(active_theme_name, THEMES.get("Dark", {}))

    if (
        not chart_data
        or not chart_data["x_labels"]
        or not any(y > 0 for y in chart_data["y_values"])
    ):
        fig = Figure(figsize=(6, 4), dpi=100)
        fig.patch.set_facecolor(theme_def.get("background", "#1e1e1e"))
        ax = fig.add_subplot(111)
        ax.set_facecolor(theme_def.get("entry_background", "#2e2e2e"))
        ax.text(
            0.5,
            0.5,
            "Brak danych...",
            horizontalalignment="center",
            verticalalignment="center",
            transform=ax.transAxes,
            color=theme_def.get("foreground", "white"),
        )
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="x", colors="none")
        ax.tick_params(axis="y", colors="none")
        return fig

    fig = Figure(figsize=(6, 4), dpi=100, facecolor=theme_def.get("background", "#1e1e1e"))
    ax = fig.add_subplot(111)
    ax.set_facecolor(theme_def.get("entry_background", "#2e2e2e"))

    x_labels = chart_data["x_labels"]
    y_values = chart_data["y_values"]
    title = chart_data["title"]
    y_label = chart_data["y_label"]

    if view_type == "Playtime by Genre (Pie)":
        colors = plt.cm.Paired(range(len(x_labels)))
        wedges, texts, autotexts = ax.pie(
            y_values,
            labels=None,
            autopct="%1.1f%%",
            startangle=90,
            colors=colors,
            wedgeprops={
                "edgecolor": theme_def.get("background", "#1e1e1e"),
                "linewidth": 0.5,
            },
        )
        plt.setp(
            autotexts,
            size=8,
            weight="bold",
            color=get_contrast_color(theme_def.get("background", "#1e1e1e")),
        )

        legend = ax.legend(
            wedges,
            [f"{l} ({v:.1f}h)" for l, v in zip(x_labels, y_values)],
            title="Gatunki",
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1),
            fontsize=8,
            labelcolor=theme_def.get("foreground", "white"),
            facecolor=theme_def.get("entry_background", "#2e2e2e"),
            edgecolor=theme_def.get("tree_heading", "#3e3e3e"),
            title_fontproperties={"weight": "bold", "size": "9"},
        )
        if legend.get_title():
            legend.get_title().set_color(theme_def.get("foreground", "white"))

        ax.set_title(title, color=theme_def.get("foreground", "white"), fontsize=12, pad=20)
    else:
        bar_color = getattr(self, "stats_bar_color", "#0078d7")
        axis_color = theme_def.get("chart_axis_color", "grey")

        bars = ax.bar(x_labels, y_values, color=bar_color)

        label_texts = []
        if view_type in [
            "Playtime per Day",
            "Playtime per Game",
            "Playtime per Game (Selected)",
            "Launcher Usage per Day",
        ]:
            label_texts = [self.format_play_time(val * 3600) for val in y_values]
            label_texts = [
                text if y_values[i] * 3600 >= 1 else ""
                for i, text in enumerate(label_texts)
            ]
        elif view_type == "Games Played per Day":
            label_texts = [f"{int(val):d}" for val in y_values]
            label_texts = [text if int(text) > 0 else "" for text in label_texts]
        elif view_type == "Most Launched Games":
            label_texts = [f"{int(val):d}" for val in y_values]
            label_texts = [text if int(text) > 0 else "" for text in label_texts]
        elif view_type == "Average Session Time":
            label_texts = [f"{val:.0f}m" if val >= 1 else "< 1m" for val in y_values]
            label_texts = [
                text if y_values[i] > 0 else ""
                for i, text in enumerate(label_texts)
            ]
        else:
            label_texts = [str(val) for val in y_values]

        if view_type != "Playtime by Genre (Pie)":
            if "bars" in locals():
                ax.bar_label(
                    bars,
                    labels=label_texts,
                    padding=3,
                    color=theme_def.get("foreground", "white"),
                    fontsize=8,
                )

        ax.set_title(title, color=theme_def.get("foreground", "white"), fontsize=12)
        ax.set_ylabel(y_label, color=theme_def.get("foreground", "white"), fontsize=10)
        ax.tick_params(axis="y", colors=theme_def.get("foreground", "white"), labelsize=8)
        ax.tick_params(
            axis="x",
            colors=theme_def.get("foreground", "white"),
            labelsize=8,
            rotation=45,
            pad=5,
        )
        plt.setp(ax.get_xticklabels(), ha="right")

        ax.yaxis.grid(True, linestyle="--", which="major", color="grey", alpha=0.25)
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_color(axis_color)
        ax.spines["left"].set_color(axis_color)

    fig.tight_layout(rect=[0, 0, 0.85, 1] if view_type == "Playtime by Genre (Pie)" else None)
    return fig


__all__ = [
    "_generate_matplotlib_figure",
]
