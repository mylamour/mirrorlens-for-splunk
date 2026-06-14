"""Generate a PDF investigation report from EventBus snapshot data."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fpdf import FPDF

log = logging.getLogger(__name__)

# ── Colours ──────────────────────────────────────────────────────────────────
_BG           = (255, 255, 255)
_TEXT         = (30,  35,  45)
_SUBTEXT      = (100, 110, 130)
_ACCENT       = (0,   90,  170)
_ACCENT_LIGHT = (232, 240, 252)
_ROW_ALT      = (247, 249, 252)
_BORDER       = (205, 215, 225)
_RULE         = (185, 198, 215)
_CODE_BG      = (245, 246, 248)
_CODE_BORDER  = (185, 195, 210)
_WHITE        = (255, 255, 255)

_SEVERITY_COLOR: dict[str, tuple[int, int, int]] = {
    "CRITICAL": (176, 28,  28),
    "HIGH":     (185, 70,  15),
    "MEDIUM":   (145, 105,  0),
    "LOW":      (22,  125, 65),
    "P1":       (176, 28,  28),
    "P2":       (185, 70,  15),
    "P3":       (145, 105,  0),
}

# ── Font discovery ────────────────────────────────────────────────────────────
_UNICODE_FONT_CANDIDATES = [
    # macOS
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    # Linux — noto-cjk
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    # Linux — dejavu (no CJK but good Latin/Greek/Cyrillic)
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu-sans/DejaVuSans.ttf",
]

_MONO_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/Library/Fonts/Courier New.ttf",
]


def _find_font(candidates: list[str]) -> Path | None:
    return next((Path(p) for p in candidates if Path(p).exists()), None)


def _setup_fonts(pdf: "ReportPDF") -> tuple[str, str]:
    """Load best available Unicode body font and mono font. Returns (body, mono)."""
    body = "Helvetica"
    unicode_path = _find_font(_UNICODE_FONT_CANDIDATES)
    if unicode_path:
        try:
            pdf.add_font("UniBody", fname=str(unicode_path))
            body = "UniBody"
            log.info("PDF font: %s", unicode_path.name)
        except Exception as exc:
            log.warning("Could not load Unicode font %s: %s", unicode_path, exc)
    else:
        log.warning("No Unicode font found; non-ASCII characters may not render correctly")

    mono = "Courier"
    mono_path = _find_font(_MONO_CANDIDATES)
    if mono_path:
        try:
            pdf.add_font("UniMono", fname=str(mono_path))
            mono = "UniMono"
        except Exception:
            pass

    return body, mono


# ── PDF class ─────────────────────────────────────────────────────────────────

class ReportPDF(FPDF):
    def __init__(self) -> None:
        super().__init__(orientation="L", unit="mm", format="A4")
        self.set_margins(18, 18, 18)
        self.set_auto_page_break(True, margin=20)
        self._body = "Helvetica"
        self._mono = "Courier"

    def setup(self) -> None:
        self._body, self._mono = _setup_fonts(self)

    def _safe(self, text: str) -> str:
        """Sanitize text for Latin-1 fonts: replace unencodable chars with '?'."""
        if self._body != "Helvetica":
            return text
        return text.encode("latin-1", errors="replace").decode("latin-1")

    # fpdf2 lifecycle
    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_font(self._body, size=7)
        self.set_text_color(*_SUBTEXT)
        self.set_y(8)
        self.cell(0, 4, "MirrorLens  |  Security Investigation Report", align="L")
        self.set_y(8)
        self.cell(0, 4, f"Page {self.page_no()}", align="R")
        self.set_y(13)
        self.set_draw_color(*_RULE)
        self.set_line_width(0.2)
        self.line(18, 13, self.w - 18, 13)
        self.ln(4)

    def footer(self) -> None:
        pass

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _hbold(self, size: float) -> None:
        """Helvetica Bold — for structural labels that are always ASCII."""
        self.set_font("Helvetica", style="B", size=size)

    def section_title(self, title: str) -> None:
        self.ln(4)
        self._hbold(13)
        self.set_text_color(*_ACCENT)
        self.multi_cell(0, 8, title)
        self.set_draw_color(*_ACCENT)
        self.set_line_width(0.4)
        self.line(18, self.get_y(), self.w - 18, self.get_y())
        self.set_text_color(*_TEXT)
        self.ln(3)

    def kv_line(self, pairs: list[tuple[str, str]], sep: str = "  |  ") -> None:
        """Render a compact key: value  |  key: value line."""
        self.set_x(self.l_margin)
        self.set_font(self._body, size=8)
        parts = [f"{k}: {v}" for k, v in pairs]
        self.set_text_color(*_SUBTEXT)
        self.multi_cell(self.epw, 5, self._safe(sep.join(parts)))
        self.set_text_color(*_TEXT)

    def heading_line(self, badge: str, title: str, right_label: str = "") -> None:
        """Render '[SEVERITY]  Title' with optional right-aligned label."""
        sev = badge.strip().upper()
        r, g, b = _SEVERITY_COLOR.get(sev, _ACCENT)

        self.set_x(self.l_margin)
        # Badge (Helvetica Bold — always ASCII)
        self._hbold(9)
        self.set_text_color(r, g, b)
        badge_text = f"[{badge}]  "
        badge_w = self.get_string_width(badge_text) + 1
        self.cell(badge_w, 6, badge_text)

        # Title (UniBody — may contain Unicode)
        self.set_font(self._body, size=9)
        self.set_text_color(*_TEXT)
        right_w = 0.0
        if right_label:
            self._hbold(8)
            right_w = self.get_string_width(right_label) + 4
            self.set_font(self._body, size=9)
        avail = max(10.0, self.epw - badge_w - right_w)
        title_str = self._fit(self._safe(title), avail)
        self.cell(avail, 6, title_str)

        if right_label:
            self._hbold(8)
            self.set_text_color(*_ACCENT)
            self.cell(right_w, 6, self._safe(right_label), align="R")

        self.ln(6)
        self.set_x(self.l_margin)
        self.set_text_color(*_TEXT)

    def body_text(self, text: str, size: float = 8.5) -> None:
        self.set_x(self.l_margin)
        self.set_font(self._body, size=size)
        self.set_text_color(*_TEXT)
        self.multi_cell(self.epw, 5, self._safe(text))

    def _wrapped_line_count(self, text: str, max_w: float, size: float = 7.5) -> int:
        """Count actual wrapped lines using font metrics (no char-count guessing)."""
        self.set_font(self._body, size=size)
        total = 0
        for paragraph in text.split("\n"):
            if not paragraph:
                total += 1
                continue
            line_w = 0.0
            para_lines = 1
            for word in paragraph.split(" "):
                w = self.get_string_width(word + " ")
                if line_w + w > max_w and line_w > 0:
                    para_lines += 1
                    line_w = w
                else:
                    line_w += w
            total += para_lines
        return max(1, total)

    def code_box(self, code: str, label: str = "SPL") -> None:
        """Render a labelled monospace code block with exact height."""
        if not code:
            return
        self.ln(1)
        self._hbold(size=7.5)
        self.set_text_color(*_SUBTEXT)
        self.cell(0, 4, label + ":", new_x="LMARGIN", new_y="NEXT")

        text_w = self.epw - 4   # 3 mm accent bar + 1 mm gap
        line_h = 4.5

        # Page-break guard (estimated)
        est_lines = self._wrapped_line_count(code, text_w)
        if self.get_y() + est_lines * line_h + 4 > self.h - 22:
            self.add_page()

        x0, y0 = self.l_margin, self.get_y()
        page0 = self.page

        # ── Step 1: draw text with per-line fill so height is always exact ──
        self.set_xy(x0 + 3, y0 + 2)
        self.set_font(self._body, size=7.5)
        self.set_text_color(*_TEXT)
        self.set_fill_color(*_CODE_BG)
        # multi_cell fill=True fills background cell-by-cell — no over-estimation
        self.multi_cell(text_w, line_h, self._safe(code), fill=True)
        y1 = self.get_y() + 2      # 2 mm bottom padding

        # ── Step 2: border + left accent bar — only when still on the same page ─
        if self.page == page0:
            actual_h = y1 - y0
            self.set_draw_color(*_CODE_BORDER)
            self.set_line_width(0.2)
            self.rect(x0, y0, self.epw, actual_h, "D")   # stroke only
            self.set_fill_color(*_ACCENT)
            self.rect(x0, y0, 1.5, actual_h, "F")        # accent bar covers left gap

        self.set_y(y1 + 2)

    def divider(self, thin: bool = False) -> None:
        self.ln(2)
        self.set_draw_color(*(_RULE if thin else _BORDER))
        self.set_line_width(0.15 if thin else 0.25)
        self.line(18, self.get_y(), self.w - 18, self.get_y())
        self.ln(3)

    def ensure_space(self, mm: float) -> None:
        if self.get_y() > self.h - 20 - mm:
            self.add_page()

    def _fit(self, text: str, max_w: float, font: str | None = None, size: float = 9) -> str:
        if font:
            self.set_font(font, size=size)
        s = str(text or "")
        while s and self.get_string_width(s) > max_w:
            s = s[:-1]
        if len(s) < len(str(text or "")):
            s = s[:-3] + "..." if len(s) > 3 else s
        return s


# ── Public API ────────────────────────────────────────────────────────────────

def _finding_section_label(pdf: ReportPDF, label: str) -> None:
    """Thin labelled divider used inside the finding card."""
    pdf.ln(4)
    pdf._hbold(8)
    pdf.set_text_color(*_SUBTEXT)
    pdf.cell(0, 4, label, new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*_RULE)
    pdf.set_line_width(0.15)
    pdf.line(18, pdf.get_y(), pdf.w - 18, pdf.get_y())
    pdf.ln(3)


def _truncate_words(text: str, max_chars: int) -> str:
    """Truncate at a word boundary and append ellipsis if needed."""
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0].rstrip(",;:")
    return cut + "…"


class _FindingCardPDF(ReportPDF):
    """ReportPDF subclass: no header on any page."""

    def header(self) -> None:
        pass


def generate_finding_pdf(finding: dict[str, Any], related: dict[str, Any] | None = None) -> bytes:
    """Generate a finding card PDF enriched with detection rules and response actions."""
    pdf = _FindingCardPDF()
    pdf.setup()
    pdf.set_auto_page_break(True, margin=18)
    pdf.add_page()

    # ── Page 1 branding block (content area, below the header zone) ───────────
    pdf._hbold(9)
    pdf.set_text_color(*_ACCENT)
    pdf.cell(0, 5, "MIRRORLENS", align="L", new_x="LMARGIN", new_y="NEXT")
    pdf._hbold(8)
    pdf.set_text_color(*_SUBTEXT)
    pdf.set_y(pdf.t_margin)
    pdf.cell(0, 5, "Security Finding Card", align="R")
    pdf.ln(7)
    pdf.set_draw_color(*_RULE)
    pdf.set_line_width(0.2)
    pdf.line(18, pdf.get_y(), pdf.w - 18, pdf.get_y())
    pdf.ln(5)

    # ── Finding identity ──────────────────────────────────────────────────────
    confidence = str(finding.get("confidence", "")).upper()
    tech_id    = str(finding.get("technique_id", ""))
    tech_name  = str(finding.get("technique_name", ""))
    title      = f"{tech_id}  {'--  ' + tech_name if tech_name else ''}".strip()
    pdf.heading_line(confidence or "INFO", title)

    pairs: list[tuple[str, str]] = []
    if finding.get("tactic"):
        pairs.append(("Tactic", str(finding["tactic"])))
    if finding.get("timestamp"):
        ts_raw = str(finding["timestamp"])
        # Only truncate ISO datetimes (e.g. "2026-06-13T10:23:45Z"); keep descriptive strings intact
        ts_val = ts_raw[:19] if len(ts_raw) > 19 and ts_raw[4:5] == "-" else ts_raw
        pairs.append(("Timestamp", ts_val))
    if finding.get("host"):
        pairs.append(("Host", str(finding["host"])))
    if pairs:
        pdf.kv_line(pairs)

    # ── Description ───────────────────────────────────────────────────────────
    desc = str(finding.get("description", ""))
    if desc:
        _finding_section_label(pdf, "DESCRIPTION")
        pdf.body_text(desc, size=9)

    # ── Evidence ──────────────────────────────────────────────────────────────
    evidence = str(finding.get("evidence", ""))
    if evidence:
        _finding_section_label(pdf, "EVIDENCE")
        pdf.body_text(evidence, size=8.5)

    # ── Detection Coverage ────────────────────────────────────────────────────
    rules: list[dict[str, Any]] = (related or {}).get("rules", [])
    _finding_section_label(pdf, "DETECTION COVERAGE")
    if rules:
        match_note = rules[0].get("_match", "exact")
        scope_label = (
            f"Detection rules mapped to {tech_id}, ordered by relevance to this finding."
            if match_note == "exact" and tech_id and tech_id != "N/A"
            else "Detection rules for this tactic, ordered by relevance to this finding."
        )
        pdf.set_font(pdf._body, size=7.5)
        pdf.set_text_color(*_SUBTEXT)
        pdf.cell(0, 4, scope_label, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        for rule in rules:
            rule_name  = str(rule.get("name", ""))
            rule_desc  = str(rule.get("description", ""))
            spl        = str(rule.get("spl_query", "")).strip()
            match_type = str(rule.get("_match", ""))
            match_note = "  (tactic match)" if match_type == "tactic" else ""

            pdf.ensure_space(30)
            # Rule name — use body font (supports Unicode em-dash, etc.)
            pdf.set_x(pdf.l_margin)
            pdf.set_font(pdf._body, size=9)
            pdf.set_text_color(*_ACCENT)
            pdf.multi_cell(pdf.epw, 5, pdf._safe(rule_name + match_note))
            pdf.set_text_color(*_SUBTEXT)
            if rule_desc:
                pdf.body_text(rule_desc, size=8.5)
            if spl:
                pdf.code_box(spl)
            pdf.ln(2)
    else:
        pdf.body_text("No detection rule found for this technique in the current investigation.", size=8.5)

    # ── Response Actions ──────────────────────────────────────────────────────
    actions: list[dict[str, Any]] = (related or {}).get("actions", [])
    _finding_section_label(pdf, "RESPONSE ACTIONS")
    if actions:
        for act in actions:
            raw   = str(act.get("action", ""))
            parts = raw.split(" \u2014 ", 1)
            badge = parts[0].strip().split()[0] if parts[0].strip() else "ACTION"
            body  = parts[1].strip() if len(parts) > 1 else raw
            pdf.ensure_space(18)
            pdf.heading_line(badge, "")
            pdf.body_text(body, size=8.5)
            pdf.ln(2)
    else:
        pdf.body_text("No response actions available for this finding.", size=8.5)

    # ── Page footer ───────────────────────────────────────────────────────────
    pdf.ln(6)
    pdf.set_draw_color(*_RULE)
    pdf.set_line_width(0.2)
    pdf.line(18, pdf.get_y(), pdf.w - 18, pdf.get_y())
    pdf.ln(3)
    pdf.set_font(pdf._body, size=7.5)
    pdf.set_text_color(*_SUBTEXT)
    ts = datetime.now(timezone.utc).strftime("%B %d, %Y  --  %H:%M UTC")
    pdf.cell(0, 4, f"Generated: {ts}  |  MirrorLens via Splunk MCP", align="C")

    return bytes(pdf.output())

