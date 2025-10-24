# Screenshot Gallery Improvements

## Summary
This document describes the improvements made to the screenshot gallery feature in the Game Launcher application.

## Changes Made

### 1. Screenshot Service (`app/services/screenshot_service.py`)

#### New Features:
- **Relative Path Storage**: Screenshots are now stored using relative paths when they are within the project directory, making backups more portable.
- **Metadata Extraction**: New method `get_screenshot_metadata()` extracts comprehensive information about screenshots:
  - Creation date and modification date
  - Image resolution (width × height)
  - File size in bytes
  - File existence check

#### New Methods:
- `_to_relative_path(absolute_path)`: Converts absolute paths to relative when inside project directory
- `_to_absolute_path(path)`: Converts relative paths back to absolute for file operations
- `get_screenshot_metadata(screenshot_path)`: Extracts and returns metadata dictionary

#### Updated Methods:
- `add_manual_screenshot()`: Now stores paths relatively and checks for duplicates using absolute path comparison

### 2. Screenshots Plugin (`app/plugins/screenshots.py`)

#### UI Improvements:
- **Enhanced Screenshot Cards**: Each screenshot card now displays:
  - Filename (bold)
  - Resolution (📐 icon)
  - Creation date (📅 icon) in format DD.MM.YYYY HH:MM
  - File size (💾 icon) in MB or KB

#### New Interaction Methods:
- **In-App Preview**: Click on screenshot thumbnail opens a preview window (`_show_preview()`)
  - Displays image at up to 80% of screen size
  - Includes button to open in system browser
  - Press ESC to close
  - Responsive sizing based on screen resolution

- **System Browser**: Double-click or use the "🌐 Otwórz" button to open in system default image viewer
  - Cross-platform support:
    - Windows: `os.startfile()`
    - macOS: `open` command
    - Linux: `xdg-open` command

#### New Buttons on Cards:
- **🔍 Podgląd**: Opens in-app preview window
- **🌐 Otwórz**: Opens in system browser/viewer
- **🗑️**: Delete screenshot (compact button)

#### Click Behaviors:
- **Single Click**: Opens in-app preview window
- **Double Click**: Opens in system browser

### 3. Cross-Platform Compatibility
All features have been verified to work across:
- Windows (using `os.startfile`)
- macOS (using `open` command)
- Linux (using `xdg-open` command)

## Technical Details

### Path Storage Strategy
```python
# Before: /home/user/project/screenshots/game1.png
# After:  screenshots/game1.png  (if inside project directory)
```

This makes the database portable and backup-friendly.

### Metadata Structure
```python
{
    "path": "screenshots/example.png",
    "exists": True,
    "created": datetime(2025, 10, 24, 21, 11, 3),
    "modified": datetime(2025, 10, 24, 21, 11, 3),
    "size": 8593,
    "width": 1920,
    "height": 1080,
    "resolution": "1920×1080"
}
```

### Preview Window Features
- Automatically scales large images to fit screen (max 80%)
- Maintains aspect ratio
- Centers window on screen
- Keyboard shortcut (ESC) to close
- Direct access to system browser from preview

## Benefits

1. **Discoverability**: Clear buttons make features obvious to users
2. **Flexibility**: Users can choose between in-app preview or system viewer
3. **Information**: Rich metadata helps users identify and manage screenshots
4. **Portability**: Relative paths make backups and project transfers easier
5. **Cross-Platform**: Verified behavior across Windows, macOS, and Linux

## Testing

All changes have been tested:
- Path conversion (relative ↔ absolute)
- Metadata extraction
- Python compilation checks
- Real image processing verification

## Future Enhancements (Optional)

- Context menu (right-click) for additional actions
- Zoom controls in preview window
- Screenshot comparison view
- Batch operations (delete multiple, export, etc.)
- Screenshot annotations
