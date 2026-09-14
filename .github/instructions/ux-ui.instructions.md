---
applyTo: "**/*.{tsx,ts,jsx,js,css,scss,html}"
---

# UX and UI standards

## Objective
Build a modern, polished dashboard and chatbot UX for a logistics AI copilot demo with a strong enterprise look and feel.

## Design expectations
- Use clear information hierarchy and strong visual separation between KPI cards, tables, and chat.
- Prioritize readability and mobile responsiveness without sacrificing the desktop demo experience.
- Use consistent spacing, typography, and component patterns across the app.
- Make the interface feel credible for an enterprise business dashboard.

## UX principles
- Keep the primary workflow obvious: ask question, see result, understand impact.
- Prefer low-friction interactions and immediate feedback.
- Show loading states, empty states, and error states clearly.
- Ensure chatbot responses are easy to scan.
- Use business-friendly language in summaries and labels.

## Accessibility requirements
- Meet baseline accessibility expectations for keyboard and screen-reader usability.
- Ensure text contrast is adequate.
- Use semantic HTML and accessible labels for controls.
- Do not rely on color alone to communicate state or severity.
- Include focus states for interactive components.

## React standards
- Use functional components with strong typing.
- Keep components small and reusable.
- Separate presentational components from data-orchestration logic.
- Prefer typed props and explicit state boundaries.
- Avoid deeply nested conditional rendering when it reduces clarity.

## State and UI behavior
- Handle async UI states cleanly: pending, success, error, and empty.
- Centralize data-fetching patterns to avoid duplicated logic.
- Keep user actions predictable and consistent.
- Use optimistic or explicit states only when they improve clarity.

## Performance
- Avoid unnecessary re-renders.
- Use memoization only when it clearly improves real performance.
- Keep chart and table rendering efficient for realistic data sizes.

## Review standard
The UI should look intentional and “production-ready,” not like a rough prototype. All pages and components should be readable, consistent, and easy to explain in a live demo.
