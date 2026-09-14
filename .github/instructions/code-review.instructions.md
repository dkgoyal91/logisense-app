---
applyTo: "**/*.{py,ts,tsx,js,jsx,md}" 
---

# Code review standards

## Objective
Maintain a consistent, senior-level quality bar across all code changes.

## Review checklist
- Does the code follow the repository standards and architecture rules?
- Is the function or module responsibility clear?
- Are names expressive and consistent?
- Is the logic simple, explicit, and testable?
- Are security and validation checks present where needed?
- Are error paths handled and documented appropriately?
- Does the code add maintainability or does it create hidden complexity?

## Red flags
- Large unreviewable functions
- Broad exception swallowing
- Missing validation at boundaries
- Inconsistent naming or layering
- Unchecked raw SQL generation
- Unexplained cleverness or unnecessary abstractions

## Quality gate
A PR is not ready for merge unless the reviewer can understand the change, verify the intent, and trust its correctness under normal usage and edge conditions.
