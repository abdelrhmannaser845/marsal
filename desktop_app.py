#!/usr/bin/env python3
"""
Marsal Desktop Application (GUI & Standalone .exe Entry Point)
"One slip, one student."

Implements the 5-screen Marsal Visual Identity (brand.md) wired directly to:
- src.utils.parser.ingest_records (Bilingual CSV/Excel ingestion)
- src.utils.phone.normalize_phone (E.164 phone normalization)
- src.services.templating.TemplateEngine (Jinja2 WhatsApp & Email rendering)
- src.services.dispatcher.NotificationDispatcher (Throttled human-paced queue)
- src.core.database.DispatchDatabase (SQLite audit ledger)
"""

import os
import sys
import csv
import math
import time
import random
import threading
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Ensure UTF-8 on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

from src.core.config import get_config, AppConfig
from src.core.models import StudentGradeRecord, DispatchChannel, DispatchStatus, DispatchResult
from src.core.database import DispatchDatabase
from src.utils.parser import ingest_records
from src.utils.phone import normalize_phone
from src.services.templating import TemplateEngine
from src.services.email_service import EmailService
from src.services.whatsapp_service import get_whatsapp_provider
from src.services.dispatcher import NotificationDispatcher


def get_resource_path(relative_path: str) -> Path:
    """Resolve bundled resources whether running from source or PyInstaller .exe."""
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
        candidate = base / relative_path
        if candidate.exists():
            return candidate
    return Path(__file__).resolve().parent / relative_path


def get_runtime_dir() -> Path:
    """Return writable directory alongside the executable or project root."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


# ============================================================================
# MARSAL BRAND PALETTE (brand.md)
# ============================================================================
NILE    = "#0F4C5C"  # Primary brand color, sidebar rail, primary buttons
NILE_DK = "#0B3946"  # Deep Nile for sidebar cards
NILE_LT = "#145A6C"  # Inactive sidebar item surface
STAMP   = "#E8553D"  # The ONE accent, once per layout (the torn stub). Graphics only!
SAND    = "#F2C14E"  # Accent on Nile and on Ink
LAGOON  = "#6FC1D0"  # Nile for dark backgrounds
INK     = "#10222A"  # Primary text and dark ground
INK_2   = "#1A333D"  # Elevated dark card surface on Ink
INK_3   = "#24424F"  # Subtle border on dark Ink
PAPER   = "#F6F0E4"  # Light ground (60% surface)
PAPER_2 = "#EAE2D1"  # Secondary warm paper surface
PAPER_3 = "#DCD2BD"  # Hairline border on Paper
CREAM   = "#FBF8F2"  # Elevated slip surface on Paper
FOG     = "#51636B"  # Secondary text (5.53:1 contrast on Paper)

FONT_HEADLINE = "Georgia"
FONT_BODY     = "Segoe UI"
FONT_MONO     = "Consolas"


# ============================================================================
# CANVAS VECTOR DRAWING HELPERS (Marsal Mark, Perforations & Stub Status Icons)
# ============================================================================
def draw_rounded_rect(canvas: tk.Canvas, x1: float, y1: float, x2: float, y2: float, radius: float = 8, **kwargs):
    """Draws a smooth rounded rectangle on a Tkinter Canvas."""
    r = max(0, min(radius, (x2 - x1) / 2, (y2 - y1) / 2))
    if r <= 1:
        return canvas.create_rectangle(x1, y1, x2, y2, **kwargs)
    points = [
        x1 + r, y1,
        x2 - r, y1,
        x2, y1,
        x2, y1 + r,
        x2, y2 - r,
        x2, y2,
        x2 - r, y2,
        x1 + r, y2,
        x1, y2,
        x1, y2 - r,
        x1, y1 + r,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


def draw_rotated_stub(canvas: tk.Canvas, cx: float, cy: float, w: float, h: float, angle_deg: float = 14.0, fill: str = STAMP, outline: str = "", width: float = 1):
    """Draws a tilted stub polygon rotated by angle_deg around (cx, cy)."""
    rad = math.radians(angle_deg)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    hw, hh = w / 2.0, h / 2.0
    # Slight chamfered corners to mimic rounded stub
    c = min(w, h) * 0.18
    local_pts = [
        (-hw + c, -hh), (hw - c, -hh),
        (hw, -hh + c), (hw, hh - c),
        (hw - c, hh), (-hw + c, hh),
        (-hw, hh - c), (-hw, -hh + c),
    ]
    pts = []
    for lx, ly in local_pts:
        rx = cx + lx * cos_a - ly * sin_a
        ry = cy + lx * sin_a + ly * cos_a
        pts.extend([rx, ry])
    return canvas.create_polygon(pts, fill=fill, outline=outline or fill, width=width, smooth=True)


def draw_marsal_mark_on_canvas(
    canvas: tk.Canvas,
    x: float,
    y: float,
    scale: float = 0.36,
    body_color: str = PAPER,
    cutout_color: str = NILE,
    torn_stub_color: str = SAND,
    show_dots: bool = True,
):
    """
    Draws the official Marsal Grade Slip & Perforated Stubs Mark on a tk.Canvas:
    - Slip body (84 x 124) with 2 text slots and 1 circular seal hole
    - 5 perforation dots
    - 3 attached stubs + 1 torn stub rotated 14 deg in the upper right
    """
    s = scale
    # Slip body
    draw_rounded_rect(canvas, x, y, x + 84 * s, y + 124 * s, radius=14 * s, fill=body_color, outline="")
    # 2 line slots inside slip
    draw_rounded_rect(canvas, x + 15 * s, y + 27 * s, x + 65 * s, y + 36 * s, radius=4.5 * s, fill=cutout_color, outline="")
    draw_rounded_rect(canvas, x + 15 * s, y + 44 * s, x + 49 * s, y + 53 * s, radius=4.5 * s, fill=cutout_color, outline="")
    # Circular stamp hole
    canvas.create_oval(x + 49 * s, y + 85 * s, x + 69 * s, y + 105 * s, fill=cutout_color, outline="")
    # 5 perforation dots
    if show_dots:
        for cy in (4.0, 33.0, 62.0, 91.0, 120.0):
            r = 2.2 * s
            px = x + 90.5 * s
            py = y + cy * s
            canvas.create_oval(px - r, py - r, px + r, py + r, fill=body_color, outline="")
    # 3 attached stubs
    for sy in (32.0, 64.0, 96.0):
        draw_rounded_rect(
            canvas,
            x + 97 * s,
            y + sy * s,
            x + 127 * s,
            y + (sy + 27.5) * s,
            radius=6 * s,
            fill=body_color,
            outline="",
        )
    # 1 torn stub in upper right tilted 14 deg
    tcx = x + (108 + 15) * s
    tcy = y + (-8 + 13.75) * s
    draw_rotated_stub(canvas, tcx, tcy, 30 * s, 27.5 * s, angle_deg=14.0, fill=torn_stub_color)


def draw_status_stub_on_canvas(
    canvas: tk.Canvas,
    x: float,
    y: float,
    status: str,
    dark_mode: bool = False,
    use_stamp: bool = False,
):
    """
    Draws the Marsal Status Stub Icon unit (brand.md Section 5):
    - SUCCESS: stub torn away (tilted 12 deg)
    - FAILED: stub still attached with a small downward tilt (-7 deg)
    - SKIPPED: outlined, empty stub position
    - PENDING: upright attached stub
    """
    dot_c = INK_3 if dark_mode else PAPER_3
    canvas.create_oval(x, y + 3, x + 3.5, y + 6.5, fill=dot_c, outline="")
    canvas.create_oval(x, y + 13, x + 3.5, y + 16.5, fill=dot_c, outline="")

    st = status.upper()
    if st == "SUCCESS":
        fill_c = STAMP if use_stamp else (LAGOON if dark_mode else NILE)
        draw_rotated_stub(canvas, x + 21, y + 8, 22, 18, angle_deg=12.0, fill=fill_c)
    elif st == "FAILED":
        fill_c = SAND if dark_mode else INK
        draw_rotated_stub(canvas, x + 16, y + 10, 22, 18, angle_deg=-7.0, fill=fill_c)
        mark_c = INK if dark_mode else PAPER
        canvas.create_line(x + 12, y + 10, x + 20, y + 10, fill=mark_c, width=2)
    elif st == "PENDING":
        fill_c = INK_3 if dark_mode else PAPER_2
        stroke_c = LAGOON if dark_mode else NILE
        draw_rounded_rect(canvas, x + 6, y + 1, x + 28, y + 19, radius=4, fill=fill_c, outline=stroke_c, width=1.5)
    else:  # SKIPPED
        stroke_c = LAGOON if dark_mode else FOG
        canvas.create_rectangle(x + 6, y + 1, x + 28, y + 19, fill="", outline=stroke_c, width=1.5, dash=(3, 2))


# ============================================================================
# MAIN MARSAL DESKTOP APPLICATION
# ============================================================================
class MarsalDesktopApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("marsal desktop  ·  One slip, one student.")
        self.geometry("1440x920")
        self.minsize(1200, 780)
        self.configure(bg=PAPER)

        # Set Window Icon (.ico)
        ico_path = get_resource_path("Marsal Visual Identity/logo/marsal.ico")
        if ico_path.exists():
            try:
                self.iconbitmap(default=str(ico_path))
            except Exception:
                pass

        # Application State & Backend Services
        self.runtime_dir = get_runtime_dir()
        from dotenv import load_dotenv
        runtime_env = self.runtime_dir / ".env"
        if runtime_env.exists():
            load_dotenv(dotenv_path=runtime_env, override=True)
        else:
            bundled_env = get_resource_path(".env")
            if bundled_env.exists():
                load_dotenv(dotenv_path=bundled_env, override=False)

        self.config_obj: AppConfig = get_config()
        # Ensure DB lives in writable runtime_dir/data/dispatches.db
        self.db_path = self.runtime_dir / "data" / "dispatches.db"
        self.config_obj.db_path = self.db_path
        self.database = DispatchDatabase(self.db_path)

        tpl_dir = get_resource_path("src/templates")
        self.template_engine = TemplateEngine(template_dir=tpl_dir)

        self.records: List[StudentGradeRecord] = []
        self.ingestion_errors: List[Dict[str, Any]] = []
        self.row_statuses: Dict[str, str] = {}  # student_id -> SUCCESS | FAILED | SKIPPED | PENDING
        self.selected_idx: int = 0
        self.loaded_file_path: Optional[Path] = None

        # Queue / Dispatch Worker State
        self.is_dispatching = False
        self.pause_requested = False
        self.stop_requested = False
        self.dry_run_var = tk.BooleanVar(value=False)
        self.send_wa_var = tk.BooleanVar(value=True)
        self.send_email_var = tk.BooleanVar(value=True)
        self.active_wa_template = tk.StringVar(value="wa_grade_report_styled.txt.j2")
        self.active_email_template = tk.StringVar(value="email_grade_report.html.j2")
        self.recent_intervals: List[tuple] = [
            ("#01", 7.2, False),
            ("#02", 11.4, False),
            ("#03", 6.1, False),
            ("#04", 10.8, False),
            ("#05", 8.3, False),
            ("#06", 5.4, False),
            ("#07", 11.9, False),
            ("#08", 7.8, False),
            ("#09", 6.9, False),
            ("#10", 9.4, True),
        ]
        self.current_flight_student: Optional[StudentGradeRecord] = None
        self.current_flight_idx: int = 0
        self.current_countdown_sec: float = 0.0

        # Configure ttk styles
        self._setup_ttk_styles()

        # Build Layout Shell: Top Status Bar + Left Sidebar Rail + Main Content Frame
        self._build_shell()

        # Load initial sample data (or generate if missing)
        self._load_initial_pad()

        # Show Tab 0 (Pad of Slips)
        self.switch_tab(0)

    def _setup_ttk_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "Marsal.Treeview",
            background=CREAM,
            fieldbackground=CREAM,
            foreground=INK,
            rowheight=36,
            font=(FONT_BODY, 10),
            borderwidth=0,
        )
        style.configure(
            "Marsal.Treeview.Heading",
            background=INK,
            foreground=PAPER,
            font=(FONT_MONO, 9, "bold"),
            padding=(8, 8),
            borderwidth=0,
        )
        style.map(
            "Marsal.Treeview",
            background=[("selected", "#D8ECEC")],
            foreground=[("selected", NILE)],
        )

    # ========================================================================
    # SHELL LAYOUT (Top Window Bar + Left Navigation Rail + Content Container)
    # ========================================================================
    def _build_shell(self):
        # 1. Top Bar (34px Ink bar)
        self.top_bar = tk.Frame(self, bg=INK, height=34)
        self.top_bar.pack(side=tk.TOP, fill=tk.X)
        self.top_bar.pack_propagate(False)

        self.top_subtitle_lbl = tk.Label(
            self.top_bar,
            text="marsal desktop  ·  01 / Pad of Slips (Spreadsheet Ingestion)",
            bg=INK,
            fg=PAPER_2,
            font=(FONT_MONO, 9, "bold"),
        )
        self.top_subtitle_lbl.pack(side=tk.LEFT, padx=16)

        tk.Label(
            self.top_bar,
            text="One slip, one student.",
            bg=INK,
            fg=SAND,
            font=(FONT_HEADLINE, 10, "bold"),
        ).pack(side=tk.LEFT, expand=True)

        self.top_meta_lbl = tk.Label(
            self.top_bar,
            text=f"SQLite: data/dispatches.db   |   Pace: {self.config_obj.throttle.min_delay_seconds}s – {self.config_obj.throttle.max_delay_seconds}s   |   v1.4.0",
            bg=INK,
            fg=LAGOON,
            font=(FONT_MONO, 9),
        )
        self.top_meta_lbl.pack(side=tk.RIGHT, padx=16)

        # 2. Body Wrapper
        self.body_wrap = tk.Frame(self, bg=PAPER)
        self.body_wrap.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 3. Left Navigation Rail (Canvas-rendered for pixel-faithful Marsal Visual Identity)
        self.sidebar_canvas = tk.Canvas(
            self.body_wrap,
            width=248,
            bg=NILE,
            highlightthickness=0,
            bd=0,
        )
        self.sidebar_canvas.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar_canvas.bind("<Configure>", lambda e: self._redraw_sidebar())
        self.sidebar_canvas.bind("<Button-1>", self._on_sidebar_click)
        self.sidebar_canvas.bind("<Motion>", self._on_sidebar_Hover)

        # 4. Right Content Area (Hosts the 5 workspace screens)
        self.content_area = tk.Frame(self.body_wrap, bg=PAPER)
        self.content_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.active_tab_idx = 0
        self.nav_hitboxes: List[tuple] = []

        # Build the 5 frames
        self.screens: List[tk.Frame] = []
        self._build_screen_01_roster()
        self._build_screen_02_composer()
        self._build_screen_03_queue_dark()
        self._build_screen_04_audit()
        self._build_screen_05_setup()

    def _redraw_sidebar(self):
        c = self.sidebar_canvas
        c.delete("all")
        h = max(c.winfo_height(), 880)
        dark_mode = (self.active_tab_idx == 2)
        rail_bg = "#0B3946" if dark_mode else NILE
        c.configure(bg=rail_bg)

        # Brand Lockup: Official Marsal Mark (with Sand torn stub on Nile) + lowercase 'marsal'
        draw_marsal_mark_on_canvas(
            c,
            x=22,
            y=24,
            scale=0.35,
            body_color=PAPER,
            cutout_color=rail_bg,
            torn_stub_color=SAND,
            show_dots=True,
        )
        c.create_text(82, 32, text="marsal", anchor="nw", fill=PAPER, font=(FONT_HEADLINE, 24, "bold"))
        c.create_text(84, 66, text="One slip, one student.", anchor="nw", fill=SAND, font=(FONT_HEADLINE, 9))

        # Perforated divider
        for px in range(22, 228, 10):
            c.create_oval(px, 98, px + 3, 101, fill="#2B6777", outline="")

        # 5 Navigation Slip Items
        nav_items = [
            ("01", "Pad of Slips", "Spreadsheet & student rows"),
            ("02", "Slip Composer", "Jinja2 notices & previews"),
            ("03", "Hand-Out Queue", "Live throttled sending"),
            ("04", "Audit Ledger", "Success, failed & skipped"),
            ("05", "Channel & Pace", "WhatsApp, SMTP & delays"),
        ]
        self.nav_hitboxes = []
        ny = 114
        for idx, (num, title, sub) in enumerate(nav_items):
            is_act = (idx == self.active_tab_idx)
            if is_act:
                bg_c = INK if dark_mode else PAPER
                txt_c = PAPER if dark_mode else INK
                sub_c = LAGOON if dark_mode else FOG
                num_c = SAND if dark_mode else NILE
                draw_rounded_rect(c, 14, ny, 234, ny + 56, radius=8, fill=bg_c, outline="")
                # Active Sand stub on right edge
                draw_rounded_rect(c, 226, ny + 13, 238, ny + 43, radius=4, fill=SAND, outline="")
            else:
                bg_c = "#104554" if dark_mode else NILE_LT
                txt_c = PAPER
                sub_c = "#A5C9D1"
                num_c = SAND
                draw_rounded_rect(c, 14, ny, 234, ny + 56, radius=8, fill=bg_c, outline="")

            c.create_text(26, ny + 12, text=num, anchor="nw", fill=num_c, font=(FONT_MONO, 9, "bold"))
            c.create_text(50, ny + 10, text=title, anchor="nw", fill=txt_c, font=(FONT_BODY, 11, "bold"))
            c.create_text(50, ny + 31, text=sub, anchor="nw", fill=sub_c, font=(FONT_BODY, 8))
            self.nav_hitboxes.append((14, ny, 234, ny + 56, idx))
            ny += 64

        # Perforated divider
        for px in range(22, 228, 10):
            c.create_oval(px, 444, px + 3, 447, fill="#2B6777", outline="")

        # Current Pad Summary Card
        box_bg = "#082C36" if dark_mode else NILE_DK
        draw_rounded_rect(c, 16, 460, 232, 628, radius=8, fill=box_bg, outline="#2B6777", width=1)
        c.create_text(28, 474, text="CURRENT PAD ON DESK", anchor="nw", fill=SAND, font=(FONT_MONO, 8, "bold"))

        course_name = self.records[0].course if self.records else "Comp 304: Compiler Design"
        if len(course_name) > 26:
            course_name = course_name[:25] + "…"
        fname = self.loaded_file_path.name if self.loaded_file_path else "students_sample.csv"

        c.create_text(28, 494, text=course_name, anchor="nw", fill=PAPER, font=(FONT_HEADLINE, 10, "bold"))
        c.create_text(28, 514, text=fname, anchor="nw", fill=LAGOON, font=(FONT_MONO, 8))

        total_n = len(self.records)
        torn_n = sum(1 for s in self.row_statuses.values() if s == "SUCCESS")
        pend_n = sum(1 for s in self.row_statuses.values() if s == "PENDING")
        skip_n = sum(1 for s in self.row_statuses.values() if s in ("SKIPPED", "FAILED"))

        c.create_text(28, 540, text=f"{total_n} student slips on pad", anchor="nw", fill=PAPER, font=(FONT_BODY, 9, "bold"))
        c.create_text(28, 562, text=f"• {torn_n} handed over (torn)", anchor="nw", fill="#B8D8DF", font=(FONT_BODY, 8))
        c.create_text(28, 580, text=f"• {pend_n} still attached", anchor="nw", fill="#B8D8DF", font=(FONT_BODY, 8))
        c.create_text(28, 598, text=f"• {skip_n} failed / skipped", anchor="nw", fill="#B8D8DF", font=(FONT_BODY, 8))

        # Bottom Channel & Pace Box
        draw_rounded_rect(c, 16, 644, 232, min(h - 16, 836), radius=8, fill=box_bg, outline="#2B6777", width=1)
        c.create_text(28, 658, text="HUMAN PACE & CHANNELS", anchor="nw", fill=SAND, font=(FONT_MONO, 8, "bold"))

        c.create_oval(28, 684, 36, 692, fill=SAND, outline="")
        c.create_text(42, 680, text=f"WhatsApp ({self.config_obj.whatsapp.provider})", anchor="nw", fill=PAPER, font=(FONT_BODY, 9, "bold"))
        c.create_text(42, 698, text="E.164 +20 normalizer ready", anchor="nw", fill="#A5C9D1", font=(FONT_MONO, 8))

        c.create_oval(28, 726, 36, 734, fill=LAGOON, outline="")
        c.create_text(42, 722, text=f"Email (SMTP :{self.config_obj.smtp.port})", anchor="nw", fill=PAPER, font=(FONT_BODY, 9, "bold"))
        c.create_text(42, 740, text=self.config_obj.smtp.host, anchor="nw", fill="#A5C9D1", font=(FONT_MONO, 8))

        c.create_line(28, 768, 218, 768, fill="#2B6777")
        c.create_text(28, 778, text="One slip every 5 to 12 sec,", anchor="nw", fill=PAPER, font=(FONT_HEADLINE, 8))
        c.create_text(28, 794, text="like a person handing papers.", anchor="nw", fill=SAND, font=(FONT_HEADLINE, 8))

    def _on_sidebar_click(self, event):
        for x1, y1, x2, y2, idx in self.nav_hitboxes:
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.switch_tab(idx)
                return

    def _on_sidebar_Hover(self, event):
        for x1, y1, x2, y2, _ in self.nav_hitboxes:
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.sidebar_canvas.configure(cursor="hand2")
                return
        self.sidebar_canvas.configure(cursor="")

    def switch_tab(self, idx: int):
        self.active_tab_idx = idx
        subtitles = [
            "01 / Pad of Slips (Spreadsheet Ingestion)",
            "02 / Slip Composer (Jinja2 Templates & Previews)",
            "03 / Hand-Out Queue (Live Human-Paced Dispatch)",
            "04 / Audit Ledger (SQLite data/dispatches.db)",
            "05 / Channel & Pace Setup (.env & Identity System)",
        ]
        self.top_subtitle_lbl.configure(text=f"marsal desktop  ·  {subtitles[idx]}")
        self.top_meta_lbl.configure(
            text=f"SQLite: data/dispatches.db   |   Pace: {self.config_obj.throttle.min_delay_seconds:.1f}s – {self.config_obj.throttle.max_delay_seconds:.1f}s   |   v1.4.0"
        )

        for i, frame in enumerate(self.screens):
            if i == idx:
                frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
            else:
                frame.pack_forget()

        self._redraw_sidebar()

        if idx == 0:
            self._refresh_roster_view()
        elif idx == 1:
            self._refresh_composer_view()
        elif idx == 2:
            self._redraw_queue_canvas()
        elif idx == 3:
            self._refresh_audit_view()
        elif idx == 4:
            self._redraw_brand_legend_canvas()

    # ========================================================================
    # DATA INGESTION & INITIAL SAMPLE PAD
    # ========================================================================
    def _load_initial_pad(self):
        data_dir = self.runtime_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        sample_csv = data_dir / "students_sample.csv"

        if not sample_csv.exists():
            bundled_csv = get_resource_path("data/students_sample.csv")
            if bundled_csv.exists() and bundled_csv != sample_csv:
                sample_csv.write_bytes(bundled_csv.read_bytes())
            else:
                self._write_default_sample_csv(sample_csv)

        self.load_spreadsheet(sample_csv)

    def _write_default_sample_csv(self, csv_path: Path):
        sample_rows = [
            ["student_id", "name", "phone", "email", "course", "midterm", "lab", "oral", "bonus", "total", "notes"],
            ["220769", "عبدالرحمن خالد سعد الدين", "01120844781", "abdelrhmannaser06@gmail.com", "Comp 304 Compiler Design - Spring", 12, 15, 5, 0, 32, "Score after adding extra bonus"],
            ["220770", "Sarah Ahmed Mahmoud", "+201012345678", "sarah.ahmed@example.com", "Comp 304 Compiler Design - Spring", 14, 35, 8, 2, 59, "Outstanding lab project — clean AST"],
            ["220771", "Mohamed Omar Farouk", "01298765432", "mohamed.omar@example.com", "Comp 304 Compiler Design - Spring", 10, 28, 6, 0, 44, "Solid parser implementation"],
            ["220772", "Nour Ibrahim Youssef", "01555554321", "nour.ibrahim@example.com", "Comp 304 Compiler Design - Spring", 13, 32, 7, 1, 53, "Excellent presentation"],
            ["220773", "Yasmine Tarek El-Sayed", "01094418820", "", "Comp 304 Compiler Design - Spring", 15, 34, 8, 0, 57, "Clean AST & symbol table"],
            ["220774", "Omar Khaled Mansour", "01143029911", "omar.mansour@example.com", "Comp 304 Compiler Design - Spring", 11, 24, 6, 0, 41, "Review LR(1) closure items"],
            ["220775", "Salma Mostafa Adel", "01226190450", "salma.adel@example.com", "Comp 304 Compiler Design - Spring", 14, 33, 7, 1, 55, "Strong lexical analyzer"],
            ["220776", "Karim Hesham Nabil", "01008831924", "karim.nabil@example.com", "Comp 304 Compiler Design - Spring", 13, 30, 7, 0, 50, "Well-tested code generator"],
        ]
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(sample_rows)

    def load_spreadsheet(self, file_path: Path):
        try:
            records, errors = ingest_records(file_path)
            self.records = records
            self.ingestion_errors = errors
            self.loaded_file_path = file_path
            self.selected_idx = 0
            self.row_statuses = {r.student_id: "PENDING" for r in records}

            self._redraw_sidebar()
            if hasattr(self, "roster_tree"):
                self._refresh_roster_view()
        except Exception as exc:
            messagebox.showerror("Spreadsheet Error", f"Could not load file:\n{exc}")

    def _open_file_dialog(self):
        fp = filedialog.askopenfilename(
            title="Select Student Spreadsheet (.csv or .xlsx)",
            initialdir=str(self.runtime_dir / "data"),
            filetypes=[("Spreadsheets", "*.csv *.xlsx *.xlsm"), ("All Files", "*.*")],
        )
        if fp:
            self.load_spreadsheet(Path(fp))

    # ========================================================================
    # SCREEN 01: PAD OF SLIPS (ROSTER & TEAR-OFF SLIP INSPECTOR)
    # ========================================================================
    def _build_screen_01_roster(self):
        f1 = tk.Frame(self.content_area, bg=PAPER)
        self.screens.append(f1)

        # Header Row
        hdr = tk.Frame(f1, bg=PAPER)
        hdr.pack(side=tk.TOP, fill=tk.X, padx=24, pady=(18, 8))

        title_col = tk.Frame(hdr, bg=PAPER)
        title_col.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(
            title_col,
            text="Pad of Slips — Student Grade Roster",
            bg=PAPER,
            fg=INK,
            font=(FONT_HEADLINE, 20, "bold"),
            anchor="w",
        ).pack(side=tk.TOP, anchor="w")
        tk.Label(
            title_col,
            text="Each spreadsheet row is a perforated grade slip, torn off and handed to one student at a human pace.",
            bg=PAPER,
            fg=FOG,
            font=(FONT_BODY, 10),
            anchor="w",
        ).pack(side=tk.TOP, anchor="w", pady=(2, 0))

        btn_col = tk.Frame(hdr, bg=PAPER)
        btn_col.pack(side=tk.RIGHT)

        tk.Button(
            btn_col,
            text="Open CSV / .xlsx Pad...",
            command=self._open_file_dialog,
            bg=PAPER_2,
            fg=INK,
            activebackground=PAPER_3,
            font=(FONT_BODY, 10, "bold"),
            relief=tk.SOLID,
            bd=1,
            padx=14,
            pady=7,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(
            btn_col,
            text="Hand Out All Slips (5–12s) →",
            command=self._start_batch_from_roster,
            bg=NILE,
            fg=PAPER,
            activebackground=NILE_DK,
            activeforeground=PAPER,
            font=(FONT_BODY, 10, "bold"),
            relief=tk.SOLID,
            bd=1,
            padx=16,
            pady=7,
            cursor="hand2",
        ).pack(side=tk.LEFT)

        # Schema & File Info Strip
        schema_bar = tk.Frame(f1, bg=PAPER_2, highlightbackground=PAPER_3, highlightthickness=1)
        schema_bar.pack(side=tk.TOP, fill=tk.X, padx=24, pady=(4, 12))

        self.file_badge_lbl = tk.Label(
            schema_bar,
            text="LOADED FILE: data/students_sample.csv",
            bg=PAPER_2,
            fg=NILE,
            font=(FONT_MONO, 9, "bold"),
            padx=12,
            pady=8,
        )
        self.file_badge_lbl.pack(side=tk.LEFT)

        tk.Label(
            schema_bar,
            text="|  BILINGUAL ALIASES MAPPED:  كود الطالب → ID   ·   الاسم → Name   ·   الموبايل → E.164   ·   أعمال سنة → Scores",
            bg=PAPER_2,
            fg=FOG,
            font=(FONT_MONO, 9),
        ).pack(side=tk.LEFT, padx=8)

        # Main Split Area: Left Table ("The Pad of Slips") + Right Tear-Off Slip Inspector
        split = tk.Frame(f1, bg=PAPER)
        split.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=24, pady=(0, 18))

        # Left Table Card
        left_card = tk.Frame(split, bg=CREAM, highlightbackground=INK, highlightthickness=2)
        left_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 16))

        cols = ("id", "name", "phone", "scores", "total", "stub")
        self.roster_tree = ttk.Treeview(
            left_card,
            columns=cols,
            show="headings",
            style="Marsal.Treeview",
            selectmode="browse",
        )
        self.roster_tree.heading("id", text="ID")
        self.roster_tree.heading("name", text="STUDENT NAME (PERSON, NOT BATCH)")
        self.roster_tree.heading("phone", text="E.164 PHONE")
        self.roster_tree.heading("scores", text="MID · LAB · ORAL (+BONUS)")
        self.roster_tree.heading("total", text="TOTAL")
        self.roster_tree.heading("stub", text="STUB STATUS")

        self.roster_tree.column("id", width=78, anchor="w")
        self.roster_tree.column("name", width=220, anchor="w")
        self.roster_tree.column("phone", width=130, anchor="w")
        self.roster_tree.column("scores", width=150, anchor="center")
        self.roster_tree.column("total", width=75, anchor="center")
        self.roster_tree.column("stub", width=110, anchor="center")

        vsb = ttk.Scrollbar(left_card, orient="vertical", command=self.roster_tree.yview)
        self.roster_tree.configure(yscrollcommand=vsb.set)
        self.roster_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.roster_tree.bind("<<TreeviewSelect>>", self._on_roster_select)

        # Right Inspector: Physical Tear-Off Grade Slip Canvas + Bottom CTA
        right_wrap = tk.Frame(split, bg=PAPER, width=410)
        right_wrap.pack(side=tk.RIGHT, fill=tk.Y)
        right_wrap.pack_propagate(False)

        self.slip_inspector_canvas = tk.Canvas(
            right_wrap,
            width=410,
            bg=PAPER,
            highlightthickness=0,
            bd=0,
        )
        self.slip_inspector_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.slip_inspector_canvas.bind("<Configure>", lambda e: self._redraw_slip_inspector())

        # Interactive Controls at bottom of Right Inspector
        ctrl_box = tk.Frame(right_wrap, bg=CREAM, highlightbackground=INK, highlightthickness=2, padx=12, pady=10)
        ctrl_box.pack(side=tk.BOTTOM, fill=tk.X, pady=(6, 0))

        ch_row = tk.Frame(ctrl_box, bg=CREAM)
        ch_row.pack(side=tk.TOP, fill=tk.X, pady=(0, 8))
        tk.Checkbutton(
            ch_row,
            text="WhatsApp",
            variable=self.send_wa_var,
            bg=CREAM,
            fg=INK,
            activebackground=CREAM,
            selectcolor=PAPER,
            font=(FONT_MONO, 9, "bold"),
        ).pack(side=tk.LEFT, padx=(0, 12))
        tk.Checkbutton(
            ch_row,
            text="Email (HTML)",
            variable=self.send_email_var,
            bg=CREAM,
            fg=INK,
            activebackground=CREAM,
            selectcolor=PAPER,
            font=(FONT_MONO, 9, "bold"),
        ).pack(side=tk.LEFT, padx=(0, 12))
        tk.Checkbutton(
            ch_row,
            text="Dry-Run",
            variable=self.dry_run_var,
            bg=CREAM,
            fg=NILE,
            activebackground=CREAM,
            selectcolor=PAPER,
            font=(FONT_MONO, 9, "bold"),
        ).pack(side=tk.RIGHT)

        self.tear_single_btn = tk.Button(
            ctrl_box,
            text="Tear & Hand Over Selected Slip",
            command=self._dispatch_selected_single_slip,
            bg=NILE,
            fg=PAPER,
            activebackground=NILE_DK,
            activeforeground=PAPER,
            font=(FONT_BODY, 10, "bold"),
            relief=tk.FLAT,
            pady=8,
            cursor="hand2",
        )
        self.tear_single_btn.pack(side=tk.TOP, fill=tk.X)

    def _refresh_roster_view(self):
        if not hasattr(self, "roster_tree"):
            return
        fname = self.loaded_file_path.name if self.loaded_file_path else "students_sample.csv"
        self.file_badge_lbl.configure(
            text=f"LOADED FILE: data/{fname}  ({len(self.records)} rows · {len(self.ingestion_errors)} warnings)"
        )
        for item in self.roster_tree.get_children():
            self.roster_tree.delete(item)

        for idx, r in enumerate(self.records):
            st = self.row_statuses.get(r.student_id, "PENDING")
            stub_txt = {
                "SUCCESS": "✓ Torn (Sent)",
                "FAILED": "! Tilted (Failed)",
                "SKIPPED": "○ Empty (Skipped)",
                "PENDING": "▪ Attached",
            }.get(st, "▪ Attached")

            m = int(r.midterm) if r.midterm is not None else 0
            l = int(r.lab) if r.lab is not None else 0
            o = int(r.oral) if r.oral is not None else 0
            b = int(r.bonus) if r.bonus else 0
            sc_str = f"{m} · {l} · {o} (+{b})"
            tot_str = f"{int(r.computed_total)}/{int(r.total_max)}"

            iid = str(idx)
            self.roster_tree.insert("", tk.END, iid=iid, values=(r.student_id, r.name, r.phone, sc_str, tot_str, stub_txt))

        if self.records:
            sel_iid = str(min(self.selected_idx, len(self.records) - 1))
            self.roster_tree.selection_set(sel_iid)
            self.roster_tree.see(sel_iid)
        self._redraw_slip_inspector()

    def _on_roster_select(self, event):
        sel = self.roster_tree.selection()
        if sel:
            self.selected_idx = int(sel[0])
            self._redraw_slip_inspector()

    def _redraw_slip_inspector(self):
        c = self.slip_inspector_canvas
        c.delete("all")
        w = max(c.winfo_width(), 400)
        h = max(c.winfo_height(), 560)

        if not self.records:
            c.create_text(w / 2, h / 2, text="No student slips loaded.", fill=FOG, font=(FONT_HEADLINE, 13))
            return

        student = self.records[min(self.selected_idx, len(self.records) - 1)]
        first_name = student.name.split()[0] if student.name else "Student"

        # Shadow + Main Slip Body (leaving 52px on right for perforation seam & stubs)
        slip_w = w - 58
        draw_rounded_rect(c, 8, 8, slip_w + 4, h - 4, radius=14, fill=INK, outline="")
        draw_rounded_rect(c, 4, 4, slip_w, h - 8, radius=14, fill=CREAM, outline=INK, width=2)

        # Perforated vertical dot seam at x = slip_w + 10
        perf_x = slip_w + 11
        for py in range(22, h - 20, 18):
            c.create_oval(perf_x - 2, py - 2, perf_x + 2, py + 2, fill=NILE, outline="")

        # The ONE Stamp (#E8553D) Torn Stub in upper-right tilted 14 deg!
        draw_rotated_stub(c, slip_w + 34, 26, 34, 30, angle_deg=14.0, fill=STAMP)

        # 3 Attached Nile Stubs + 3 Waiting Paper_2 Stubs
        for sy in (68, 110, 152):
            draw_rounded_rect(c, slip_w + 18, sy, slip_w + 50, sy + 28, radius=6, fill=NILE, outline="")
        for sy in (194, 236, 278):
            draw_rounded_rect(c, slip_w + 18, sy, slip_w + 50, sy + 28, radius=6, fill=PAPER_2, outline=NILE, width=1.5)

        # Top Nile Header inside Slip
        draw_rounded_rect(c, 4, 4, slip_w, 88, radius=12, fill=NILE, outline=INK, width=2)
        c.create_text(
            20, 18,
            text=f"PERSONAL GRADE SLIP  ·  ROW #{self.selected_idx + 1} OF {len(self.records)}",
            anchor="nw", fill=SAND, font=(FONT_MONO, 8, "bold")
        )
        c.create_text(
            20, 36,
            text=f"{first_name}, your grade slip",
            anchor="nw", fill=PAPER, font=(FONT_HEADLINE, 14, "bold")
        )
        c.create_text(
            20, 58,
            text="is ready to hand over.",
            anchor="nw", fill=PAPER, font=(FONT_HEADLINE, 14, "bold")
        )

        # Student Identity
        c.create_text(20, 102, text="STUDENT", anchor="nw", fill=FOG, font=(FONT_MONO, 8, "bold"))
        c.create_text(20, 118, text=student.name, anchor="nw", fill=INK, font=(FONT_BODY, 12, "bold"))
        c.create_text(
            20, 140,
            text=f"ID: {student.student_id}   ·   {student.course[:28]}",
            anchor="nw", fill=FOG, font=(FONT_MONO, 8)
        )

        # Perforated divider row
        for px in range(20, int(slip_w - 16), 10):
            c.create_oval(px, 164, px + 3, 167, fill=PAPER_3, outline="")

        # Score Breakdown 2x2 Grid
        c.create_text(20, 176, text="SCORE BREAKDOWN (AFTER EXTRA BONUS)", anchor="nw", fill=NILE, font=(FONT_MONO, 8, "bold"))
        box_w = (slip_w - 48) / 2
        m_val = int(student.midterm) if student.midterm is not None else "-"
        l_val = int(student.lab) if student.lab is not None else "-"
        o_val = int(student.oral) if student.oral is not None else "-"
        b_val = f"+{int(student.bonus)}" if student.bonus else "+0"

        tiles = [
            (20, 196, "MIDTERM EXAM", str(m_val), f"/ {int(student.midterm_max)}"),
            (28 + box_w, 196, "PRACTICAL LAB", str(l_val), f"/ {int(student.lab_max)}"),
            (20, 256, "ORAL EXAM", str(o_val), f"/ {int(student.oral_max)}"),
            (28 + box_w, 256, "EXTRA BONUS", b_val, "pts"),
        ]
        for tx, ty, tlbl, tval, tmax in tiles:
            draw_rounded_rect(c, tx, ty, tx + box_w, ty + 52, radius=7, fill=PAPER, outline=PAPER_3, width=1.5)
            c.create_text(tx + 10, ty + 8, text=tlbl, anchor="nw", fill=FOG, font=(FONT_MONO, 8, "bold"))
            c.create_text(tx + 10, ty + 24, text=tval, anchor="nw", fill=INK, font=(FONT_MONO, 14, "bold"))
            c.create_text(tx + 52, ty + 28, text=tmax, anchor="nw", fill=FOG, font=(FONT_MONO, 9))

        # Total Accumulated Score Box
        draw_rounded_rect(c, 20, 318, slip_w - 16, 368, radius=8, fill=PAPER_2, outline=NILE, width=2)
        c.create_text(32, 328, text="TOTAL ACCUMULATED SCORE", anchor="nw", fill=NILE, font=(FONT_MONO, 8, "bold"))
        c.create_text(32, 346, text=f"formatted: {student.formatted_scores}", anchor="nw", fill=FOG, font=(FONT_MONO, 8))
        c.create_text(
            slip_w - 28, 334,
            text=f"{int(student.computed_total)} / {int(student.total_max)}",
            anchor="ne", fill=NILE, font=(FONT_MONO, 15, "bold")
        )

        # Instructor Note Box
        draw_rounded_rect(c, 20, 378, slip_w - 16, 430, radius=8, fill=PAPER, outline=SAND, width=2)
        c.create_text(32, 386, text="INSTRUCTOR NOTE (student.notes)", anchor="nw", fill=INK, font=(FONT_MONO, 8, "bold"))
        note_str = student.notes or "Recorded on course evaluation pad."
        if len(note_str) > 40:
            note_str = note_str[:39] + "…"
        c.create_text(32, 404, text=f"\"{note_str}\"", anchor="nw", fill=INK, font=(FONT_HEADLINE, 9, "bold"))

        # Recipient Info Pills
        draw_rounded_rect(c, 20, 440, slip_w - 16, 470, radius=6, fill=PAPER, outline=PAPER_3, width=1)
        c.create_text(30, 448, text=f"WA: {student.phone}", anchor="nw", fill=INK, font=(FONT_MONO, 9, "bold"))

        draw_rounded_rect(c, 20, 476, slip_w - 16, 506, radius=6, fill=PAPER, outline=PAPER_3, width=1)
        c.create_text(30, 484, text=f"Email: {student.email or '— (will skip email)'}", anchor="nw", fill=INK if student.email else FOG, font=(FONT_MONO, 9))

        # Circular Punch Seal at bottom of slip
        c.create_oval(22, 516, 42, 536, fill=PAPER_2, outline=NILE, width=1.5)
        st = self.row_statuses.get(student.student_id, "PENDING")
        c.create_text(50, 519, text=f"Current Stub Status: {st}", anchor="nw", fill=NILE, font=(FONT_HEADLINE, 9, "bold"))

        self.tear_single_btn.configure(text=f"Tear & Hand Over {first_name}'s Slip")

    def _resolve_selected_channel(self) -> DispatchChannel:
        wa = self.send_wa_var.get()
        em = self.send_email_var.get()
        if wa and em:
            return DispatchChannel.BOTH
        elif em:
            return DispatchChannel.EMAIL
        return DispatchChannel.WHATSAPP

    def _dispatch_selected_single_slip(self):
        if not self.records:
            return
        student = self.records[min(self.selected_idx, len(self.records) - 1)]
        ch = self._resolve_selected_channel()
        dry = self.dry_run_var.get()
        self.tear_single_btn.configure(text="Sending Slip...", state=tk.DISABLED)

        def worker():
            dispatcher = NotificationDispatcher(
                config=self.config_obj,
                database=self.database,
                template_engine=self.template_engine,
                dry_run=dry,
            )
            results = dispatcher.dispatch_single_student(
                student=student,
                channel=ch,
                wa_template=self.active_wa_template.get(),
                email_template=self.active_email_template.get(),
            )
            final_status = "SUCCESS"
            for r in results:
                if r.status == DispatchStatus.FAILED:
                    final_status = "FAILED"
                    break
                elif r.status == DispatchStatus.SKIPPED and final_status != "SUCCESS":
                    final_status = "SKIPPED"
            self.row_statuses[student.student_id] = final_status
            self.after(0, self._on_single_slip_done, student, results)

        threading.Thread(target=worker, daemon=True).start()

    def _on_single_slip_done(self, student: StudentGradeRecord, results: List[DispatchResult]):
        self.tear_single_btn.configure(state=tk.NORMAL)
        self._refresh_roster_view()
        self._redraw_sidebar()
        summary_lines = [
            f"Student: {student.name} (ID: {student.student_id})",
            f"Mode: {'DRY-RUN (Simulated)' if self.dry_run_var.get() else 'LIVE TRANSMISSION'}",
            "",
        ]
        any_failed = False
        for r in results:
            if r.status == DispatchStatus.FAILED:
                any_failed = True
            err = f" ({r.error_message})" if r.error_message else ""
            summary_lines.append(f"• {r.channel.value.upper()} → {r.recipient}: {r.status.value}{err}")
        if any_failed:
            messagebox.showwarning("Dispatch Issue", "\n".join(summary_lines))
        else:
            messagebox.showinfo("Slip Handed Over", "\n".join(summary_lines))

    def _start_batch_from_roster(self):
        self.switch_tab(2)
        self._start_batch_queue()

    # ========================================================================
    # SCREEN 02: SLIP COMPOSER (JINJA2 TEMPLATES & PREVIEWS)
    # ========================================================================
    def _build_screen_02_composer(self):
        f2 = tk.Frame(self.content_area, bg=PAPER)
        self.screens.append(f2)

        hdr = tk.Frame(f2, bg=PAPER)
        hdr.pack(side=tk.TOP, fill=tk.X, padx=24, pady=(18, 10))

        title_col = tk.Frame(hdr, bg=PAPER)
        title_col.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(
            title_col,
            text="Slip Composer — Personal Notice Templates",
            bg=PAPER,
            fg=INK,
            font=(FONT_HEADLINE, 20, "bold"),
        ).pack(side=tk.TOP, anchor="w")
        tk.Label(
            title_col,
            text="Name the person, not the batch. Edit Jinja2 templates and preview personal Email & WhatsApp slips.",
            bg=PAPER,
            fg=FOG,
            font=(FONT_BODY, 10),
        ).pack(side=tk.TOP, anchor="w", pady=(2, 0))

        # Student switcher top-right
        nav_pill = tk.Frame(hdr, bg=CREAM, highlightbackground=INK, highlightthickness=1, padx=10, pady=6)
        nav_pill.pack(side=tk.RIGHT)
        tk.Button(
            nav_pill, text="◀ Prev", command=lambda: self._step_composer_student(-1),
            bg=PAPER_2, fg=INK, relief=tk.FLAT, font=(FONT_MONO, 9, "bold"), cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 8))
        self.composer_student_lbl = tk.Label(
            nav_pill, text="Sarah Ahmed Mahmoud (220770)", bg=CREAM, fg=INK, font=(FONT_BODY, 10, "bold")
        )
        self.composer_student_lbl.pack(side=tk.LEFT, padx=6)
        tk.Button(
            nav_pill, text="Next ▶", command=lambda: self._step_composer_student(1),
            bg=PAPER_2, fg=INK, relief=tk.FLAT, font=(FONT_MONO, 9, "bold"), cursor="hand2"
        ).pack(side=tk.LEFT, padx=(8, 0))

        # Split Panes
        split = tk.Frame(f2, bg=PAPER)
        split.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=24, pady=(0, 18))

        # Left Editor Card
        left_card = tk.Frame(split, bg=CREAM, highlightbackground=INK, highlightthickness=2, padx=14, pady=14)
        left_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 16))

        tab_row = tk.Frame(left_card, bg=CREAM)
        tab_row.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
        tk.Label(tab_row, text="TEMPLATE FILE:", bg=CREAM, fg=FOG, font=(FONT_MONO, 9, "bold")).pack(side=tk.LEFT, padx=(0, 8))

        self.editing_tpl_var = tk.StringVar(value="wa_grade_report_styled.txt.j2")
        for tpl_file in ("wa_grade_report_styled.txt.j2", "wa_grade_report.txt.j2", "email_grade_report.html.j2"):
            tk.Radiobutton(
                tab_row,
                text=tpl_file,
                variable=self.editing_tpl_var,
                value=tpl_file,
                command=self._load_template_into_editor,
                bg=CREAM,
                fg=NILE,
                selectcolor=PAPER,
                font=(FONT_MONO, 8, "bold"),
            ).pack(side=tk.LEFT, padx=4)

        # Clickable Pydantic Token Chips
        chip_row = tk.Frame(left_card, bg=CREAM)
        chip_row.pack(side=tk.TOP, fill=tk.X, pady=(0, 8))
        tk.Label(chip_row, text="INSERT TOKEN:", bg=CREAM, fg=FOG, font=(FONT_MONO, 8, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        for tok in ("{{ student.name }}", "{{ student.student_id }}", "{{ student.formatted_scores }}", "{{ student.total }}", "{{ student.notes }}"):
            tk.Button(
                chip_row,
                text=tok,
                command=lambda t=tok: self._insert_token_into_editor(t),
                bg=PAPER,
                fg=NILE,
                relief=tk.SOLID,
                bd=1,
                font=(FONT_MONO, 8),
                padx=5,
                pady=2,
                cursor="hand2",
            ).pack(side=tk.LEFT, padx=3)

        # Dark Ink Code Editor
        self.tpl_editor = tk.Text(
            left_card,
            bg=INK,
            fg=PAPER,
            insertbackground=SAND,
            selectbackground=NILE,
            font=(FONT_MONO, 10),
            relief=tk.FLAT,
            padx=12,
            pady=12,
            height=18,
            wrap=tk.WORD,
        )
        self.tpl_editor.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.tpl_editor.bind("<KeyRelease>", lambda e: self._render_composer_previews())

        bot_bar = tk.Frame(left_card, bg=CREAM)
        bot_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        tk.Button(
            bot_bar,
            text="Save Template & Re-render",
            command=self._save_template_from_editor,
            bg=NILE,
            fg=PAPER,
            font=(FONT_BODY, 9, "bold"),
            relief=tk.FLAT,
            padx=14,
            pady=6,
            cursor="hand2",
        ).pack(side=tk.LEFT)
        self.tpl_status_lbl = tk.Label(
            bot_bar,
            text="✓ Jinja2 syntax valid · Brand voice guardrails active",
            bg=CREAM,
            fg=FOG,
            font=(FONT_MONO, 8),
        )
        self.tpl_status_lbl.pack(side=tk.RIGHT)

        # Right Live Previews (Email Slip + WhatsApp Plain Notice)
        right_col = tk.Frame(split, bg=PAPER, width=540)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH)
        right_col.pack_propagate(False)

        # Email Preview Canvas (Marsal Nile & Paper card with Stamp mark in footer)
        self.email_preview_canvas = tk.Canvas(right_col, bg=CREAM, height=380, highlightbackground=INK, highlightthickness=2)
        self.email_preview_canvas.pack(side=tk.TOP, fill=tk.X, pady=(0, 12))
        self.email_preview_canvas.bind("<Configure>", lambda e: self._render_composer_previews())

        # WhatsApp Plain Slip Preview Box
        wa_card = tk.Frame(right_col, bg=CREAM, highlightbackground=INK, highlightthickness=2)
        wa_card.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        wa_hdr = tk.Frame(wa_card, bg=NILE, height=32)
        wa_hdr.pack(side=tk.TOP, fill=tk.X)
        wa_hdr.pack_propagate(False)
        tk.Label(
            wa_hdr,
            text="WHATSAPP PERSONAL TEXT SLIP  (No chat bubbles, plain personal text)",
            bg=NILE,
            fg=PAPER,
            font=(FONT_MONO, 8, "bold"),
            padx=12,
        ).pack(side=tk.LEFT, fill=tk.Y)

        self.wa_preview_text = tk.Text(
            wa_card,
            bg=CREAM,
            fg=INK,
            font=(FONT_MONO, 10),
            relief=tk.FLAT,
            padx=14,
            pady=12,
            wrap=tk.WORD,
            state=tk.DISABLED,
        )
        self.wa_preview_text.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self._load_template_into_editor()

    def _step_composer_student(self, delta: int):
        if not self.records:
            return
        self.selected_idx = (self.selected_idx + delta) % len(self.records)
        self._refresh_composer_view()

    def _insert_token_into_editor(self, token: str):
        self.tpl_editor.insert(tk.INSERT, token)
        self._render_composer_previews()

    def _load_template_into_editor(self):
        tpl_name = self.editing_tpl_var.get()
        tpl_path = self.template_engine.template_dir / tpl_name
        if tpl_path.exists():
            content = tpl_path.read_text(encoding="utf-8")
            self.tpl_editor.delete("1.0", tk.END)
            self.tpl_editor.insert("1.0", content)
        self._render_composer_previews()

    def _save_template_from_editor(self):
        tpl_name = self.editing_tpl_var.get()
        tpl_path = self.template_engine.template_dir / tpl_name
        try:
            content = self.tpl_editor.get("1.0", tk.END).strip() + "\n"
            tpl_path.write_text(content, encoding="utf-8")
            self.tpl_status_lbl.configure(text=f"✓ Saved {tpl_name} at {datetime.now().strftime('%H:%M:%S')}", fg=NILE)
            self._render_composer_previews()
        except Exception as exc:
            self.tpl_status_lbl.configure(text=f"Error: {exc}", fg=STAMP)

    def _refresh_composer_view(self):
        if not self.records:
            return
        student = self.records[min(self.selected_idx, len(self.records) - 1)]
        self.composer_student_lbl.configure(
            text=f"{student.name} (ID: {student.student_id})   [{self.selected_idx + 1}/{len(self.records)}]"
        )
        self._render_composer_previews()

    def _render_composer_previews(self):
        if not self.records or not hasattr(self, "wa_preview_text"):
            return
        student = self.records[min(self.selected_idx, len(self.records) - 1)]

        # 1. Render WhatsApp Preview using live editor if editing a WA template
        try:
            raw_tpl = self.tpl_editor.get("1.0", tk.END)
            if self.editing_tpl_var.get().startswith("wa_"):
                from jinja2 import Template
                rendered_wa = Template(raw_tpl).render(student=student).strip()
            else:
                rendered_wa = self.template_engine.render_whatsapp(student, template_name=self.active_wa_template.get())
            self.tpl_status_lbl.configure(text="✓ Jinja2 syntax valid · Brand voice guardrails active", fg=FOG)
        except Exception as exc:
            rendered_wa = f"[Jinja2 Syntax Preview Notice]: {exc}"
            self.tpl_status_lbl.configure(text=f"Jinja2 Syntax Error: {exc}", fg=INK)

        self.wa_preview_text.configure(state=tk.NORMAL)
        self.wa_preview_text.delete("1.0", tk.END)
        self.wa_preview_text.insert("1.0", rendered_wa)
        self.wa_preview_text.configure(state=tk.DISABLED)

        # 2. Draw Email Slip Preview Card on Canvas (brand.md Section 7)
        c = self.email_preview_canvas
        c.delete("all")
        w = max(c.winfo_width(), 520)
        h = max(c.winfo_height(), 360)

        # Dark Ink Header Strip
        c.create_rectangle(0, 0, w, 30, fill=INK, outline="")
        c.create_text(
            12, 8,
            text=f"EMAIL HTML SLIP PREVIEW  ·  To: {student.email or 'N/A'}",
            anchor="nw", fill=PAPER, font=(FONT_MONO, 8, "bold")
        )

        # Inner Paper Card
        draw_rounded_rect(c, 16, 40, w - 16, h - 12, radius=8, fill=PAPER, outline=PAPER_3, width=1.5)
        draw_rounded_rect(c, 16, 40, w - 16, 94, radius=8, fill=NILE, outline="")
        c.create_text(30, 50, text="ACADEMIC GRADE SLIP  ·  MARSAL DISPATCH", anchor="nw", fill=SAND, font=(FONT_MONO, 8, "bold"))
        c.create_text(30, 66, text=student.course, anchor="nw", fill=PAPER, font=(FONT_HEADLINE, 13, "bold"))

        c.create_text(30, 104, text=f"Dear {student.name} (ID: {student.student_id}),", anchor="nw", fill=NILE, font=(FONT_HEADLINE, 11, "bold"))
        c.create_text(30, 124, text="Your personal evaluation slip has been torn off the course pad:", anchor="nw", fill=FOG, font=(FONT_BODY, 9))

        # Score table inside email card
        c.create_rectangle(30, 148, w - 30, 170, fill=PAPER_2, outline="")
        c.create_text(40, 153, text="ASSESSMENT COMPONENT", anchor="nw", fill=INK, font=(FONT_MONO, 8, "bold"))
        c.create_text(w - 130, 153, text="MAX", anchor="nw", fill=FOG, font=(FONT_MONO, 8, "bold"))
        c.create_text(w - 80, 153, text="SCORE", anchor="nw", fill=NILE, font=(FONT_MONO, 8, "bold"))

        rows = [
            ("Midterm Exam", str(int(student.midterm_max)), str(int(student.midterm) if student.midterm is not None else "-")),
            ("Practical Lab", str(int(student.lab_max)), str(int(student.lab) if student.lab is not None else "-")),
            ("Oral Exam", str(int(student.oral_max)), str(int(student.oral) if student.oral is not None else "-")),
            ("Extra Bonus", "—", f"+{int(student.bonus)}"),
        ]
        ry = 176
        for rlbl, rmax, rsc in rows:
            c.create_text(40, ry, text=rlbl, anchor="nw", fill=INK, font=(FONT_BODY, 9))
            c.create_text(w - 125, ry, text=rmax, anchor="nw", fill=FOG, font=(FONT_MONO, 9))
            c.create_text(w - 75, ry, text=rsc, anchor="nw", fill=NILE if "+" in rsc else INK, font=(FONT_MONO, 9, "bold"))
            ry += 20

        draw_rounded_rect(c, 30, 260, w - 30, 288, radius=5, fill="#E3EFEF", outline=NILE, width=1)
        c.create_text(40, 266, text="Total Accumulated Score", anchor="nw", fill=NILE, font=(FONT_BODY, 9, "bold"))
        c.create_text(w - 85, 266, text=f"{int(student.computed_total)} / {int(student.total_max)}", anchor="nw", fill=NILE, font=(FONT_MONO, 10, "bold"))

        # Footer with the ONE Stamp (#E8553D) mark in the email footer!
        draw_marsal_mark_on_canvas(c, x=32, y=300, scale=0.22, body_color=NILE, cutout_color=PAPER, torn_stub_color=STAMP)
        c.create_text(
            68, 308,
            text=f"marsal  ·  One slip, one student. Note: \"{student.notes or 'Good luck!'}\"",
            anchor="nw", fill=FOG, font=(FONT_BODY, 8)
        )

    # ========================================================================
    # SCREEN 03: HAND-OUT QUEUE (DARK INK THEME — LIVE THROTTLED SENDING)
    # ========================================================================
    def _build_screen_03_queue_dark(self):
        f3 = tk.Frame(self.content_area, bg=INK)
        self.screens.append(f3)

        hdr = tk.Frame(f3, bg=INK)
        hdr.pack(side=tk.TOP, fill=tk.X, padx=24, pady=(18, 10))

        title_col = tk.Frame(hdr, bg=INK)
        title_col.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(
            title_col,
            text="Hand-Out Queue — One Slip at a Human Pace",
            bg=INK,
            fg=PAPER,
            font=(FONT_HEADLINE, 20, "bold"),
        ).pack(side=tk.TOP, anchor="w")
        tk.Label(
            title_col,
            text="One message every 5 to 12 seconds, like a person handing out papers rather than a blast.",
            bg=INK,
            fg=LAGOON,
            font=(FONT_BODY, 10),
        ).pack(side=tk.TOP, anchor="w", pady=(2, 0))

        ctrl_col = tk.Frame(hdr, bg=INK)
        ctrl_col.pack(side=tk.RIGHT)

        tk.Checkbutton(
            ctrl_col,
            text="Dry-Run Mode (Safe)",
            variable=self.dry_run_var,
            command=self._redraw_queue_canvas,
            bg=INK_2,
            fg=SAND,
            activebackground=INK_2,
            activeforeground=SAND,
            selectcolor=INK,
            font=(FONT_MONO, 9, "bold"),
            padx=10,
            pady=6,
        ).pack(side=tk.LEFT, padx=(0, 10))

        self.queue_start_btn = tk.Button(
            ctrl_col,
            text="▶ Start Handing Out Slips",
            command=self._start_batch_queue,
            bg=SAND,
            fg=INK,
            activebackground=PAPER,
            font=(FONT_BODY, 10, "bold"),
            relief=tk.FLAT,
            padx=16,
            pady=7,
            cursor="hand2",
        )
        self.queue_start_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.queue_stop_btn = tk.Button(
            ctrl_col,
            text="■ Stop",
            command=self._stop_batch_queue,
            bg=INK_2,
            fg=PAPER,
            activebackground=INK_3,
            font=(FONT_BODY, 10, "bold"),
            relief=tk.SOLID,
            bd=1,
            padx=12,
            pady=7,
            cursor="hand2",
        )
        self.queue_stop_btn.pack(side=tk.LEFT)

        # Full Dark-Mode Canvas for Hero Flight Stage, Cadence Bar Plot & Queue Lists
        self.queue_canvas = tk.Canvas(f3, bg=INK, highlightthickness=0, bd=0)
        self.queue_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=24, pady=(0, 18))
        self.queue_canvas.bind("<Configure>", lambda e: self._redraw_queue_canvas())

    def _start_batch_queue(self):
        if self.is_dispatching:
            return
        if not self.records:
            messagebox.showwarning("Empty Pad", "Please load a student spreadsheet first.")
            return

        self.is_dispatching = True
        self.stop_requested = False
        self.queue_start_btn.configure(text="Handing Out Slips...", state=tk.DISABLED)

        ch = self._resolve_selected_channel()
        dry = self.dry_run_var.get()
        min_d = self.config_obj.throttle.min_delay_seconds
        max_d = self.config_obj.throttle.max_delay_seconds

        def batch_worker():
            dispatcher = NotificationDispatcher(
                config=self.config_obj,
                database=self.database,
                template_engine=self.template_engine,
                dry_run=dry,
            )
            total = len(self.records)
            for idx, student in enumerate(self.records, start=1):
                if self.stop_requested:
                    break
                self.current_flight_student = student
                self.current_flight_idx = idx
                self.after(0, self._redraw_queue_canvas)

                results = dispatcher.dispatch_single_student(
                    student=student,
                    channel=ch,
                    wa_template=self.active_wa_template.get(),
                    email_template=self.active_email_template.get(),
                )
                st = "SUCCESS"
                for r in results:
                    if r.status == DispatchStatus.FAILED:
                        st = "FAILED"
                        break
                    elif r.status == DispatchStatus.SKIPPED and st != "SUCCESS":
                        st = "SKIPPED"
                self.row_statuses[student.student_id] = st

                gap = round(random.uniform(min_d, max_d), 1)
                self.recent_intervals.append((f"#{idx:02d}", gap, True))
                if len(self.recent_intervals) > 14:
                    self.recent_intervals = [(lbl, g, False) for lbl, g, _ in self.recent_intervals[-14:]]
                    self.recent_intervals[-1] = (f"#{idx:02d}", gap, True)

                self.after(0, self._redraw_sidebar)
                self.after(0, self._redraw_queue_canvas)

                if idx < total and not self.stop_requested:
                    # In Dry-Run mode we animate the countdown rapidly (0.6s) while showing the simulated human gap
                    wait_total = 0.6 if dry else gap
                    steps = 6
                    for s_i in range(steps, 0, -1):
                        if self.stop_requested:
                            break
                        self.current_countdown_sec = round(gap * (s_i / steps), 1)
                        self.after(0, self._redraw_queue_canvas)
                        time.sleep(wait_total / steps)

            self.is_dispatching = False
            self.current_countdown_sec = 0.0
            self.after(0, self._on_batch_finished)

        threading.Thread(target=batch_worker, daemon=True).start()

    def _stop_batch_queue(self):
        self.stop_requested = True

    def _on_batch_finished(self):
        self.queue_start_btn.configure(text="▶ Start Handing Out Slips", state=tk.NORMAL)
        self._redraw_sidebar()
        self._redraw_queue_canvas()

    def _redraw_queue_canvas(self):
        c = self.queue_canvas
        c.delete("all")
        w = max(c.winfo_width(), 1100)
        h = max(c.winfo_height(), 720)

        student = self.current_flight_student or (self.records[self.selected_idx] if self.records else None)
        idx_num = self.current_flight_idx or (self.selected_idx + 1 if self.records else 0)
        total_num = len(self.records)

        # 1. HERO STAGE: THE SLIP IN FLIGHT (y=4..244)
        draw_rounded_rect(c, 2, 4, w - 2, 244, radius=12, fill=INK_2, outline=LAGOON, width=1.5)

        # Left Active Student Card inside Hero
        draw_rounded_rect(c, 22, 22, 510, 226, radius=10, fill=INK, outline=LAGOON, width=2)
        status_hdr = "NOW HANDING OVER" if self.is_dispatching else "READY ON THE PAD"
        c.create_text(40, 36, text=f"{status_hdr}  ·  SLIP #{idx_num} OF {total_num}", anchor="nw", fill=SAND, font=(FONT_MONO, 9, "bold"))

        if student:
            c.create_text(40, 58, text=student.name, anchor="nw", fill=PAPER, font=(FONT_HEADLINE, 18, "bold"))
            c.create_text(
                40, 90,
                text=f"ID: {student.student_id}  ·  {student.phone}  ·  {student.email or 'No email'}",
                anchor="nw", fill=LAGOON, font=(FONT_MONO, 9)
            )
            draw_rounded_rect(c, 40, 116, 490, 168, radius=7, fill=INK_2, outline=INK_3, width=1)
            c.create_text(
                52, 124,
                text=f"Scores: Midterm {student.midterm or '-'}  ·  Lab {student.lab or '-'}  ·  Oral {student.oral or '-'}  ·  Bonus +{student.bonus}",
                anchor="nw", fill=PAPER, font=(FONT_MONO, 8)
            )
            c.create_text(
                52, 144,
                text=f"Total Score: {int(student.computed_total)} / {int(student.total_max)}   —   \"{student.notes or 'Recorded'}\"",
                anchor="nw", fill=SAND, font=(FONT_MONO, 9, "bold")
            )
            c.create_text(
                40, 182,
                text="✓ Logged to SQLite data/dispatches.db as SUCCESS, FAILED or SKIPPED.",
                anchor="nw", fill=LAGOON, font=(FONT_MONO, 8, "bold")
            )

        # Center Large Slip & Stubs Mark with the ONE Stamp (#E8553D) Torn Stub lifting away!
        mark_x = 555
        draw_marsal_mark_on_canvas(
            c,
            x=mark_x,
            y=50,
            scale=1.08,
            body_color=LAGOON,
            cutout_color=INK_2,
            torn_stub_color=STAMP,  # The ONE Stamp (#E8553D) accent in Screen 03!
            show_dots=True,
        )
        # Motion arc dots
        for ax, ay in [(mark_x + 112, 66), (mark_x + 120, 52), (mark_x + 128, 40)]:
            c.create_oval(ax, ay, ax + 5, ay + 5, fill=SAND, outline="")

        # Right Human Pace Timer Box
        pace_x = 740
        draw_rounded_rect(c, pace_x, 22, w - 22, 226, radius=10, fill=INK, outline=INK_3, width=1.5)
        c.create_text(pace_x + 20, 38, text="UNHURRIED HUMAN PACE", anchor="nw", fill=SAND, font=(FONT_MONO, 9, "bold"))
        gap_txt = f"Next slip in {self.current_countdown_sec:.1f}s" if self.is_dispatching else f"Pace: {self.config_obj.throttle.min_delay_seconds:.1f}s – {self.config_obj.throttle.max_delay_seconds:.1f}s"
        c.create_text(pace_x + 20, 62, text=gap_txt, anchor="nw", fill=PAPER, font=(FONT_HEADLINE, 20, "bold"))
        c.create_text(
            pace_x + 20, 98,
            text="Uneven gaps between sends so it feels like a person handing out papers.",
            anchor="nw", fill=LAGOON, font=(FONT_BODY, 9)
        )

        # Progress bar
        bar_w = max(180, (w - 44) - (pace_x + 20))
        draw_rounded_rect(c, pace_x + 20, 132, pace_x + 20 + bar_w, 146, radius=6, fill=INK_2, outline=INK_3, width=1)
        done_count = sum(1 for s in self.row_statuses.values() if s != "PENDING")
        fill_ratio = (done_count / max(1, total_num)) if total_num else 0.35
        draw_rounded_rect(c, pace_x + 20, 132, pace_x + 20 + max(18, bar_w * fill_ratio), 146, radius=6, fill=SAND, outline="")

        c.create_text(
            pace_x + 20, 160,
            text=f"Progress: {done_count} of {total_num} slips processed  ·  Mode: {'DRY-RUN' if self.dry_run_var.get() else 'LIVE'}",
            anchor="nw", fill=PAPER_2, font=(FONT_MONO, 9, "bold")
        )
        c.create_text(
            pace_x + 20, 184,
            text="Never animate or blast all stubs at once.",
            anchor="nw", fill=FOG, font=(FONT_HEADLINE, 9)
        )

        # 2. MIDDLE STRIP: RANDOMIZED ANTI-BAN CADENCE BAR CHART (y=258..392)
        draw_rounded_rect(c, 2, 258, w - 2, 392, radius=10, fill=INK_2, outline=INK_3, width=1.5)
        c.create_text(22, 270, text="RANDOMIZED ANTI-BAN CADENCE (UNEVEN GAPS BETWEEN EACH STUDENT SLIP)", anchor="nw", fill=LAGOON, font=(FONT_MONO, 8, "bold"))

        bx = 26
        step_x = max(62, (w - 60) // max(1, len(self.recent_intervals)))
        for rlbl, rsec, is_curr in self.recent_intervals:
            bh = max(16, min(58, int(rsec * 4.6)))
            by = 362 - bh
            bcol = SAND if is_curr else LAGOON
            draw_rounded_rect(c, bx, by, bx + 44, 362, radius=4, fill=bcol, outline="")
            c.create_text(bx + 22, by - 12, text=f"{rsec:.1f}s", anchor="n", fill=SAND if is_curr else PAPER_2, font=(FONT_MONO, 8, "bold"))
            c.create_text(bx + 22, 368, text=rlbl, anchor="n", fill=LAGOON, font=(FONT_MONO, 8))
            bx += step_x

        # 3. BOTTOM SPLIT: RECENTLY HANDED OVER vs NEXT ON THE PAD (y=406..h-4)
        half_w = (w - 16) / 2
        draw_rounded_rect(c, 2, 406, half_w, h - 4, radius=10, fill=INK_2, outline=INK_3, width=1.5)
        c.create_text(22, 420, text="RECENTLY HANDED OVER (STUBS TORN OFF)", anchor="nw", fill=LAGOON, font=(FONT_MONO, 9, "bold"))

        draw_rounded_rect(c, half_w + 14, 406, w - 2, h - 4, radius=10, fill=INK_2, outline=INK_3, width=1.5)
        c.create_text(half_w + 34, 420, text="WAITING ON THE PAD (STUBS STILL ATTACHED)", anchor="nw", fill=SAND, font=(FONT_MONO, 9, "bold"))

        done_records = [r for r in self.records if self.row_statuses.get(r.student_id) != "PENDING"][-5:]
        wait_records = [r for r in self.records if self.row_statuses.get(r.student_id) == "PENDING"][:5]

        ry = 448
        for r in reversed(done_records):
            st = self.row_statuses.get(r.student_id, "SUCCESS")
            draw_rounded_rect(c, 18, ry, half_w - 16, ry + 42, radius=6, fill=INK, outline=INK_3, width=1)
            c.create_text(30, ry + 13, text=r.student_id, anchor="nw", fill=SAND, font=(FONT_MONO, 9, "bold"))
            c.create_text(95, ry + 12, text=r.name[:26], anchor="nw", fill=PAPER, font=(FONT_BODY, 10, "bold"))
            c.create_text(half_w - 140, ry + 13, text=st, anchor="nw", fill=LAGOON, font=(FONT_MONO, 8, "bold"))
            draw_status_stub_on_canvas(c, half_w - 64, ry + 11, st, dark_mode=True)
            ry += 48

        wy = 448
        for r in wait_records:
            draw_rounded_rect(c, half_w + 30, wy, w - 18, wy + 42, radius=6, fill=INK, outline=INK_3, width=1)
            c.create_text(half_w + 42, wy + 13, text=r.student_id, anchor="nw", fill=LAGOON, font=(FONT_MONO, 9, "bold"))
            c.create_text(half_w + 108, wy + 12, text=r.name[:26], anchor="nw", fill=PAPER, font=(FONT_BODY, 10, "bold"))
            c.create_text(w - 150, wy + 13, text=f"{int(r.computed_total)}/{int(r.total_max)}", anchor="nw", fill=SAND, font=(FONT_MONO, 9, "bold"))
            draw_status_stub_on_canvas(c, w - 66, wy + 11, "PENDING", dark_mode=True)
            wy += 48

    # ========================================================================
    # SCREEN 04: AUDIT LEDGER (SQLite data/dispatches.db)
    # ========================================================================
    def _build_screen_04_audit(self):
        f4 = tk.Frame(self.content_area, bg=PAPER)
        self.screens.append(f4)

        hdr = tk.Frame(f4, bg=PAPER)
        hdr.pack(side=tk.TOP, fill=tk.X, padx=24, pady=(18, 8))

        title_col = tk.Frame(hdr, bg=PAPER)
        title_col.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(
            title_col,
            text="Audit Ledger — Every Send Recorded Plainly",
            bg=PAPER,
            fg=INK,
            font=(FONT_HEADLINE, 20, "bold"),
        ).pack(side=tk.TOP, anchor="w")
        tk.Label(
            title_col,
            text="Every send is logged in data/dispatches.db as success, failed or skipped.",
            bg=PAPER,
            fg=FOG,
            font=(FONT_BODY, 10),
        ).pack(side=tk.TOP, anchor="w", pady=(2, 0))

        btn_col = tk.Frame(hdr, bg=PAPER)
        btn_col.pack(side=tk.RIGHT)
        tk.Button(
            btn_col,
            text="Export Audit CSV...",
            command=self._export_audit_csv,
            bg=PAPER_2,
            fg=INK,
            font=(FONT_BODY, 9, "bold"),
            relief=tk.SOLID,
            bd=1,
            padx=14,
            pady=6,
            cursor="hand2",
        ).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(
            btn_col,
            text="Refresh Ledger",
            command=self._refresh_audit_view,
            bg=NILE,
            fg=PAPER,
            font=(FONT_BODY, 9, "bold"),
            relief=tk.FLAT,
            padx=14,
            pady=7,
            cursor="hand2",
        ).pack(side=tk.LEFT)

        # 4 Summary Cards with Stub Status Icons (drawn on a Canvas strip)
        self.audit_cards_canvas = tk.Canvas(f4, bg=PAPER, height=110, highlightthickness=0, bd=0)
        self.audit_cards_canvas.pack(side=tk.TOP, fill=tk.X, padx=24, pady=(4, 10))
        self.audit_cards_canvas.bind("<Configure>", lambda e: self._redraw_audit_summary_cards())

        # Filter Bar
        fbar = tk.Frame(f4, bg=PAPER_2, highlightbackground=PAPER_3, highlightthickness=1, padx=12, pady=6)
        fbar.pack(side=tk.TOP, fill=tk.X, padx=24, pady=(0, 10))

        tk.Label(fbar, text="CHANNEL:", bg=PAPER_2, fg=FOG, font=(FONT_MONO, 9, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        self.audit_ch_filter = tk.StringVar(value="ALL")
        for ch_opt in ("ALL", "wa", "email"):
            tk.Radiobutton(
                fbar,
                text=ch_opt.upper(),
                variable=self.audit_ch_filter,
                value=ch_opt,
                command=self._refresh_audit_view,
                bg=PAPER_2,
                fg=INK,
                selectcolor=CREAM,
                font=(FONT_MONO, 9, "bold"),
            ).pack(side=tk.LEFT, padx=4)

        tk.Label(fbar, text="   SEARCH:", bg=PAPER_2, fg=FOG, font=(FONT_MONO, 9, "bold")).pack(side=tk.LEFT, padx=(16, 6))
        self.audit_search_var = tk.StringVar()
        self.audit_search_var.trace_add("write", lambda *_: self._refresh_audit_view())
        tk.Entry(
            fbar,
            textvariable=self.audit_search_var,
            bg=CREAM,
            fg=INK,
            font=(FONT_BODY, 10),
            width=36,
            relief=tk.SOLID,
            bd=1,
        ).pack(side=tk.LEFT)

        # Audit Table
        tbl_card = tk.Frame(f4, bg=CREAM, highlightbackground=INK, highlightthickness=2)
        tbl_card.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=24, pady=(0, 18))

        acols = ("id", "timestamp", "student", "channel", "recipient", "status", "detail")
        self.audit_tree = ttk.Treeview(tbl_card, columns=acols, show="headings", style="Marsal.Treeview")
        self.audit_tree.heading("id", text="LOG #")
        self.audit_tree.heading("timestamp", text="TIMESTAMP")
        self.audit_tree.heading("student", text="STUDENT (NAME & ID)")
        self.audit_tree.heading("channel", text="CHANNEL")
        self.audit_tree.heading("recipient", text="RECIPIENT")
        self.audit_tree.heading("status", text="STUB STATUS")
        self.audit_tree.heading("detail", text="PLAIN AUDIT RECORD")

        self.audit_tree.column("id", width=65, anchor="center")
        self.audit_tree.column("timestamp", width=155, anchor="w")
        self.audit_tree.column("student", width=230, anchor="w")
        self.audit_tree.column("channel", width=95, anchor="center")
        self.audit_tree.column("recipient", width=185, anchor="w")
        self.audit_tree.column("status", width=120, anchor="center")
        self.audit_tree.column("detail", width=240, anchor="w")

        avsb = ttk.Scrollbar(tbl_card, orient="vertical", command=self.audit_tree.yview)
        self.audit_tree.configure(yscrollcommand=avsb.set)
        self.audit_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        avsb.pack(side=tk.RIGHT, fill=tk.Y)

    def _redraw_audit_summary_cards(self):
        c = self.audit_cards_canvas
        c.delete("all")
        w = max(c.winfo_width(), 1000)
        summary = self.database.get_summary()

        cards = [
            ("SUCCESS (STUB TORN AWAY)", str(summary["success"]), "Slips handed over cleanly", "SUCCESS", True),
            ("FAILED (STUB ATTACHED)", str(summary["failed"]), "Slips waiting retry on pad", "FAILED", False),
            ("SKIPPED (EMPTY STUB SLOT)", str(summary["skipped"]), "Missing optional email", "SKIPPED", False),
            ("RECORDED HUMAN PACE", f"{self.config_obj.throttle.min_delay_seconds:.0f}–{self.config_obj.throttle.max_delay_seconds:.0f}s", f"Total audit logs: {summary['total']}", None, False),
        ]
        gap = 16
        card_w = (w - gap * 3) / 4
        cx = 0
        for title, val, sub, st_code, use_stamp in cards:
            draw_rounded_rect(c, cx + 3, 5, cx + card_w + 3, 104, radius=10, fill=PAPER_3, outline="")
            draw_rounded_rect(c, cx, 2, cx + card_w, 101, radius=10, fill=CREAM, outline=INK, width=1.5)
            c.create_text(cx + 16, 14, text=title, anchor="nw", fill=NILE if st_code != "FAILED" else INK, font=(FONT_MONO, 8, "bold"))
            c.create_text(cx + 16, 34, text=val, anchor="nw", fill=INK, font=(FONT_HEADLINE, 22, "bold"))
            c.create_text(cx + 16, 74, text=sub, anchor="nw", fill=FOG, font=(FONT_BODY, 9))
            if st_code:
                # Uses the ONE Stamp (#E8553D) accent on the SUCCESS card torn stub!
                draw_status_stub_on_canvas(c, cx + card_w - 50, 38, st_code, dark_mode=False, use_stamp=use_stamp)
            cx += card_w + gap

    def _refresh_audit_view(self):
        if not hasattr(self, "audit_tree"):
            return
        self._redraw_audit_summary_cards()

        ch_val = self.audit_ch_filter.get()
        ch_arg = None if ch_val == "ALL" else ch_val
        rows = self.database.get_history(limit=150, channel=ch_arg)
        q = self.audit_search_var.get().strip().lower()

        for item in self.audit_tree.get_children():
            self.audit_tree.delete(item)

        for r in rows:
            stud_str = f"{r['student_name'] or 'Student'} ({r['student_id']})"
            rec_str = str(r["recipient"])
            if q and (q not in stud_str.lower() and q not in rec_str.lower()):
                continue
            st = r["status"]
            st_badge = {
                "SUCCESS": "✓ SUCCESS (Torn)",
                "FAILED": "! FAILED (Tilted)",
                "SKIPPED": "○ SKIPPED (Empty)",
            }.get(st, st)
            detail = r["error_message"] or "Handed over at human pace"
            ts = str(r["timestamp"])[:19].replace("T", " ")
            self.audit_tree.insert(
                "",
                tk.END,
                values=(f"#{r['id']}", ts, stud_str, r["channel"].upper(), rec_str, st_badge, detail),
            )

    def _export_audit_csv(self):
        fp = filedialog.asksaveasfilename(
            title="Export SQLite Audit Ledger to CSV",
            defaultextension=".csv",
            initialfile="marsal_audit_export.csv",
            filetypes=[("CSV Files", "*.csv")],
        )
        if not fp:
            return
        rows = self.database.get_history(limit=1000)
        with open(fp, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "timestamp", "student_id", "student_name", "channel", "recipient", "status", "error_message"])
            for r in rows:
                writer.writerow([r["id"], r["timestamp"], r["student_id"], r["student_name"], r["channel"], r["recipient"], r["status"], r["error_message"]])
        messagebox.showinfo("Export Complete", f"Exported {len(rows)} audit records to:\n{fp}")

    # ========================================================================
    # SCREEN 05: CHANNEL & PACE SETUP (+ BUILT-IN VISUAL IDENTITY SPEC)
    # ========================================================================
    def _build_screen_05_setup(self):
        f5 = tk.Frame(self.content_area, bg=PAPER)
        self.screens.append(f5)

        hdr = tk.Frame(f5, bg=PAPER)
        hdr.pack(side=tk.TOP, fill=tk.X, padx=24, pady=(18, 10))

        title_col = tk.Frame(hdr, bg=PAPER)
        title_col.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(
            title_col,
            text="Channel & Pace Setup — Unhurried & Dependable",
            bg=PAPER,
            fg=INK,
            font=(FONT_HEADLINE, 20, "bold"),
        ).pack(side=tk.TOP, anchor="w")
        tk.Label(
            title_col,
            text="Configure human-paced throttling, WhatsApp & SMTP providers, and inspect Marsal's stub status system.",
            bg=PAPER,
            fg=FOG,
            font=(FONT_BODY, 10),
        ).pack(side=tk.TOP, anchor="w", pady=(2, 0))

        tk.Button(
            hdr,
            text="Test All Channels (--channel all)",
            command=self._test_all_channels,
            bg=NILE,
            fg=PAPER,
            font=(FONT_BODY, 10, "bold"),
            relief=tk.FLAT,
            padx=16,
            pady=7,
            cursor="hand2",
        ).pack(side=tk.RIGHT)

        # 3 Columns
        cols = tk.Frame(f5, bg=PAPER)
        cols.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=24, pady=(0, 18))

        # Column 1: Human Pace & Phone Normalizer
        c1 = tk.Frame(cols, bg=CREAM, highlightbackground=INK, highlightthickness=2, padx=14, pady=14)
        c1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))

        tk.Label(c1, text="1. HUMAN PACE & THROTTLING", bg=NILE, fg=PAPER, font=(FONT_MONO, 9, "bold"), padx=10, pady=6, anchor="w").pack(side=tk.TOP, fill=tk.X, pady=(0, 12))
        tk.Label(c1, text="One message every 5 to 12 seconds,\nlike a person would.", bg=CREAM, fg=INK, font=(FONT_HEADLINE, 13, "bold"), justify=tk.LEFT, anchor="w").pack(side=tk.TOP, anchor="w")

        delay_frame = tk.Frame(c1, bg=CREAM, pady=10)
        delay_frame.pack(side=tk.TOP, fill=tk.X)
        tk.Label(delay_frame, text="MIN_DELAY_SECONDS:", bg=CREAM, fg=FOG, font=(FONT_MONO, 9, "bold")).grid(row=0, column=0, sticky="w", pady=4)
        self.min_delay_var = tk.StringVar(value=str(self.config_obj.throttle.min_delay_seconds))
        tk.Entry(delay_frame, textvariable=self.min_delay_var, width=10, font=(FONT_MONO, 11, "bold"), bg=PAPER, fg=NILE).grid(row=0, column=1, padx=8, pady=4)

        tk.Label(delay_frame, text="MAX_DELAY_SECONDS:", bg=CREAM, fg=FOG, font=(FONT_MONO, 9, "bold")).grid(row=1, column=0, sticky="w", pady=4)
        self.max_delay_var = tk.StringVar(value=str(self.config_obj.throttle.max_delay_seconds))
        tk.Entry(delay_frame, textvariable=self.max_delay_var, width=10, font=(FONT_MONO, 11, "bold"), bg=PAPER, fg=NILE).grid(row=1, column=1, padx=8, pady=4)

        # Interactive E.164 Normalizer Tester
        tk.Frame(c1, bg=PAPER_3, height=1).pack(side=tk.TOP, fill=tk.X, pady=12)
        tk.Label(c1, text="LIVE E.164 PHONE NORMALIZER TESTER (EG +20)", bg=CREAM, fg=NILE, font=(FONT_MONO, 9, "bold")).pack(side=tk.TOP, anchor="w")
        self.phone_test_in = tk.StringVar(value="01120844781")
        self.phone_test_in.trace_add("write", lambda *_: self._update_phone_test())
        tk.Entry(c1, textvariable=self.phone_test_in, font=(FONT_MONO, 11), bg=PAPER, fg=INK).pack(side=tk.TOP, fill=tk.X, pady=(6, 4))
        self.phone_test_out = tk.Label(c1, text="→ Normalized E.164: +201120844781", bg=CREAM, fg=NILE, font=(FONT_MONO, 10, "bold"), anchor="w")
        self.phone_test_out.pack(side=tk.TOP, fill=tk.X)

        # Column 2: WhatsApp & SMTP Providers
        c2 = tk.Frame(cols, bg=CREAM, highlightbackground=INK, highlightthickness=2, padx=14, pady=14)
        c2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))

        tk.Label(c2, text="2. DELIVERY CHANNELS (WA & SMTP)", bg=NILE, fg=PAPER, font=(FONT_MONO, 9, "bold"), padx=10, pady=6, anchor="w").pack(side=tk.TOP, fill=tk.X, pady=(0, 12))

        tk.Label(c2, text="WHATSAPP PROVIDER (WA_PROVIDER):", bg=CREAM, fg=FOG, font=(FONT_MONO, 8, "bold")).pack(side=tk.TOP, anchor="w")
        self.wa_prov_var = tk.StringVar(value=self.config_obj.whatsapp.provider)
        for pkey, plbl in [("pywhatkit", "PyWhatKit Web Automation"), ("meta", "Meta WhatsApp Cloud API"), ("mock", "Mock Provider (Dry-Run)")]:
            tk.Radiobutton(
                c2, text=f"{plbl} ({pkey})", variable=self.wa_prov_var, value=pkey,
                bg=CREAM, fg=INK, selectcolor=PAPER, font=(FONT_BODY, 9, "bold")
            ).pack(side=tk.TOP, anchor="w", pady=2)

        tk.Frame(c2, bg=PAPER_3, height=1).pack(side=tk.TOP, fill=tk.X, pady=10)
        tk.Label(c2, text="SMTP EMAIL TLS SETTINGS:", bg=CREAM, fg=FOG, font=(FONT_MONO, 8, "bold")).pack(side=tk.TOP, anchor="w")

        self.smtp_host_var = tk.StringVar(value=self.config_obj.smtp.host)
        self.smtp_port_var = tk.StringVar(value=str(self.config_obj.smtp.port))
        self.smtp_user_var = tk.StringVar(value=self.config_obj.smtp.user)
        self.smtp_pass_var = tk.StringVar(value=self.config_obj.smtp.password)
        self.smtp_name_var = tk.StringVar(value=self.config_obj.smtp.from_name)

        for flbl, fvar, is_pw in [
            ("SMTP_HOST:", self.smtp_host_var, False),
            ("SMTP_PORT:", self.smtp_port_var, False),
            ("SMTP_USER:", self.smtp_user_var, False),
            ("SMTP_PASSWORD:", self.smtp_pass_var, True),
            ("SMTP_FROM_NAME:", self.smtp_name_var, False),
        ]:
            row = tk.Frame(c2, bg=CREAM)
            row.pack(side=tk.TOP, fill=tk.X, pady=2)
            tk.Label(row, text=flbl, width=15, anchor="w", bg=CREAM, fg=FOG, font=(FONT_MONO, 8, "bold")).pack(side=tk.LEFT)
            ent_kw = {"show": "•"} if is_pw else {}
            tk.Entry(row, textvariable=fvar, bg=PAPER, fg=INK, font=(FONT_MONO, 9), **ent_kw).pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Button(
            c2,
            text="Apply Pace & Channel Settings",
            command=self._apply_setup_changes,
            bg=NILE,
            fg=PAPER,
            font=(FONT_BODY, 9, "bold"),
            relief=tk.FLAT,
            pady=7,
            cursor="hand2",
        ).pack(side=tk.TOP, fill=tk.X, pady=(12, 8))

        self.conn_result_lbl = tk.Label(
            c2,
            text="Click 'Test All Channels' to verify SMTP & WhatsApp.",
            bg=PAPER_2,
            fg=INK,
            font=(FONT_MONO, 8),
            justify=tk.LEFT,
            anchor="w",
            padx=8,
            pady=8,
        )
        self.conn_result_lbl.pack(side=tk.BOTTOM, fill=tk.X)

        # Column 3: Built-in Marsal Visual Identity & Stub Legend Canvas
        c3 = tk.Frame(cols, bg=CREAM, highlightbackground=INK, highlightthickness=2)
        c3.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.brand_legend_canvas = tk.Canvas(c3, bg=CREAM, highlightthickness=0, bd=0)
        self.brand_legend_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.brand_legend_canvas.bind("<Configure>", lambda e: self._redraw_brand_legend_canvas())

    def _update_phone_test(self):
        raw = self.phone_test_in.get()
        try:
            norm = normalize_phone(raw)
            self.phone_test_out.configure(text=f"→ Normalized E.164: {norm}", fg=NILE)
        except Exception as exc:
            self.phone_test_out.configure(text=f"→ Invalid: {exc}", fg=INK)

    def _apply_setup_changes(self):
        try:
            self.config_obj.throttle.min_delay_seconds = float(self.min_delay_var.get())
            self.config_obj.throttle.max_delay_seconds = float(self.max_delay_var.get())
            self.config_obj.whatsapp.provider = self.wa_prov_var.get()
            self.config_obj.smtp.host = self.smtp_host_var.get().strip()
            self.config_obj.smtp.port = int(self.smtp_port_var.get().strip())
            self.config_obj.smtp.user = self.smtp_user_var.get().strip()
            self.config_obj.smtp.password = self.smtp_pass_var.get().strip()
            if self.config_obj.smtp.user and not self.config_obj.smtp.from_email:
                self.config_obj.smtp.from_email = self.config_obj.smtp.user
            self.config_obj.smtp.from_name = self.smtp_name_var.get().strip()
            self._redraw_sidebar()
            self.conn_result_lbl.configure(text="✓ Applied pace and channel configuration.", fg=NILE)
        except Exception as exc:
            messagebox.showerror("Configuration Error", str(exc))

    def _test_all_channels(self):
        self._apply_setup_changes()
        email_svc = EmailService(self.config_obj.smtp)
        ok_em, msg_em = email_svc.test_connection()
        wa_prov = get_whatsapp_provider(self.config_obj.whatsapp, dry_run=self.dry_run_var.get())
        ok_wa, msg_wa = wa_prov.test_connection()

        txt = (
            f"[{'OK' if ok_em else 'X'}] SMTP: {msg_em[:44]}\n"
            f"[{'OK' if ok_wa else 'X'}] WhatsApp ({self.config_obj.whatsapp.provider}): {msg_wa[:44]}"
        )
        self.conn_result_lbl.configure(text=txt, fg=NILE if (ok_em and ok_wa) else INK)

    def _redraw_brand_legend_canvas(self):
        c = self.brand_legend_canvas
        c.delete("all")
        w = max(c.winfo_width(), 340)

        c.create_rectangle(0, 0, w, 34, fill=INK, outline="")
        c.create_text(14, 10, text="3. MARSAL VISUAL IDENTITY & STUB LEGEND", anchor="nw", fill=SAND, font=(FONT_MONO, 8, "bold"))

        # Brand Lockup Card with the ONE Stamp (#E8553D) Torn Stub on Screen 05!
        draw_rounded_rect(c, 14, 46, w - 14, 136, radius=8, fill=PAPER, outline=PAPER_3, width=1.5)
        draw_marsal_mark_on_canvas(c, x=28, y=56, scale=0.48, body_color=NILE, cutout_color=PAPER, torn_stub_color=STAMP)
        c.create_text(106, 62, text="marsal", anchor="nw", fill=INK, font=(FONT_HEADLINE, 22, "bold"))
        c.create_text(108, 96, text="One slip, one student.", anchor="nw", fill=NILE, font=(FONT_HEADLINE, 10, "bold"))

        # Status Icons Legend
        c.create_text(14, 148, text="STATUS ICONS (A STUB IS THE UNIT)", anchor="nw", fill=FOG, font=(FONT_MONO, 8, "bold"))
        stubs = [
            ("SUCCESS", "Stub torn away from perforation", "SUCCESS"),
            ("FAILED", "Stub still attached with a small tilt", "FAILED"),
            ("SKIPPED", "Outlined, empty stub position", "SKIPPED"),
        ]
        sy = 166
        for stitle, sdesc, scode in stubs:
            draw_rounded_rect(c, 14, sy, w - 14, sy + 40, radius=6, fill=PAPER, outline=PAPER_3, width=1)
            draw_status_stub_on_canvas(c, 26, sy + 10, scode, dark_mode=False)
            c.create_text(70, sy + 6, text=stitle, anchor="nw", fill=INK, font=(FONT_MONO, 8, "bold"))
            c.create_text(70, sy + 21, text=sdesc, anchor="nw", fill=FOG, font=(FONT_BODY, 8))
            sy += 46

        # Color Palette Swatches
        c.create_text(14, 312, text="BRAND PALETTE (60% PAPER/INK · 30% NILE · 10% ACCENT)", anchor="nw", fill=FOG, font=(FONT_MONO, 8, "bold"))
        swatches = [
            (NILE, "Nile", "#0F4C5C", "Primary brand · 8.38:1 on Paper", PAPER),
            (STAMP, "Stamp", "#E8553D", "Torn stub accent once/layout (graphics)", PAPER),
            (SAND, "Sand", "#F2C14E", "Accent on Nile (5.67:1) & on Ink", INK),
            (LAGOON, "Lagoon", "#6FC1D0", "Nile for dark Ink grounds (7.95:1)", INK),
            (INK, "Ink", "#10222A", "Primary text & dark ground (14.41:1)", PAPER),
            (PAPER, "Paper", "#F6F0E4", "Warm light slip ground", INK),
            (FOG, "Fog", "#51636B", "Secondary metadata text (5.53:1)", PAPER),
        ]
        wy = 332
        for scol, sname, shex, srole, stxt in swatches:
            draw_rounded_rect(c, 14, wy, w - 14, wy + 34, radius=5, fill=PAPER, outline=PAPER_3, width=1)
            draw_rounded_rect(c, 20, wy + 5, 80, wy + 29, radius=4, fill=scol, outline=INK if scol == PAPER else "", width=1)
            c.create_text(50, wy + 17, text=sname, anchor="center", fill=stxt, font=(FONT_BODY, 8, "bold"))
            c.create_text(90, wy + 5, text=shex, anchor="nw", fill=INK, font=(FONT_MONO, 8, "bold"))
            c.create_text(90, wy + 18, text=srole, anchor="nw", fill=FOG, font=(FONT_BODY, 7))
            wy += 38


def main():
    app = MarsalDesktopApp()
    app.mainloop()


if __name__ == "__main__":
    main()
