# Codex Instructions

This repository is intended for full autonomous Codex implementation and verification.

- Proceed with code changes, tests, builds, and documentation updates needed to complete assigned Jira work without asking for intermediate approval.
- Prefer Vercel-compatible architecture: Vite frontend, Python serverless API under `api/`, and Neon Postgres via `DATABASE_URL` for production persistence.
- Do not introduce required self-hosting, Docker-only deployment, or production SQLite persistence.
- Keep repository analysis static. Never execute code from analyzed GitHub repositories.
- Enforce file count and file size limits for GitHub fetching so API work remains suitable for Vercel serverless limits.
- Use local SQLite only for tests and optional local development fallback.
- Run focused backend tests and frontend builds before handoff when dependencies are available.
