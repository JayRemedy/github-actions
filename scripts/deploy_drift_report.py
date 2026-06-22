#!/usr/bin/env python3
"""Generate sanitized deploy drift report artifacts.

The script compares a caller repository file tree or fixture file list against a
remote file list. It writes aggregate Markdown and JSON artifacts only; raw file
lists are intentionally not copied into the output.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


REPORT_NAME = "deploy-drift-report.md"
SUMMARY_NAME = "deploy-drift-summary.json"

WEB_ROOT_SEGMENTS = {"public", "public_html", "www", "html", "htdocs", "webroot"}
ENTRYPOINT_NAMES = {"index.html", "index.htm", "index.php", "index.js"}
MANIFEST_NAMES = {
    "composer.json",
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "Gemfile",
}

EXTENSION_CATEGORIES = {
    ".css": "assets",
    ".gif": "media",
    ".html": "content",
    ".htm": "content",
    ".ico": "media",
    ".jpeg": "media",
    ".jpg": "media",
    ".js": "code",
    ".json": "config",
    ".map": "generated",
    ".md": "content",
    ".pdf": "content",
    ".php": "code",
    ".png": "media",
    ".py": "code",
    ".svg": "media",
    ".toml": "config",
    ".txt": "content",
    ".webp": "media",
    ".xml": "config",
    ".yaml": "config",
    ".yml": "config",
}

SEGMENT_CATEGORIES = {
    ".cache": "generated",
    ".git": "metadata",
    "assets": "assets",
    "build": "generated",
    "cache": "generated",
    "css": "assets",
    "dist": "generated",
    "images": "media",
    "img": "media",
    "js": "assets",
    "media": "media",
    "node_modules": "dependencies",
    "public": "content",
    "static": "assets",
    "tmp": "generated",
    "vendor": "dependencies",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--local-root", help="Local directory to scan.")
    source.add_argument("--local-list", help="Newline-delimited local fixture file list.")
    parser.add_argument("--remote-list", required=True, help="Newline-delimited remote file list.")
    parser.add_argument(
        "--exclude-file",
        action="append",
        default=[],
        help="File containing newline-delimited exclude patterns.",
    )
    parser.add_argument("--output-dir", required=True, help="Directory for sanitized artifacts.")
    parser.add_argument("--fixture-name", default="", help="Optional fixture label for the report.")
    return parser.parse_args()


def normalize_path(raw_path: str) -> str:
    path = raw_path.strip().replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    path = path.lstrip("/")
    parts = [part for part in path.split("/") if part and part != "."]
    if any(part == ".." for part in parts):
        return ""
    return "/".join(parts)


def read_list(path: Path) -> set[str]:
    entries: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        normalized = normalize_path(line)
        if normalized:
            entries.add(normalized)
    return entries


def scan_local_root(root: Path) -> set[str]:
    if not root.is_dir():
        raise SystemExit("Configured source_path is not a directory.")

    entries: set[str] = set()
    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in {".git"}]
        current = Path(current_root)
        for filename in filenames:
            full_path = current / filename
            relative = full_path.relative_to(root).as_posix()
            normalized = normalize_path(relative)
            if normalized:
                entries.add(normalized)
    return entries


def read_excludes(paths: Iterable[str]) -> list[str]:
    patterns: list[str] = []
    for raw_path in paths:
        if not raw_path:
            continue
        path = Path(raw_path)
        if not path.exists():
            raise SystemExit("Configured exclude file was not found.")
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            patterns.append(stripped)
    return patterns


def is_excluded(path: str, patterns: Iterable[str]) -> bool:
    basename = path.rsplit("/", 1)[-1]
    for pattern in patterns:
        normalized = normalize_path(pattern)
        if not normalized:
            continue
        if fnmatch.fnmatch(path, normalized):
            return True
        if "/" not in normalized and fnmatch.fnmatch(basename, normalized):
            return True
        if normalized.endswith("/**") and path.startswith(normalized[:-3].rstrip("/") + "/"):
            return True
    return False


def apply_excludes(paths: set[str], patterns: list[str]) -> set[str]:
    if not patterns:
        return paths
    return {path for path in paths if not is_excluded(path, patterns)}


def extension_for(path: str) -> str:
    suffix = Path(path).suffix.lower()
    return suffix if suffix else "[none]"


def extension_counts(paths: Iterable[str], limit: int = 12) -> dict[str, int]:
    counts = Counter(extension_for(path) for path in paths)
    return dict(counts.most_common(limit))


def depth_bucket(path: str) -> str:
    depth = path.count("/")
    if depth == 0:
        return "root_files"
    if depth == 1:
        return "one_directory"
    if depth == 2:
        return "two_directories"
    return "deep_paths"


def category_for(path: str) -> str:
    parts = path.split("/")
    lowered_parts = [part.lower() for part in parts]
    for part in lowered_parts[:-1]:
        if part in SEGMENT_CATEGORIES:
            return SEGMENT_CATEGORIES[part]
        if part.startswith("."):
            return "metadata"
    return EXTENSION_CATEGORIES.get(Path(path).suffix.lower(), "other")


def bucket_counts(paths: Iterable[str], classifier) -> dict[str, int]:
    counts = Counter(classifier(path) for path in paths)
    return dict(sorted(counts.items()))


def copied_tree_heuristic(local_paths: set[str], extra_remote_paths: set[str]) -> dict[str, object]:
    total_extra = len(extra_remote_paths)
    total_local = max(len(local_paths), 1)

    web_root_hits = 0
    entrypoint_hits = 0
    manifest_hits = 0
    deep_hits = 0

    for path in extra_remote_paths:
        parts = [part.lower() for part in path.split("/")]
        basename = parts[-1] if parts else ""
        if any(part in WEB_ROOT_SEGMENTS for part in parts[:-1]):
            web_root_hits += 1
        if basename in ENTRYPOINT_NAMES:
            entrypoint_hits += 1
        if basename in {name.lower() for name in MANIFEST_NAMES}:
            manifest_hits += 1
        if path.count("/") >= 3:
            deep_hits += 1

    signals = {
        "extra_remote_ratio_over_25_percent": (total_extra / total_local) > 0.25,
        "common_web_root_segment_seen": web_root_hits > 0,
        "entrypoint_file_seen_in_extra_paths": entrypoint_hits > 0,
        "manifest_file_seen_in_extra_paths": manifest_hits > 0,
        "deep_extra_paths_over_25_percent": total_extra > 0 and (deep_hits / total_extra) > 0.25,
    }
    score = sum(1 for enabled in signals.values() if enabled)

    return {
        "possible": score >= 3,
        "score": score,
        "signals": signals,
        "signal_counts": {
            "common_web_root_segment_paths": web_root_hits,
            "entrypoint_files": entrypoint_hits,
            "manifest_files": manifest_hits,
            "deep_extra_paths": deep_hits,
        },
    }


def markdown_table(mapping: dict[str, int]) -> str:
    if not mapping:
        return "_None._\n"
    lines = ["| Bucket | Count |", "| --- | ---: |"]
    for key, value in mapping.items():
        lines.append(f"| `{key}` | {value} |")
    return "\n".join(lines) + "\n"


def build_summary(
    local_paths: set[str],
    remote_paths: set[str],
    excluded_count: dict[str, int],
    fixture_name: str,
) -> dict[str, object]:
    only_local = local_paths - remote_paths
    only_remote = remote_paths - local_paths
    matching = local_paths & remote_paths

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "fixture" if fixture_name else "report",
        "fixture_name": fixture_name,
        "safety": {
            "deleted": False,
            "uploaded": False,
            "deployed": False,
        },
        "counts": {
            "local_files": len(local_paths),
            "remote_files": len(remote_paths),
            "matching_files": len(matching),
            "only_local_files": len(only_local),
            "only_remote_files": len(only_remote),
            "excluded_local_files": excluded_count["local"],
            "excluded_remote_files": excluded_count["remote"],
        },
        "path_bucket_analysis": {
            "local_by_depth": bucket_counts(local_paths, depth_bucket),
            "remote_by_depth": bucket_counts(remote_paths, depth_bucket),
            "extra_remote_by_depth": bucket_counts(only_remote, depth_bucket),
            "extra_remote_by_category": bucket_counts(only_remote, category_for),
            "extra_remote_by_extension": extension_counts(only_remote),
        },
        "possible_copied_site_tree": copied_tree_heuristic(local_paths, only_remote),
    }


def build_report(summary: dict[str, object]) -> str:
    counts = summary["counts"]
    safety = summary["safety"]
    buckets = summary["path_bucket_analysis"]
    heuristic = summary["possible_copied_site_tree"]
    signals = heuristic["signals"]
    signal_counts = heuristic["signal_counts"]

    lines = [
        "# Deploy Drift Report",
        "",
        "This report is sanitized. It contains aggregate counts and bucket analysis only.",
        "Raw local and remote file lists are not included.",
        "",
        "## Safety",
        "",
        f"- deleted: `{str(safety['deleted']).lower()}`",
        f"- uploaded: `{str(safety['uploaded']).lower()}`",
        f"- deployed: `{str(safety['deployed']).lower()}`",
        "",
        "## Summary",
        "",
        f"- local files: `{counts['local_files']}`",
        f"- remote files: `{counts['remote_files']}`",
        f"- matching files: `{counts['matching_files']}`",
        f"- local-only files: `{counts['only_local_files']}`",
        f"- remote-only files: `{counts['only_remote_files']}`",
        f"- excluded local files: `{counts['excluded_local_files']}`",
        f"- excluded remote files: `{counts['excluded_remote_files']}`",
        "",
        "## Extra Remote Path Buckets",
        "",
        "### By Depth",
        "",
        markdown_table(buckets["extra_remote_by_depth"]),
        "### By Category",
        "",
        markdown_table(buckets["extra_remote_by_category"]),
        "### By Extension",
        "",
        markdown_table(buckets["extra_remote_by_extension"]),
        "## Possible Copied Site Tree Heuristic",
        "",
        f"- possible copied tree: `{str(heuristic['possible']).lower()}`",
        f"- score: `{heuristic['score']}`",
        "",
        "### Signals",
        "",
    ]

    for key, value in signals.items():
        lines.append(f"- {key}: `{str(value).lower()}`")

    lines.extend(["", "### Signal Counts", ""])
    for key, value in signal_counts.items():
        lines.append(f"- {key}: `{value}`")

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- This workflow is report-only.",
            "- Caller repositories provide all remote connection details and exclude configuration.",
            "- Extra remote paths are summarized into generic buckets to avoid leaking raw remote lists.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    exclude_patterns = read_excludes(args.exclude_file)

    if args.local_root:
        raw_local = scan_local_root(Path(args.local_root))
    else:
        raw_local = read_list(Path(args.local_list))

    raw_remote = read_list(Path(args.remote_list))
    local_paths = apply_excludes(raw_local, exclude_patterns)
    remote_paths = apply_excludes(raw_remote, exclude_patterns)
    excluded_count = {
        "local": len(raw_local) - len(local_paths),
        "remote": len(raw_remote) - len(remote_paths),
    }

    summary = build_summary(local_paths, remote_paths, excluded_count, args.fixture_name)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / SUMMARY_NAME).write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / REPORT_NAME).write_text(build_report(summary), encoding="utf-8")


if __name__ == "__main__":
    main()
