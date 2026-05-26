# Submission Copy

## Inspiration

Security teams already have the data, but the path from alert to understanding
is still too manual. MirrorLens explores how an AI agent can use Splunk MCP
Server to gather evidence directly from Splunk and turn noisy telemetry into a
clear, explainable investigation.

## What It Does

MirrorLens loads a sanitized attack scenario into Splunk, then runs an agentic
investigation through Splunk MCP Server. It builds a timeline, explains the
evidence, highlights detection gaps, and suggests next-step searches or safe
dry-run response actions.

## How We Built It

We built a public, self-contained demo around Splunk Enterprise, Splunk MCP
Server, synthetic security data, and a lightweight agent workflow. The project
is designed to be reviewed independently without exposing commercial X2 product
code.
