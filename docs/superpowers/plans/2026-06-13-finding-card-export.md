# Finding Card Export — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Export a single Timeline finding as a 1-page PDF card via a button in the DetailDrawer.

**Architecture:** New `POST /api/report/finding` backend endpoint receives finding JSON, generates a 1-page PDF using the existing `ReportPDF` class and font stack, returns as file download. Frontend adds a `footer` prop to `DetailDrawer` and injects an export button when `detail.type === "timeline"`.

**Tech Stack:** fpdf2 (existing), FastAPI (existing), React + MUI (existing), fetch API for blob download.

---

## File Map

| File | Change |
|------|--------|
| `dashboard/backend/src/mirrorlens_dashboard/report_generator.py` | Add `generate_finding_pdf(finding)` function |
| `dashboard/backend/src/mirrorlens_dashboard/routes/report.py` | Add `POST /api/report/finding` endpoint |
| `dashboard/frontend/src/components/shared/DetailDrawer.tsx` | Add `footer?: ReactNode` prop |
| `dashboard/frontend/src/components/CenterPanel.tsx` | Pass export button as `footer` when `detail.type === "timeline"` |
| `dashboard/frontend/src/data/api.ts` | Export `REPORT_FINDING_URL` constant |

---

## Task 1: Backend — `generate_finding_pdf`

**Files:**
- Modify: `dashboard/backend/src/mirrorlens_dashboard/report_generator.py`

- [ ] **Step 1: Add `generate_finding_pdf` at the bottom of `report_generator.py`, before the final `generate_pdf` function**

```python
def generate_finding_pdf(finding: dict[str, Any]) -> bytes:
    """Generate a 1-page PDF card for a single timeline finding."""
    pdf = ReportPDF()
    pdf.setup()
    pdf.set_auto_page_break(False)
    pdf.add_page()

    # Top accent line
    pdf.set_fill_color(*_ACCENT)
    pdf.rect(0, 0, pdf.w, 3, "F")

    # Header bar
    pdf.set_y(10)
    pdf._hbold(9)
    pdf.set_text_color(*_ACCENT)
    pdf.cell(0, 5, "MIRRORLENS", align="L", new_x="LMARGIN", new_y="NEXT")
    pdf._hbold(8)
    pdf.set_text_color(*_SUBTEXT)
    pdf.set_y(10)
    pdf.cell(0, 5, "Security Finding Card", align="R")
    pdf.ln(7)
    pdf.set_draw_color(*_RULE)
    pdf.set_line_width(0.2)
    pdf.line(18, pdf.get_y(), pdf.w - 18, pdf.get_y())
    pdf.ln(6)

    # Heading line: [CONFIDENCE]  technique_id -- technique_name
    confidence = str(finding.get("confidence", "")).upper()
    tech_id    = finding.get("technique_id", "")
    tech_name  = finding.get("technique_name", "")
    title      = f"{tech_id}  {('--  ' + tech_name) if tech_name else ''}".strip()
    pdf.heading_line(confidence or "INFO", title)

    # Metadata row
    pairs = []
    if finding.get("timestamp"):
        pairs.append(("Timestamp", str(finding["timestamp"])[:19]))
    if finding.get("tactic"):
        pairs.append(("Tactic", str(finding["tactic"])))
    if finding.get("host"):
        pairs.append(("Host", str(finding["host"])))
    if pairs:
        pdf.kv_line(pairs)
    pdf.ln(4)

    # Description
    desc = finding.get("description", "")
    if desc:
        pdf._hbold(8)
        pdf.set_text_color(*_SUBTEXT)
        pdf.cell(0, 4, "DESCRIPTION", new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(*_RULE)
        pdf.set_line_width(0.15)
        pdf.line(18, pdf.get_y(), pdf.w - 18, pdf.get_y())
        pdf.ln(3)
        pdf.body_text(desc, size=9)
        pdf.ln(3)

    # Evidence
    evidence = finding.get("evidence", "")
    if evidence:
        pdf._hbold(8)
        pdf.set_text_color(*_SUBTEXT)
        pdf.cell(0, 4, "EVIDENCE", new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(*_RULE)
        pdf.set_line_width(0.15)
        pdf.line(18, pdf.get_y(), pdf.w - 18, pdf.get_y())
        pdf.ln(3)
        pdf.body_text(evidence, size=8.5)

    # Footer
    pdf.set_y(pdf.h - 12)
    pdf.set_draw_color(*_RULE)
    pdf.set_line_width(0.2)
    pdf.line(18, pdf.get_y(), pdf.w - 18, pdf.get_y())
    pdf.ln(3)
    pdf.set_font(pdf._body, size=7.5)
    pdf.set_text_color(*_SUBTEXT)
    ts = datetime.now(timezone.utc).strftime("%B %d, %Y  --  %H:%M UTC")
    pdf.cell(0, 4, f"Generated: {ts}  |  MirrorLens via Splunk MCP", align="C")

    return bytes(pdf.output())
```

- [ ] **Step 2: Smoke-test locally**

```bash
cd dashboard/backend
uv run python3 - <<'EOF'
from src.mirrorlens_dashboard.report_generator import generate_finding_pdf
sample = {
    "technique_id": "T1562.001",
    "technique_name": "Impair Defenses: Disable or Modify Tools",
    "tactic": "Defense Evasion",
    "host": "Splunk ES",
    "confidence": "HIGH",
    "description": "Test description with eventResultCode=\"失败\" unicode.",
    "evidence": "cim_modactions index",
    "timestamp": "Ongoing",
}
pdf = generate_finding_pdf(sample)
open("/tmp/finding-test.pdf", "wb").write(pdf)
print(f"OK: {len(pdf):,} bytes")
EOF
```

Expected: `OK: XXXXX bytes` (no errors, CJK renders without crash)

- [ ] **Step 3: Commit**

```bash
git add dashboard/backend/src/mirrorlens_dashboard/report_generator.py
git commit -m "feat: add generate_finding_pdf for single-finding card export"
```

---

## Task 2: Backend — API endpoint

**Files:**
- Modify: `dashboard/backend/src/mirrorlens_dashboard/routes/report.py`

- [ ] **Step 1: Add the POST endpoint to `routes/report.py`**

Add after the existing `download_pdf_report` function:

```python
from pydantic import BaseModel

class FindingRequest(BaseModel):
    finding: dict[str, Any]

@router.post("/report/finding")
async def download_finding_pdf(req: FindingRequest) -> StreamingResponse:
    if not req.finding:
        return JSONResponse(status_code=400, content={"error": "missing finding data"})

    try:
        pdf_bytes = generate_finding_pdf(req.finding)
    except Exception as exc:
        log.exception("Finding PDF generation failed")
        return JSONResponse(status_code=500, content={"error": f"PDF generation failed: {exc}"})

    tech_id = str(req.finding.get("technique_id", "finding"))
    safe_id = tech_id.lower().replace(".", "-").replace("/", "-")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    filename = f"mirrorlens-finding-{safe_id}-{ts}.pdf"

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

Also add the import at the top of the file alongside existing imports:
```python
from mirrorlens_dashboard.report_generator import generate_finding_pdf, generate_pdf
```

(Replace the existing `from mirrorlens_dashboard.report_generator import generate_pdf` line.)

- [ ] **Step 2: Verify endpoint works**

```bash
# Restart backend if running, then:
curl -s -X POST http://localhost:8091/api/report/finding \
  -H "Content-Type: application/json" \
  -d '{"finding":{"technique_id":"T1562.001","confidence":"HIGH","description":"Test","tactic":"Defense Evasion","host":"splunk-es","evidence":"cim_modactions"}}' \
  -o /tmp/curl-finding.pdf -w "HTTP %{http_code}\n"
file /tmp/curl-finding.pdf
```

Expected:
```
HTTP 200
/tmp/curl-finding.pdf: PDF document, version 1.3, 1 pages
```

- [ ] **Step 3: Commit**

```bash
git add dashboard/backend/src/mirrorlens_dashboard/routes/report.py
git commit -m "feat: add POST /api/report/finding endpoint"
```

---

## Task 3: Frontend — `REPORT_FINDING_URL` + `DetailDrawer` footer prop

**Files:**
- Modify: `dashboard/frontend/src/data/api.ts`
- Modify: `dashboard/frontend/src/components/shared/DetailDrawer.tsx`

- [ ] **Step 1: Add `REPORT_FINDING_URL` to `api.ts`**

Add directly below the existing `REPORT_PDF_URL` line:

```ts
export const REPORT_FINDING_URL = `${API_BASE}/api/report/finding`;
```

- [ ] **Step 2: Add `footer` prop to `DetailDrawer`**

Change the `Props` interface:

```ts
interface Props {
  open: boolean;
  onClose: () => void;
  title: string;
  accent?: AccentColor;
  children: ReactNode;
  footer?: ReactNode;
}
```

Change the function signature:

```ts
export default function DetailDrawer({ open, onClose, title, accent = "cyan", children, footer }: Props) {
```

Add footer rendering after the scrollable content area (before the closing `</Box>` of the outer container):

```tsx
              <Box sx={{ flex: 1, overflow: "auto", p: 2.5, minHeight: 0 }}>
                {children}
              </Box>

              {footer && (
                <Box sx={{
                  px: 2.5, py: 1.5, flexShrink: 0,
                  borderTop: `1px solid ${c}22`,
                  background: `rgba(0,0,0,0.15)`,
                }}>
                  {footer}
                </Box>
              )}
```

- [ ] **Step 3: Verify TS compiles**

```bash
cd dashboard/frontend && npx tsc -b 2>&1 | head -5 && echo "TS OK"
```

Expected: `TS OK`

- [ ] **Step 4: Commit**

```bash
git add dashboard/frontend/src/data/api.ts \
        dashboard/frontend/src/components/shared/DetailDrawer.tsx
git commit -m "feat: add footer slot to DetailDrawer and REPORT_FINDING_URL"
```

---

## Task 4: Frontend — Export button in CenterPanel

**Files:**
- Modify: `dashboard/frontend/src/components/CenterPanel.tsx`

- [ ] **Step 1: Add imports at the top of `CenterPanel.tsx`**

Add `Button` is already imported. Add `REPORT_FINDING_URL` to the api import:

```ts
import { triggerInvestigation, loadDemoData, fetchDashboardConfig, REPORT_PDF_URL, REPORT_FINDING_URL } from "../data/api";
```

- [ ] **Step 2: Add `exportFinding` state and handler near the other state declarations**

Add after `const [showCompletionModal, setShowCompletionModal] = useState(false);`:

```ts
const [exportingFinding, setExportingFinding] = useState(false);

const handleExportFinding = async (finding: Record<string, unknown>) => {
  setExportingFinding(true);
  try {
    const res = await fetch(REPORT_FINDING_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ finding }),
    });
    if (!res.ok) return;
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const techId = String(finding.technique_id ?? "finding")
      .toLowerCase().replace(/[./]/g, "-");
    a.download = `mirrorlens-finding-${techId}-${new Date().toISOString().slice(0,10)}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  } finally {
    setExportingFinding(false);
  }
};
```

- [ ] **Step 3: Pass `footer` prop to `<DetailDrawer>` when `detail.type === "timeline"`**

Find the `<DetailDrawer>` usage (around line 238) and add the `footer` prop:

```tsx
      <DetailDrawer
        open={detail !== null}
        onClose={() => setDetail(null)}
        title={detail ? DETAIL_TITLES[detail.type] : ""}
        accent={detail ? DETAIL_ACCENTS[detail.type] : "cyan"}
        footer={detail?.type === "timeline" ? (
          <Button
            variant="outlined"
            size="small"
            disabled={exportingFinding}
            onClick={() => handleExportFinding(detail.data)}
            sx={{
              borderColor: `${COLORS.cyan}55`,
              color: COLORS.cyan,
              fontFamily: "'Orbitron'",
              fontSize: 10,
              fontWeight: 600,
              letterSpacing: 1,
              "&:hover": { background: `${COLORS.cyan}12`, borderColor: COLORS.cyan },
            }}
          >
            {exportingFinding ? "EXPORTING..." : "EXPORT FINDING CARD"}
          </Button>
        ) : undefined}
      >
        {detail && <DetailContent item={detail} />}
      </DetailDrawer>
```

- [ ] **Step 4: Verify build passes**

```bash
pnpm build 2>&1 | grep -E "error TS|built in"
```

Expected: `✓ built in XXXms`

- [ ] **Step 5: Commit**

```bash
git add dashboard/frontend/src/components/CenterPanel.tsx
git commit -m "feat: add Export Finding Card button to timeline DetailDrawer"
```

---

## Task 5: End-to-end test + push

- [ ] **Step 1: Restart backend**

```bash
kill $(lsof -ti:8091) 2>/dev/null; sleep 1
cd /path/to/mirrorlens-for-splunk/dashboard/backend
uv run uvicorn mirrorlens_dashboard.server:app --port 8091 > /tmp/backend.log 2>&1 &
sleep 3 && curl -s http://localhost:8091/api/health
```

Expected: `{"status":"ok","subscribers":0}`

- [ ] **Step 2: Load sample investigation**

```bash
curl -s -X POST http://localhost:8091/api/demo/load | python3 -m json.tool | grep ok
```

Expected: `"ok": true`

- [ ] **Step 3: Manual browser test**

1. Open http://localhost:5174
2. Wait ~60s for full replay
3. Click any Timeline finding card
4. Verify DetailDrawer opens and shows "EXPORT FINDING CARD" button at the bottom
5. Click the button — verify PDF downloads as `mirrorlens-finding-t1562-001-YYYYMMDD.pdf`
6. Open the PDF — verify 1 page, correct technique name, description, evidence, no truncation, CJK renders if applicable

- [ ] **Step 4: Push to remote**

```bash
git push fork eric/pdf-export-report
```
