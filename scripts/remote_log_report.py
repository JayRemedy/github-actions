#!/usr/bin/env python3
"""Generate a bounded, redacted report from remote log excerpts."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

START_RE = re.compile(r"^__REMOTE_LOG_FILE_START__\t(?P<path>.+)$")
END_MARKER = "__REMOTE_LOG_FILE_END__"
META_RE = re.compile(r"^__REMOTE_LOG_META__\t(?P<key>[^\t]+)\t(?P<value>.*)$")

REDACTIONS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?i)(password|passwd|pwd|secret|token|api[_-]?key|auth[_-]?token|private[_-]?key)(\s*[=:]\s*)[^\s&;'\"<>]+"), r"\1\2[REDACTED]"),
    (re.compile(r"(?i)(authorization:\s*(?:bearer|basic)\s+)[A-Za-z0-9._~+/=-]+"), r"\1[REDACTED]"),
    (re.compile(r"\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{12,}\b"), "[REDACTED_STRIPE_KEY]"),
    (re.compile(r"\bAC[a-fA-F0-9]{32}\b"), "[REDACTED_TWILIO_ACCOUNT_SID]"),
    (re.compile(r"\bSK[a-fA-F0-9]{32}\b"), "[REDACTED_TWILIO_API_KEY]"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S), "[REDACTED_PRIVATE_KEY]"),
]


def redact(text: str) -> str:
    redacted = text
    for pattern, repl in REDACTIONS:
        redacted = pattern.sub(repl, redacted)
    return redacted


def parse_remote_output(raw: str) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    body: list[str] = []

    for line in raw.splitlines():
        start = START_RE.match(line)
        if start:
            if current is not None:
                current["excerpt"] = "\n".join(body)
                entries.append(current)
            current = {"path": start.group("path"), "metadata": {}}
            body = []
            continue

        if line == END_MARKER:
            if current is not None:
                current["excerpt"] = "\n".join(body)
                entries.append(current)
                current = None
                body = []
            continue

        if current is not None:
            meta = META_RE.match(line)
            if meta:
                metadata = current.setdefault("metadata", {})
                assert isinstance(metadata, dict)
                metadata[meta.group("key")] = meta.group("value")
            else:
                body.append(line)

    if current is not None:
        current["excerpt"] = "\n".join(body)
        entries.append(current)

    return entries


def write_reports(entries: list[dict[str, object]], output_dir: Path, report_label: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    safe_entries = []
    for entry in entries:
        excerpt = str(entry.get("excerpt", ""))
        safe_entry = dict(entry)
        safe_entry["excerpt"] = redact(excerpt)
        safe_entries.append(safe_entry)

    summary = {
        "generated_at": generated_at,
        "report_label": report_label,
        "file_count": len(safe_entries),
        "files": safe_entries,
    }
    (output_dir / "remote-log-summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    lines: list[str] = []
    title = "Remote log report"
    if report_label:
        title += f" — {report_label}"
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"Generated: `{generated_at}`")
    lines.append(f"Files included: `{len(safe_entries)}`")
    lines.append("")
    lines.append("Secret-shaped values are best-effort redacted. Review artifacts carefully before sharing outside the repository.")
    lines.append("")

    if not safe_entries:
        lines.append("No matching log files were found.")
    for entry in safe_entries:
        path = str(entry.get("path", ""))
        metadata = entry.get("metadata", {})
        excerpt = str(entry.get("excerpt", ""))
        lines.append(f"## `{path}`")
        if isinstance(metadata, dict) and metadata:
            for key in sorted(metadata):
                lines.append(f"- {key}: `{metadata[key]}`")
        else:
            lines.append("- metadata: unavailable")
        lines.append("")
        lines.append("```text")
        lines.append(excerpt.rstrip() or "(empty excerpt)")
        lines.append("```")
        lines.append("")

    (output_dir / "remote-log-report.md").write_text("\n".join(lines).rstrip() + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-log", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--report-label", default="")
    args = parser.parse_args()

    raw = args.raw_log.read_text(errors="replace")
    entries = parse_remote_output(raw)
    write_reports(entries, args.output_dir, args.report_label)


if __name__ == "__main__":
    main()
