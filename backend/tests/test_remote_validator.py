import socket

from app.analyzer import remote_validator
from app.analyzer.remote_validator import validate_remote_url


def test_remote_validator_allows_public_https_url(monkeypatch):
    monkeypatch.setattr(
        remote_validator.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 443))],
    )

    assert validate_remote_url("https://example.com/health") == "https://example.com/health"


def test_remote_validator_blocks_localhost(monkeypatch):
    monkeypatch.setattr(
        remote_validator.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 443))],
    )

    try:
        validate_remote_url("https://localhost/health")
    except ValueError as exc:
        assert "private or reserved" in str(exc)
    else:
        raise AssertionError("localhost should be blocked")


def test_remote_validator_blocks_private_ip(monkeypatch):
    monkeypatch.setattr(
        remote_validator.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 443))],
    )

    try:
        validate_remote_url("https://127.0.0.1/health")
    except ValueError as exc:
        assert "private or reserved" in str(exc)
    else:
        raise AssertionError("private IP should be blocked")


def test_remote_validator_requires_https_by_default():
    try:
        validate_remote_url("http://example.com/health")
    except ValueError as exc:
        assert "requires HTTPS" in str(exc)
    else:
        raise AssertionError("HTTP should be blocked by default")
