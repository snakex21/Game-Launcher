import importlib

_EXPORTS = {
    "ExtendedModManager": "ui.mod_manager",
    "GameForm": "ui.game_form",
    "SaveManager": "ui.save_manager",
    "ManageGenresWindow": "ui.manage_genres_window",
    "ToolTip": "ui.components",
    "TrackOverlayWindow": "ui.overlay",
    "GameDetailsWindow": "ui.game_details",
    "MusicPlayerPage": "ui.music_player",
    "AddProfileDialog": "ui.dialogs",
    "ScanVerificationWindow": "ui.dialogs",
    "AchievementForm": "ui.dialogs",
    "ChatServerEditorDialog": "ui.dialogs",
    "AdvancedFilterManager": "ui.filters",
    "FilterEditorWindow": "ui.filters",
    "RuleEditor": "ui.filters",
    "ThemeEditorWindow": "ui.filters",
}

__all__ = list(_EXPORTS.keys())


def __getattr__(name):
    module_path = _EXPORTS.get(name)
    if module_path is None:
        raise AttributeError(f"module 'ui' has no attribute '{name}'")
    module = importlib.import_module(module_path)
    value = getattr(module, name)
    globals()[name] = value
    return value
