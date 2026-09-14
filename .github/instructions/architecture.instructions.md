---
applyTo: "**/*.{py,ts,tsx,js,jsx}" 
---

# Architecture standards

## Objective
Create a maintainable application built around clear boundaries, service separation, and sensible design patterns.

## Required architecture practices
- Follow SOLID principles consistently.
- Separate UI concerns from business logic and persistent data access.
- Use explicit interfaces for repositories, services, and orchestrators.
- Prefer composition over deep inheritance hierarchies.
- Keep domain logic independent from framework-specific details.

## Recommended patterns
- Repository pattern for data access
- Service layer for business orchestration
- Strategy pattern where behavior varies by context
- Factory or builder patterns only when they meaningfully improve clarity
- Use DTOs or typed schemas for request/response contracts

## Design expectations
- Avoid circular dependencies.
- Keep modules focused and discoverable.
- Keep configuration explicit and environment-driven.
- Prefer a single obvious path for each major workflow.

## Maintainability
- Favor readability and explicitness over clever abstractions.
- Document architectural decisions when non-obvious trade-offs are made.
- Refactor when the code becomes harder to follow than the domain itself.

## Senior-engineer standard
The architecture should be easy for a senior engineer to review and explain in a live technical session without needing deep hidden context.
