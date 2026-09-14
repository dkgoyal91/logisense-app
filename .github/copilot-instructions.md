# Repository Copilot Instructions

## Purpose
This repository is a senior-grade logistics AI demo for a 45-minute session. The goal is to build a production-quality prototype that demonstrates a real logistics copilot: natural language questions, safe SQL generation, local SQLite data access, and dashboard-style business insights.

## Core standards
- Follow SOLID principles in all code.
- Prefer explicit, readable code over clever abstractions.
- Keep layers clean: UI, application services, domain logic, data access, and infrastructure.
- Prefer composition over inheritance.
- Use design patterns intentionally where they reduce complexity and improve maintainability.
- Keep code testable and deterministic.
- Treat the solution as a professional engineering artifact, not a toy demo.

## Quality bar
- Write clear names for variables, functions, classes, and modules.
- Prefer small functions with single responsibilities.
- Add docstrings for public classes and core business logic.
- Avoid dead code, unused imports, and hidden side effects.
- Validate inputs at boundaries.
- Handle errors with meaningful messages and safe fallbacks.
- Add tests for critical behavior: SQL safety, query translation, business rules, API endpoints, and main UI interactions.

## Security rules
- Never execute arbitrary SQL from the frontend.
- All database queries must be validated and restricted to safe, allowed tables and columns.
- Use parameterization and schema validation, not string concatenation for queries.
- Never leak secrets, tokens, or internal environment values in logs or responses.
- Add input sanitization and output encoding for all user-generated content.
- Default to deny; grant access only to known safe operations.

## AI safety rules
- Treat prompts and SQL generation as security-sensitive components.
- Validate that user intent maps only to approved entities and business rules.
- Do not allow prompt injection to bypass query restrictions.
- Enforce safe result limits and row caps.
- Prefer structured responses and typed models over free-form outputs.
- Summaries must never invent data or misrepresent query results.

## Review rules
- Code must be understandable by a senior engineer at first read.
- Keep comments focused on intent, risk, or non-obvious decisions.
- Avoid comment clutter for obvious logic.
- Prefer maintainable abstractions and explicit contracts.
- Every feature should have a clear user or business value.

## Session-facing requirements
- Build a demo that is understandable in 45 minutes.
- Use realistic logistics data and narratives.
- Keep the UI polished, responsive, and accessible.
- Make the chatbot flow feel real: user question → safe SQL → results → summary.
- Prioritize a working prototype that demonstrates architecture and value over complexity.

## Working style
- Keep the codebase organized and consistent.
- Prefer small, reviewable changes.
- If the architecture becomes muddy, refactor before adding more features.
- Do not hide complexity behind over-engineering.
- Document assumptions clearly when critical decisions are made.

## Completion criteria
A feature is only complete when:
- it works in the local environment,
- it is validated with tests or smoke checks,
- it follows the repository quality rules,
- it is understandable to another engineer,
- it does not compromise security or data integrity.
