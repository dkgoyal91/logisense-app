---
applyTo: "**/*.{py,ts,tsx,js,jsx,env,json,yml,yaml}" 
---

# Security standards

## Objective
Build the demo with secure defaults and a strong enterprise mindset for data handling and access control.

## Mandatory security practices
- Never expose secrets or credentials in source code, logs, or API responses.
- Use environment variables for configuration and secret values.
- Validate all incoming request data at API boundaries.
- Validate all output data before showing it to users.
- Restrict database access to known safe operations and approved schemas.

## Transport and data handling
- Use HTTPS in production-style environments.
- Do not log sensitive or personally identifiable information.
- Ensure request payloads are validated and safely parsed.
-Keep API responses free from internal implementation details when possible.

## Access and trust boundaries
- Treat all user-generated input as untrusted.
- Separate internal services from user-facing flows.
- Make authorization and permission checks explicit when introducing user roles.
- Avoid broad catch-all exception handling that hides security issues.

## Secure coding expectations
- Prefer safe defaults over permissive access.
- Use parameterization for database interaction.
- Validate model or user inputs before passing them downstream.
- Keep dependencies current and avoid adding unnecessary external packages.

## Review expectation
Security is not optional. Any feature that touches prompts, SQL generation, keys, databases, or user-generated content must be reviewed through a security lens before merge.
