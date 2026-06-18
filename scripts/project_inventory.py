#!/usr/bin/env python3
"""Generate a concise, non-destructive project inventory for architecture audits."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable


SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".next",
    ".nuxt",
    ".turbo",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "target",
    ".idea",
    ".vscode",
}

MANIFESTS = [
    "package.json",
    "pnpm-workspace.yaml",
    "yarn.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "Pipfile",
    "poetry.lock",
    "Cargo.toml",
    "go.mod",
    "Gemfile",
    "composer.json",
    "Dockerfile",
    "docker-compose.yml",
    "compose.yml",
    "wrangler.toml",
    "wrangler.jsonc",
    "vercel.json",
    "netlify.toml",
]

CONFIG_HINTS = [
    "README.md",
    "AGENTS.md",
    ".env.example",
    ".env.sample",
    "tsconfig.json",
    "vite.config.ts",
    "next.config.js",
    "next.config.mjs",
    "eslint.config.js",
    ".github/workflows",
]


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def iter_files(root: Path, max_files: int) -> Iterable[Path]:
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS]
        for filename in sorted(filenames):
            count += 1
            if count > max_files:
                return
            yield Path(dirpath) / filename


def tree(root: Path, max_depth: int, max_entries: int) -> list[str]:
    lines: list[str] = []

    def walk(path: Path, depth: int) -> None:
        if len(lines) >= max_entries or depth > max_depth:
            return
        try:
            children = sorted(
                [child for child in path.iterdir() if child.name not in SKIP_DIRS],
                key=lambda child: (not child.is_dir(), child.name.lower()),
            )
        except OSError:
            return
        for child in children:
            if len(lines) >= max_entries:
                return
            suffix = "/" if child.is_dir() else ""
            lines.append(f"{'  ' * depth}{child.name}{suffix}")
            if child.is_dir():
                walk(child, depth + 1)

    walk(root, 0)
    return lines


def find_existing(root: Path, names: list[str]) -> list[str]:
    found: list[str] = []
    for name in names:
        path = root / name
        if path.exists():
            found.append(name)
    return found


def find_by_name(root: Path, names: set[str], max_files: int) -> list[str]:
    found: list[str] = []
    for path in iter_files(root, max_files):
        if path.name in names:
            found.append(rel(path, root))
    return sorted(found)


def package_json_summary(root: Path) -> dict[str, object] | None:
    path = root / "package.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"error": "package.json could not be parsed"}

    deps = data.get("dependencies") or {}
    dev_deps = data.get("devDependencies") or {}
    return {
        "name": data.get("name"),
        "type": data.get("type"),
        "scripts": sorted((data.get("scripts") or {}).keys()),
        "dependencies": sorted(deps.keys())[:40],
        "devDependencies": sorted(dev_deps.keys())[:40],
        "dependency_count": len(deps),
        "dev_dependency_count": len(dev_deps),
    }


def git_summary(root: Path) -> dict[str, object] | None:
    git_dir = root / ".git"
    if not git_dir.exists():
        return None

    def run(args: list[str]) -> str:
        try:
            return subprocess.check_output(
                ["git", *args],
                cwd=root,
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=5,
            ).strip()
        except (subprocess.SubprocessError, OSError):
            return ""

    status = run(["status", "--short"])
    branch = run(["branch", "--show-current"]) or run(["rev-parse", "--short", "HEAD"])
    lines = [line for line in status.splitlines() if line.strip()]
    return {
        "branch_or_head": branch,
        "changed_file_count": len(lines),
        "changed_files_sample": lines[:20],
    }


def infer_test_dirs(root: Path) -> list[str]:
    candidates = {"test", "tests", "__tests__", "spec", "e2e"}
    found: list[str] = []
    for path in root.rglob("*"):
        if path.is_dir() and path.name in candidates and not any(part in SKIP_DIRS for part in path.parts):
            found.append(rel(path, root))
            if len(found) >= 20:
                break
    return sorted(found)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a project inventory for architecture audits.")
    parser.add_argument("repo", nargs="?", default=".", help="Repository root to inspect.")
    parser.add_argument("--max-depth", type=int, default=3, help="Directory tree depth.")
    parser.add_argument("--max-entries", type=int, default=180, help="Maximum tree entries.")
    parser.add_argument("--max-files", type=int, default=5000, help="Maximum files to scan by name.")
    args = parser.parse_args()

    root = Path(args.repo).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2

    manifest_names = set(MANIFESTS)
    config_names = {name for name in CONFIG_HINTS if "/" not in name}

    print("# Project Inventory")
    print()
    print(f"Root: `{root}`")
    print()

    git = git_summary(root)
    if git:
        print("## Git")
        print(f"- Branch/head: `{git['branch_or_head'] or 'unknown'}`")
        print(f"- Changed files: {git['changed_file_count']}")
        for item in git["changed_files_sample"]:
            print(f"  - `{item}`")
        print()

    print("## Directory Tree")
    for line in tree(root, args.max_depth, args.max_entries):
        print(f"- `{line}`")
    print()

    print("## Manifests And Config")
    existing = sorted(set(find_existing(root, MANIFESTS + CONFIG_HINTS) + find_by_name(root, manifest_names | config_names, args.max_files)))
    if existing:
        for item in existing:
            print(f"- `{item}`")
    else:
        print("- No common manifests or config files found.")
    print()

    pkg = package_json_summary(root)
    if pkg:
        print("## package.json Summary")
        if "error" in pkg:
            print(f"- {pkg['error']}")
        else:
            print(f"- Name: `{pkg.get('name') or 'unknown'}`")
            print(f"- Type: `{pkg.get('type') or 'unspecified'}`")
            print(f"- Scripts: {', '.join(f'`{script}`' for script in pkg['scripts']) or 'none'}")
            print(f"- Dependencies: {pkg['dependency_count']} runtime, {pkg['dev_dependency_count']} dev")
            if pkg["dependencies"]:
                print(f"- Runtime dependency sample: {', '.join(f'`{dep}`' for dep in pkg['dependencies'])}")
            if pkg["devDependencies"]:
                print(f"- Dev dependency sample: {', '.join(f'`{dep}`' for dep in pkg['devDependencies'])}")
        print()

    tests = infer_test_dirs(root)
    print("## Test Surface")
    if tests:
        for item in tests:
            print(f"- `{item}`")
    else:
        print("- No common test directories found by name.")
    print()

    env_files = sorted(rel(path, root) for path in root.glob(".env*") if path.is_file())
    print("## Environment Files")
    if env_files:
        for item in env_files:
            print(f"- `{item}` (name only; contents not read)")
    else:
        print("- No `.env*` files found at repository root.")
    print()

    print("## Next Manual Checks")
    print("- Read the listed manifests and entrypoints directly.")
    print("- Identify actual test/build/lint commands before running verification.")
    print("- Inspect secrets, auth, storage, provider, and deployment boundaries only through source/config, not private env values.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
