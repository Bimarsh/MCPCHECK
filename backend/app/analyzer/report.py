from __future__ import annotations

from .config_generator import generate_client_configs
from .detector import detect_mcp
from .github_client import RepoSnapshot
from .scoring import score_report


def build_report(snapshot: RepoSnapshot) -> dict[str, object]:
    detection = detect_mcp(snapshot.files)
    scores, risk, findings, fixes = score_report(snapshot.metadata, snapshot.files, detection)
    report = {
        "id": "",
        "repo": snapshot.metadata,
        "mcpDetection": detection,
        "scores": scores,
        "risk": risk,
        "findings": findings,
        "recommendedFixes": fixes,
        "clientConfigs": generate_client_configs(snapshot.metadata, snapshot.files),
        "analysisLimits": {
            "fetchedFiles": len(snapshot.files),
            "skipped": snapshot.skipped,
        },
    }
    return report

