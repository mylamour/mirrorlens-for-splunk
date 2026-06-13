# Export PDF Report — Design Spec

**Date:** 2026-06-13  
**Branch:** eric/hackathon-dashboard-polish  
**Status:** Approved

## Goal

After a MirrorLens investigation completes, automatically prompt the user to download a PDF report containing the full findings — attack timeline, detection gaps, generated SPL rules, response recommendations, and an MCP query appendix. Also provide a persistent header button as a secondary entry point.

## User Flow

1. Investigation completes → `status` channel emits `{event: "completed"}`.
2. Frontend shows a completion modal (MUI Dialog) with summary stats and a **Download PDF Report** button.
3. User clicks the button → browser calls `GET /api/report/pdf` → PDF downloads as `mirrorlens-report-{timestamp}.pdf`.
4. If user dismisses the modal, a persistent **EXPORT REPORT** button in the Header remains visible while data exists.

## Backend

### New dependency

Add `fpdf2` to `dashboard/backend/pyproject.toml`.

### New file: `routes/report.py`

Single route: `GET /api/report/pdf`

- Reads current EventBus replay data for channels: `analysis`, `recommendation`, `discovery`, `mcp_call`.
- Calls `generate_pdf(snapshot_data)` from `report_generator.py`.
- Returns `StreamingResponse` with:
  - `media_type="application/pdf"`
  - `Content-Disposition: attachment; filename="mirrorlens-report-{YYYYMMDD-HHMMSS}.pdf"`
- If no data available (all channels empty), returns HTTP 404 with JSON `{"error": "No investigation data"}`.

Register the router in `server.py` under the `/api` prefix.

### New file: `report_generator.py`

Function signature:
```python
def generate_pdf(data: dict[str, list[dict]]) -> bytes
```

Extracts from `data`:
- `executive_summary`, `recommendations` ← `recommendation` channel events
- `timeline` ← `analysis` channel, `type == "timeline"`
- `detection_gaps` ← `analysis` channel, `type == "gaps"`
- `use_cases` ← `analysis` channel, `type == "use_cases"`
- `mcp_calls` ← `mcp_call` channel events (SPL queries with status=done)

PDF sections (in order):

| # | Section | Content |
|---|---------|---------|
| 1 | Cover | Title "MirrorLens Investigation Report", generation timestamp, executive summary paragraph |
| 2 | Attack Timeline | Table: Timestamp / Technique ID / Tactic / Host / Description / Confidence |
| 3 | Detection Gaps | Table: Severity / Technique / Gap Description / Recommended SPL |
| 4 | Generated Detection Rules | Table: Priority / Name / MITRE / SPL Query / Alert Condition |
| 5 | Response Recommendations | Table: # / Category / Action / Risk Level |
| 6 | Appendix: MCP Proof | Table: Tool / SPL Query / Row Count — all `run_query` calls with status=done |

Styling:
- Font: built-in `Helvetica` (no external font files needed)
- Cover page: large bold title, subtitle with timestamp, full-width executive summary text box
- Section headers: bold, 14pt, with a thin cyan-ish separator line (`R=0, G=188, B=212`)
- Table headers: filled background (`R=30, G=41, B=59`), white text
- Alternating row shading for readability
- Long text cells truncated to 120 chars with `…` to prevent layout overflow
- Page numbers in footer

## Frontend

### `CenterPanel.tsx` — Completion Modal

- Add state: `showCompletionModal: boolean`, initialized `false`.
- In the WebSocket/channel message handler, when `channel === "status"` and `payload.event === "completed"`, set `showCompletionModal = true`.
- Render a MUI `Dialog` when `showCompletionModal` is true:
  - Title: "Investigation Complete"
  - Body: summary stats (iterations, events collected) from the completed status payload
  - Primary button: "Download PDF Report" → `window.open('/api/report/pdf', '_blank')`
  - Secondary button: "Dismiss"
  - `onClose` → set `showCompletionModal = false`

### `Header.tsx` — Persistent Export Button

- Accept a new prop `hasData: boolean` (true when any analysis/recommendation events exist in state).
- When `hasData` is true, render an "EXPORT REPORT" button styled consistently with the existing "AGENT TRACE / MCP PROOF" button.
- `onClick` → `window.open('/api/report/pdf', '_blank')`.
- Pass `hasData` from `CenterPanel` (or the parent that owns channel state) down to `Header`.

## Error Handling

- If `generate_pdf` raises an exception, the route catches it, logs the error, and returns HTTP 500 with `{"error": "PDF generation failed"}`.
- If the browser download fails (e.g., no data), the user sees no file — no additional UI feedback needed for hackathon scope.

## Out of Scope

- Markdown export format
- Email delivery of the report
- Custom branding / logo image
- Pagination controls or report configuration UI
