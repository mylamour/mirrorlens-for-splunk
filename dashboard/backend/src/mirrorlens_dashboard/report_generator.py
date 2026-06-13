"""Generate a PDF investigation report from EventBus snapshot data."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fpdf import FPDF

# ── Colour palette (professional report, light throughout) ───────────────────
_WHITE       = (255, 255, 255)
_BG          = (255, 255, 255)
_TEXT        = (30,  35,  45)    # near-black body text
_SUBTEXT     = (100, 110, 125)   # secondary / captions
_ACCENT      = (0,   90,  170)   # blue accent — titles, borders
_ACCENT_LIGHT= (230, 238, 250)   # very light blue — header fills, card bg
_ROW_ALT     = (247, 249, 252)   # alternating row tint
_BORDER      = (200, 210, 220)   # table cell borders
_RULE        = (180, 195, 215)   # horizontal rules

_SEVERITY_TEXT: dict[str, tuple[int, int, int]] = {
    "CRITICAL": (180, 30,  30),
    "HIGH":     (190, 75,  15),
    "MEDIUM":   (150, 110,  0),
    "LOW":      (25,  130, 70),
    "P1":       (180, 30,  30),
    "P2":       (190, 75,  15),
    "P3":       (150, 110,  0),
}

_UNICODE_MAP = str.maketrans({
    "—": "--",  "–": "-",
    "'": "'",   "'": "'",
    "“": '"',  "”": '"',
    "…": "...", "•": "*",
    "→": "->",  "←": "<-",
    " ": " ", "·": "*",
})


def _clean(text: str) -> str:
    s = str(text or "").translate(_UNICODE_MAP)
    return "".join(c if ord(c) < 256 else "?" for c in s)


class _PDF(FPDF):
    def __init__(self) -> None:
        super().__init__(orientation="L", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(18, 18, 18)

    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*_SUBTEXT)
        self.set_y(8)
        self.cell(0, 4, "MirrorLens  |  Autonomous Security Investigation Report", align="L")
        self.set_y(8)
        self.cell(0, 4, f"Page {self.page_no()}", align="R")
        self.set_y(13)
        self.set_draw_color(*_RULE)
        self.set_line_width(0.2)
        self.line(18, 13, self.w - 18, 13)
        self.ln(4)

    def footer(self) -> None:
        pass

    def section_title(self, title: str) -> None:
        self.ln(5)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*_ACCENT)
        self.cell(0, 8, _clean(title), ln=True)
        self.set_draw_color(*_ACCENT)
        self.set_line_width(0.4)
        self.line(18, self.get_y(), self.w - 18, self.get_y())
        self.set_text_color(*_TEXT)
        self.ln(3)

    def _fit(self, text: str, max_w: float) -> str:
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
        pad   = 2.0

        # Header row — light blue fill, accent text
        self.set_fill_color(*_ACCENT_LIGHT)
        self.set_text_color(*_ACCENT)
        self.set_font("Helvetica", "B", 8)
        self.set_draw_color(*_BORDER)
        self.set_line_width(0.15)
        for h, w in zip(headers, widths):
            self.cell(w, row_h, self._fit(h, w - pad * 2),
                      border=1, fill=True, align="C")
        self.ln()

        # Data rows
        for i, row in enumerate(rows):
            if self.get_y() > self.h - 26:
                self.add_page()
            fill = i % 2 == 1
            self.set_fill_color(*(_ROW_ALT if fill else _BG))
            for j, (cell_text, w) in enumerate(zip(row, widths)):
                text = self._fit(cell_text, w - pad * 2)
                if severity_col is not None and j == severity_col:
                    sev = str(cell_text).strip().upper()
                    self.set_text_color(*_SEVERITY_TEXT.get(sev, _TEXT))
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

    # Use the LAST matching event so watch-mode reinvestigations always export current data.
    def _last(events: list, key: str, val: str) -> dict:
        return next((e for e in reversed(events) if e.get(key) == val), {})

    timeline        = _last(analysis, "type", "timeline").get("data", [])
    gaps            = _last(analysis, "type", "gaps").get("data", [])
    use_cases       = _last(analysis, "type", "use_cases").get("data", [])
    rec_event       = next((e for e in reversed(recommendation) if e.get("data")), {})
    recommendations = rec_event.get("data", [])
    exec_summary    = rec_event.get("executive_summary", "")

    pdf = _PDF()

    # ══════════════════════════════════════════════════════════════════
    # Page 1 — Cover  (auto page-break OFF so nothing spills to page 2)
    # ══════════════════════════════════════════════════════════════════
    pdf.set_auto_page_break(False)
    pdf.add_page()

    # Thin top accent line
    pdf.set_fill_color(*_ACCENT)
    pdf.rect(0, 0, pdf.w, 3, "F")

    # Logo / product name
    pdf.set_y(16)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*_ACCENT)
    pdf.cell(0, 6, "MIRRORLENS", align="C", ln=True)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*_SUBTEXT)
    pdf.cell(0, 5, "Autonomous AI Security Investigator", align="C", ln=True)

    # Divider
    pdf.ln(6)
    pdf.set_draw_color(*_RULE)
    pdf.set_line_width(0.3)
    pdf.line(40, pdf.get_y(), pdf.w - 40, pdf.get_y())
    pdf.ln(10)

    # Report title
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(*_TEXT)
    pdf.cell(0, 14, "Security Investigation Report", align="C", ln=True)

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*_SUBTEXT)
    pdf.cell(0, 7, "Powered by Splunk MCP Server", align="C", ln=True)

    pdf.ln(3)
    pdf.set_font("Helvetica", "", 9)
    ts = datetime.now(timezone.utc).strftime("%B %d, %Y  --  %H:%M UTC")
    pdf.cell(0, 6, _clean(ts), align="C", ln=True)

    # Stats row
    pdf.ln(10)
    stats = [
        ("Timeline Steps", len(timeline)),
        ("Detection Gaps",  len(gaps)),
        ("SPL Rules",        len(use_cases)),
    ]
    card_w = (pdf.epw - 16) / len(stats)
    card_h = 20.0
    y_card = pdf.get_y()
    for idx, (label, value) in enumerate(stats):
        x = 18 + 8 + idx * card_w
        pdf.set_fill_color(*_ACCENT_LIGHT)
        pdf.set_draw_color(*_BORDER)
        pdf.set_line_width(0.25)
        pdf.rect(x, y_card, card_w - 4, card_h, "FD")
        # Left accent bar on card
        pdf.set_fill_color(*_ACCENT)
        pdf.rect(x, y_card, 2, card_h, "F")
        # Value
        pdf.set_xy(x + 2, y_card + 2)
        pdf.set_font("Helvetica", "B", 20)
        pdf.set_text_color(*_ACCENT)
        pdf.cell(card_w - 6, 10, str(value), align="C")
        # Label
        pdf.set_xy(x + 2, y_card + 12)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*_SUBTEXT)
        pdf.cell(card_w - 6, 6, label, align="C")

    pdf.set_y(y_card + card_h + 8)

    # Executive summary
    if exec_summary:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*_SUBTEXT)
        pdf.set_x(18)
        pdf.cell(0, 5, "EXECUTIVE SUMMARY", ln=True)
        pdf.set_draw_color(*_RULE)
        pdf.set_line_width(0.2)
        pdf.line(18, pdf.get_y(), pdf.w - 18, pdf.get_y())
        pdf.ln(3)
        pdf.set_x(18)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*_TEXT)
        pdf.multi_cell(pdf.epw, 5.5, _clean(exec_summary), align="J")

    # Bottom rule + confidential note
    pdf.set_y(pdf.h - 16)
    pdf.set_draw_color(*_RULE)
    pdf.set_line_width(0.2)
    pdf.line(18, pdf.get_y(), pdf.w - 18, pdf.get_y())
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*_SUBTEXT)
    pdf.cell(0, 5, "CONFIDENTIAL -- For authorized personnel only", align="C")

    # ══════════════════════════════════════════════════════════════════
    # Content pages  (re-enable auto page-break)
    # ══════════════════════════════════════════════════════════════════
    pdf.set_auto_page_break(True, margin=20)

    if timeline:
        pdf.add_page()
        pdf.section_title("Attack Timeline  (MITRE ATT&CK)")
        headers = ["Timestamp",  "Technique ID", "Technique",  "Tactic",  "Host",  "Description",  "Conf."]
        widths  = [32.0,         18.0,           44.0,         28.0,      24.0,    88.0,            10.0]
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

    if gaps:
        pdf.add_page()
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

    if use_cases:
        pdf.add_page()
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

    if recommendations:
        pdf.add_page()
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

    spl_calls = [
        c for c in mcp_calls
        if c.get("tool") == "run_query" and c.get("status") == "done" and c.get("spl")
    ]
    if spl_calls:
        pdf.add_page()
        pdf.section_title("Appendix -- MCP Proof: SPL Queries Executed")
        headers = ["#",   "SPL Query",  "Rows"]
        widths  = [8.0,   228.0,        8.0]
        rows = [
            [str(i + 1), c.get("spl", ""), str(c.get("row_count", ""))]
            for i, c in enumerate(spl_calls)
        ]
        pdf.table(headers, widths, rows)

    return bytes(pdf.output())
