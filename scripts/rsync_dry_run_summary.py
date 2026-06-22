#!/usr/bin/env python3
"""Build sanitized summaries for rsync dry-run itemized output."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

REPORT_NAME = "rsync-dry-run-report.md"
SUMMARY_NAME = "rsync-dry-run-summary.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--itemize-log", required=True, help="Path to rsync --itemize-changes output.")
    parser.add_argument("--output-dir", required=True, help="Directory for sanitized artifacts.")
    parser.add_argument("--report-label", default="", help="Optional caller-provided target/environment label.")
    parser.add_argument("--max-paths", type=int, default=50, help="Maximum changed repo paths to show.")
    return parser.parse_args()


def normalize_itemized_path(path: str) -> str:
    path = path.strip().replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    path = path.lstrip("/")
    parts = [part for part in path.split("/") if part and part != "."]
    if any(part == ".." for part in parts):
        return ""
    return "/".join(parts)


def action_for(itemize: str) -> str:
    if itemize.startswith("*deleting"):
        return "delete"
    prefix = itemize[0] if itemize else "?"
    if prefix == ">":
        return "send"
    if prefix == "c":
        return "create_or_change"
    if prefix == ".":
        return "metadata_only"
    if prefix == "h":
        return "hard_link"
    if prefix == "<":
        return "receive"
    return "other"


def type_for(itemize: str) -> str:
    if itemize.startswith("*deleting"):
        return "delete"
    if len(itemize) < 2:
        return "unknown"
    return {
        "f": "file",
        "d": "directory",
        "L": "symlink",
        "D": "device",
        "S": "special",
    }.get(itemize[1], "other")


def parse_itemize_log(path: Path) -> list[dict[str, str]]:
    changes: list[dict[str, str]] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.rstrip("\n")
        if not line.strip():
            continue
        if line.startswith("sent ") or line.startswith("total size "):
            continue
        if " " not in line:
            continue
        itemize, changed_path = line.split(" ", 1)
        normalized = normalize_itemized_path(changed_path)
        if not normalized:
            continue
        changes.append(
            {
                "itemize": itemize,
                "action": action_for(itemize),
                "type": type_for(itemize),
                "path": normalized,
            }
        )
    return changes


def build_summary(changes: list[dict[str, str]], report_label: str, max_paths: int) -> dict[str, Any]:
    paths = [change["path"] for change in changes]
    shown_paths = paths[:max_paths]
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "dry_run",
        "report_label": report_label,
        "safety": {
            "dry_run": True,
            "deleted": False,
            "uploaded": False,
            "deployed": False,
        },
        "counts": {
            "total_changes": len(changes),
            "shown_paths": len(shown_paths),
            "truncated_paths": len(paths) > max_paths,
        },
        "actions": dict(sorted(Counter(change["action"] for change in changes).items())),
        "types": dict(sorted(Counter(change["type"] for change in changes).items())),
        "changed_paths": shown_paths,
    }


def markdown_counts(mapping: dict[str, int]) -> str:
    if not mapping:
        return "_None._\n"
    lines = ["| Bucket | Count |", "| --- | ---: |"]
    for key, value in mapping.items():
        lines.append(f"| `{key}` | {value} |")
    return "\n".join(lines) + "\n"


def build_report(summary: dict[str, Any]) -> str:
    safety = cast(dict[str, bool], summary["safety"])
    counts = cast(dict[str, Any], summary["counts"])
    actions = cast(dict[str, int], summary["actions"])
    types = cast(dict[str, int], summary["types"])
    changed_paths = cast(list[str], summary["changed_paths"])

    lines = [
        "# Rsync Deploy Dry-Run Report",
        "",
        "This report is sanitized. It contains aggregate counts and bounded repo-side changed path samples only.",
        "No files were uploaded, deleted, moved, chmodded, or deployed.",
        "",
        "## Run Context",
        "",
        f"- target: `{summary.get('report_label') or 'dry-run'}`",
        f"- mode: `{summary.get('mode')}`",
        "",
        "## Safety",
        "",
        f"- dry-run: `{str(safety['dry_run']).lower()}`",
        f"- deleted: `{str(safety['deleted']).lower()}`",
        f"- uploaded: `{str(safety['uploaded']).lower()}`",
        f"- deployed: `{str(safety['deployed']).lower()}`",
        "",
        "## Summary",
        "",
        f"- total changes rsync would make: `{counts['total_changes']}`",
        f"- changed paths shown: `{counts['shown_paths']}`",
        f"- changed paths truncated: `{str(counts['truncated_paths']).lower()}`",
        "",
        "## Change Actions",
        "",
        markdown_counts(actions),
        "## Change Types",
        "",
        markdown_counts(types),
        "## Changed Repo Paths",
        "",
    ]

    if changed_paths:
        lines.extend(f"- `{path}`" for path in changed_paths)
        if counts["truncated_paths"]:
            lines.append("- _Path list truncated. Download the JSON artifact for the bounded sample only._")
    else:
        lines.append("_None. The dry-run found no upload/update changes._")

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- This workflow is dry-run only.",
            "- Caller repositories provide all remote connection details and exclude configuration.",
            "- The workflow does not use rsync delete behavior.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    changes = parse_itemize_log(Path(args.itemize_log))
    summary = build_summary(changes, args.report_label, args.max_paths)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / SUMMARY_NAME).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / REPORT_NAME).write_text(build_report(summary), encoding="utf-8")


if __name__ == "__main__":
    main()
