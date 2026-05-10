# MCPCheck

MCPCheck is a Vercel-deployable web app that statically analyzes a public GitHub repository for MCP server quality, security, and agent-readiness.

The app does not execute repository code. It fetches selected text files from GitHub, runs deterministic checks, stores the report in Neon Postgres, and displays the report in a Vite frontend.

## Stack

- Frontend: React, TypeScript, Vite
- API: Python FastAPI app exposed as a Vercel Python function
- Production database: Neon Postgres through `DATABASE_URL`
- Local/test persistence: SQLite fallback when `DATABASE_URL` is not set

## Project Layout

```text
api/index.py                 Vercel Python function entrypoint
backend/app/main.py          FastAPI app and API routes
backend/app/database.py      Neon/Postgres persistence and local SQLite fallback
backend/app/analyzer/        Static GitHub/MCP analysis modules
backend/tests/               Backend unit tests
frontend/src/                React app
vercel.json                  Vercel build, function, and rewrite config
```

## Environment Variables

Copy `.env.example` for local development.

```bash
cp .env.example .env
```

Required for production:

- `DATABASE_URL`: Neon Postgres connection string. Use the pooled connection string when deploying to Vercel.

Optional:

- `GITHUB_TOKEN`: GitHub token used to avoid anonymous API rate limits.
- `MCP_MAX_FILES`: max relevant files fetched per repository.
- `MCP_MAX_FILE_BYTES`: max bytes fetched per file.
- `MCP_MAX_TREE_ITEMS`: max GitHub tree entries considered.

## Neon Setup

1. Create a Neon project.
2. Create or use the default database.
3. Copy the pooled Postgres connection string.
4. Add it to Vercel as `DATABASE_URL`.
5. Ensure the connection string includes SSL, usually `sslmode=require`.

The API creates the `reports` table automatically on first use.

## Local Development

Install frontend dependencies:

```bash
npm --prefix frontend install
```

Install backend dependencies:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements-dev.txt
```

Run the backend locally:

```bash
uvicorn app.main:app --app-dir backend --reload --port 8000
```

Run the frontend locally:

```bash
npm run dev:frontend
```

Open `http://localhost:5173`. The Vite dev server proxies `/api` to `http://localhost:8000`.

## Deploy to Vercel

1. Import this repository into Vercel.
2. Use the repository root as the project root.
3. Keep the default build settings from `vercel.json`.
4. Add environment variables:
   - `DATABASE_URL`: Neon pooled connection string
   - `GITHUB_TOKEN`: optional but recommended
5. Deploy.

The frontend and `/api/*` routes are served from the same Vercel deployment. `/reports/:id` is rewritten to the Vite app for client-side routing.

## API

```http
GET /api/health
```

Returns:

```json
{ "status": "ok" }
```

```http
POST /api/analyze
Content-Type: application/json

{ "repoUrl": "https://github.com/modelcontextprotocol/servers" }
```

Returns:

```json
{
  "reportId": "uuid",
  "status": "completed",
  "summary": {
    "overallScore": 74,
    "riskLevel": "Medium",
    "repoName": "org/repo"
  }
}
```

```http
GET /api/reports/{reportId}
```

Returns the full report JSON.

## Scoring

MCPCheck uses deterministic scoring out of 100:

- Documentation: 20
- Installability: 15
- MCP Schema Quality: 20
- Security / Permissions: 20
- Maintenance: 15
- Tests / Examples: 10

Risk is classified from security score and detected tool keywords. High-risk keywords include shell, command, delete, upload, deploy, payment, transfer, and SQL/write-like operations.

## Tests

Run backend tests:

```bash
npm run test:backend
```

Build frontend:

```bash
npm run build
```

## Limitations

- Tool extraction is heuristic and best-effort.
- The app does not execute MCP servers or benchmark live tool calls.
- Large repositories are limited by configured file count, file size, tree size, and Vercel function duration.
- Generated Claude Desktop and Cursor configs are suggestions and may need editing.
