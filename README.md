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
src/                         React app
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
- `MCP_MAX_CONFIG_BYTES`: max pasted MCP config size accepted by `/api/analyze-config`.
- `MCP_MAX_CONFIG_SERVERS`: max MCP server entries accepted per pasted config.
- `MCP_MAX_CONFIG_ANALYSES`: max GitHub-backed MCP servers analyzed per config.
- `MCP_MAX_REMOTE_VALIDATIONS`: max explicit remote health URLs checked per config.
- `MCP_REMOTE_VALIDATION_TIMEOUT_SECONDS`: timeout for remote MCP health checks.
- `MCP_ALLOW_HTTP_REMOTE_VALIDATION`: set to `true` only if you intentionally want non-HTTPS remote checks.
- `MCPCHECK_ALLOWED_ORIGINS`: comma-separated browser origins allowed by CORS. Use your production domain instead of `*` for public deployments.

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
npm install
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
npm run dev
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

## Public Deployment Safety

MCPCheck is designed to stay public without executing user-supplied MCP commands:

- It never runs `npx`, `uvx`, shell commands, local scripts, Docker, or repository code from pasted configs.
- Repository analysis fetches selected text files from GitHub only, with file count, file size, and tree limits.
- Remote MCP validation only checks explicit HTTP(S) URLs from fields such as `url`, `endpoint`, or `healthCheckUrl`.
- Remote validation requires HTTPS by default, blocks private/reserved/localhost addresses, blocks credentials in URLs, blocks non-standard ports, does not follow redirects, and uses short timeouts.
- Pasted config analysis has separate byte, server count, GitHub repo, and remote URL limits so anonymous requests remain bounded.
- If no explicit remote health URL is available, the UI reports the response code as `Not available`.

For production, configure Vercel WAF/rate limits or another edge rate limiter for `/api/analyze` and `/api/analyze-config`. Anonymous analysis can still consume GitHub API quota and serverless execution time even though it does not execute untrusted code.

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

```http
POST /api/analyze-config
Content-Type: application/json

{ "config": "{\"mcpServers\":{\"server\":{\"url\":\"https://example.com/health\"}}}" }
```

Returns one result per MCP server, including a report link when a GitHub repo is analyzed and a `responseCode` when an explicit remote health URL can be checked.

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
