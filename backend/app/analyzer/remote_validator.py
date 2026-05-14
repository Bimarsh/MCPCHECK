from __future__ import annotations

import ipaddress
import os
import socket
import urllib.error
import urllib.parse
import urllib.request


REMOTE_VALIDATION_TIMEOUT_SECONDS = float(os.getenv("MCP_REMOTE_VALIDATION_TIMEOUT_SECONDS", "3"))
ALLOW_HTTP_REMOTE_VALIDATION = os.getenv("MCP_ALLOW_HTTP_REMOTE_VALIDATION", "false").lower() == "true"
ALLOWED_PORTS = {443} | ({80} if ALLOW_HTTP_REMOTE_VALIDATION else set())


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "Redirects are not followed.", headers, fp)


def _public_ips_for_host(hostname: str) -> list[str]:
    try:
        resolved = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError("Remote host could not be resolved.") from exc

    ips = sorted({item[4][0] for item in resolved})
    if not ips:
        raise ValueError("Remote host could not be resolved.")
    for raw_ip in ips:
        ip = ipaddress.ip_address(raw_ip)
        if not ip.is_global:
            raise ValueError("Remote URL resolves to a private or reserved address.")
    return ips


def validate_remote_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Remote validation only supports HTTP(S) URLs.")
    if parsed.scheme == "http" and not ALLOW_HTTP_REMOTE_VALIDATION:
        raise ValueError("Remote validation requires HTTPS URLs.")
    if parsed.username or parsed.password:
        raise ValueError("Remote validation URLs must not include credentials.")
    if not parsed.hostname:
        raise ValueError("Remote validation URL must include a host.")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if port not in ALLOWED_PORTS:
        raise ValueError("Remote validation URL uses a blocked port.")
    _public_ips_for_host(parsed.hostname)
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", parsed.params, parsed.query, ""))


def remote_response_code(url: str) -> tuple[int | None, str | None]:
    try:
        safe_url = validate_remote_url(url)
    except ValueError as exc:
        return None, str(exc)

    opener = urllib.request.build_opener(NoRedirectHandler)
    headers = {"User-Agent": "mcpcheck-remote-validator", "Accept": "*/*"}
    request = urllib.request.Request(safe_url, method="HEAD", headers=headers)
    try:
        with opener.open(request, timeout=REMOTE_VALIDATION_TIMEOUT_SECONDS) as response:
            return response.status, None
    except urllib.error.HTTPError as exc:
        if exc.code in {301, 302, 303, 307, 308}:
            return exc.code, None
        if exc.code == 405:
            get_request = urllib.request.Request(safe_url, headers={**headers, "Range": "bytes=0-0"})
            try:
                with opener.open(get_request, timeout=REMOTE_VALIDATION_TIMEOUT_SECONDS) as response:
                    response.read(1)
                    return response.status, None
            except urllib.error.HTTPError as get_exc:
                return get_exc.code, None
            except urllib.error.URLError as get_exc:
                return None, str(get_exc.reason)
        return exc.code, None
    except urllib.error.URLError as exc:
        return None, str(exc.reason)
