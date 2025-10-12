from __future__ import annotations

"""Shared import hub for the refactored Game Launcher package."""

import asyncio
import datetime
import functools
import importlib
import json
import logging
import mimetypes
import operator as py_operator
import os
import queue
import random
import re
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import uuid
import webbrowser
import zipfile
from collections import defaultdict
from io import BytesIO
from typing import Dict, Iterable, Tuple

import tkinter as tk
from tkinter import colorchooser, filedialog, font, messagebox, simpledialog, ttk

import requests


# Registry that tracks optional dependencies that failed to import.
OPTIONAL_IMPORT_ERRORS: Dict[str, Exception] = {}


def _optional_import(module_name: str, attributes: Iterable[str] | None = None) -> Tuple[object, ...] | object | None:
    """Attempt to import a module or attributes, returning ``None`` when unavailable.

    When ``attributes`` is provided, the function returns a tuple containing the
    resolved attributes in order. Attributes that could not be imported are
    represented by ``None`` placeholders so downstream code can gracefully
    degrade. Failures are stored inside :data:`OPTIONAL_IMPORT_ERRORS` for
    diagnostic purposes.
    """

    try:
        module = importlib.import_module(module_name)
    except Exception as exc:  # pragma: no cover - best effort logging
        OPTIONAL_IMPORT_ERRORS[module_name] = exc
        if not attributes:
            return None
        return tuple(None for _ in attributes)

    if not attributes:
        return module

    results = []
    for attribute in attributes:
        try:
            results.append(getattr(module, attribute))
        except AttributeError as exc:  # pragma: no cover - best effort logging
            OPTIONAL_IMPORT_ERRORS[f"{module_name}.{attribute}"] = exc
            results.append(None)
    return tuple(results)


# Optional third-party dependencies --------------------------------------------------

socketio = _optional_import("socketio")
pylast = _optional_import("pylast")
keyboard = _optional_import("pynput.keyboard")
pygame = _optional_import("pygame")
plt = _optional_import("matplotlib.pyplot")
(Figure,) = _optional_import("matplotlib.figure", ("Figure",))
(FigureCanvasTkAgg, NavigationToolbar2Tk) = _optional_import(
    "matplotlib.backends.backend_tkagg", ("FigureCanvasTkAgg", "NavigationToolbar2Tk")
)
(MutagenFile,) = _optional_import("mutagen", ("File",))
(Calendar, DateEntry) = _optional_import("tkcalendar", ("Calendar", "DateEntry"))
(
    Flask,
    jsonify,
    request,
    render_template_string,
    send_file,
    abort,
    redirect,
    url_for,
) = _optional_import(
    "flask",
    ("Flask", "jsonify", "request", "render_template_string", "send_file", "abort", "redirect", "url_for"),
)
pystray = _optional_import("pystray")
notification = _optional_import("plyer.notification")
psutil = _optional_import("psutil")
try:  # pragma: no cover - Windows-only
    import winreg  # type: ignore[attr-defined]
except Exception as exc:  # pragma: no cover - best effort logging
    OPTIONAL_IMPORT_ERRORS["winreg"] = exc
    winreg = None  # type: ignore[assignment]
(Github, GithubException) = _optional_import("github", ("Github", "GithubException"))
(get_gamepad, UnpluggedError) = _optional_import("inputs", ("get_gamepad", "UnpluggedError"))
feedparser = _optional_import("feedparser")
(HTMLLabel,) = _optional_import("tkhtmlview", ("HTMLLabel",))
version = _optional_import("packaging.version")
(Presence, PyPresenceException) = _optional_import("pypresence", ("Presence", "PyPresenceException"))
Image = _optional_import("PIL.Image")
ImageTk = _optional_import("PIL.ImageTk")
ImageDraw = _optional_import("PIL.ImageDraw")
ImageFont = _optional_import("PIL.ImageFont")
(UnidentifiedImageError,) = _optional_import("PIL", ("UnidentifiedImageError",))


# Public re-exports -----------------------------------------------------------------

__all__ = [name for name in globals().keys() if not name.startswith("_")]
