# Bugfix: Border Color Transparency Issue

## Problem

CustomTkinter (CTkFrame) does not accept "transparent" as a valid `border_color` value. This causes a `ValueError` when trying to create achievement cards that are not unlocked:

```
ValueError: transparency is not allowed for this attribute
```

## Location

File: `app/plugins/achievements.py`
Method: `_create_achievement_card()`

## Original Code

```python
card = ctk.CTkFrame(
    self.scrollable,
    corner_radius=15,
    fg_color=self.theme.accent if unlocked else self.theme.surface_alt,
    border_width=2,
    border_color=self.theme.accent if unlocked else "transparent"  # ❌ Error here
)
```

## Fix

Instead of using "transparent" for the border_color, we set `border_width=0` for unlocked achievements, which effectively removes the border:

```python
card = ctk.CTkFrame(
    self.scrollable,
    corner_radius=15,
    fg_color=self.theme.accent if unlocked else self.theme.surface_alt,
    border_width=2 if unlocked else 0,  # ✓ No border when not unlocked
    border_color=self.theme.accent if unlocked else self.theme.surface_alt  # ✓ Valid color fallback
)
```

## Result

- **Unlocked achievements**: Show with 2px accent-colored border
- **Locked achievements**: Show with no border (border_width=0)
- No more ValueError exceptions when displaying achievements view

## Note

There's a similar pattern in `app/plugins/library.py` (line 199) that may need the same fix if it causes issues:

```python
border_color=theme.accent if game.rating >= 8.0 else "transparent"
```

This hasn't been changed as it's outside the scope of the current task, but should be monitored.
