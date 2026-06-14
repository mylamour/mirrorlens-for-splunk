# Finding Card Export — Design Spec

**Date:** 2026-06-13
**Branch:** eric/pdf-export-report
**Status:** Implemented

## Goal

Allow users to export a single Timeline finding as a PDF "card" directly from the DetailDrawer. Designed for SOC analysts who need to file a focused evidence card into a ticketing system (Jira, ServiceNow, email).

## User Flow

1. User clicks a Timeline entry in the dashboard → DetailDrawer opens.
2. At the bottom of the Drawer, an **"Export Finding Card"** button appears (only for `type === "timeline"` drawers).
3. User clicks the button → browser downloads `mirrorlens-finding-{technique_id}-{date}.pdf`.
4. The PDF contains the full finding details, detection rules, and response actions. Content flows across pages as needed.

## Backend

### Route: `POST /api/report/finding`

- Accepts JSON body: `{ finding: { timestamp, technique_id, technique_name, tactic, host, description, evidence, confidence } }`
- Calls `generate_finding_pdf(finding, related)` from `report_generator.py`
- `_related_context()` pulls matched detection rules (by MITRE technique, fallback to tactic) and top-scored response actions from EventBus at export time
- Returns `StreamingResponse` with `Content-Disposition: attachment; filename="mirrorlens-finding-{technique_id}-{YYYYMMDD}.pdf"`
- Returns HTTP 400 with `{"error": "missing finding data"}` if body is empty or malformed

### Function: `generate_finding_pdf(finding, related) -> bytes`

In `report_generator.py`. Uses `_FindingCardPDF` subclass (no running header on any page) with auto page-break enabled — content flows naturally to additional pages.

**Layout (landscape A4, multi-page):**

```
┌──────────────────────────────────────────────────────────────────┐
│  MIRRORLENS                            Security Finding Card     │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  [HIGH]  T1562.001 -- Impair Defenses: Disable or Modify...     │
│                                                                   │
│  Timestamp: Ongoing  │  Tactic: Defense Evasion  │  Host: ES    │
│                                                                   │
│  DESCRIPTION ──────────────────────────────────────────────────  │
│  Full description text                                            │
│                                                                   │
│  EVIDENCE ─────────────────────────────────────────────────────  │
│  Full evidence text                                               │
│                                                                   │
│  DETECTION COVERAGE ───────────────────────────────────────────  │
│  Rule name  (exact technique match, ordered by relevance)        │
│  Rule description + SPL code block                               │
│                                                                   │
│  RESPONSE ACTIONS ─────────────────────────────────────────────  │
│  [CATEGORY]  Action text                                          │
│                                                                   │
│  ─────────────────────────────────────────────────────────────── │
│  Generated: June 13, 2026  12:30 UTC  │  MirrorLens via Splunk  │
└──────────────────────────────────────────────────────────────────┘
```

## Frontend

### `DetailDrawer.tsx`

Accepts a `footer?: ReactNode` prop. When provided, renders it in a fixed strip at the bottom of the drawer (with top border).

### `CenterPanel.tsx`

Passes an "EXPORT FINDING CARD" `<Button>` as the `footer` prop when `detail.type === "timeline"`. The click handler:

1. `fetch(REPORT_FINDING_URL, { method: 'POST', body: JSON.stringify({ finding }), ... })`
2. `response.blob()` → `URL.createObjectURL(blob)` → append `<a>` to DOM → `.click()` → remove from DOM → revoke URL
3. Button shows "EXPORTING..." while in-flight.

### `api.ts`

Exports `REPORT_FINDING_URL = \`${API_BASE}/api/report/finding\`` for use in `CenterPanel`.

## File Naming

`mirrorlens-finding-{technique_id_sanitised}-{YYYYMMDD}.pdf`

- `technique_id_sanitised`: replace `.` and `/` with `-`, lowercase (e.g., `t1562-001`)
- Falls back to `mirrorlens-finding-finding-{YYYYMMDD}.pdf` if no technique ID

## Error Handling

- Backend exception → HTTP 500 `{"error": "..."}`.
- Frontend fetch error → button reverts to normal state (silent fail).

## Out of Scope

- Exporting Gap, Rule, or Recommendation items as cards.
- Batch export of multiple findings at once.
