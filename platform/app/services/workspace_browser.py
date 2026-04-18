"""Workspace file browser + git diff helpers (read-only).

Used by UI tabs:
- Files: list workspace tree, view file content (with size guards)
- Changes per task: git diff between task's start commit and end commit
"""

import pathlib
import subprocess


# File size + count guards to keep UI responsive
MAX_FILE_BYTES = 200 * 1024  # 200KB inline view
MAX_DIFF_BYTES = 500 * 1024  # 500KB max diff
MAX_LIST_ITEMS = 2000  # cap directory listings


# Always exclude from tree (noise / large)
EXCLUDE_DIRS = {".git", "__pycache__", "node_modules", ".pytest_cache", ".venv",
                "venv", "dist", "build", ".next", ".turbo", ".cache"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".so", ".o", ".dll"}


def list_workspace_tree(workspace_dir: str, max_depth: int = 8) -> dict:
    """Return tree as {dirs: [...], files: [...]} flat list with full relative paths."""
    base = pathlib.Path(workspace_dir)
    if not base.exists():
        return {"dirs": [], "files": [], "error": f"workspace does not exist: {workspace_dir}"}
    items_dirs: list[dict] = []
    items_files: list[dict] = []
    truncated = False
    for path in sorted(base.rglob("*")):
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        rel = path.relative_to(base)
        depth = len(rel.parts)
        if depth > max_depth:
            continue
        if path.is_dir():
            items_dirs.append({"path": str(rel).replace("\\", "/"), "depth": depth})
        elif path.is_file():
            if path.suffix in EXCLUDE_SUFFIXES:
                continue
            try:
                size = path.stat().st_size
            except OSError:
                size = -1
            items_files.append({
                "path": str(rel).replace("\\", "/"),
                "depth": depth, "size": size,
            })
        if len(items_dirs) + len(items_files) >= MAX_LIST_ITEMS:
            truncated = True
            break
    return {"dirs": items_dirs, "files": items_files, "truncated": truncated}


def read_file(workspace_dir: str, rel_path: str) -> dict:
    """Return file content (text) or info if binary/too-large."""
    base = pathlib.Path(workspace_dir).resolve()
    target = (base / rel_path).resolve()
    # Path traversal guard
    try:
        target.relative_to(base)
    except ValueError:
        return {"error": "path traversal not allowed"}
    if not target.exists():
        return {"error": "file does not exist"}
    if not target.is_file():
        return {"error": "not a regular file"}
    size = target.stat().st_size
    if size > MAX_FILE_BYTES:
        return {"error": f"file too large ({size} bytes > {MAX_FILE_BYTES})", "size": size}
    try:
        content = target.read_text(encoding="utf-8")
        binary = False
    except UnicodeDecodeError:
        return {"error": "binary file (cannot display)", "size": size, "binary": True}
    return {"path": rel_path, "size": size, "content": content, "binary": binary}


def git_diff(workspace_dir: str, from_sha: str, to_sha: str = "HEAD") -> dict:
    """Get unified diff between two commits."""
    if not from_sha:
        return {"error": "no from_sha"}
    try:
        proc = subprocess.run(
            ["git", "diff", "--unified=3", f"{from_sha}..{to_sha}"],
            cwd=workspace_dir,
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return {"error": "git diff timeout"}
    except FileNotFoundError:
        return {"error": "git not installed"}
    diff = proc.stdout
    truncated = False
    if len(diff) > MAX_DIFF_BYTES:
        diff = diff[:MAX_DIFF_BYTES] + "\n\n... (truncated — diff too large)"
        truncated = True
    # Get file list summary
    try:
        proc2 = subprocess.run(
            ["git", "diff", "--numstat", f"{from_sha}..{to_sha}"],
            cwd=workspace_dir,
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=15,
        )
        files = []
        for line in proc2.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 3:
                files.append({"added": parts[0], "removed": parts[1], "path": parts[2]})
    except Exception:
        files = []
    return {
        "from_sha": from_sha, "to_sha": to_sha,
        "files": files,
        "diff": diff,
        "truncated": truncated,
        "exit_code": proc.returncode,
    }
