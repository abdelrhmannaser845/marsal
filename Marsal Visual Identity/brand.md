# Marsal: Brand Guidelines

> One slip, one student.

Marsal (مرسال, "messenger") turns a spreadsheet of grades, attendance and notices into a personal message for each student, sent one by one over WhatsApp and email.

*"Marsal" is a working name, chosen because the README had none. Swap the wordmark if the project is named differently; the mark does not depend on it.*

## 1. Brand idea

A spreadsheet is a pad of slips: each row is torn off and handed to one person, at a human pace. That is literally how the tool works. It reads rows, renders one personal notice per student, and releases them through a throttled queue with uneven gaps, so the sending feels like a person handing out papers rather than a blast.

The mark is a grade slip with a perforated stub column. Three stubs are still attached and one has been torn off and tilts away in the accent color. The feel is dependable, personal and unhurried. It is not corporate, not spammy and not flashy, so the README's "enterprise-ready" language is not carried into the visuals. Envelopes, speech bubbles, paper planes and WhatsApp green are deliberately avoided.

## 2. Logo

| File | Use |
|---|---|
| `logo/marsal-mark.svg` | Mark alone, light backgrounds |
| `logo/marsal-mark-on-dark.svg` | Mark alone, dark backgrounds |
| `logo/marsal-mark-mono-ink.svg` / `-mono-white.svg` | One-color uses (stamps, print, terminals) |
| `logo/marsal-logo.svg` / `-on-paper.svg` / `-on-dark.svg` | Horizontal lockups |
| `logo/marsal-app-icon.svg` | App icon, repo avatar, favicon |
| `logo/marsal.ico` | Multi-size icon, 16 to 256 px (shortcuts, docs favicon) |
| `social/marsal-social-banner.png` | GitHub social preview, 1280×640 |
| `social/marsal-readme-header.png` | README header, 1600×400 (paper ground baked in) |

PNG exports are included. Text in the SVGs is converted to outlines, so no font is needed to open them.

**Clear space:** at least the width of one stub (about a quarter of the slip's width) on every side of the mark, measured including the torn stub.
**Minimum size:** mark 20 px high, lockup 120 px wide. Below 24 px use the app icon, which drops the perforation dots.

**Don't:**
- Move the torn stub back into the column, or put it anywhere but upper right.
- Recolor the torn stub: it is Stamp on light and dark grounds, Sand inside the Nile app icon, and the same flat color in one-color versions.
- Stretch, outline, add shadows or gradients, or set the wordmark in uppercase.
- Show a second torn stub. One is the idea.

## 3. Color

| Name | Hex | Role |
|---|---|---|
| Nile | `#0F4C5C` | Primary brand color, app icon tile |
| Stamp | `#E8553D` | The one accent, once per layout (the torn stub). Graphics only, never text |
| Sand | `#F2C14E` | Accent on Nile and on Ink (torn stub in the icon, tagline on dark) |
| Lagoon | `#6FC1D0` | Nile for dark backgrounds |
| Ink | `#10222A` | Text and dark ground |
| Paper | `#F6F0E4` | Light ground |
| Fog | `#51636B` | Secondary text |

Proportions: about 60% Paper or Ink, 30% Nile or Lagoon, 10% accent.

Contrast checks: Nile on Paper 8.38:1, Lagoon on Ink 7.95:1, Sand on Nile 5.67:1, Fog on Paper 5.53:1, Paper on Nile 8.38:1, Ink on Paper 14.41:1. Stamp on Paper is 3.19:1 and on Ink 4.51:1, so it is for graphics only. Stamp on Nile fails (2.63:1): use Sand there.

## 4. Typography

- **Fraunces SemiBold:** wordmark and headlines (lowercase wordmark, tracking about -2.5%, soft optical settings).
- **DM Sans:** body text and interface.
- Fallback: system serif for headlines, system sans-serif for body. Both fonts are free on Google Fonts. Use a monospace only inside code blocks and CLI output.
- Arabic: pair with Cairo or IBM Plex Sans Arabic for body text. An Arabic wordmark (مرسال) is not included yet; see Next steps.

## 5. Motion, pattern and icons

**Motion:** the torn stub lifts and tilts away along a short arc, then the next stub waits. Intervals are uneven on purpose and mirror the tool's randomized delays. Never animate all stubs at once.

**Pattern:** a column of rounded stubs with perforation dots, repeated as a divider or border. Use it as a low-contrast background (Ink 2 `#1A333D` on Ink, Paper 2 `#EAE2D1` on Paper), as in the social banner.

**Status icons (CLI, docs, reports):** a stub is the unit. SUCCESS is a stub torn away; FAILED is a stub still attached with a small tilt; SKIPPED is an outlined, empty stub position. Use flat fills, 6-unit corner radius on a 27-unit stub, no gradients.

**Imagery:** documents and hands, never inboxes or chat bubbles. Warm paper textures are fine; avoid stock "students with laptops".

## 6. Voice

1. **Name the person, not the batch.**
   Yes: "Sara, your Physics lab grade is in." No: "Bulk notification processed."
2. **Describe the pace, don't boast about speed.**
   Yes: "One message every 5 to 12 seconds, like a person would." No: "Blazing-fast mass messaging."
3. **Say plainly what is recorded.**
   Yes: "Every send is logged as success, failed or skipped." No: "Enterprise-grade audit intelligence."

Taglines considered: **One slip, one student.** (chosen), "Every row, handed over.", "Tear one off. Hand it over."

## 7. Usage

- Repo avatar and favicon: `logo/marsal-app-icon.svg` (PNG 1024 included).
- GitHub social preview: `social/marsal-social-banner.png` (1280×640).
- README header: `social/marsal-readme-header.png`, display at 800 px wide or less.
- CLI banner: use the mono-ink or mono-white mark; terminals only need one color.
- Email templates: Nile for headings and links, Paper for the card ground, Stamp only for the mark in the footer.
- WhatsApp: no logo images. Use the tagline voice in text.
