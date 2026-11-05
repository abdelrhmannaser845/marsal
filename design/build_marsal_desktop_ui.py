#!/usr/bin/env python3
"""
Marsal Desktop Application UI — FigCraft Automation Builder
Generates a 5-frame production-ready desktop UI canvas adhering strictly to
Marsal's Visual Identity (brand.md) and the FigCraft automation specification.

Brand Philosophy:
  "One slip, one student."
  Marsal (مرسال, "messenger") turns a spreadsheet of grades, attendance and notices
  into a personal message for each student, sent one by one over WhatsApp and email.
"""

import os
import re
import sys
import json
import subprocess
from pathlib import Path

CLI_PATH = (
    r"C:\Program Files\FigCraft\figcraft-cli.exe"
    if sys.platform == "win32"
    else "/usr/local/bin/figcraft-cli"
)

# ============================================================================
# MARSAL BRAND PALETTE (from brand.md)
# ============================================================================
NILE    = "#0F4C5C"  # Primary brand color, app icon tile, sidebar rail
STAMP   = "#E8553D"  # The ONE accent, once per layout (the torn stub). Graphics only, never text!
SAND    = "#F2C14E"  # Accent on Nile and on Ink (torn stub in icon, tagline on dark)
LAGOON  = "#6FC1D0"  # Nile for dark backgrounds
INK     = "#10222A"  # Text and dark ground
INK_2   = "#1A333D"  # Low-contrast dark surface / pattern on Ink
INK_3   = "#24424F"  # Subtle border on dark Ink
PAPER   = "#F6F0E4"  # Light ground
PAPER_2 = "#EAE2D1"  # Secondary warm paper surface / pattern on Paper
PAPER_3 = "#DCD2BD"  # Hairline border on Paper
CREAM   = "#FBF8F2"  # Elevated slip card surface on Paper
FOG     = "#51636B"  # Secondary text (5.53:1 on Paper)

# Typography (System-safe fallbacks matching brand.md Section 4: zero missingFonts)
FONT_HEADLINE = "Georgia"   # Serif fallback for Fraunces SemiBold headlines
FONT_BODY     = "Inter"     # Sans-serif for DM Sans interface & body
FONT_MONO     = "Consolas"  # Monospace for IDs, E.164 phones, Jinja2 code, timestamps


def load_normalized_wordmark() -> str:
    """Extracts and normalizes the Fraunces SemiBold 'marsal' outlined wordmark path."""
    svg_path = Path(r"D:\projects\marsal\Marsal Visual Identity\logo\marsal-logo.svg")
    svg_text = svg_path.read_text(encoding="utf-8")
    paths = re.findall(r'<path d="([^"]+)"', svg_text)
    raw_d = paths[1]

    tokens = re.findall(r"[A-Za-z]|[-+]?\d*\.?\d+", raw_d)
    out = []
    cmd = ""
    i = 0
    dx, dy = -165.30, -66.23
    while i < len(tokens):
        t = tokens[i]
        if t.isalpha():
            cmd = t
            out.append(t)
            i += 1
        else:
            if cmd == "H":
                out.append(f"{float(t) + dx:.2f}")
                i += 1
            elif cmd == "V":
                out.append(f"{float(t) + dy:.2f}")
                i += 1
            elif cmd in ("M", "L", "T"):
                out.append(f"{float(tokens[i]) + dx:.2f}")
                out.append(f"{float(tokens[i + 1]) + dy:.2f}")
                i += 2
            elif cmd in ("Q", "S"):
                out.append(f"{float(tokens[i]) + dx:.2f}")
                out.append(f"{float(tokens[i + 1]) + dy:.2f}")
                out.append(f"{float(tokens[i + 2]) + dx:.2f}")
                out.append(f"{float(tokens[i + 3]) + dy:.2f}")
                i += 4
            elif cmd == "C":
                for k in range(0, 6, 2):
                    out.append(f"{float(tokens[i + k]) + dx:.2f}")
                    out.append(f"{float(tokens[i + k + 1]) + dy:.2f}")
                i += 6
            else:
                out.append(t)
                i += 1
    return " ".join(out)


WORDMARK_PATH = load_normalized_wordmark()


class MarsalFigCraftBuilder:
    def __init__(self):
        self.commands = []
        self.next_id = 2  # Document root page is 1; first node is 2

    def _alloc_id(self) -> int:
        nid = self.next_id
        self.next_id += 1
        return nid

    def add_frame(self, name: str, x: float, y: float, w: float, h: float, bg: str = PAPER, stroke: str = INK, stroke_weight: float = 2) -> int:
        fid = self._alloc_id()
        props = {
            "fills": [{"type": "solid", "color": bg}],
            "clip": True,
        }
        if stroke and stroke_weight > 0:
            props["strokes"] = [{"type": "solid", "color": stroke, "weight": stroke_weight}]
        self.commands.append({
            "command": "frame.create",
            "params": {
                "name": name,
                "x": x,
                "y": y,
                "width": w,
                "height": h,
                "props": props,
            }
        })
        return fid

    def rect(self, parent: int, x: float, y: float, w: float, h: float, fill: str = None, stroke: str = None, weight: float = 1, radius: float = 0, rotation: float = 0, name: str = "Rect", dashes: list = None) -> int:
        nid = self._alloc_id()
        props = {"cornerRadius": radius}
        if fill:
            props["fills"] = [{"type": "solid", "color": fill}]
        else:
            props["fills"] = []
        if stroke and weight > 0:
            props["strokes"] = [{"type": "solid", "color": stroke, "weight": weight}]
        else:
            props["strokes"] = []
        if rotation:
            props["rotation"] = rotation
        if dashes:
            props["dashes"] = dashes
        self.commands.append({
            "command": "shape.rectangle",
            "params": {
                "name": name,
                "parent": parent,
                "x": round(x, 2),
                "y": round(y, 2),
                "width": round(w, 2),
                "height": round(h, 2),
                "props": props,
            }
        })
        return nid

    def card(self, parent: int, x: float, y: float, w: float, h: float, fill: str = CREAM, stroke: str = INK, weight: float = 1.5, radius: float = 10, shadow_color: str = PAPER_3, shadow_offset: float = 4, name: str = "Card") -> int:
        """Draws a crisp deterministic offset shadow + card surface."""
        if shadow_color and shadow_offset > 0:
            self.rect(parent, x + shadow_offset, y + shadow_offset, w, h, fill=shadow_color, stroke=None, radius=radius, name=f"{name}_Shadow")
        return self.rect(parent, x, y, w, h, fill=fill, stroke=stroke, weight=weight, radius=radius, name=name)

    def ellipse(self, parent: int, x: float, y: float, w: float, h: float, fill: str = None, stroke: str = None, weight: float = 1, name: str = "Dot") -> int:
        nid = self._alloc_id()
        props = {}
        if fill:
            props["fills"] = [{"type": "solid", "color": fill}]
        else:
            props["fills"] = []
        if stroke and weight > 0:
            props["strokes"] = [{"type": "solid", "color": stroke, "weight": weight}]
        else:
            props["strokes"] = []
        self.commands.append({
            "command": "shape.ellipse",
            "params": {
                "name": name,
                "parent": parent,
                "x": round(x, 2),
                "y": round(y, 2),
                "width": round(w, 2),
                "height": round(h, 2),
                "props": props,
            }
        })
        return nid

    def line(self, parent: int, x: float, y: float, length: float, color: str = PAPER_3, weight: float = 1, rotation: float = 0, dashes: list = None, name: str = "Divider") -> int:
        nid = self._alloc_id()
        props = {
            "strokes": [{"type": "solid", "color": color, "weight": weight}],
            "rotation": rotation,
        }
        if dashes:
            props["dashes"] = dashes
        self.commands.append({
            "command": "shape.line",
            "params": {
                "name": name,
                "parent": parent,
                "x": round(x, 2),
                "y": round(y, 2),
                "width": round(length, 2),
                "props": props,
            }
        })
        return nid

    def text(self, parent: int, content: str, x: float, y: float, size: float = 13, weight: int = 400, color: str = INK, family: str = FONT_BODY, width: float = None, letter_spacing: str = None, align: str = None, line_height: str = None, name: str = None) -> int:
        nid = self._alloc_id()
        props = {
            "fontSize": size,
            "fontWeight": weight,
            "fontFamily": family,
            "fills": [{"type": "solid", "color": color}],
        }
        if letter_spacing:
            props["letterSpacing"] = letter_spacing
        if align:
            props["textAlign"] = align
        if line_height:
            props["lineHeight"] = line_height
        params = {
            "text": str(content),
            "parent": parent,
            "x": round(x, 2),
            "y": round(y, 2),
            "props": props,
        }
        if width:
            params["width"] = round(width, 2)
        if name:
            params["name"] = name
        self.commands.append({
            "command": "text.create",
            "params": params,
        })
        return nid

    def vector(self, parent: int, path_d: str, x: float, y: float, width: float = None, fill: str = None, stroke: str = None, weight: float = 1, name: str = "Vector") -> int:
        nid = self._alloc_id()
        props = {}
        if fill:
            props["fills"] = [{"type": "solid", "color": fill}]
        else:
            props["fills"] = []
        if stroke and weight > 0:
            props["strokes"] = [{"type": "solid", "color": stroke, "weight": weight}]
        else:
            props["strokes"] = []
        params = {
            "name": name,
            "parent": parent,
            "path": path_d,
            "x": round(x, 2),
            "y": round(y, 2),
            "props": props,
        }
        if width:
            params["width"] = round(width, 2)
        self.commands.append({
            "command": "vector.create",
            "params": params,
        })
        return nid

    # ========================================================================
    # MARSAL BRAND IDENTITY PRIMITIVES
    # ========================================================================
    def draw_marsal_mark(self, parent: int, x: float, y: float, scale: float = 0.36, body_color: str = PAPER, cutout_color: str = NILE, torn_stub_color: str = SAND, show_dots: bool = True):
        """
        Draws the official Marsal Grade Slip & Perforated Stubs Mark:
        - Slip body: 84 x 124 (rx 14)
        - 2 horizontal text slots + 1 circular seal cutout
        - 5 perforation dots at cx=90.5
        - 3 attached stubs at x=97, y=32, 64, 96 (30 x 27.5, rx 6)
        - 1 torn stub at x=112, y=-18 (30 x 27.5, rx 6, rotated 14 deg)
        """
        s = scale
        # Main slip body
        self.rect(parent, x, y, 84 * s, 124 * s, fill=body_color, radius=14 * s, name="Mark_SlipBody")
        # 2 line slots inside slip
        self.rect(parent, x + 15 * s, y + 27 * s, 50 * s, 9 * s, fill=cutout_color, radius=4.5 * s, name="Mark_Line1")
        self.rect(parent, x + 15 * s, y + 44 * s, 34 * s, 9 * s, fill=cutout_color, radius=4.5 * s, name="Mark_Line2")
        # Circular stamp hole at bottom right of slip
        self.ellipse(parent, x + 49 * s, y + 85 * s, 20 * s, 20 * s, fill=cutout_color, name="Mark_SealHole")
        # Perforation dots
        if show_dots:
            for cy in (4.0, 33.0, 62.0, 91.0, 120.0):
                self.ellipse(parent, x + (90.5 - 2.2) * s, y + (cy - 2.2) * s, 4.4 * s, 4.4 * s, fill=body_color, name="Mark_PerfDot")
        # 3 attached stubs
        for sy in (32.0, 64.0, 96.0):
            self.rect(parent, x + 97 * s, y + sy * s, 30 * s, 27.5 * s, fill=body_color, radius=6 * s, name="Mark_StubAttached")
        # 1 torn stub lifting away in upper right (rotated 14 deg)
        self.rect(parent, x + 108 * s, y - 14 * s, 30 * s, 27.5 * s, fill=torn_stub_color, radius=6 * s, rotation=14, name="Mark_StubTorn")

    def draw_marsal_wordmark(self, parent: int, x: float, y: float, width: float = 96, color: str = PAPER):
        """Places the outlined Fraunces SemiBold lowercase 'marsal' wordmark."""
        self.vector(parent, WORDMARK_PATH, x, y, width=width, fill=color, name="Marsal_Wordmark")

    def draw_perforation_column(self, parent: int, x: float, y_start: float, y_end: float, step: float = 12, dot_size: float = 4, color: str = PAPER_3):
        """Draws a vertical column of perforation dots (the core Marsal divider motif)."""
        cy = y_start
        while cy <= y_end:
            self.ellipse(parent, x - dot_size / 2, cy - dot_size / 2, dot_size, dot_size, fill=color, name="Perf_Dot")
            cy += step

    def draw_perforation_row(self, parent: int, x_start: float, x_end: float, y: float, step: float = 12, dot_size: float = 3.5, color: str = PAPER_3):
        """Draws a horizontal row of perforation dots."""
        cx = x_start
        while cx <= x_end:
            self.ellipse(parent, cx - dot_size / 2, y - dot_size / 2, dot_size, dot_size, fill=color, name="Perf_Dot_H")
            cx += step

    def draw_background_stub_pattern(self, parent: int, x: float, y: float, height: float, dark_mode: bool = False):
        """
        Draws the subtle repeated column of rounded stubs + perforation dots
        specified in brand.md Section 5 ('Pattern: a column of rounded stubs with perforation dots,
        repeated as a divider or border. Use it as a low-contrast background').
        """
        color = INK_2 if dark_mode else PAPER_2
        dot_c = INK_3 if dark_mode else PAPER_3
        cy = y
        while cy + 24 <= y + height:
            self.ellipse(parent, x, cy + 2, 3.5, 3.5, fill=dot_c, name="Pattern_Dot1")
            self.ellipse(parent, x, cy + 16, 3.5, 3.5, fill=dot_c, name="Pattern_Dot2")
            self.rect(parent, x + 8, cy, 24, 21, fill=color, radius=5, name="Pattern_Stub")
            cy += 28

    def draw_status_stub(self, parent: int, x: float, y: float, status: str, dark_mode: bool = False, use_stamp_accent: bool = False):
        """
        Draws the Marsal Status Icon unit from brand.md Section 5:
        - 'a stub is the unit.'
        - SUCCESS: a stub torn away (shifted right and tilted)
        - FAILED: a stub still attached with a small tilt
        - SKIPPED: an outlined, empty stub position
        """
        dot_color = INK_3 if dark_mode else PAPER_3
        # 2 perforation dots on the left seam
        self.ellipse(parent, x, y + 3, 3.2, 3.2, fill=dot_color, name="StubStatus_Dot1")
        self.ellipse(parent, x, y + 13, 3.2, 3.2, fill=dot_color, name="StubStatus_Dot2")

        st = status.upper()
        if st == "SUCCESS":
            fill_c = STAMP if use_stamp_accent else (LAGOON if dark_mode else NILE)
            # Torn away: shifted right +7px, lifted -2px, tilted 12 deg
            self.rect(parent, x + 10, y - 1, 22, 18, fill=fill_c, radius=4.5, rotation=12, name="Stub_Success_Torn")
        elif st == "FAILED":
            fill_c = SAND if dark_mode else INK
            # Still attached close to seam with a small downward tilt
            self.rect(parent, x + 5, y + 1, 22, 18, fill=fill_c, radius=4.5, rotation=-7, name="Stub_Failed_Attached")
            # Small inner mark showing snag
            inner_c = INK if dark_mode else PAPER
            self.rect(parent, x + 12, y + 8, 8, 2.5, fill=inner_c, radius=1, name="Stub_Failed_Mark")
        elif st == "PENDING":
            # Attached upright stub waiting on the pad
            fill_c = PAPER_2 if not dark_mode else INK_3
            stroke_c = NILE if not dark_mode else LAGOON
            self.rect(parent, x + 5, y, 22, 18, fill=fill_c, stroke=stroke_c, weight=1.5, radius=4.5, name="Stub_Pending_Attached")
        else:  # SKIPPED
            stroke_c = FOG if not dark_mode else LAGOON
            # Outlined empty stub position
            self.rect(parent, x + 6, y, 22, 18, fill=None, stroke=stroke_c, weight=1.5, radius=4.5, dashes=[3, 2], name="Stub_Skipped_Empty")

    # ========================================================================
    # SHARED DESKTOP SHELL (Window Titlebar + Left Navigation Rail)
    # ========================================================================
    def draw_desktop_shell(self, frame_id: int, active_nav_idx: int, window_subtitle: str, dark_mode: bool = False):
        """
        Builds the Desktop App Window Chrome (1440 x 960):
        - Top OS/App Window Bar (height: 38px)
        - Left Brand & Navigation Rail (width: 248px, Nile #0F4C5C on Paper frames, Ink_2/Nile on Dark frame)
        """
        # 1. Top Desktop Window Bar
        bar_bg = INK if dark_mode else INK
        self.rect(frame_id, 0, 0, 1440, 38, fill=bar_bg, name="Window_TitleBar")
        # Window controls (subtle minimal circles on left/right)
        self.ellipse(frame_id, 18, 13, 12, 12, fill=STAMP if False else "#3B525B", name="Win_Close")
        self.ellipse(frame_id, 38, 13, 12, 12, fill=SAND, name="Win_Min")
        self.ellipse(frame_id, 58, 13, 12, 12, fill=LAGOON, name="Win_Max")

        self.text(frame_id, f"marsal desktop  ·  {window_subtitle}", 88, 11, size=12, weight=600, color=PAPER_2, family=FONT_MONO)
        self.text(frame_id, "One slip, one student.", 640, 11, size=12, weight=600, color=SAND, family=FONT_HEADLINE)
        self.text(frame_id, "SQLite: data/dispatches.db   |   Pace: 5.0s – 12.0s   |   v1.4.0", 1035, 12, size=11, weight=400, color=LAGOON, family=FONT_MONO)

        # 2. Left Navigation Rail (x=0, y=38, w=248, h=922)
        rail_bg = "#0B3946" if dark_mode else NILE
        self.rect(frame_id, 0, 38, 248, 922, fill=rail_bg, name="Sidebar_Rail")

        # Brand Lockup inside Sidebar Header (Slip mark + Sand torn stub + Fraunces 'marsal' wordmark)
        self.draw_marsal_mark(
            frame_id,
            x=24,
            y=66,
            scale=0.35,
            body_color=PAPER,
            cutout_color=rail_bg,
            torn_stub_color=SAND,  # Per brand.md: Sand inside the Nile tile!
            show_dots=True,
        )
        self.draw_marsal_wordmark(frame_id, x=84, y=75, width=108, color=PAPER)
        self.text(frame_id, "One slip, one student.", 85, 108, size=12, weight=400, color=SAND, family=FONT_HEADLINE)

        # Perforated divider in sidebar
        self.draw_perforation_row(frame_id, 24, 224, 142, step=10, dot_size=3, color="#2B6777")

        # Navigation Items (each styled like a slip tab with stub indicator)
        nav_items = [
            ("01", "Pad of Slips", "Spreadsheet & student rows"),
            ("02", "Slip Composer", "Jinja2 notices & previews"),
            ("03", "Hand-Out Queue", "Live throttled sending"),
            ("04", "Audit Ledger", "Success, failed & skipped"),
            ("05", "Channel & Pace", "WhatsApp, SMTP & delays"),
        ]
        ny = 162
        for idx, (num, label, sub) in enumerate(nav_items):
            is_active = (idx == active_nav_idx)
            if is_active:
                self.rect(frame_id, 14, ny, 220, 58, fill=PAPER if not dark_mode else INK, radius=8, name=f"Nav_Active_{num}")
                # Active stub tab on right edge
                self.rect(frame_id, 226, ny + 14, 12, 30, fill=SAND, radius=4, name=f"Nav_Stub_{num}")
                txt_c = INK if not dark_mode else PAPER
                sub_c = FOG if not dark_mode else LAGOON
                num_c = NILE if not dark_mode else SAND
            else:
                self.rect(frame_id, 14, ny, 220, 58, fill="#145A6C" if not dark_mode else "#104554", radius=8, name=f"Nav_Item_{num}")
                txt_c = PAPER
                sub_c = "#A5C9D1"
                num_c = SAND

            self.text(frame_id, num, 28, ny + 13, size=11, weight=700, color=num_c, family=FONT_MONO)
            self.text(frame_id, label, 54, ny + 11, size=14, weight=700, color=txt_c, family=FONT_BODY)
            self.text(frame_id, sub, 54, ny + 31, size=11, weight=400, color=sub_c, family=FONT_BODY)
            ny += 68

        # Current Batch Pad Summary Box in Sidebar
        self.draw_perforation_row(frame_id, 24, 224, 520, step=10, dot_size=3, color="#2B6777")
        self.rect(frame_id, 18, 538, 212, 178, fill="#0B3B48" if not dark_mode else "#082C36", stroke="#2B6777", weight=1, radius=8, name="Sidebar_PadBox")
        self.text(frame_id, "CURRENT PAD ON DESK", 32, 554, size=10, weight=700, color=SAND, family=FONT_MONO, letter_spacing="6%")
        self.text(frame_id, "Comp 304: Compiler Design", 32, 574, size=13, weight=700, color=PAPER, family=FONT_HEADLINE)
        self.text(frame_id, "students_sample.xlsx", 32, 595, size=11, weight=400, color=LAGOON, family=FONT_MONO)

        self.text(frame_id, "48 student slips total", 32, 622, size=12, weight=600, color=PAPER, family=FONT_BODY)
        self.text(frame_id, "• 34 handed over (torn)", 32, 644, size=11, weight=400, color="#B8D8DF", family=FONT_BODY)
        self.text(frame_id, "• 12 still attached", 32, 664, size=11, weight=400, color="#B8D8DF", family=FONT_BODY)
        self.text(frame_id, "• 2 skipped (no email)", 32, 684, size=11, weight=400, color="#B8D8DF", family=FONT_BODY)

        # Bottom Channel & Pace Status Footer in Sidebar
        self.rect(frame_id, 18, 734, 212, 204, fill="#0B3B48" if not dark_mode else "#082C36", stroke="#2B6777", weight=1, radius=8, name="Sidebar_ChannelFooter")
        self.text(frame_id, "HUMAN PACE & CHANNELS", 32, 750, size=10, weight=700, color=SAND, family=FONT_MONO, letter_spacing="6%")

        self.ellipse(frame_id, 32, 777, 8, 8, fill=SAND)
        self.text(frame_id, "WhatsApp (PyWhatKit)", 48, 773, size=12, weight=600, color=PAPER, family=FONT_BODY)
        self.text(frame_id, "Session active · E.164 +20", 48, 791, size=11, weight=400, color="#A5C9D1", family=FONT_MONO)

        self.ellipse(frame_id, 32, 821, 8, 8, fill=LAGOON)
        self.text(frame_id, "Email (SMTP TLS :587)", 48, 817, size=12, weight=600, color=PAPER, family=FONT_BODY)
        self.text(frame_id, "smtp.gmail.com verified", 48, 835, size=11, weight=400, color="#A5C9D1", family=FONT_MONO)

        self.line(frame_id, 32, 864, 184, color="#2B6777", weight=1)
        self.text(frame_id, "One slip every 5 to 12 sec,", 32, 876, size=11, weight=400, color=PAPER, family=FONT_HEADLINE)
        self.text(frame_id, "like a person handing papers.", 32, 894, size=11, weight=400, color=SAND, family=FONT_HEADLINE)


    # ========================================================================
    # FRAME 1: PAD OF SLIPS (ROSTER & PERSONAL SLIP INSPECTOR)
    # ========================================================================
    def build_frame_1_roster(self, x_offset: float = 0):
        f1 = self.add_frame("01_Pad_Of_Slips_Roster", x_offset, 0, 1440, 960, bg=PAPER, stroke=INK, stroke_weight=2)
        self.draw_desktop_shell(f1, active_nav_idx=0, window_subtitle="01 / Pad of Slips (Spreadsheet Ingestion)", dark_mode=False)

        # Subtle background stub pattern along far right margin
        self.draw_background_stub_pattern(f1, 1404, 48, 900, dark_mode=False)

        # Top Workspace Header (x=276, y=58)
        self.text(f1, "Pad of Slips — Comp 304: Compiler Design", 276, 58, size=26, weight=700, color=INK, family=FONT_HEADLINE)
        self.text(f1, "Each spreadsheet row is a perforated grade slip, torn off and handed to one student at a human pace.", 276, 92, size=13, weight=400, color=FOG, family=FONT_BODY)

        # Action buttons top right
        self.rect(f1, 956, 60, 196, 42, fill=PAPER_2, stroke=INK, weight=1.5, radius=8, name="Btn_LoadSheet")
        self.text(f1, "Open CSV / .xlsx Pad...", 978, 73, size=13, weight=600, color=INK, family=FONT_BODY)

        self.card(f1, 1166, 60, 224, 42, fill=NILE, stroke=INK, weight=1.5, radius=8, shadow_color=INK, shadow_offset=3, name="Btn_StartHandout")
        self.text(f1, "Hand Out 48 Slips (5–12s)", 1188, 73, size=13, weight=700, color=PAPER, family=FONT_BODY)

        # Ingestion & Schema Bar (y=124)
        self.rect(f1, 276, 124, 1114, 46, fill=PAPER_2, stroke=PAPER_3, weight=1, radius=8, name="Schema_Bar")
        self.text(f1, "LOADED FILE:", 294, 140, size=11, weight=700, color=NILE, family=FONT_MONO)
        self.text(f1, "data/students_sample.xlsx (Sheet: Grades)", 384, 140, size=12, weight=600, color=INK, family=FONT_MONO)
        self.text(f1, "|  BILINGUAL ALIASES MAPPED:", 680, 140, size=11, weight=700, color=FOG, family=FONT_MONO)
        for bx, btxt in [(878, "كود الطالب → ID"), (1000, "الاسم → Name"), (1112, "الموبايل → E.164"), (1248, "أعمال سنة → Scores")]:
            self.rect(f1, bx, 133, 118 if "Scores" in btxt else 104, 28, fill=CREAM, stroke=PAPER_3, weight=1, radius=5)
            self.text(f1, btxt, bx + 8, 141, size=10, weight=600, color=INK, family=FONT_MONO)

        # --------------------------------------------------------------------
        # LEFT COLUMN: THE PAD OF SLIPS (x=276, y=188, w=686, h=744)
        # --------------------------------------------------------------------
        self.card(f1, 276, 188, 686, 744, fill=CREAM, stroke=INK, weight=1.5, radius=10, shadow_color=PAPER_3, shadow_offset=4, name="Pad_Table_Container")

        # Table Header (Ink bar)
        self.rect(f1, 276, 188, 686, 44, fill=INK, radius=8, name="Pad_Table_Header")
        self.text(f1, "ID", 294, 203, size=11, weight=700, color=SAND, family=FONT_MONO)
        self.text(f1, "STUDENT NAME (PERSON, NOT BATCH)", 362, 203, size=11, weight=700, color=PAPER, family=FONT_MONO)
        self.text(f1, "E.164 PHONE", 588, 203, size=11, weight=700, color=PAPER, family=FONT_MONO)
        self.text(f1, "MID · LAB · ORAL", 714, 203, size=11, weight=700, color=PAPER, family=FONT_MONO)
        self.text(f1, "TOTAL", 842, 203, size=11, weight=700, color=SAND, family=FONT_MONO)
        self.text(f1, "STUB", 906, 203, size=11, weight=700, color=LAGOON, family=FONT_MONO)

        # Vertical perforation line separating the spreadsheet rows from their stub column!
        self.draw_perforation_column(f1, 894, 238, 868, step=11, dot_size=3.5, color=PAPER_3)

        students = [
            ("220769", "عبدالرحمن خالد سعد الدين", "+20 112 084 4781", "12 · 15 · 5 (+0)", "32/60", "SUCCESS", False, "Score after adding extra bonus"),
            ("220770", "Sarah Ahmed Mahmoud", "+20 101 234 5678", "14 · 35 · 8 (+2)", "59/60", "SELECTED", True, "Outstanding lab project"),
            ("220771", "Mohamed Omar Farouk", "+20 129 876 5432", "10 · 28 · 6 (+0)", "44/60", "SUCCESS", False, "Solid parser implementation"),
            ("220772", "Nour Ibrahim Youssef", "+20 155 555 4321", "13 · 32 · 7 (+1)", "53/60", "SUCCESS", False, "Excellent presentation"),
            ("220773", "Yasmine Tarek El-Sayed", "+20 109 441 8820", "15 · 34 · 8 (+0)", "57/60", "SKIPPED", False, "Clean AST & symbol table"),
            ("220774", "Omar Khaled Mansour", "+20 114 302 9911", "11 · 24 · 6 (+0)", "41/60", "FAILED", False, "Review LR(1) closure items"),
            ("220775", "Salma Mostafa Adel", "+20 122 619 0450", "14 · 33 · 7 (+1)", "55/60", "PENDING", False, "Strong lexical analyzer"),
            ("220776", "Karim Hesham Nabil", "+20 100 883 1924", "13 · 30 · 7 (+0)", "50/60", "PENDING", False, "Well-tested code generator"),
            ("220777", "Mariam Hany Soliman", "+20 155 209 7412", "15 · 36 · 8 (+1)", "60/60", "PENDING", False, "Full marks — exemplary work"),
        ]

        ry = 236
        for idx, (sid, sname, sphone, sbreak, stotal, sstatus, is_sel, snote) in enumerate(students):
            row_h = 68
            if is_sel:
                # Highlighted active slip row in Nile tint / strong border
                self.rect(f1, 282, ry, 674, row_h, fill="#E3EFEF", stroke=NILE, weight=2, radius=6, name=f"Row_Selected_{sid}")
                self.rect(f1, 282, ry, 6, row_h, fill=NILE, radius=3)
            else:
                row_bg = CREAM if idx % 2 == 0 else PAPER
                self.rect(f1, 282, ry, 674, row_h, fill=row_bg, radius=4, name=f"Row_{sid}")
                self.line(f1, 286, ry + row_h, 666, color=PAPER_2, weight=1)

            self.text(f1, sid, 294, ry + 16, size=12, weight=700, color=NILE if is_sel else INK, family=FONT_MONO)
            self.text(f1, f"Row #{idx + 1}", 294, ry + 36, size=10, weight=400, color=FOG, family=FONT_MONO)

            self.text(f1, sname, 362, ry + 14, size=14, weight=700 if is_sel else 600, color=INK, family=FONT_BODY)
            self.text(f1, f"Note: {snote}", 362, ry + 36, size=11, weight=400, color=FOG, family=FONT_BODY)

            self.text(f1, sphone, 588, ry + 16, size=11, weight=600, color=INK, family=FONT_MONO)
            self.text(f1, "WhatsApp + Email", 588, ry + 36, size=10, weight=400, color=FOG, family=FONT_BODY)

            self.text(f1, sbreak, 714, ry + 24, size=11, weight=400, color=INK, family=FONT_MONO)
            self.text(f1, stotal, 842, ry + 22, size=13, weight=700, color=NILE, family=FONT_MONO)

            # Right Stub Status Cell (x=904)
            if sstatus == "SELECTED":
                # Pointing to the right inspector where the Stamp stub is tearing off
                self.rect(f1, 904, ry + 14, 44, 24, fill=NILE, radius=5)
                self.text(f1, "OPEN", 911, ry + 20, size=9, weight=700, color=SAND, family=FONT_MONO)
                self.text(f1, "inspect →", 904, ry + 42, size=9, weight=600, color=NILE, family=FONT_MONO)
            else:
                self.draw_status_stub(f1, 904, ry + 15, sstatus, dark_mode=False)
                lbl = "Torn" if sstatus == "SUCCESS" else ("Tilted" if sstatus == "FAILED" else ("Empty" if sstatus == "SKIPPED" else "Attached"))
                self.text(f1, lbl, 904, ry + 40, size=9, weight=600, color=FOG, family=FONT_MONO)

            ry += row_h + 4

        # Table Footer Bar
        self.text(f1, "Showing rows 1–9 of 48  ·  Every row is validated with Pydantic & E.164 phone normalization before tearing.", 294, 898, size=11, weight=400, color=FOG, family=FONT_BODY)

        # --------------------------------------------------------------------
        # RIGHT COLUMN: SELECTED STUDENT SLIP INSPECTOR (x=980, y=188, w=410, h=744)
        # --------------------------------------------------------------------
        # Physical Tear-Off Grade Slip Card with Perforated Stub Column on Right
        self.card(f1, 980, 188, 352, 744, fill=CREAM, stroke=INK, weight=2, radius=14, shadow_color=INK, shadow_offset=5, name="Inspector_GradeSlip")

        # Perforation dots along right edge of the slip (x=1342)
        self.draw_perforation_column(f1, 1342, 206, 910, step=18, dot_size=4.5, color=NILE)

        # Attached stubs along x=1352 (3 attached in Nile, and 1 TORN STUB at top in STAMP #E8553D!)
        # Brand rule: "Stamp #E8553D: The one accent, once per layout (the torn stub). Graphics only, never text."
        self.rect(f1, 1358, 178, 38, 34, fill=STAMP, radius=7, rotation=14, name="ActiveSlip_TornStub_Stamp")
        for sy in (242, 290, 338):
            self.rect(f1, 1350, sy, 36, 32, fill=NILE, radius=7, name="ActiveSlip_AttachedStub")
        for sy in (386, 434, 482):
            self.rect(f1, 1350, sy, 36, 32, fill=PAPER_2, stroke=NILE, weight=1.5, radius=7, name="ActiveSlip_WaitingStub")

        # Slip Top Banner (Nile #0F4C5C)
        self.rect(f1, 980, 188, 352, 92, fill=NILE, stroke=INK, weight=2, radius=12, name="Slip_Header")
        self.text(f1, "PERSONAL GRADE SLIP  ·  ROW #2 OF 48", 1002, 206, size=10, weight=700, color=SAND, family=FONT_MONO, letter_spacing="5%")
        self.text(f1, "Sarah, your Comp 304", 1002, 224, size=19, weight=700, color=PAPER, family=FONT_HEADLINE)
        self.text(f1, "grade slip is ready.", 1002, 248, size=19, weight=700, color=PAPER, family=FONT_HEADLINE)

        # Student Identity Block
        self.text(f1, "STUDENT", 1002, 298, size=10, weight=700, color=FOG, family=FONT_MONO)
        self.text(f1, "Sarah Ahmed Mahmoud", 1002, 314, size=16, weight=700, color=INK, family=FONT_BODY)
        self.text(f1, "ID: 220770   ·   Comp 304 Compiler Design", 1002, 336, size=12, weight=400, color=FOG, family=FONT_MONO)

        self.draw_perforation_row(f1, 1002, 1310, 366, step=10, dot_size=3, color=PAPER_3)

        # Score Breakdown Grid (2x2 + Total Banner)
        self.text(f1, "SCORE BREAKDOWN (AFTER EXTRA BONUS)", 1002, 380, size=10, weight=700, color=NILE, family=FONT_MONO)

        score_boxes = [
            (1002, 400, "MIDTERM EXAM", "14", "/ 15"),
            (1162, 400, "PRACTICAL LAB", "35", "/ 37"),
            (1002, 468, "ORAL EXAM", "8", "/ 8"),
            (1162, 468, "EXTRA BONUS", "+2", "pts"),
        ]
        for bx, by, blbl, bval, bmax in score_boxes:
            self.rect(f1, bx, by, 148, 58, fill=PAPER, stroke=PAPER_3, weight=1.5, radius=8)
            self.text(f1, blbl, bx + 12, by + 10, size=10, weight=700, color=FOG, family=FONT_MONO)
            self.text(f1, bval, bx + 12, by + 27, size=20, weight=700, color=INK, family=FONT_MONO)
            self.text(f1, bmax, bx + 54, by + 33, size=12, weight=600, color=FOG, family=FONT_MONO)

        # Total Score Box
        self.rect(f1, 1002, 538, 308, 56, fill=PAPER_2, stroke=NILE, weight=2, radius=8)
        self.text(f1, "TOTAL ACCUMULATED SCORE", 1016, 551, size=10, weight=700, color=NILE, family=FONT_MONO)
        self.text(f1, "formatted_scores: 14/15, 35/37, 8/8, 59/60", 1016, 569, size=10, weight=400, color=FOG, family=FONT_MONO)
        self.text(f1, "59 / 60", 1218, 553, size=20, weight=700, color=NILE, family=FONT_MONO)

        # Instructor Note Box
        self.rect(f1, 1002, 608, 308, 62, fill=PAPER, stroke=SAND, weight=2, radius=8)
        self.text(f1, "INSTRUCTOR NOTE (student.notes)", 1016, 618, size=10, weight=700, color=INK, family=FONT_MONO)
        self.text(f1, "\"Outstanding lab project — clean AST.\"", 1016, 638, size=12, weight=600, color=INK, family=FONT_HEADLINE)

        # Delivery Channels for this slip
        self.text(f1, "HAND-OVER CHANNELS", 1002, 686, size=10, weight=700, color=FOG, family=FONT_MONO)
        self.rect(f1, 1002, 706, 308, 36, fill=PAPER, stroke=NILE, weight=1.5, radius=6)
        self.text(f1, "[x] WhatsApp   +20 101 234 5678", 1014, 717, size=12, weight=600, color=INK, family=FONT_MONO)

        self.rect(f1, 1002, 748, 308, 36, fill=PAPER, stroke=NILE, weight=1.5, radius=6)
        self.text(f1, "[x] Email      sarah.ahmed@example.com", 1014, 759, size=12, weight=600, color=INK, family=FONT_MONO)

        # Circular punch seal + Primary Tear & Hand Over CTA
        self.ellipse(f1, 1008, 804, 24, 24, fill=PAPER_2, stroke=NILE, weight=1.5, name="Slip_PunchSeal")
        self.text(f1, "Ready to tear off and hand to Sarah.", 1042, 809, size=12, weight=400, color=FOG, family=FONT_HEADLINE)

        self.card(f1, 1002, 844, 308, 48, fill=NILE, stroke=INK, weight=1.5, radius=8, shadow_color=INK, shadow_offset=3, name="Btn_TearSingleSlip")
        self.text(f1, "Tear & Hand Over Sarah's Slip", 1048, 860, size=14, weight=700, color=PAPER, family=FONT_BODY)

        self.text(f1, "Or preview rendered Jinja2 slip in Slip Composer →", 1014, 904, size=11, weight=400, color=FOG, family=FONT_BODY)


    # ========================================================================
    # FRAME 2: SLIP COMPOSER (JINJA2 TEMPLATES & EMAIL/WHATSAPP SLIP PREVIEWS)
    # ========================================================================
    def build_frame_2_composer(self, x_offset: float = 1560):
        f2 = self.add_frame("02_Slip_Composer_Studio", x_offset, 0, 1440, 960, bg=PAPER, stroke=INK, stroke_weight=2)
        self.draw_desktop_shell(f2, active_nav_idx=1, window_subtitle="02 / Slip Composer (Jinja2 Templates & Previews)", dark_mode=False)

        self.draw_background_stub_pattern(f2, 1404, 48, 900, dark_mode=False)

        # Header
        self.text(f2, "Slip Composer — Personal Notice Templates", 276, 58, size=26, weight=700, color=INK, family=FONT_HEADLINE)
        self.text(f2, "Name the person, not the batch. Render personal grade slips in WhatsApp text and responsive HTML email.", 276, 92, size=13, weight=400, color=FOG, family=FONT_BODY)

        # Student Switcher Pill in Header
        self.rect(f2, 1010, 60, 380, 44, fill=CREAM, stroke=INK, weight=1.5, radius=8)
        self.text(f2, "PREVIEWING SLIP FOR:", 1026, 70, size=9, weight=700, color=NILE, family=FONT_MONO)
        self.text(f2, "Sarah Ahmed Mahmoud (ID: 220770)   ◀  2 / 48  ▶", 1026, 84, size=12, weight=700, color=INK, family=FONT_BODY)

        # --------------------------------------------------------------------
        # LEFT PANE: JINJA2 TEMPLATE EDITOR (x=276, y=126, w=510, h=806)
        # --------------------------------------------------------------------
        self.card(f2, 276, 126, 510, 806, fill=CREAM, stroke=INK, weight=1.5, radius=10, shadow_color=PAPER_3, shadow_offset=4, name="Composer_EditorCard")

        # Template Tabs
        self.rect(f2, 292, 142, 232, 36, fill=NILE, radius=6)
        self.text(f2, "email_grade_report.html.j2", 308, 154, size=11, weight=700, color=PAPER, family=FONT_MONO)

        self.rect(f2, 532, 142, 238, 36, fill=PAPER_2, stroke=PAPER_3, weight=1, radius=6)
        self.text(f2, "wa_grade_report_styled.txt.j2", 546, 154, size=11, weight=600, color=INK, family=FONT_MONO)

        # Variable Token Chips
        self.text(f2, "AVAILABLE PYDANTIC TOKENS (CLICK TO INSERT):", 292, 194, size=10, weight=700, color=FOG, family=FONT_MONO)
        tokens = [
            (292, 214, 136, "{{ student.name }}"),
            (436, 214, 174, "{{ student.student_id }}"),
            (618, 214, 152, "{{ student.course }}"),
            (292, 246, 194, "{{ student.formatted_scores }}"),
            (494, 246, 146, "{{ student.total }}"),
            (648, 246, 122, "{{ student.notes }}"),
        ]
        for tx, ty, w_chip, tlabel in tokens:
            self.rect(f2, tx, ty, w_chip, 26, fill=PAPER, stroke=NILE, weight=1, radius=5)
            self.text(f2, tlabel, tx + 8, ty + 6, size=10, weight=600, color=NILE, family=FONT_MONO)

        # Dark Ink Code Block for Jinja2 Template (x=292, y=286, w=478, h=430)
        self.rect(f2, 292, 286, 478, 430, fill=INK, stroke=INK_3, weight=1.5, radius=8, name="Jinja_CodeEditor")
        self.rect(f2, 292, 286, 478, 32, fill=INK_2, radius=6)
        self.text(f2, "src/templates/wa_grade_report_styled.txt.j2  ·  UTF-8 (Arabic/English)", 306, 296, size=10, weight=600, color=LAGOON, family=FONT_MONO)

        code_lines = [
            ("01", "Academic Grade Slip — {{ student.course }}", PAPER),
            ("02", "--------------------------------------------", FOG),
            ("03", "{{ student.name }}, your grade slip is in.", SAND),
            ("04", "Student ID: {{ student.student_id }}", LAGOON),
            ("05", "", PAPER),
            ("06", "Score Breakdown (After Extra Bonus):", PAPER),
            ("07", "• Midterm Exam:  {{ student.midterm }} / {{ student.midterm_max|int }}", PAPER_2),
            ("08", "• Practical Lab: {{ student.lab }} / {{ student.lab_max|int }}", PAPER_2),
            ("09", "• Oral Exam:     {{ student.oral }} / {{ student.oral_max|int }}", PAPER_2),
            ("10", "{% if student.bonus > 0 %}", LAGOON),
            ("11", "• Extra Bonus:   +{{ student.bonus }} pts", SAND),
            ("12", "{% endif %}", LAGOON),
            ("13", "Total Score:     {{ student.total }} / {{ student.total_max|int }}", SAND),
            ("14", "", PAPER),
            ("15", "{% if student.notes %}", LAGOON),
            ("16", "Instructor Note: \"{{ student.notes }}\"", PAPER),
            ("17", "{% endif %}", LAGOON),
            ("18", "-- Handed over via Marsal · One slip, one student.", FOG),
        ]
        cy = 330
        for ln, ctext, ccol in code_lines:
            self.text(f2, ln, 304, cy, size=11, weight=400, color=FOG, family=FONT_MONO)
            self.text(f2, ctext, 332, cy, size=11, weight=600 if ccol in (SAND, LAGOON) else 400, color=ccol, family=FONT_MONO)
            cy += 20

        # Voice & Editorial Guidelines Check Box inside Editor
        self.rect(f2, 292, 732, 478, 182, fill=PAPER, stroke=PAPER_3, weight=1.5, radius=8)
        self.text(f2, "MARSAL VOICE & BRAND GUARDRAILS", 308, 748, size=10, weight=700, color=NILE, family=FONT_MONO, letter_spacing="5%")
        self.text(f2, "✓  Names the person ('Sarah, your Comp 304 grade is in'), never 'Bulk batch'.", 308, 772, size=12, weight=600, color=INK, family=FONT_BODY)
        self.text(f2, "✓  Email card uses Nile (#0F4C5C) headings and Paper (#F6F0E4) ground.", 308, 796, size=12, weight=600, color=INK, family=FONT_BODY)
        self.text(f2, "✓  Stamp (#E8553D) appears only once: on the torn stub mark in the footer.", 308, 820, size=12, weight=600, color=INK, family=FONT_BODY)
        self.text(f2, "✓  WhatsApp uses plain personal text — no logo images or spammy banners.", 308, 844, size=12, weight=600, color=INK, family=FONT_BODY)

        self.rect(f2, 308, 874, 210, 30, fill=NILE, radius=6)
        self.text(f2, "Save Template Changes", 336, 883, size=11, weight=700, color=PAPER, family=FONT_BODY)
        self.text(f2, "Jinja2 syntax valid · 0 warnings", 536, 884, size=11, weight=600, color=FOG, family=FONT_MONO)

        # --------------------------------------------------------------------
        # RIGHT PANE: LIVE RENDERED SLIP PREVIEWS (x=804, y=126, w=586, h=806)
        # --------------------------------------------------------------------
        # 1. EMAIL HTML GRADE SLIP PREVIEW (Following brand.md Section 7:
        # "Email templates: Nile for headings and links, Paper for the card ground, Stamp only for the mark in the footer.")
        self.card(f2, 804, 126, 586, 488, fill=CREAM, stroke=INK, weight=1.5, radius=10, shadow_color=PAPER_3, shadow_offset=4, name="Preview_EmailCard")
        self.rect(f2, 804, 126, 586, 38, fill=INK, radius=8)
        self.text(f2, "EMAIL HTML SLIP PREVIEW  ·  Subject: Sarah, your Comp 304 grade slip is ready", 822, 139, size=11, weight=700, color=PAPER, family=FONT_MONO)

        # Inner Email Paper Card
        self.rect(f2, 828, 180, 538, 414, fill=PAPER, stroke=PAPER_3, weight=1.5, radius=10, name="Email_InnerPaper")
        # Email Nile Header
        self.rect(f2, 828, 180, 538, 72, fill=NILE, radius=8)
        self.text(f2, "ACADEMIC GRADE SLIP  ·  SPRING TERM", 850, 196, size=10, weight=700, color=SAND, family=FONT_MONO, letter_spacing="6%")
        self.text(f2, "Comp 304: Compiler Design", 850, 216, size=20, weight=700, color=PAPER, family=FONT_HEADLINE)

        # Email Body Copy
        self.text(f2, "Dear Sarah Ahmed Mahmoud (ID: 220770),", 850, 268, size=14, weight=700, color=NILE, family=FONT_HEADLINE)
        self.text(f2, "Your evaluation slip has been torn off the course pad and recorded below:", 850, 290, size=12, weight=400, color=FOG, family=FONT_BODY)

        # Email Score Table
        self.rect(f2, 850, 316, 494, 28, fill=PAPER_2, radius=4)
        self.text(f2, "COMPONENT", 864, 325, size=10, weight=700, color=INK, family=FONT_MONO)
        self.text(f2, "MAX", 1160, 325, size=10, weight=700, color=FOG, family=FONT_MONO)
        self.text(f2, "OBTAINED", 1260, 325, size=10, weight=700, color=NILE, family=FONT_MONO)

        email_rows = [
            ("Midterm Examination", "15", "14"),
            ("Practical Lab & Compiler Project", "37", "35"),
            ("Oral Examination", "8", "8"),
            ("Extra Bonus Points Added", "—", "+2"),
        ]
        ey = 350
        for rname, rmax, robt in email_rows:
            self.text(f2, rname, 864, ey, size=12, weight=600 if "+" in robt else 400, color=INK, family=FONT_BODY)
            self.text(f2, rmax, 1164, ey, size=12, weight=400, color=FOG, family=FONT_MONO)
            self.text(f2, robt, 1278, ey, size=12, weight=700, color=NILE if "+" in robt else INK, family=FONT_MONO)
            self.line(f2, 850, ey + 20, 494, color=PAPER_2, weight=1)
            ey += 25

        # Email Total Row
        self.rect(f2, 850, 454, 494, 34, fill="#E3EFEF", stroke=NILE, weight=1, radius=6)
        self.text(f2, "Total Accumulated Score", 864, 464, size=13, weight=700, color=NILE, family=FONT_BODY)
        self.text(f2, "60", 1164, 464, size=13, weight=600, color=NILE, family=FONT_MONO)
        self.text(f2, "59 / 60", 1264, 464, size=14, weight=700, color=NILE, family=FONT_MONO)

        # Instructor feedback + Footer with the ONE Stamp (#E8553D) mark in the footer!
        self.text(f2, "Instructor feedback: \"Outstanding lab project.\"", 850, 502, size=12, weight=600, color=INK, family=FONT_HEADLINE)
        self.draw_perforation_row(f2, 850, 1344, 530, step=10, dot_size=3, color=PAPER_3)

        # Mini Marsal mark in Email Footer with the ONE Stamp (#E8553D) torn stub in this frame!
        self.draw_marsal_mark(
            f2,
            x=852,
            y=542,
            scale=0.26,
            body_color=NILE,
            cutout_color=PAPER,
            torn_stub_color=STAMP,  # Brand rule: "Stamp only for the mark in the footer"
            show_dots=True,
        )
        self.text(f2, "marsal  ·  One slip, one student. Handed over personally to sarah.ahmed@example.com", 896, 554, size=11, weight=600, color=FOG, family=FONT_BODY)

        # 2. WHATSAPP PLAIN SLIP PREVIEW (No chat bubbles, no WhatsApp green! Plain typographic slip)
        self.card(f2, 804, 632, 586, 300, fill=CREAM, stroke=INK, weight=1.5, radius=10, shadow_color=PAPER_3, shadow_offset=4, name="Preview_WhatsAppSlip")
        self.rect(f2, 804, 632, 586, 36, fill=NILE, radius=8)
        self.text(f2, "WHATSAPP PERSONAL TEXT SLIP  ·  Recipient: +20 101 234 5678 (No images, plain text)", 822, 644, size=11, weight=700, color=PAPER, family=FONT_MONO)

        # Perforated right stub on the WhatsApp slip preview
        self.draw_perforation_column(f2, 1326, 682, 916, step=14, dot_size=3.5, color=PAPER_3)
        self.rect(f2, 1340, 700, 32, 26, fill=NILE, radius=6)
        self.rect(f2, 1340, 738, 32, 26, fill=PAPER_2, stroke=NILE, weight=1, radius=6)
        self.rect(f2, 1340, 776, 32, 26, fill=PAPER_2, stroke=NILE, weight=1, radius=6)

        wa_lines = [
            ("Sarah Ahmed Mahmoud, your Comp 304 grade slip is in.", 15, 700, INK, FONT_HEADLINE),
            ("Student ID: 220770   ·   Course: Comp 304 Compiler Design - Spring", 12, 600, FOG, FONT_MONO),
            ("Score after adding extra bonus (midterm, lab, oral, total):", 12, 600, NILE, FONT_BODY),
            ("14/15,  35/37,  8/8,  +2 bonus  →  Total: 59 / 60", 14, 700, INK, FONT_MONO),
            ("Instructor Note: \"Outstanding lab project\"", 12, 600, INK, FONT_BODY),
            ("One slip, one student. Sent at a human pace (every 5 to 12s).", 11, 400, FOG, FONT_HEADLINE),
        ]
        wy = 684
        for wtxt, wsz, wwt, wcol, wfam in wa_lines:
            self.text(f2, wtxt, 828, wy, size=wsz, weight=wwt, color=wcol, family=wfam)
            wy += 36


    # ========================================================================
    # FRAME 3: HAND-OUT QUEUE (DARK INK THEME — LIVE THROTTLED SENDING)
    # ========================================================================
    def build_frame_3_queue_dark(self, x_offset: float = 3120):
        """
        Showcases Marsal's Dark Ground Visual Identity:
        - Ground: Ink (#10222A)
        - Elevated surfaces & pattern: Ink 2 (#1A333D)
        - Primary brand color on dark: Lagoon (#6FC1D0)
        - Accent on dark: Sand (#F2C14E)
        - The ONE Stamp (#E8553D) accent: the active torn stub lifting away from Slip #14!
        """
        f3 = self.add_frame("03_Hand_Out_Queue_Dark", x_offset, 0, 1440, 960, bg=INK, stroke=LAGOON, stroke_weight=2)
        self.draw_desktop_shell(f3, active_nav_idx=2, window_subtitle="03 / Hand-Out Queue (Live Human-Paced Dispatch)", dark_mode=True)

        # Low-contrast Ink_2 stub column pattern on right margin (matching social banner in brand.md)
        self.draw_background_stub_pattern(f3, 1404, 48, 900, dark_mode=True)

        # Header
        self.text(f3, "Hand-Out Queue — One Slip at a Human Pace", 276, 58, size=26, weight=700, color=PAPER, family=FONT_HEADLINE)
        self.text(f3, "One message every 5 to 12 seconds, like a person handing out papers rather than a blast.", 276, 92, size=13, weight=400, color=LAGOON, family=FONT_BODY)

        # Queue Controls Top Right
        self.rect(f3, 980, 60, 180, 42, fill=INK_2, stroke=LAGOON, weight=1.5, radius=8)
        self.text(f3, "Mode: LIVE SEND", 1012, 74, size=12, weight=700, color=SAND, family=FONT_MONO)

        self.rect(f3, 1174, 60, 216, 42, fill=SAND, stroke=INK, weight=1.5, radius=8)
        self.text(f3, "Pause After Current Slip", 1200, 74, size=13, weight=700, color=INK, family=FONT_BODY)

        # --------------------------------------------------------------------
        # HERO STAGE: THE SLIP IN FLIGHT (x=276, y=126, w=1114, h=286)
        # --------------------------------------------------------------------
        self.card(f3, 276, 126, 1114, 286, fill=INK_2, stroke=LAGOON, weight=1.5, radius=12, shadow_color="#071217", shadow_offset=5, name="Hero_SlipInFlight")

        # Left side of Hero: Active Student Slip Card being torn & handed over
        self.rect(f3, 304, 152, 480, 234, fill=INK, stroke=LAGOON, weight=2, radius=12, name="Active_Flight_Slip")
        self.text(f3, "NOW HANDING OVER  ·  SLIP #14 OF 48", 328, 172, size=11, weight=700, color=SAND, family=FONT_MONO, letter_spacing="6%")
        self.text(f3, "Nour Ibrahim Youssef", 328, 196, size=24, weight=700, color=PAPER, family=FONT_HEADLINE)
        self.text(f3, "ID: 220772  ·  +20 155 555 4321  ·  nour.ibrahim@example.com", 328, 228, size=10.5, weight=400, color=LAGOON, family=FONT_MONO)

        self.rect(f3, 328, 256, 432, 54, fill=INK_2, stroke=INK_3, weight=1, radius=8)
        self.text(f3, "Comp 304 Scores:  Midterm 13/15  ·  Lab 32/37  ·  Oral 7/8  ·  Bonus +1", 344, 268, size=10.5, weight=400, color=PAPER, family=FONT_MONO)
        self.text(f3, "Total Score: 53 / 60   —   \"Excellent presentation\"", 344, 288, size=12, weight=700, color=SAND, family=FONT_MONO)

        self.text(f3, "✓ WhatsApp handed over (18:09:42)   ·   ✓ Email handed over (18:09:44)", 328, 330, size=10.5, weight=600, color=LAGOON, family=FONT_MONO)
        self.text(f3, "Logged to SQLite data/dispatches.db as SUCCESS.", 328, 352, size=11, weight=400, color=PAPER_2, family=FONT_BODY)

        # Center Visual: Large Slip & Stubs Mark showing the ONE Stamp (#E8553D) Torn Stub lifting away!
        # Brand rule: "Motion: the torn stub lifts and tilts away along a short arc, then the next stub waits."
        self.draw_marsal_mark(
            f3,
            x=826,
            y=188,
            scale=1.15,
            body_color=LAGOON,
            cutout_color=INK_2,
            torn_stub_color=STAMP,  # The ONE Stamp (#E8553D) accent in Frame 3!
            show_dots=True,
        )
        # Motion arc indicator dots showing the short lift arc
        self.ellipse(f3, 944, 210, 5, 5, fill=SAND)
        self.ellipse(f3, 952, 196, 5, 5, fill=SAND)
        self.ellipse(f3, 960, 184, 5, 5, fill=SAND)

        # Right side of Hero: Human-Pace Breathing Timer
        self.rect(f3, 1024, 152, 340, 234, fill=INK, stroke=INK_3, weight=1.5, radius=12, name="Pace_TimerBox")
        self.text(f3, "UNHURRIED HUMAN PACE", 1048, 174, size=10, weight=700, color=SAND, family=FONT_MONO, letter_spacing="6%")
        self.text(f3, "Next slip in 9.4s", 1048, 198, size=28, weight=700, color=PAPER, family=FONT_HEADLINE)
        self.text(f3, "Waiting uneven interval before Row #15", 1048, 236, size=12, weight=400, color=LAGOON, family=FONT_BODY)
        self.text(f3, "(Yasmine Tarek El-Sayed · ID 220773)", 1048, 254, size=12, weight=600, color=PAPER, family=FONT_MONO)

        # Progress bar inside Pace Box
        self.rect(f3, 1048, 286, 292, 14, fill=INK_2, stroke=INK_3, weight=1, radius=7)
        self.rect(f3, 1048, 286, 186, 14, fill=SAND, radius=7)

        self.text(f3, "Window: min 5.0s — max 12.0s", 1048, 314, size=11, weight=600, color=LAGOON, family=FONT_MONO)
        self.text(f3, "Never animate or send all stubs at once.", 1048, 336, size=11, weight=400, color=PAPER_2, family=FONT_HEADLINE)
        self.text(f3, "Uneven gaps mirror a person handing slips.", 1048, 354, size=11, weight=400, color=PAPER_2, family=FONT_HEADLINE)

        # --------------------------------------------------------------------
        # MIDDLE STRIP: UNEVEN INTERVAL RHYTHM (x=276, y=430, w=1114, h=148)
        # --------------------------------------------------------------------
        self.card(f3, 276, 430, 1114, 148, fill=INK_2, stroke=INK_3, weight=1.5, radius=10, shadow_color="#071217", shadow_offset=4, name="Rhythm_Strip")
        self.text(f3, "RANDOMIZED ANTI-BAN CADENCE (UNEVEN GAPS BETWEEN EACH STUDENT SLIP)", 300, 448, size=10, weight=700, color=LAGOON, family=FONT_MONO, letter_spacing="5%")
        self.text(f3, "Mean pace: 8.6s / slip   ·   14 of 48 slips handed over   ·   Est. 4m 52s remaining", 860, 448, size=11, weight=600, color=SAND, family=FONT_MONO)

        intervals = [
            ("#05", "7.2s", 34, LAGOON),
            ("#06", "11.4s", 56, LAGOON),
            ("#07", "6.1s", 28, LAGOON),
            ("#08", "10.8s", 52, LAGOON),
            ("#09", "8.3s", 40, LAGOON),
            ("#10", "5.4s", 24, LAGOON),
            ("#11", "11.9s", 58, LAGOON),
            ("#12", "7.8s", 37, LAGOON),
            ("#13", "6.9s", 32, LAGOON),
            ("#14", "9.4s", 46, SAND),    # Current active gap
            ("#15", "8.1s", 38, INK_3),
            ("#16", "11.2s", 54, INK_3),
            ("#17", "6.5s", 30, INK_3),
            ("#18", "10.1s", 49, INK_3),
            ("#19", "7.6s", 36, INK_3),
            ("#20", "9.8s", 47, INK_3),
        ]
        ix = 300
        for rnum, rsec, rbar_h, rcol in intervals:
            bar_y = 536 - rbar_h
            self.rect(f3, ix, bar_y, 48, rbar_h, fill=rcol, radius=4)
            self.text(f3, rsec, ix + 6, bar_y - 16, size=10, weight=700 if rcol == SAND else 400, color=SAND if rcol == SAND else PAPER_2, family=FONT_MONO)
            self.text(f3, rnum, ix + 10, 544, size=10, weight=600, color=LAGOON if rcol != INK_3 else FOG, family=FONT_MONO)
            ix += 66

        # --------------------------------------------------------------------
        # BOTTOM SPLIT: RECENTLY TORN SLIPS vs WAITING ON PAD (y=596, h=336)
        # --------------------------------------------------------------------
        # Left Box: Recently Torn & Handed Over
        self.card(f3, 276, 596, 546, 336, fill=INK_2, stroke=INK_3, weight=1.5, radius=10, shadow_color="#071217", shadow_offset=4, name="Queue_RecentTorn")
        self.text(f3, "RECENTLY HANDED OVER (STUBS TORN OFF)", 300, 616, size=11, weight=700, color=LAGOON, family=FONT_MONO)

        recent_rows = [
            ("220772", "Nour Ibrahim Youssef", "WA + Email", "Handed over · 9.4s gap", "SUCCESS"),
            ("220771", "Mohamed Omar Farouk", "WA + Email", "Handed over · 6.9s gap", "SUCCESS"),
            ("220770", "Sarah Ahmed Mahmoud", "WA + Email", "Handed over · 7.8s gap", "SUCCESS"),
            ("220769", "عبدالرحمن خالد سعد الدين", "WA + Email", "Handed over · 11.9s gap", "SUCCESS"),
            ("220768", "Hossam El-Din Magdy", "WA only", "Email skipped (empty)", "SKIPPED"),
        ]
        qy = 648
        for qid, qname, qch, qgap, qst in recent_rows:
            self.rect(f3, 296, qy, 506, 48, fill=INK, stroke=INK_3, weight=1, radius=6)
            self.text(f3, qid, 310, qy + 16, size=11, weight=700, color=SAND, family=FONT_MONO)
            self.text(f3, qname, 372, qy + 15, size=13, weight=600, color=PAPER, family=FONT_BODY)
            self.text(f3, qgap, 560, qy + 16, size=11, weight=400, color=LAGOON, family=FONT_MONO)
            self.draw_status_stub(f3, 752, qy + 14, qst, dark_mode=True)
            qy += 54

        # Right Box: Waiting on the Pad (Stubs Still Attached)
        self.card(f3, 844, 596, 546, 336, fill=INK_2, stroke=INK_3, weight=1.5, radius=10, shadow_color="#071217", shadow_offset=4, name="Queue_WaitingPad")
        self.text(f3, "NEXT ON THE PAD (STUBS STILL ATTACHED)", 868, 616, size=11, weight=700, color=SAND, family=FONT_MONO)

        waiting_rows = [
            ("220773", "Yasmine Tarek El-Sayed", "Next up in 9.4s", "57 / 60", "ATTACHED"),
            ("220774", "Omar Khaled Mansour", "Follows after ~8.1s", "41 / 60", "ATTACHED"),
            ("220775", "Salma Mostafa Adel", "Follows after ~11.2s", "55 / 60", "ATTACHED"),
            ("220776", "Karim Hesham Nabil", "Follows after ~6.5s", "50 / 60", "ATTACHED"),
            ("220777", "Mariam Hany Soliman", "Follows after ~10.1s", "60 / 60", "ATTACHED"),
        ]
        wy = 648
        for wid, wname, weta, wscore, wst in waiting_rows:
            self.rect(f3, 864, wy, 506, 48, fill=INK, stroke=INK_3, weight=1, radius=6)
            self.text(f3, wid, 878, wy + 16, size=11, weight=700, color=LAGOON, family=FONT_MONO)
            self.text(f3, wname, 940, wy + 15, size=13, weight=600, color=PAPER, family=FONT_BODY)
            self.text(f3, weta, 1132, wy + 16, size=11, weight=400, color=SAND if "9.4s" in weta else PAPER_2, family=FONT_MONO)
            # Attached stub icon
            self.ellipse(f3, 1320, wy + 18, 3.2, 3.2, fill=LAGOON)
            self.ellipse(f3, 1320, wy + 28, 3.2, 3.2, fill=LAGOON)
            self.rect(f3, 1326, wy + 15, 22, 18, fill=LAGOON, radius=4.5)
            wy += 54


    # ========================================================================
    # FRAME 4: AUDIT LEDGER (SQLite data/dispatches.db & STUB STATUS REPORT)
    # ========================================================================
    def build_frame_4_audit_ledger(self, x_offset: float = 4680):
        f4 = self.add_frame("04_Audit_Ledger_History", x_offset, 0, 1440, 960, bg=PAPER, stroke=INK, stroke_weight=2)
        self.draw_desktop_shell(f4, active_nav_idx=3, window_subtitle="04 / Audit Ledger (SQLite data/dispatches.db)", dark_mode=False)

        self.draw_background_stub_pattern(f4, 1404, 48, 900, dark_mode=False)

        # Header with plain-spoken Brand Voice (brand.md Section 6 Rule 3: "Say plainly what is recorded.")
        self.text(f4, "Audit Ledger — Every Send Recorded Plainly", 276, 58, size=26, weight=700, color=INK, family=FONT_HEADLINE)
        self.text(f4, "Every send is logged in data/dispatches.db as success, failed or skipped.", 276, 92, size=13, weight=400, color=FOG, family=FONT_BODY)

        # Top Right Actions
        self.rect(f4, 1004, 60, 180, 42, fill=PAPER_2, stroke=INK, weight=1.5, radius=8)
        self.text(f4, "Export Audit CSV", 1036, 74, size=13, weight=600, color=INK, family=FONT_BODY)

        self.card(f4, 1198, 60, 192, 42, fill=NILE, stroke=INK, weight=1.5, radius=8, shadow_color=INK, shadow_offset=3)
        self.text(f4, "Retry 4 Failed Slips", 1228, 74, size=13, weight=700, color=PAPER, family=FONT_BODY)

        # --------------------------------------------------------------------
        # 4 SUMMARY METRIC CARDS WITH STUB STATUS ICONS (y=126, h=112)
        # --------------------------------------------------------------------
        # Card 1: SUCCESS (Uses the ONE Stamp #E8553D torn stub accent in this layout!)
        self.card(f4, 276, 126, 266, 112, fill=CREAM, stroke=INK, weight=1.5, radius=10, shadow_color=PAPER_3, shadow_offset=4)
        self.text(f4, "SUCCESS (STUB TORN AWAY)", 294, 144, size=10, weight=700, color=NILE, family=FONT_MONO)
        self.text(f4, "142", 294, 166, size=34, weight=700, color=INK, family=FONT_HEADLINE)
        self.text(f4, "Slips handed over cleanly", 294, 208, size=12, weight=400, color=FOG, family=FONT_BODY)
        self.draw_status_stub(f4, 488, 162, "SUCCESS", dark_mode=False, use_stamp_accent=True)

        # Card 2: FAILED (Stub attached with small tilt)
        self.card(f4, 558, 126, 266, 112, fill=CREAM, stroke=INK, weight=1.5, radius=10, shadow_color=PAPER_3, shadow_offset=4)
        self.text(f4, "FAILED (STUB STILL ATTACHED)", 576, 144, size=10, weight=700, color=INK, family=FONT_MONO)
        self.text(f4, "4", 576, 166, size=34, weight=700, color=INK, family=FONT_HEADLINE)
        self.text(f4, "Slips waiting retry on pad", 576, 208, size=12, weight=400, color=FOG, family=FONT_BODY)
        self.draw_status_stub(f4, 772, 162, "FAILED", dark_mode=False)

        # Card 3: SKIPPED (Outlined empty stub position)
        self.card(f4, 840, 126, 266, 112, fill=CREAM, stroke=INK, weight=1.5, radius=10, shadow_color=PAPER_3, shadow_offset=4)
        self.text(f4, "SKIPPED (EMPTY STUB SLOT)", 858, 144, size=10, weight=700, color=FOG, family=FONT_MONO)
        self.text(f4, "6", 858, 166, size=34, weight=700, color=INK, family=FONT_HEADLINE)
        self.text(f4, "Missing optional email address", 858, 208, size=12, weight=400, color=FOG, family=FONT_BODY)
        self.draw_status_stub(f4, 1054, 162, "SKIPPED", dark_mode=False)

        # Card 4: HUMAN PACE SUMMARY
        self.card(f4, 1122, 126, 268, 112, fill=CREAM, stroke=INK, weight=1.5, radius=10, shadow_color=PAPER_3, shadow_offset=4)
        self.text(f4, "RECORDED HUMAN PACE", 1140, 144, size=10, weight=700, color=NILE, family=FONT_MONO)
        self.text(f4, "8.6s", 1140, 166, size=34, weight=700, color=NILE, family=FONT_HEADLINE)
        self.text(f4, "Uneven gap (5.0s to 12.0s)", 1140, 208, size=12, weight=400, color=FOG, family=FONT_BODY)

        # Filter Bar (y=254)
        self.rect(f4, 276, 254, 1114, 44, fill=PAPER_2, stroke=PAPER_3, weight=1, radius=8)
        self.text(f4, "FILTER CHANNEL:", 294, 270, size=10, weight=700, color=FOG, family=FONT_MONO)
        self.rect(f4, 404, 262, 58, 28, fill=NILE, radius=5)
        self.text(f4, "ALL", 422, 270, size=10, weight=700, color=PAPER, family=FONT_MONO)
        self.rect(f4, 468, 262, 92, 28, fill=CREAM, stroke=PAPER_3, weight=1, radius=5)
        self.text(f4, "WHATSAPP", 482, 270, size=10, weight=600, color=INK, family=FONT_MONO)
        self.rect(f4, 566, 262, 68, 28, fill=CREAM, stroke=PAPER_3, weight=1, radius=5)
        self.text(f4, "EMAIL", 582, 270, size=10, weight=600, color=INK, family=FONT_MONO)

        self.text(f4, "STATUS:", 660, 270, size=10, weight=700, color=FOG, family=FONT_MONO)
        self.rect(f4, 720, 262, 250, 28, fill=CREAM, stroke=PAPER_3, weight=1, radius=5)
        self.text(f4, "All (Success · Failed · Skipped)", 734, 270, size=10, weight=600, color=INK, family=FONT_MONO)

        self.rect(f4, 990, 262, 384, 28, fill=CREAM, stroke=PAPER_3, weight=1, radius=5)
        self.text(f4, "Search student name, ID (e.g. 220770), or phone...", 1004, 270, size=11, weight=400, color=FOG, family=FONT_BODY)

        # --------------------------------------------------------------------
        # AUDIT DATA GRID (x=276, y=312, w=1114, h=620)
        # --------------------------------------------------------------------
        self.card(f4, 276, 312, 1114, 620, fill=CREAM, stroke=INK, weight=1.5, radius=10, shadow_color=PAPER_3, shadow_offset=4, name="Audit_TableCard")

        self.rect(f4, 276, 312, 1114, 42, fill=INK, radius=8)
        self.text(f4, "LOG #", 294, 327, size=11, weight=700, color=SAND, family=FONT_MONO)
        self.text(f4, "TIMESTAMP", 360, 327, size=11, weight=700, color=PAPER, family=FONT_MONO)
        self.text(f4, "STUDENT (NAME & ID)", 518, 327, size=11, weight=700, color=PAPER, family=FONT_MONO)
        self.text(f4, "CHANNEL", 764, 327, size=11, weight=700, color=PAPER, family=FONT_MONO)
        self.text(f4, "RECIPIENT", 864, 327, size=11, weight=700, color=PAPER, family=FONT_MONO)
        self.text(f4, "STUB STATUS", 1072, 327, size=11, weight=700, color=SAND, family=FONT_MONO)
        self.text(f4, "PLAIN AUDIT RECORD", 1188, 327, size=11, weight=700, color=PAPER, family=FONT_MONO)

        self.draw_perforation_column(f4, 1058, 360, 886, step=12, dot_size=3.5, color=PAPER_3)

        audit_logs = [
            ("#152", "2026-11-05 18:09:44", "Nour Ibrahim Youssef (220772)", "EMAIL", "nour.ibrahim@example.com", "SUCCESS", "Handed over after 9.4s gap"),
            ("#151", "2026-11-05 18:09:42", "Nour Ibrahim Youssef (220772)", "WHATSAPP", "+201555554321", "SUCCESS", "Handed over via PyWhatKit"),
            ("#150", "2026-11-05 18:09:31", "Mohamed Omar Farouk (220771)", "EMAIL", "mohamed.omar@example.com", "SUCCESS", "Handed over after 6.9s gap"),
            ("#149", "2026-11-05 18:09:29", "Mohamed Omar Farouk (220771)", "WHATSAPP", "+201298765432", "SUCCESS", "Handed over via PyWhatKit"),
            ("#148", "2026-11-05 18:09:18", "Omar Khaled Mansour (220774)", "EMAIL", "omar.mansour@example.com", "FAILED", "SMTP timeout — stub still attached"),
            ("#147", "2026-11-05 18:09:07", "Yasmine Tarek El-Sayed (220773)", "EMAIL", "— (empty column)", "SKIPPED", "Skipped — no email in spreadsheet"),
            ("#146", "2026-11-05 18:09:05", "Yasmine Tarek El-Sayed (220773)", "WHATSAPP", "+201094418820", "SUCCESS", "Handed over after 11.4s gap"),
            ("#145", "2026-11-05 18:08:51", "Sarah Ahmed Mahmoud (220770)", "EMAIL", "sarah.ahmed@example.com", "SUCCESS", "Handed over after 7.8s gap"),
            ("#144", "2026-11-05 18:08:49", "Sarah Ahmed Mahmoud (220770)", "WHATSAPP", "+201012345678", "SUCCESS", "Handed over via PyWhatKit"),
            ("#143", "2026-11-05 18:08:36", "عبدالرحمن خالد سعد الدين (220769)", "WHATSAPP", "+201120844781", "SUCCESS", "Handed over after 11.9s gap"),
        ]

        ay = 358
        for idx, (lid, lts, lstud, lch, lrec, lst, lmsg) in enumerate(audit_logs):
            rh = 52
            bg_c = CREAM if idx % 2 == 0 else PAPER
            if lst == "FAILED":
                bg_c = "#F9EFEA"
            self.rect(f4, 282, ay, 1102, rh, fill=bg_c, radius=4)
            self.line(f4, 286, ay + rh, 1094, color=PAPER_2, weight=1)

            self.text(f4, lid, 294, ay + 18, size=11, weight=700, color=FOG, family=FONT_MONO)
            self.text(f4, lts, 360, ay + 18, size=11, weight=400, color=INK, family=FONT_MONO)
            self.text(f4, lstud, 518, ay + 17, size=12, weight=700, color=INK, family=FONT_BODY)

            # Channel pill
            ch_bg = NILE if lch == "WHATSAPP" else PAPER_2
            ch_fg = PAPER if lch == "WHATSAPP" else INK
            self.rect(f4, 764, ay + 13, 82, 24, fill=ch_bg, radius=5)
            self.text(f4, lch, 774, ay + 19, size=10, weight=700, color=ch_fg, family=FONT_MONO)

            self.text(f4, lrec, 864, ay + 18, size=11, weight=400, color=INK if "empty" not in lrec else FOG, family=FONT_MONO)

            # Stub Status Icon + Label
            self.draw_status_stub(f4, 1072, ay + 16, lst, dark_mode=False)
            self.text(f4, lst, 1112, ay + 19, size=10, weight=700, color=NILE if lst == "SUCCESS" else (INK if lst == "FAILED" else FOG), family=FONT_MONO)

            self.text(f4, lmsg, 1188, ay + 18, size=11, weight=400, color=INK if lst == "FAILED" else FOG, family=FONT_BODY)
            ay += rh

        self.text(f4, "SQLite Audit Table: dispatches (id, timestamp, student_id, student_name, channel, recipient, status, error_message)", 294, 898, size=11, weight=400, color=FOG, family=FONT_MONO)


    # ========================================================================
    # FRAME 5: CHANNEL & PACE SETUP (+ BUILT-IN VISUAL IDENTITY SPEC)
    # ========================================================================
    def build_frame_5_setup_and_brand(self, x_offset: float = 6240):
        f5 = self.add_frame("05_Channel_And_Pace_Setup", x_offset, 0, 1440, 960, bg=PAPER, stroke=INK, stroke_weight=2)
        self.draw_desktop_shell(f5, active_nav_idx=4, window_subtitle="05 / Channel & Pace Setup (.env & Identity System)", dark_mode=False)

        self.draw_background_stub_pattern(f5, 1404, 48, 900, dark_mode=False)

        # Header
        self.text(f5, "Channel & Pace Setup — Unhurried & Dependable", 276, 58, size=26, weight=700, color=INK, family=FONT_HEADLINE)
        self.text(f5, "Configure human-paced throttling, WhatsApp & SMTP providers, and inspect Marsal's stub status system.", 276, 92, size=13, weight=400, color=FOG, family=FONT_BODY)

        self.card(f5, 1154, 60, 236, 42, fill=NILE, stroke=INK, weight=1.5, radius=8, shadow_color=INK, shadow_offset=3)
        self.text(f5, "Test All Channels (--channel all)", 1172, 74, size=12, weight=700, color=PAPER, family=FONT_BODY)

        # --------------------------------------------------------------------
        # COLUMN 1: HUMAN PACE & ANTI-BAN THROTTLING (x=276, y=126, w=356, h=806)
        # --------------------------------------------------------------------
        self.card(f5, 276, 126, 356, 806, fill=CREAM, stroke=INK, weight=1.5, radius=10, shadow_color=PAPER_3, shadow_offset=4, name="Setup_Col1_Pace")
        self.rect(f5, 276, 126, 356, 42, fill=NILE, radius=8)
        self.text(f5, "1. HUMAN PACE & THROTTLING", 294, 141, size=11, weight=700, color=PAPER, family=FONT_MONO, letter_spacing="5%")

        self.text(f5, "One message every 5 to 12 seconds,", 296, 188, size=18, weight=700, color=INK, family=FONT_HEADLINE)
        self.text(f5, "like a person would.", 296, 212, size=18, weight=700, color=NILE, family=FONT_HEADLINE)
        self.text(f5, "Marsal releases slips through a throttled queue with uneven gaps so sending feels personal and protects accounts from rate bans.", 296, 242, size=12, weight=400, color=FOG, family=FONT_BODY, width=316)

        # Min / Max Delay Controls
        self.rect(f5, 296, 310, 150, 74, fill=PAPER, stroke=INK, weight=1.5, radius=8)
        self.text(f5, "MIN_DELAY_SECONDS", 308, 322, size=9, weight=700, color=FOG, family=FONT_MONO)
        self.text(f5, "5.0 s", 308, 344, size=24, weight=700, color=NILE, family=FONT_MONO)

        self.rect(f5, 462, 310, 150, 74, fill=PAPER, stroke=INK, weight=1.5, radius=8)
        self.text(f5, "MAX_DELAY_SECONDS", 474, 322, size=9, weight=700, color=FOG, family=FONT_MONO)
        self.text(f5, "12.0 s", 474, 344, size=24, weight=700, color=NILE, family=FONT_MONO)

        # Visual Range Slider
        self.text(f5, "RANDOMIZED DELAY WINDOW (5.0s – 12.0s)", 296, 404, size=10, weight=700, color=FOG, family=FONT_MONO)
        self.rect(f5, 296, 426, 316, 12, fill=PAPER_2, stroke=PAPER_3, weight=1, radius=6)
        self.rect(f5, 360, 426, 148, 12, fill=NILE, radius=6)
        self.ellipse(f5, 352, 421, 22, 22, fill=SAND, stroke=INK, weight=1.5)
        self.ellipse(f5, 498, 421, 22, 22, fill=SAND, stroke=INK, weight=1.5)

        # Dry-Run Safety Mode Box
        self.rect(f5, 296, 464, 316, 86, fill=PAPER, stroke=NILE, weight=1.5, radius=8)
        self.text(f5, "DRY-RUN SAFETY MODE (--dry-run)", 312, 480, size=11, weight=700, color=NILE, family=FONT_MONO)
        self.text(f5, "Simulates tearing & handing over all 48 slips and logs to SQLite without live transmission.", 312, 500, size=11, weight=400, color=FOG, family=FONT_BODY, width=284)

        # E.164 Phone Normalization Box
        self.rect(f5, 296, 568, 316, 134, fill=PAPER, stroke=PAPER_3, weight=1.5, radius=8)
        self.text(f5, "E.164 PHONE NORMALIZER (src/utils/phone.py)", 312, 584, size=10, weight=700, color=INK, family=FONT_MONO)
        self.text(f5, "Default Region: Egypt (EG +20)", 312, 606, size=12, weight=700, color=NILE, family=FONT_BODY)
        self.text(f5, "• 01120844781    →  +201120844781", 312, 630, size=11, weight=600, color=INK, family=FONT_MONO)
        self.text(f5, "• 1012345678     →  +201012345678", 312, 650, size=11, weight=600, color=INK, family=FONT_MONO)
        self.text(f5, "• +20 155 555... →  +201555554321", 312, 670, size=11, weight=600, color=INK, family=FONT_MONO)

        # Security Note
        self.rect(f5, 296, 720, 316, 190, fill=INK, radius=8)
        self.text(f5, "CREDENTIAL VAULT (.env)", 312, 738, size=10, weight=700, color=SAND, family=FONT_MONO, letter_spacing="5%")
        self.text(f5, "All SMTP App Passwords and Meta Cloud tokens are isolated in .env (git-ignored).", 312, 760, size=12, weight=400, color=PAPER, family=FONT_BODY, width=284)
        self.text(f5, "DB_PATH = data/dispatches.db", 312, 814, size=11, weight=600, color=LAGOON, family=FONT_MONO)
        self.text(f5, "WA_PROVIDER = pywhatkit", 312, 836, size=11, weight=600, color=LAGOON, family=FONT_MONO)
        self.text(f5, "SMTP_USE_TLS = true", 312, 858, size=11, weight=600, color=LAGOON, family=FONT_MONO)

        # --------------------------------------------------------------------
        # COLUMN 2: WHATSAPP & EMAIL DELIVERY PROVIDERS (x=652, y=126, w=356, h=806)
        # --------------------------------------------------------------------
        self.card(f5, 652, 126, 356, 806, fill=CREAM, stroke=INK, weight=1.5, radius=10, shadow_color=PAPER_3, shadow_offset=4, name="Setup_Col2_Providers")
        self.rect(f5, 652, 126, 356, 42, fill=NILE, radius=8)
        self.text(f5, "2. DELIVERY CHANNELS (WA & SMTP)", 670, 141, size=11, weight=700, color=PAPER, family=FONT_MONO, letter_spacing="5%")

        # WhatsApp Provider Section
        self.text(f5, "WHATSAPP PROVIDER (WA_PROVIDER)", 672, 186, size=10, weight=700, color=FOG, family=FONT_MONO)

        wa_opts = [
            ("pywhatkit", "PyWhatKit Web Automation", "Uses logged-in browser session with human pace", True),
            ("meta", "Meta WhatsApp Cloud API", "Direct Graph API v19.0 webhook & token dispatch", False),
            ("mock", "Mock Provider (Dry-Run)", "Zero network traffic; tests local template & DB", False),
        ]
        wy = 208
        for wkey, wtitle, wdesc, wsel in wa_opts:
            self.rect(f5, 672, wy, 316, 68, fill="#E3EFEF" if wsel else PAPER, stroke=NILE if wsel else PAPER_3, weight=2 if wsel else 1, radius=8)
            self.ellipse(f5, 688, wy + 24, 16, 16, fill=NILE if wsel else PAPER, stroke=NILE, weight=2)
            if wsel:
                self.ellipse(f5, 693, wy + 29, 6, 6, fill=SAND)
            self.text(f5, f"{wtitle} ({wkey})", 716, wy + 16, size=13, weight=700, color=INK, family=FONT_BODY)
            self.text(f5, wdesc, 716, wy + 38, size=11, weight=400, color=FOG, family=FONT_BODY)
            wy += 78

        self.draw_perforation_row(f5, 672, 988, 454, step=10, dot_size=3, color=PAPER_3)

        # SMTP Email Section
        self.text(f5, "EMAIL SMTP TLS CONFIGURATION", 672, 472, size=10, weight=700, color=FOG, family=FONT_MONO)

        smtp_fields = [
            ("SMTP_HOST : PORT", "smtp.gmail.com : 587 (STARTTLS)"),
            ("SMTP_FROM_NAME", "Student Academic Portal — Marsal"),
            ("SMTP_FROM_EMAIL", "academic.portal@university.edu.eg"),
            ("SMTP_PASSWORD", "•••• •••• •••• •••• (16-char Google App Pass)"),
        ]
        sfy = 494
        for flbl, fval in smtp_fields:
            self.rect(f5, 672, sfy, 316, 54, fill=PAPER, stroke=PAPER_3, weight=1, radius=6)
            self.text(f5, flbl, 686, sfy + 10, size=9, weight=700, color=FOG, family=FONT_MONO)
            self.text(f5, fval, 686, sfy + 28, size=12, weight=600, color=INK, family=FONT_MONO)
            sfy += 62

        # Connection Test Output Box
        self.rect(f5, 672, 750, 316, 160, fill=PAPER_2, stroke=NILE, weight=1.5, radius=8)
        self.text(f5, "LAST CONNECTIVITY CHECK", 688, 766, size=10, weight=700, color=NILE, family=FONT_MONO)
        self.text(f5, "[OK] SMTP Email Service:", 688, 792, size=11, weight=700, color=NILE, family=FONT_MONO)
        self.text(f5, "TLS handshake verified with smtp.gmail.com:587", 688, 810, size=11, weight=400, color=INK, family=FONT_BODY)
        self.text(f5, "[OK] WhatsApp Provider (pywhatkit):", 688, 840, size=11, weight=700, color=NILE, family=FONT_MONO)
        self.text(f5, "Web session ready · Anti-ban delay 5.0s–12.0s", 688, 858, size=11, weight=400, color=INK, family=FONT_BODY)

        # --------------------------------------------------------------------
        # COLUMN 3: MARSAL VISUAL IDENTITY & STUB LEGEND (x=1028, y=126, w=362, h=806)
        # --------------------------------------------------------------------
        self.card(f5, 1028, 126, 362, 806, fill=CREAM, stroke=INK, weight=1.5, radius=10, shadow_color=PAPER_3, shadow_offset=4, name="Setup_Col3_BrandSpec")
        self.rect(f5, 1028, 126, 362, 42, fill=INK, radius=8)
        self.text(f5, "3. MARSAL VISUAL IDENTITY & STUB LEGEND", 1046, 141, size=11, weight=700, color=SAND, family=FONT_MONO, letter_spacing="4%")

        # Brand Mark Preview Card on Paper (with the ONE Stamp #E8553D torn stub in Frame 5!)
        self.rect(f5, 1048, 184, 322, 114, fill=PAPER, stroke=PAPER_3, weight=1.5, radius=8)
        self.draw_marsal_mark(
            f5,
            x=1068,
            y=204,
            scale=0.58,
            body_color=NILE,
            cutout_color=PAPER,
            torn_stub_color=STAMP,  # The ONE Stamp (#E8553D) accent in Frame 5!
            show_dots=True,
        )
        self.draw_marsal_wordmark(f5, x=1164, y=214, width=124, color=INK)
        self.text(f5, "One slip, one student.", 1166, 258, size=13, weight=700, color=NILE, family=FONT_HEADLINE)

        # Status Stub Unit Legend (brand.md Section 5)
        self.text(f5, "STATUS ICONS (A STUB IS THE UNIT)", 1048, 316, size=10, weight=700, color=FOG, family=FONT_MONO)

        stub_legend = [
            ("SUCCESS", "Stub torn away from perforation", "SUCCESS"),
            ("FAILED", "Stub still attached with a small tilt", "FAILED"),
            ("SKIPPED", "Outlined, empty stub position", "SKIPPED"),
        ]
        sly = 338
        for sname, sdesc, scode in stub_legend:
            self.rect(f5, 1048, sly, 322, 48, fill=PAPER, stroke=PAPER_3, weight=1, radius=6)
            self.draw_status_stub(f5, 1064, sly + 15, scode, dark_mode=False)
            self.text(f5, sname, 1114, sly + 10, size=11, weight=700, color=INK, family=FONT_MONO)
            self.text(f5, sdesc, 1114, sly + 27, size=11, weight=400, color=FOG, family=FONT_BODY)
            sly += 56

        # Official Color System Swatches (brand.md Section 3)
        self.text(f5, "COLOR PALETTE & CONTRAST (60 / 30 / 10)", 1048, 518, size=10, weight=700, color=FOG, family=FONT_MONO)

        swatches = [
            (NILE, "Nile", "#0F4C5C", "Primary brand · 8.38:1 on Paper", PAPER),
            (STAMP, "Stamp", "#E8553D", "Torn stub accent once/layout (graphics only)", PAPER),
            (SAND, "Sand", "#F2C14E", "Accent on Nile (5.67:1) & on Ink", INK),
            (LAGOON, "Lagoon", "#6FC1D0", "Nile for dark Ink grounds (7.95:1)", INK),
            (INK, "Ink", "#10222A", "Primary text & dark ground (14.41:1)", PAPER),
            (PAPER, "Paper", "#F6F0E4", "Warm light slip ground (60% surface)", INK),
            (FOG, "Fog", "#51636B", "Secondary metadata text (5.53:1)", PAPER),
        ]
        swy = 540
        for scol, sname, shex, srole, stxt in swatches:
            self.rect(f5, 1048, swy, 322, 46, fill=PAPER, stroke=PAPER_3, weight=1, radius=6)
            self.rect(f5, 1056, swy + 7, 68, 32, fill=scol, stroke=INK if scol == PAPER else None, weight=1, radius=5)
            self.text(f5, sname, 1066, swy + 16, size=11, weight=700, color=stxt, family=FONT_BODY)
            self.text(f5, shex, 1136, swy + 9, size=11, weight=700, color=INK, family=FONT_MONO)
            self.text(f5, srole, 1136, swy + 25, size=10, weight=400, color=FOG, family=FONT_BODY)
            swy += 52

    # ========================================================================
    # BUILD & EXPORT PIPELINE
    # ========================================================================
    def build_all(self, output_figcraft_path: Path, export_dir: Path):
        # Multi-frame horizontal layout: FrameWidth = 1440, Gutter = 120 -> step = 1560
        self.build_frame_1_roster(x_offset=0)
        self.build_frame_2_composer(x_offset=1560)
        self.build_frame_3_queue_dark(x_offset=3120)
        self.build_frame_4_audit_ledger(x_offset=4680)
        self.build_frame_5_setup_and_brand(x_offset=6240)

        output_figcraft_path.parent.mkdir(parents=True, exist_ok=True)
        export_dir.mkdir(parents=True, exist_ok=True)

        script_path = output_figcraft_path.parent / "marsal_desktop_ui_commands.json"
        script_path.write_text(json.dumps(self.commands, indent=2), encoding="utf-8")

        print(f"[1/4] Executing FigCraft headless engine ({len(self.commands)} commands)...")
        subprocess.run([CLI_PATH, "run", str(script_path), "--out", str(output_figcraft_path)], check=True)

        print("[2/4] Auditing structural metadata with figcraft-cli info --json...")
        subprocess.run([CLI_PATH, "info", str(output_figcraft_path), "--json"], check=True)

        print("[3/4] Exporting 2x high-resolution PNG frames...")
        subprocess.run([CLI_PATH, "export", str(output_figcraft_path), "-o", str(export_dir), "--format", "png", "--scale", "2"], check=True)

        print("[4/4] Exporting vector SVG and PDF documents...")
        subprocess.run([CLI_PATH, "export", str(output_figcraft_path), "-o", str(export_dir / "marsal_desktop_ui_canvas.svg"), "--format", "svg"], check=True)
        subprocess.run([CLI_PATH, "export", str(output_figcraft_path), "-o", str(export_dir / "marsal_desktop_ui_canvas.pdf"), "--format", "pdf"], check=True)


if __name__ == "__main__":
    base_dir = Path(r"D:\projects\marsal\design")
    figcraft_file = base_dir / "marsal_desktop_ui.figcraft"
    exports_folder = base_dir / "exports"

    builder = MarsalFigCraftBuilder()
    builder.build_all(figcraft_file, exports_folder)
