# Architecture Diagram

```mermaid
flowchart LR
  data["Sanitized attack-chain dataset"] --> ingest["Splunk ingest script"]
  ingest --> splunk["Splunk Enterprise index"]
  agent["MirrorLens agent workflow"] --> mcp["Splunk MCP Server"]
  mcp --> splunk
  agent --> report["Investigation report"]
  report --> outputs["Timeline, evidence explanation, detection gaps, dry-run recommendations"]
```

MirrorLens treats Splunk as the source of truth. The agent uses Splunk MCP
Server to discover data, run investigation searches, explain the evidence, and
produce auditable recommendations.
