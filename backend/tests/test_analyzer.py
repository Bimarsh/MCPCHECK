from dataclasses import dataclass

from app.analyzer.detector import detect_mcp
from app.analyzer.risk import classify_tool_name
from app.analyzer.scoring import score_report
from app.analyzer.tool_extractor import extract_tools


@dataclass
class File:
    path: str
    content: str
    size: int = 0


def test_extracts_typescript_tool_with_schema_and_description():
    files = [
        File(
            "src/server.ts",
            """
            server.tool("search_issues", "Search GitHub issues", {
              inputSchema: z.object({ query: z.string() })
            })
            """,
        )
    ]

    tools = extract_tools(files)

    assert tools[0]["name"] == "search_issues"
    assert tools[0]["hasInputSchema"] is True
    assert tools[0]["riskLevel"] == "Low"


def test_extracts_python_decorated_tool():
    files = [
        File(
            "server/main.py",
            '''
            @mcp.tool()
            def delete_file(path: str):
                """Delete a file."""
                return path
            ''',
        )
    ]

    tools = extract_tools(files)

    assert tools[0]["name"] == "delete_file"
    assert tools[0]["riskLevel"] == "High"


def test_mcp_detection_uses_dependency_and_source_evidence():
    files = [
        File("README.md", "This is a Model Context Protocol server."),
        File("package.json", '{"dependencies":{"@modelcontextprotocol/sdk":"latest"}}'),
        File("src/server.ts", 'server.tool("list_items", { inputSchema: z.object({}) })'),
    ]

    detection = detect_mcp(files)

    assert detection["isLikelyMcpServer"] is True
    assert detection["confidence"] > 0.5
    assert detection["detectedCapabilities"]["tools"][0]["name"] == "list_items"


def test_risk_classifier_keywords():
    assert classify_tool_name("execute_command") == "High"
    assert classify_tool_name("update_issue") == "Medium"
    assert classify_tool_name("read_page") == "Low"


def test_scoring_is_deterministic_and_sums_to_overall():
    repo = {
        "url": "https://github.com/acme/mcp",
        "owner": "acme",
        "name": "mcp",
        "stars": 10,
        "forks": 1,
        "license": "MIT",
        "lastCommitDate": "2026-05-01T00:00:00Z",
    }
    files = [
        File("README.md", "MCP server setup install usage environment TOKEN permissions example Claude"),
        File("package.json", '{"bin":{"mcp":"./dist/index.js"},"dependencies":{"@modelcontextprotocol/sdk":"latest"}}'),
        File("src/server.ts", 'server.tool("read_page", "Read page content", { inputSchema: z.object({ url: z.string() }) })'),
        File("tests/server.test.ts", "test('works', () => {})"),
    ]
    detection = detect_mcp(files)

    scores_a, risk_a, findings_a, fixes_a = score_report(repo, files, detection)
    scores_b, risk_b, findings_b, fixes_b = score_report(repo, files, detection)

    assert scores_a == scores_b
    assert risk_a == risk_b
    assert findings_a == findings_b
    assert fixes_a == fixes_b
    assert scores_a["overall"] == sum(value for key, value in scores_a.items() if key != "overall")

