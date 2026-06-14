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
        self.multi_cell(self.epw, 5, sep.join(parts))
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
        title_str = self._fit(title, avail)
        self.cell(avail, 6, title_str)

        if right_label:
            self._hbold(8)
            self.set_text_color(*_ACCENT)
            self.cell(right_w, 6, right_label, align="R")

        self.ln(6)
        self.set_x(self.l_margin)
        self.set_text_color(*_TEXT)

    def body_text(self, text: str, size: float = 8.5) -> None:
        self.set_x(self.l_margin)
        self.set_font(self._body, size=size)
        self.set_text_color(*_TEXT)
        self.multi_cell(self.epw, 5, text)

    def code_box(self, code: str, label: str = "SPL") -> None:
        """Render a labelled monospace code block."""
        if not code:
            return
        self.ln(1)
        self._hbold( size=7.5)
        self.set_text_color(*_SUBTEXT)
        self.cell(0, 4, label + ":", new_x="LMARGIN", new_y="NEXT")

        # Estimate height; check page break
        lines = max(1, code.count("\n") + 1 + len(code) // 90)
        box_h = lines * 4.5 + 4
        if self.get_y() + box_h > self.h - 22:
            self.add_page()

        x0, y0 = self.get_x(), self.get_y()
        # Draw background
        self.set_fill_color(*_CODE_BG)
        self.set_draw_color(*_CODE_BORDER)
        self.set_line_width(0.2)
        self.rect(x0, y0, self.epw, box_h, "FD")
        # Left accent bar
        self.set_fill_color(*_ACCENT)
        self.rect(x0, y0, 1.5, box_h, "F")
        # Code text — use body font so Unicode (CJK, em-dash) renders correctly
        self.set_xy(x0 + 3, y0 + 2)
        self.set_font(self._body, size=7.5)
        self.set_text_color(*_TEXT)
        self.multi_cell(self.epw - 4, 4.5, code)
        # Ensure y is past the box
        self.set_y(max(self.get_y(), y0 + box_h) + 2)

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


# ── Section renderers ─────────────────────────────────────────────────────────

def _render_cover(pdf: ReportPDF, exec_summary: str, stats: dict) -> None:
    pdf.set_auto_page_break(False)
    pdf.add_page()

    # Top accent line
    pdf.set_fill_color(*_ACCENT)
    pdf.rect(0, 0, pdf.w, 3, "F")

    # Brand
    pdf.set_y(16)
    pdf._hbold( size=11)
    pdf.set_text_color(*_ACCENT)
    pdf.cell(0, 6, "MIRRORLENS", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(pdf._body, size=9)
    pdf.set_text_color(*_SUBTEXT)
    pdf.cell(0, 5, "Autonomous AI Security Investigator", align="C", new_x="LMARGIN", new_y="NEXT")

    # Divider
    pdf.ln(5)
    pdf.set_draw_color(*_RULE)
    pdf.set_line_width(0.3)
    pdf.line(40, pdf.get_y(), pdf.w - 40, pdf.get_y())
    pdf.ln(8)

    # Title
    pdf._hbold( size=28)
    pdf.set_text_color(*_TEXT)
    pdf.cell(0, 14, "Security Investigation Report", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(pdf._body, size=11)
    pdf.set_text_color(*_SUBTEXT)
    pdf.cell(0, 7, "Powered by Splunk MCP Server", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font(pdf._body, size=9)
    ts = datetime.now(timezone.utc).strftime("%B %d, %Y  --  %H:%M UTC")
    pdf.cell(0, 6, ts, align="C", new_x="LMARGIN", new_y="NEXT")

    # Stat cards
    pdf.ln(8)
    stat_items = [
        ("Timeline Steps", stats.get("timeline", 0)),
        ("Detection Gaps",  stats.get("gaps", 0)),
        ("SPL Rules",        stats.get("rules", 0)),
    ]
    card_w = (pdf.epw - 12) / 3
    card_h = 20.0
    y_card = pdf.get_y()
    for idx, (label, value) in enumerate(stat_items):
        x = 18 + 6 + idx * card_w
        pdf.set_fill_color(*_ACCENT_LIGHT)
        pdf.set_draw_color(*_BORDER)
        pdf.set_line_width(0.25)
        pdf.rect(x, y_card, card_w - 3, card_h, "FD")
        pdf.set_fill_color(*_ACCENT)
        pdf.rect(x, y_card, 2, card_h, "F")
        pdf.set_xy(x + 3, y_card + 2)
        pdf._hbold( size=20)
        pdf.set_text_color(*_ACCENT)
        pdf.cell(card_w - 5, 11, str(value), align="C")
        pdf.set_xy(x + 3, y_card + 13)
        pdf.set_font(pdf._body, size=7.5)
        pdf.set_text_color(*_SUBTEXT)
        pdf.cell(card_w - 5, 5, label, align="C")

    pdf.set_y(y_card + card_h + 7)

    # Executive summary
    if exec_summary:
        pdf._hbold( size=8.5)
        pdf.set_text_color(*_SUBTEXT)
        pdf.cell(0, 5, "EXECUTIVE SUMMARY", new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(*_RULE)
        pdf.set_line_width(0.2)
        pdf.line(18, pdf.get_y(), pdf.w - 18, pdf.get_y())
        pdf.ln(3)
        pdf.set_font(pdf._body, size=9)
        pdf.set_text_color(*_TEXT)
        pdf.multi_cell(0, 5.5, exec_summary, align="J")

    # Bottom
    pdf.set_y(pdf.h - 14)
    pdf.set_draw_color(*_RULE)
    pdf.set_line_width(0.2)
    pdf.line(18, pdf.get_y(), pdf.w - 18, pdf.get_y())
    pdf.ln(3)
    pdf.set_font("Helvetica", style="I", size=8)
    pdf.set_text_color(*_SUBTEXT)
    pdf.cell(0, 5, "CONFIDENTIAL -- For authorized personnel only", align="C")

    pdf.set_auto_page_break(True, margin=20)


def _render_key_findings(pdf: ReportPDF, key_findings: list, risk_level: str,
                          validated_rules: list) -> None:
    pdf.add_page()
    pdf.section_title("Key Findings & Risk Summary")

    # Overall risk
    pdf._hbold( size=10)
    r, g, b = _SEVERITY_COLOR.get(risk_level.upper(), _TEXT)
    pdf.set_text_color(r, g, b)
    pdf.cell(0, 7, f"Overall Risk Level: {risk_level.upper()}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*_TEXT)
    pdf.ln(2)

    # Key findings list
    if key_findings:
        pdf._hbold( size=9)
        pdf.set_text_color(*_SUBTEXT)
        pdf.cell(0, 5, f"KEY FINDINGS  ({len(key_findings)})", new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(*_RULE)
        pdf.set_line_width(0.2)
        pdf.line(18, pdf.get_y(), pdf.w - 18, pdf.get_y())
        pdf.ln(3)

        for i, finding in enumerate(key_findings, 1):
            pdf.ensure_space(14)
            finding_str = str(finding)
            # Parse severity prefix if present (e.g. "CRITICAL - ...")
            sev = "INFO"
            text = finding_str
            for s in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
                if finding_str.upper().startswith(s):
                    sev = s
                    text = finding_str[len(s):].lstrip(" -")
                    break
            r2, g2, b2 = _SEVERITY_COLOR.get(sev, _SUBTEXT)
            pdf._hbold( size=8)
            pdf.set_text_color(r2, g2, b2)
            pdf.cell(pdf.get_string_width(f"{i}. [{sev}]  ") + 1, 5,
                     f"{i}. [{sev}]  ", new_x="RIGHT", new_y="TOP")
            pdf.set_font(pdf._body, size=8)
            pdf.set_text_color(*_TEXT)
            pdf.multi_cell(0, 5, text)
            pdf.ln(1)

    pdf.ln(2)

    # Validated rules
    if validated_rules:
        pdf.ensure_space(30)
        pdf._hbold( size=9)
        pdf.set_text_color(*_SUBTEXT)
        pdf.cell(0, 5, f"VALIDATED DETECTION RULES  ({len(validated_rules)} with live matches)",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(*_RULE)
        pdf.set_line_width(0.2)
        pdf.line(18, pdf.get_y(), pdf.w - 18, pdf.get_y())
        pdf.ln(3)

        for rule in validated_rules:
            pdf.ensure_space(20)
            name = rule.get("rule_name", "")
            match_count = rule.get("match_count", 0)
            would_fire = rule.get("would_fire", False)
            badge = "MATCH" if would_fire else "NO MATCH"
            r2, g2, b2 = (22, 125, 65) if would_fire else (100, 110, 130)

            pdf._hbold( size=8.5)
            pdf.set_text_color(r2, g2, b2)
            prefix = f"[{badge}]  "
            pdf.cell(pdf.get_string_width(prefix) + 1, 5, prefix, new_x="RIGHT", new_y="TOP")
            pdf.set_text_color(*_TEXT)
            pdf.set_font(pdf._body, size=8.5)
            pdf.cell(0, 5, f"{name}  ({match_count:,} matches)", new_x="LMARGIN", new_y="NEXT")

            expected = rule.get("expected_behavior", "")
            if expected:
                pdf.set_font(pdf._body, size=7.5)
                pdf.set_text_color(*_SUBTEXT)
                pdf.multi_cell(0, 4.5, expected)
                pdf.set_text_color(*_TEXT)
            pdf.ln(2)


def _render_timeline(pdf: ReportPDF, timeline: list) -> None:
    pdf.add_page()
    pdf.section_title("Attack Timeline  (MITRE ATT&CK)")

    for entry in timeline:
        pdf.ensure_space(28)

        ts        = str(entry.get("timestamp", ""))[:19]
        tech_id   = entry.get("technique_id", "")
        tech_name = entry.get("technique_name", "")
        tactic    = entry.get("tactic", "")
        host      = entry.get("host", "")
        confidence= entry.get("confidence", "")
        desc      = entry.get("description", "")
        evidence  = entry.get("evidence", "")

        badge = confidence.upper()
        title = f"{tech_id}  {tech_name}" if tech_id != "N/A" else tech_name
        pdf.heading_line(badge, title)

        pdf.kv_line([
            ("Timestamp", ts or "Ongoing"),
            ("Tactic",    tactic),
            ("Host",      host),
        ])
        pdf.ln(1)

        if desc:
            pdf.body_text(desc, size=8.5)
        if evidence:
            pdf.set_x(pdf.l_margin)
            pdf.set_font(pdf._body, size=8)
            pdf.set_text_color(*_SUBTEXT)
            pdf.multi_cell(pdf.epw, 4.5, f"Evidence: {evidence}")
            pdf.set_text_color(*_TEXT)

        pdf.divider(thin=True)


def _render_gaps(pdf: ReportPDF, gaps: list) -> None:
    pdf.add_page()
    pdf.section_title("Detection Gaps")

    for gap in gaps:
        pdf.ensure_space(32)

        severity  = gap.get("severity", "")
        tech_id   = gap.get("technique_id", "")
        tech_name = gap.get("technique_name", "")
        gap_desc  = gap.get("gap_description", "")
        spl       = gap.get("recommended_spl", "")
        alert_name= gap.get("recommended_alert_name", "")

        title = f"{tech_id}  {tech_name}" if tech_id and tech_id != "N/A" else tech_name
        pdf.heading_line(severity, title)

        if alert_name:
            pdf.kv_line([("Recommended Alert", alert_name)])
        if gap_desc:
            pdf.body_text(gap_desc)
        if spl:
            pdf.code_box(spl, label="Recommended SPL")

        pdf.divider(thin=True)


def _render_rules(pdf: ReportPDF, use_cases: list) -> None:
    pdf.add_page()
    pdf.section_title("Generated Detection Rules")

    for uc in use_cases:
        pdf.ensure_space(40)

        priority   = uc.get("priority", "")
        name       = uc.get("name", "")
        mitre      = uc.get("mitre_technique", "")
        tactic     = uc.get("mitre_tactic", "")
        spl        = uc.get("spl_query", "")
        alert_cond = uc.get("alert_condition", "")
        description= uc.get("description", "")
        sources    = ", ".join(uc.get("data_sources_required", []))

        pdf.heading_line(priority, name)
        meta = [("MITRE", mitre)] if mitre else []
        if tactic:
            meta.append(("Tactic", tactic))
        if alert_cond:
            meta.append(("Alert Condition", alert_cond))
        if meta:
            pdf.kv_line(meta)
        if sources:
            pdf.kv_line([("Data Sources", sources)])
        if description:
            pdf.body_text(description)
        if spl:
            pdf.code_box(spl, label="SPL Query")

        pdf.divider(thin=True)


def _render_recommendations(pdf: ReportPDF, recommendations: list) -> None:
    pdf.add_page()
    pdf.section_title("Response Recommendations  (Dry-Run)")

    for i, rec in enumerate(recommendations, 1):
        pdf.ensure_space(30)

        risk       = rec.get("risk_level", "")
        category   = rec.get("category", "")
        action     = rec.get("action", "")
        spl_val    = rec.get("spl_validation", "")

        pdf.heading_line(risk, f"{i}. {action}", right_label=category.upper())
        if spl_val:
            pdf.code_box(spl_val, label="Validation SPL")

        pdf.divider(thin=True)


def _render_appendix(pdf: ReportPDF, mcp_calls: list) -> None:
    spl_calls = [
        c for c in mcp_calls
        if c.get("tool") == "run_query" and c.get("status") == "done" and c.get("spl")
    ]
    if not spl_calls:
        return

    # Only show the 25 most relevant (non-trivial) queries
    def _priority(c: dict) -> int:
        rows = c.get("row_count", 0)
        spl  = c.get("spl", "")
        if rows and int(rows) > 0:
            return 0
        if "fieldsummary" in spl or "head 5" in spl:
            return 2
        return 1

    top_calls = sorted(spl_calls, key=_priority)[:25]

    pdf.add_page()
    pdf.section_title(f"Appendix -- MCP Proof: SPL Queries Executed  ({len(spl_calls)} total)")

    for i, c in enumerate(top_calls, 1):
        pdf.ensure_space(18)
        spl       = c.get("spl", "")
        row_count = c.get("row_count", "")

        pdf._hbold( size=7.5)
        pdf.set_text_color(*_SUBTEXT)
        label = f"Query {i}"
        if row_count != "":
            label += f"  --  {row_count} rows"
        pdf.cell(0, 5, label, new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*_TEXT)

        pdf.code_box(spl, label="")

        if i < len(top_calls):
            pdf.divider(thin=True)


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
    """ReportPDF subclass with a consistent header on every page."""

    def header(self) -> None:
        # Top accent bar
        self.set_fill_color(*_ACCENT)
        self.rect(0, 0, self.w, 3, "F")
        # MIRRORLENS left, "Security Finding Card" right, page number far right
        self.set_y(8)
        self._hbold(9)
        self.set_text_color(*_ACCENT)
        self.cell(0, 5, "MIRRORLENS", align="L", new_x="LMARGIN", new_y="NEXT")
        self.set_font(self._body, size=8)
        self.set_text_color(*_SUBTEXT)
        self.set_y(8)
        page_label = f"Security Finding Card  |  p. {self.page_no()}"
        self.cell(0, 5, page_label, align="R")
        self.set_y(16)
        self.set_draw_color(*_RULE)
        self.set_line_width(0.2)
        self.line(18, self.get_y(), self.w - 18, self.get_y())
        self.ln(4)


def generate_finding_pdf(finding: dict[str, Any], related: dict[str, Any] | None = None) -> bytes:
    """Generate a finding card PDF enriched with detection rules and response actions."""
    pdf = _FindingCardPDF()
    pdf.setup()
    pdf.set_auto_page_break(True, margin=18)
    pdf.add_page()

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
            pdf.multi_cell(pdf.epw, 5, rule_name + match_note)
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
            badge = parts[0].strip().split()[0] if parts else "ACTION"
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


def generate_pdf(data: dict[str, list[dict[str, Any]]]) -> bytes:
    analysis       = data.get("analysis", [])
    recommendation = data.get("recommendation", [])
    mcp_calls      = data.get("mcp_call", [])

    def _last(events: list, key: str, val: str) -> dict:
        return next((e for e in reversed(events) if e.get(key) == val), {})

    timeline_ev     = _last(analysis, "type", "timeline")
    gaps_ev         = _last(analysis, "type", "gaps")
    use_cases_ev    = _last(analysis, "type", "use_cases")
    rec_ev          = next((e for e in reversed(recommendation) if e.get("data")), {})

    timeline        = timeline_ev.get("data", [])
    gaps            = gaps_ev.get("data", [])
    use_cases       = use_cases_ev.get("data", [])
    recommendations = rec_ev.get("data", [])
    exec_summary    = rec_ev.get("executive_summary", "")
    key_findings    = rec_ev.get("key_findings", [])
    risk_level      = rec_ev.get("risk_level", "UNKNOWN")
    validated_rules = rec_ev.get("validated_rules", [])

    pdf = ReportPDF()
    pdf.setup()

    _render_cover(pdf, exec_summary, {
        "timeline": len(timeline),
        "gaps":     len(gaps),
        "rules":    len(use_cases),
    })

    if key_findings or validated_rules:
        _render_key_findings(pdf, key_findings, risk_level, validated_rules)

    if timeline:
        _render_timeline(pdf, timeline)

    if gaps:
        _render_gaps(pdf, gaps)

    if use_cases:
        _render_rules(pdf, use_cases)

    if recommendations:
        _render_recommendations(pdf, recommendations)

    _render_appendix(pdf, mcp_calls)

    return bytes(pdf.output())
