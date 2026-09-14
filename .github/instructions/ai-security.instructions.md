---
applyTo: "**/*.{py,ts,tsx,js,jsx,md}" 
---

# AI security standards

## Objective
Protect the AI-driven workflow from prompt injection, unsafe SQL generation, and misleading outputs.

## Core guardrails
- Treat prompts, model choices, and generated SQL as untrusted until validated.
- Restrict the system to a known allowed schema and approved query patterns.
- Reject unsafe instructions that attempt to override database rules or access restricted tables.
- Use structured prompt templates and deterministic safety checks wherever possible.

## SQL safety
- Allow only read-only queries for the demo scope.
- Block DDL, DCL, and write operations by default.
- Validate table names and column names against an approved schema map.
- Enforce row limits and execution timeouts.
- Use typed query generation instead of raw string concatenation.

## Prompt injection protection
- Strip or neutralize instructions embedded in user input that attempt to override system behavior.
- Keep the LLM inside a constrained execution context.
- Require tool outputs to be validated before being surfaced to users.
- Fail safely when the model response cannot be mapped to approved actions.

## Output integrity
- The system must never claim data that was not returned from a validated query.
- Summaries must be traceable to underlying query results.
- If confidence is low, prefer a safer answer or a request for clarification.

## Review expectation
AI-related features must be reviewed as security-sensitive code. The business value is real, but the safety and trust boundaries are equally important.
