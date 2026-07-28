from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MAX_SCANNED_FILE_BYTES = 2_000_000


@dataclass(frozen=True)
class Finding:
    scope: str
    rule: str
    location: str
    line: int | None = None
    commit: str | None = None


SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "private_key_material",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    ),
    (
        "openai_api_key",
        re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    ),
    (
        "clerk_or_stripe_secret_key",
        re.compile(r"\bsk_(?:live|test)_[A-Za-z0-9]{20,}\b"),
    ),
    (
        "github_token",
        re.compile(r"\b(?:github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{30,})\b"),
    ),
    (
        "aws_access_key",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    ),
    (
        "credential_bearing_database_url",
        re.compile(
            r"(?i)\b(?:postgres(?:ql)?|mysql|mariadb|redis|mongodb(?:\+srv)?)://"
            r"[^\s:/@]+:[^\s@]+@"
        ),
    ),
    (
        "jwt_token",
        re.compile(
            r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"
        ),
    ),
)

FORBIDDEN_TRACKED_NAMES = {
    ".env",
    ".env.local",
    "credentials.json",
    "service-account.json",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
}
FORBIDDEN_TRACKED_SUFFIXES = {
    ".key",
    ".p12",
    ".pfx",
    ".pem",
}


def _git(*args: str, text: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=text,
    )


def _tracked_paths() -> list[Path]:
    result = _git("ls-files", "-z", text=False)
    return [
        REPOSITORY_ROOT / value.decode("utf-8")
        for value in result.stdout.split(b"\0")
        if value
    ]


def _scan_lines(
    lines: Iterable[str],
    *,
    scope: str,
    location: str,
    commit: str | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    for line_number, line in enumerate(lines, start=1):
        for rule, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                findings.append(
                    Finding(
                        scope=scope,
                        rule=rule,
                        location=location,
                        line=line_number,
                        commit=commit,
                    )
                )
    return findings


def scan_tracked_tree() -> list[Finding]:
    findings: list[Finding] = []
    for path in _tracked_paths():
        relative = path.relative_to(REPOSITORY_ROOT).as_posix()
        lowered_name = path.name.lower()
        if lowered_name in FORBIDDEN_TRACKED_NAMES or path.suffix.lower() in FORBIDDEN_TRACKED_SUFFIXES:
            findings.append(
                Finding(
                    scope="tracked_tree",
                    rule="forbidden_secret_filename",
                    location=relative,
                )
            )

        try:
            if path.stat().st_size > MAX_SCANNED_FILE_BYTES:
                continue
            raw = path.read_bytes()
        except OSError:
            continue
        if b"\0" in raw:
            continue
        text = raw.decode("utf-8", errors="replace")
        findings.extend(
            _scan_lines(
                text.splitlines(),
                scope="tracked_tree",
                location=relative,
            )
        )
    return findings


def scan_git_history() -> list[Finding]:
    process = subprocess.Popen(
        [
            "git",
            "log",
            "--all",
            "--format=commit:%H",
            "--patch",
            "--no-color",
            "--no-ext-diff",
        ],
        cwd=REPOSITORY_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert process.stdout is not None

    findings: list[Finding] = []
    commit = "unknown"
    location = "unknown"
    patch_line = 0
    for raw_line in process.stdout:
        line = raw_line.rstrip("\n")
        if line.startswith("commit:"):
            commit = line.removeprefix("commit:").strip()[:40]
            location = "unknown"
            patch_line = 0
            continue
        if line.startswith("+++ b/"):
            location = line.removeprefix("+++ b/").strip()
            patch_line = 0
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        patch_line += 1
        content = line[1:]
        for rule, pattern in SECRET_PATTERNS:
            if pattern.search(content):
                findings.append(
                    Finding(
                        scope="git_history",
                        rule=rule,
                        location=location,
                        line=patch_line,
                        commit=commit,
                    )
                )

    _, stderr = process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"git history scan failed with exit code {process.returncode}: {stderr[:200]}")
    return findings


def evaluate_secret_log_safety(*, include_history: bool) -> dict:
    findings = scan_tracked_tree()
    if include_history:
        findings.extend(scan_git_history())

    deduplicated = sorted(
        {
            (
                finding.scope,
                finding.rule,
                finding.location,
                finding.line,
                finding.commit,
            ): finding
            for finding in findings
        }.values(),
        key=lambda finding: (
            finding.scope,
            finding.location,
            finding.line or 0,
            finding.rule,
        ),
    )
    return {
        "version": 1,
        "passed": not deduplicated,
        "history_scanned": include_history,
        "tracked_files_scanned": len(_tracked_paths()),
        "finding_count": len(deduplicated),
        "findings": [asdict(finding) for finding in deduplicated],
    }


def format_report(report: dict) -> str:
    status = "PASS" if report["passed"] else "FAIL"
    lines = [
        f"Secret and repository safety audit: {status}",
        f"Tracked files scanned: {report['tracked_files_scanned']}",
        f"Full git history scanned: {report['history_scanned']}",
        f"Findings: {report['finding_count']}",
    ]
    for finding in report["findings"][:20]:
        commit = f" commit={finding['commit']}" if finding.get("commit") else ""
        line = f":{finding['line']}" if finding.get("line") else ""
        lines.append(
            f"- {finding['rule']} at {finding['location']}{line}{commit}"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--history",
        action="store_true",
        help="Scan all reachable commit patches in addition to the tracked tree.",
    )
    args = parser.parse_args()

    report = evaluate_secret_log_safety(include_history=args.history)
    print(format_report(report))
    print("\nJSON report:")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
