"""Generate a PDF investigation report from EventBus snapshot data."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fpdf import FPDF

# ── Colour palette (light / professional) ────────────────────────────────────
_BG           = (255, 255, 255)   # page background
_COVER_BG     = (15,  31,  60)    # cover page background (dark navy)
_HEADER_FILL  = (15,  31,  60)    # table header row fill
_ROW_ALT      = (245, 247, 250)   # alternating table row fill
_ACCENT       = (0,   120, 190)   # blue accent (section titles, cover title)
_CYAN_COVER   = (0,   188, 212)   # cyan used on cover only
_TEXT         = (30,  40,  60)    # body text
_SUBTEXT      = (90,  105, 130)   # secondary text
_WHITE        = (255, 255, 255)
_BORDER       = (200, 210, 220)   # light cell border

_SEVERITY_TEXT: dict[str, tuple[int, int, int]] = {
    "CRITICAL": (180, 30,  30),
    "HIGH":     (200, 80,  20),
    "MEDIUM":   (160, 120,  0),
    "LOW":      (30,  140, 80),
    "P1":       (180, 30,  30),
    "P2":       (200, 80,  20),
    "P3":       (160, 120,  0),
}

_UNICODE_MAP = str.maketrans({
    "—": "--",  "–": "-",
    "‘": "'",   "’": "'",
    "“": '"',   "”": '"',
    "…": "...", "•": "*",
    "→": "->",  "←": "<-",
    " ": " ",   "·": "*",
})


def _clean(text: str) -> str:
    s = str(text or "").translate(_UNICODE_MAP)
    return "".join(c if ord(c) < 256 else "?" for c in s)


class _PDF(FPDF):
    def __init__(self) -> None:
        super().__init__(orientation="L", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(14, 14, 14)

    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_fill_color(*_BG)
        self.rect(0, 0, self.w, 10, "F")
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*_SUBTEXT)
        self.set_y(3)
        self.cell(0, 5, "MirrorLens -- Autonomous Security Investigation Report", align="L")
        self.set_y(3)
        self.cell(0, 5, f"Page {self.page_no()}", align="R")
        self.set_y(10)
        self.set_draw_color(*_BORDER)
        self.set_line_width(0.2)
        self.line(14, 10, self.w - 14, 10)
        self.ln(3)

    def footer(self) -> None:
        pass  # page number is in header for content pages

    def section_title(self, title: str) -> None:
        self.ln(4)
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(*_ACCENT)
        self.cell(0, 9, _clean(title), ln=True)
        self.set_draw_color(*_ACCENT)
        self.set_line_width(0.5)
        self.line(14, self.get_y(), self.w - 14, self.get_y())
        self.set_text_color(*_TEXT)
        self.ln(3)

    def _fit_text(self, text: str, max_w: float) -> str:
        """Truncate text to fit within max_w mm using actual rendered width."""
        s = _clean(text)
        while s and self.get_string_width(s) > max_w:
            s = s[:-1]
        if len(s) < len(_clean(text)):
            s = s[:-3] + "..." if len(s) > 3 else s
        return s

    def table(
        self,
        headers: list[str],
        widths: list[float],
        rows: list[list[str]],
        severity_col: int | None = None,
    ) -> None:
        row_h = 7.0
        pad = 1.5

        # ── Header row ───────────────────────────────────────────────
        self.set_fill_color(*_HEADER_FILL)
        self.set_text_color(*_WHITE)
        self.set_font("Helvetica", "B", 8)
        self.set_draw_color(*_BORDER)
        self.set_line_width(0.1)
        for h, w in zip(headers, widths):
            self.set_x(self.get_x())
            text = self._fit_text(h, w - pad * 2)
            self.cell(w, row_h, text, border=1, fill=True, align="C")
        self.ln()

        # ── Data rows ────────────────────────────────────────────────
        self.set_font("Helvetica", "", 7.5)
        for i, row in enumerate(rows):
            if self.get_y() > self.h - 24:
                self.add_page()
            fill = i % 2 == 1
            self.set_fill_color(*(_ROW_ALT if fill else _BG))
            for j, (cell_text, w) in enumerate(zip(row, widths)):
                text = self._fit_text(cell_text, w - pad * 2)
                if severity_col is not None and j == severity_col:
                    sev = str(cell_text).strip().upper()
                    r, g, b = _SEVERITY_TEXT.get(sev, _TEXT)
                    self.set_text_color(r, g, b)
                    self.set_font("Helvetica", "B", 7.5)
                else:
                    self.set_text_color(*_TEXT)
                    self.set_font("Helvetica", "", 7.5)
                self.cell(w, row_h, text, border=1, fill=fill)
            self.ln()
        self.ln(3)


# ── Public API ────────────────────────────────────────────────────────────────


def generate_pdf(data: dict[str, list[dict[str, Any]]]) -> bytes:
    analysis       = data.get("analysis", [])
    recommendation = data.get("recommendation", [])
    mcp_calls      = data.get("mcp_call", [])

    timeline        = next((e.get("data", []) for e in analysis if e.get("type") == "timeline"), [])
    gaps            = next((e.get("data", []) for e in analysis if e.get("type") == "gaps"), [])
    use_cases       = next((e.get("data", []) for e in analysis if e.get("type") == "use_cases"), [])
    rec_event       = next((e for e in recommendation if e.get("data")), {})
    recommendations = rec_event.get("data", [])
    exec_summary    = rec_event.get("executive_summary", "")

    pdf = _PDF()

    # ══════════════════════════════════════════════════════════════════
    # Cover page
    # ══════════════════════════════════════════════════════════════════
    pdf.add_page()

    # Dark navy background
    pdf.set_fill_color(*_COVER_BG)
    pdf.rect(0, 0, pdf.w, pdf.h, "F")

    # Left accent bar
    pdf.set_fill_color(*_ACCENT)
    pdf.rect(0, 0, 6, pdf.h, "F")

    # Title block (vertically centred)
    pdf.set_y(50)
    pdf.set_font("Helvetica", "B", 36)
    pdf.set_text_color(*_CYAN_COVER)
    pdf.cell(0, 16, "MirrorLens", align="C", ln=True)

    pdf.set_font("Helvetica", "", 15)
    pdf.set_text_color(*_WHITE)
    pdf.cell(0, 8, "Autonomous Security Investigation Report", align="C", ln=True)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*_SUBTEXT)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d  %H:%M UTC")
    pdf.cell(0, 7, ts, align="C", ln=True)

    # Divider
    pdf.ln(6)
    pdf.set_draw_color(*_ACCENT)
    pdf.set_line_width(0.6)
    pdf.line(50, pdf.get_y(), pdf.w - 50, pdf.get_y())
    pdf.ln(8)

    # Executive summary box
    if exec_summary:
        box_x, box_w = 30, pdf.w - 60
        pdf.set_fill_color(25, 45, 80)
        pdf.set_draw_color(*_ACCENT)
        pdf.set_line_width(0.4)
        y0 = pdf.get_y()
        pdf.set_x(box_x)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(210, 225, 240)
        pdf.multi_cell(box_w, 5.5, _clean(exec_summary), border=0, align="J", fill=False)
        y1 = pdf.get_y()
        pdf.rect(box_x - 2, y0 - 2, box_w + 4, y1 - y0 + 4, "D")

    # Stats row
    pdf.ln(10)
    stats = [
        ("TIMELINE STEPS", len(timeline)),
        ("DETECTION GAPS",  len(gaps)),
        ("SPL RULES",        len(use_cases)),
    ]
    col_w = (pdf.epw - 20) / len(stats)
    start_x = pdf.get_x() + 10
    for idx, (label, value) in enumerate(stats):
        x = start_x + idx * col_w
        pdf.set_xy(x, pdf.get_y())
        pdf.set_font("Helvetica", "B", 26)
        pdf.set_text_color(*_CYAN_COVER)
        pdf.cell(col_w, 12, str(value), align="C")
        pdf.set_xy(x, pdf.get_y() + 12)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*_SUBTEXT)
        pdf.cell(col_w, 5, label, align="C")
    pdf.ln(18)

    # Footer note
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(80, 100, 130)
    pdf.cell(0, 5, "CONFIDENTIAL -- For authorized personnel only", align="C", ln=True)

    # ══════════════════════════════════════════════════════════════════
    # Content pages (white background)
    # ══════════════════════════════════════════════════════════════════

    # ── Attack timeline ──────────────────────────────────────────────
    if timeline:
        pdf.add_page()
        pdf.set_fill_color(*_BG)
        pdf.rect(0, 0, pdf.w, pdf.h, "F")
        pdf.section_title("Attack Timeline  (MITRE ATT&CK)")
        headers = ["Timestamp",  "Technique ID", "Technique",  "Tactic",  "Host",  "Description",                       "Conf."]
        widths  = [32.0,         18.0,           44.0,         28.0,      24.0,    88.0,                                10.0]
        rows = [
            [
                str(s.get("timestamp", ""))[:19],
                s.get("technique_id", ""),
                s.get("technique_name", ""),
                s.get("tactic", ""),
                s.get("host", ""),
                s.get("description", ""),
                s.get("confidence", ""),
            ]
            for s in timeline
        ]
        pdf.table(headers, widths, rows)

    # ── Detection gaps ───────────────────────────────────────────────
    if gaps:
        pdf.add_page()
        pdf.set_fill_color(*_BG)
        pdf.rect(0, 0, pdf.w, pdf.h, "F")
        pdf.section_title("Detection Gaps")
        headers = ["Severity", "Technique ID", "Technique",  "Gap Description",  "Recommended SPL"]
        widths  = [18.0,       16.0,           36.0,         68.0,               106.0]
        rows = [
            [
                g.get("severity", ""),
                g.get("technique_id", ""),
                g.get("technique_name", ""),
                g.get("gap_description", ""),
                g.get("recommended_spl", ""),
            ]
            for g in gaps
        ]
        pdf.table(headers, widths, rows, severity_col=0)

    # ── Generated detection rules ────────────────────────────────────
    if use_cases:
        pdf.add_page()
        pdf.set_fill_color(*_BG)
        pdf.rect(0, 0, pdf.w, pdf.h, "F")
        pdf.section_title("Generated Detection Rules")
        headers = ["Priority", "Name",  "MITRE",  "Tactic",  "SPL Query",  "Alert Condition"]
        widths  = [14.0,       52.0,    20.0,      22.0,      120.0,        16.0]
        rows = [
            [
                uc.get("priority", ""),
                uc.get("name", ""),
                uc.get("mitre_technique", ""),
                uc.get("mitre_tactic", ""),
                uc.get("spl_query", ""),
                uc.get("alert_condition", ""),
            ]
            for uc in use_cases
        ]
        pdf.table(headers, widths, rows, severity_col=0)

    # ── Response recommendations ─────────────────────────────────────
    if recommendations:
        pdf.add_page()
        pdf.set_fill_color(*_BG)
        pdf.rect(0, 0, pdf.w, pdf.h, "F")
        pdf.section_title("Response Recommendations  (Dry-Run)")
        headers = ["#",   "Category", "Action",  "Risk",   "Validation SPL"]
        widths  = [8.0,   26.0,       80.0,       14.0,    116.0]
        rows = [
            [
                str(i + 1),
                r.get("category", ""),
                r.get("action", ""),
                r.get("risk_level", ""),
                r.get("spl_validation", ""),
            ]
            for i, r in enumerate(recommendations)
        ]
        pdf.table(headers, widths, rows, severity_col=3)

    # ── Appendix: MCP proof ──────────────────────────────────────────
    spl_calls = [
        c for c in mcp_calls
        if c.get("tool") == "run_query" and c.get("status") == "done" and c.get("spl")
    ]
    if spl_calls:
        pdf.add_page()
        pdf.set_fill_color(*_BG)
        pdf.rect(0, 0, pdf.w, pdf.h, "F")
        pdf.section_title("Appendix -- MCP Proof: SPL Queries Executed")
        headers = ["#",   "SPL Query",  "Rows"]
        widths  = [8.0,   228.0,        8.0]
        rows = [
            [str(i + 1), c.get("spl", ""), str(c.get("row_count", ""))]
            for i, c in enumerate(spl_calls)
        ]
        pdf.table(headers, widths, rows)

    return bytes(pdf.output())
