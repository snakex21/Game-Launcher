"""Common imports for legacy Game Launcher components."""
from __future__ import annotations

import asyncio
import datetime
import functools
import json
import logging
import mimetypes
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
import webbrowser
import zipfile
from collections import defaultdict
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import pygame
import pylast
import pystray
import requests
import socketio
import psutil
import winreg
from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template_string,
    request,
    send_file,
    url_for,
)
from github import Github, GithubException
from inputs import UnpluggedError, get_gamepad
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from mutagen import File as MutagenFile
from packaging import version
from PIL import Image, ImageDraw, ImageFont, ImageTk, UnidentifiedImageError
from plyer import notification
from pypresence import Presence, PyPresenceException
from tkcalendar import Calendar, DateEntry
from tkhtmlview import HTMLLabel
import feedparser

import tkinter as tk
from tkinter import colorchooser, filedialog, font, messagebox, simpledialog, ttk

# Names re-exported when using ``from .base import *``
__all__ = [name for name in globals().keys() if not name.startswith("_")]
