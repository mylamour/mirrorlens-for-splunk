"""Generate a PDF investigation report from EventBus snapshot data."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fpdf import FPDF

# Colour palette
_CYAN_R, _CYAN_G, _CYAN_B = 0, 188, 212
_HEADER_R, _HEADER_G, _HEADER_B = 30, 41, 59
_ALT_R, _ALT_G, _ALT_B = 15, 23, 42
_WHITE = (255, 255, 255)
_LIGHT_GREY = (200, 210, 220)
_TEXT = (200, 220, 230)

_SEVERITY_COLOURS: dict[str, tuple[int, int, int]] = {
    "CRITICAL": (220, 38, 38),
    "HIGH": (234, 88, 12),
    "MEDIUM": (234, 179, 8),
    "LOW": (34, 197, 94),
    "P1": (220, 38, 38),
    "P2": (234, 88, 12),
    "P3": (234, 179, 8),
}

_MAX_CELL = 120

_UNICODE_MAP = str.maketrans({
    "—": "--",   # em dash
    "–": "-",    # en dash
    "‘": "'",    # left single quote
    "’": "'",    # right single quote
    "“": '"',    # left double quote
    "”": '"',    # right double quote
    "…": "...",  # ellipsis
    "•": "*",    # bullet
    "→": "->",   # right arrow
    "←": "<-",   # left arrow
    " ": " ",    # non-breaking space
    "·": "*",    # middle dot
})


def _clean(text: str) -> str:
    s = str(text or "").translate(_UNICODE_MAP)
    return "".join(c if ord(c) < 256 else "?" for c in s)


def _trunc(text: str, n: int = _MAX_CELL) -> str:
    s = _clean(text)
    return s if len(s) <= n else s[:n] + "..."


class _PDF(FPDF):
    def __init__(self) -> None:
        super().__init__(orientation="L", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(12, 12, 12)

    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(80, 100, 120)
        self.cell(0, 5, "MirrorLens Investigation Report -- CONFIDENTIAL", align="L")
        self.ln(6)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(80, 100, 120)
        self.cell(0, 5, f"Page {self.page_no()}", align="C")

    # ── Section heading ──────────────────────────────────────────────

    def section_title(self, title: str) -> None:
        self.ln(4)
        self.set_draw_color(_CYAN_R, _CYAN_G, _CYAN_B)
        self.set_line_width(0.4)
        self.line(self.get_x(), self.get_y(), self.get_x() + self.epw, self.get_y())
        self.ln(2)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(_CYAN_R, _CYAN_G, _CYAN_B)
        self.cell(0, 8, _clean(title), ln=True)
        self.set_text_color(*_TEXT)
        self.ln(1)

    # ── Generic table ────────────────────────────────────────────────

    def table(self, headers: list[str], widths: list[float], rows: list[list[str]]) -> None:
        # Header row
        self.set_fill_color(_HEADER_R, _HEADER_G, _HEADER_B)
        self.set_text_color(*_WHITE)
        self.set_font("Helvetica", "B", 8)
        for h, w in zip(headers, widths):
            self.cell(w, 7, h, border=0, fill=True)
        self.ln()

        # Data rows
        self.set_font("Helvetica", "", 7.5)
        for i, row in enumerate(rows):
            if self.get_y() > self.h - 30:
                self.add_page()
            fill = i % 2 == 1
            self.set_fill_color(_ALT_R, _ALT_G, _ALT_B)
            self.set_text_color(*_TEXT)
            for cell, w in zip(row, widths):
                self.cell(w, 6, _trunc(cell, int(w * 1.8)), border=0, fill=fill)
            self.ln()
        self.ln(2)


# ── Public API ───────────────────────────────────────────────────────────────


def generate_pdf(data: dict[str, list[dict[str, Any]]]) -> bytes:
    """Build a PDF from EventBus snapshot data and return raw bytes."""
    analysis = data.get("analysis", [])
    recommendation = data.get("recommendation", [])
    mcp_calls = data.get("mcp_call", [])

    timeline = next((e.get("data", []) for e in analysis if e.get("type") == "timeline"), [])
    gaps = next((e.get("data", []) for e in analysis if e.get("type") == "gaps"), [])
    use_cases = next((e.get("data", []) for e in analysis if e.get("type") == "use_cases"), [])
    rec_event = next((e for e in recommendation if e.get("data")), {})
    recommendations = rec_event.get("data", [])
    executive_summary = rec_event.get("executive_summary", "")

    pdf = _PDF()

    # ── Cover page ───────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_fill_color(_HEADER_R, _HEADER_G, _HEADER_B)
    pdf.rect(0, 0, pdf.w, pdf.h, "F")

    pdf.ln(30)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(_CYAN_R, _CYAN_G, _CYAN_B)
    pdf.cell(0, 14, "MirrorLens", align="C", ln=True)

    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(*_LIGHT_GREY)
    pdf.cell(0, 8, "Autonomous Security Investigation Report", align="C", ln=True)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 130, 150)
    pdf.cell(0, 6, ts, align="C", ln=True)

    if executive_summary:
        pdf.ln(12)
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(*_TEXT)
        pdf.set_x(30)
        pdf.multi_cell(pdf.epw - 20, 6, _clean(executive_summary), align="L")

    # stats row
    pdf.ln(10)
    stats = [
        ("TIMELINE STEPS", str(len(timeline))),
        ("DETECTION GAPS", str(len(gaps))),
        ("SPL RULES", str(len(use_cases))),
    ]
    col_w = (pdf.epw - 20) / len(stats)
    for label, value in stats:
        x = pdf.get_x()
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(_CYAN_R, _CYAN_G, _CYAN_B)
        pdf.cell(col_w, 10, value, align="C")
        pdf.set_xy(x, pdf.get_y() + 10)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(100, 130, 150)
        pdf.cell(col_w, 5, label, align="C")
        pdf.set_xy(x + col_w, pdf.get_y() - 10)
    pdf.ln(15)

    # ── Attack timeline ──────────────────────────────────────────────
    if timeline:
        pdf.add_page()
        pdf.set_fill_color(_HEADER_R, _HEADER_G, _HEADER_B)
        pdf.rect(0, 0, pdf.w, pdf.h, "F")
        pdf.set_text_color(*_TEXT)
        pdf.section_title("Attack Timeline  (MITRE ATT&CK)")
        headers = ["Timestamp", "Technique ID", "Technique", "Tactic", "Host", "Description", "Conf."]
        widths  = [32.0,        20.0,           40.0,        28.0,     24.0,   90.0,           12.0]
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
        pdf.set_fill_color(_HEADER_R, _HEADER_G, _HEADER_B)
        pdf.rect(0, 0, pdf.w, pdf.h, "F")
        pdf.set_text_color(*_TEXT)
        pdf.section_title("Detection Gaps")
        headers = ["Severity", "Technique ID", "Technique", "Gap Description", "Recommended SPL"]
        widths  = [20.0,      18.0,           36.0,       70.0,               102.0]
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
        pdf.table(headers, widths, rows)

    # ── Generated detection rules ────────────────────────────────────
    if use_cases:
        pdf.add_page()
        pdf.set_fill_color(_HEADER_R, _CYAN_G // 4, _HEADER_B)
        pdf.rect(0, 0, pdf.w, pdf.h, "F")
        pdf.set_fill_color(_HEADER_R, _HEADER_G, _HEADER_B)
        pdf.rect(0, 0, pdf.w, pdf.h, "F")
        pdf.set_text_color(*_TEXT)
        pdf.section_title("Generated Detection Rules")
        headers = ["Priority", "Name", "MITRE Technique", "Tactic", "SPL Query", "Alert Condition"]
        widths  = [16.0,      48.0,   24.0,              24.0,     100.0,        34.0]
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
        pdf.table(headers, widths, rows)

    # ── Response recommendations ─────────────────────────────────────
    if recommendations:
        pdf.add_page()
        pdf.set_fill_color(_HEADER_R, _HEADER_G, _HEADER_B)
        pdf.rect(0, 0, pdf.w, pdf.h, "F")
        pdf.set_text_color(*_TEXT)
        pdf.section_title("Response Recommendations  (Dry-Run)")
        headers = ["#", "Category", "Action", "Risk", "Validation SPL"]
        widths  = [8.0, 28.0,      80.0,     16.0,  114.0]
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
        pdf.table(headers, widths, rows)

    # ── Appendix: MCP proof ──────────────────────────────────────────
    spl_calls = [
        c for c in mcp_calls
        if c.get("tool") == "run_query" and c.get("status") == "done" and c.get("spl")
    ]
    if spl_calls:
        pdf.add_page()
        pdf.set_fill_color(_HEADER_R, _HEADER_G, _HEADER_B)
        pdf.rect(0, 0, pdf.w, pdf.h, "F")
        pdf.set_text_color(*_TEXT)
        pdf.section_title("Appendix -- MCP Proof: SPL Queries Executed")
        headers = ["#", "SPL Query", "Rows Returned"]
        widths  = [8.0, 220.0,      18.0]
        rows = [
            [str(i + 1), c.get("spl", ""), str(c.get("row_count", ""))]
            for i, c in enumerate(spl_calls)
        ]
        pdf.table(headers, widths, rows)

    return bytes(pdf.output())
