import pytest

from app.analyzer.mcp_config import extract_mcp_server_repos


def test_extracts_github_repos_from_mcp_servers():
    config = """
    {
      "mcpServers": {
        "one": {
          "command": "npx",
          "args": ["-y", "https://github.com/acme/server-one.git"]
        },
        "two": {
          "command": "uvx",
          "args": ["github:acme/server-two"]
        },
        "three": {
          "command": "node",
          "args": ["github.com/acme/server-three"]
        }
      }
    }
    """

    repos = extract_mcp_server_repos(config)

    assert repos == [
        {"serverName": "one", "repoUrl": "https://github.com/acme/server-one", "healthCheckUrl": ""},
        {"serverName": "two", "repoUrl": "https://github.com/acme/server-two", "healthCheckUrl": ""},
        {"serverName": "three", "repoUrl": "https://github.com/acme/server-three", "healthCheckUrl": ""},
    ]


def test_extracts_remote_health_url_from_mcp_server():
    config = """
    {
      "mcpServers": {
        "remote": {
          "url": "https://mcp.example.com/sse",
          "headers": {"Authorization": "Bearer token"}
        }
      }
    }
    """

    repos = extract_mcp_server_repos(config)

    assert repos == [{"serverName": "remote", "repoUrl": "", "healthCheckUrl": "https://mcp.example.com/sse"}]


def test_keeps_servers_without_github_repo_as_unmapped():
    config = '{"mcpServers":{"filesystem":{"command":"npx","args":["-y","@modelcontextprotocol/server-filesystem"]}}}'

    repos = extract_mcp_server_repos(config)

    assert repos == [{"serverName": "filesystem", "repoUrl": "", "healthCheckUrl": ""}]


def test_rejects_invalid_config():
    with pytest.raises(ValueError, match="valid JSON"):
        extract_mcp_server_repos("{")
