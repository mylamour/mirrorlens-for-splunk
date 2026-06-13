# Finding Card Export — Design Spec

**Date:** 2026-06-13
**Branch:** eric/pdf-export-report
**Status:** Approved

## Goal

Allow users to export a single Timeline finding as a 1-page PDF "card" directly from the DetailDrawer. Designed for SOC analysts who need to file a focused evidence card into a ticketing system (Jira, ServiceNow, email) without generating the full 22-page investigation report.

## User Flow

1. User clicks a Timeline entry in the dashboard → DetailDrawer opens.
2. At the bottom of the Drawer, an **"Export Finding Card"** button appears (only for `type === "timeline"` drawers).
3. User clicks the button → browser downloads `mirrorlens-finding-{technique_id}-{date}.pdf`.
4. The PDF is a single landscape A4 page with the full finding details.

## Backend

### New route: `POST /api/report/finding`

- Accepts JSON body: `{ finding: { timestamp, technique_id, technique_name, tactic, host, description, evidence, confidence } }`
- Calls `generate_finding_pdf(finding)` from `report_generator.py`
- Returns `StreamingResponse` with `Content-Disposition: attachment; filename="mirrorlens-finding-{technique_id}-{YYYYMMDD}.pdf"`
- Returns HTTP 400 with `{"error": "missing finding data"}` if body is empty or malformed

### New function: `generate_finding_pdf(finding: dict) -> bytes`

Added to `report_generator.py`. Reuses existing `ReportPDF` class, fonts, and colour constants.

**1-page layout (landscape A4):**

```
┌──────────────────────────────────────────────────────────────────┐
│  MIRRORLENS                            Security Finding Card     │
│  Thin blue top line accent                                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  [HIGH]  T1562.001 -- Impair Defenses: Disable or Modify...     │
│  (severity badge in colour + technique heading)                   │
│                                                                   │
│  Timestamp: Ongoing  │  Tactic: Defense Evasion                  │
│  Host: Splunk ES     │  Confidence: HIGH                         │
│                                                                   │
│  DESCRIPTION ──────────────────────────────────────────────────  │
│  Full description text (multi_cell, wraps as needed)              │
│                                                                   │
│  EVIDENCE ─────────────────────────────────────────────────────  │
│  Full evidence text (multi_cell, wraps as needed)                 │
│                                                                   │
│  ─────────────────────────────────────────────────────────────── │
│  Generated: June 13, 2026  12:30 UTC  │  MirrorLens via Splunk  │
└──────────────────────────────────────────────────────────────────┘
```

`auto_page_break = False` for the entire card so content never spills to page 2.

## Frontend

### `routes/report.py`

Register the new `POST /api/report/finding` router alongside the existing PDF route.

### `DetailDrawer.tsx`

- Accept new optional prop: `finding?: Record<string, unknown>`
- When `finding` is present (i.e., the drawer type is `"timeline"`), render an **"Export Finding Card"** button at the bottom of the drawer content.
- Button click handler:
  1. `fetch(REPORT_PDF_URL.replace('/pdf', '/finding'), { method: 'POST', body: JSON.stringify({ finding }), headers: { 'Content-Type': 'application/json' } })`
  2. `response.blob()` → `URL.createObjectURL(blob)` → create `<a>` element → `.click()` → revoke URL
  3. Button shows "Exporting..." while in-flight; reverts to normal on completion or error.

### `CenterPanel.tsx`

- When setting `detail` state for a timeline entry, include the raw finding object alongside the existing `data` field.
- Pass `finding={detail.finding}` to `<DetailDrawer>` when `detail.type === "timeline"`.

## File Naming

`mirrorlens-finding-{technique_id_sanitised}-{YYYYMMDD}.pdf`

- `technique_id_sanitised`: replace `.` and `/` with `-`, lowercase (e.g., `t1562-001`)
- Falls back to `mirrorlens-finding-{YYYYMMDD}.pdf` if no technique ID

## Error Handling

- Backend exception during PDF generation → HTTP 500 `{"error": "..."}`.
- Frontend fetch error → button reverts to normal state; no modal (silent fail is acceptable for hackathon scope).

## Out of Scope

- Exporting Gap, Rule, or Recommendation items as cards.
- Batch export of multiple findings at once.
- Adding finding-specific SPL recommendations (those live in the Gaps section, not the Timeline entry).
