---
applyTo: "**/*.py"
---

# Backend standards

## Objective
Build a robust Python 3.12 backend using clear layering, secure defaults, and maintainable service boundaries.

## Core principles
- Use FastAPI for API endpoints and WebSocket handling.
- Keep API handlers thin and orchestrator-focused.
- Move business logic into services and domain components.
- Use typed models and explicit request/response schemas.
- Prefer deterministic, explainable behavior over hidden magic.

## Code quality
- Write small, composable functions with clear responsibilities.
- Use dependency injection for services that require configuration or repositories.
- Define repository interfaces and implementations explicitly.
- Handle exceptions at the boundary with safe, user-friendly responses.
- Add structured logging for traceability and debugging.

## Data and database
- Use SQLite for local demo data and simplicity of startup.
- Keep SQL generation explicit, validated, and schema-aware.
- Apply row limits and timeout protection for all database execution.
- Do not allow untrusted raw SQL from client inputs.

## API conventions
- Keep responses structured and predictable.
- Include status codes and descriptive error payloads.
- Add health checks for readiness and basic service status.
- Support WebSocket-based chat interaction with clear event schemas.

## Testing
- Add tests for API routes, query safety, and database handlers.
- Validate failure modes, especially malformed input and blocked unsafe SQL.
- Prefer direct tests of real behavior over mocking everything.

## Engineering standard
The backend should feel like a production service: maintainable, secure, traceable, and easy to reason about.
