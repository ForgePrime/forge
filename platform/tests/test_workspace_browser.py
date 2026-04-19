"""Unit tests for services/workspace_browser — FS listing + read + git diff.

Uses tmp_path fixtures; no live DB or orchestrate run needed.
Git tests require `git` on PATH; skipped otherwise.
"""
import pathlib
import subprocess
import pytest

from app.services.workspace_browser import (
    list_workspace_tree, read_file, git_diff,
    EXCLUDE_DIRS, EXCLUDE_SUFFIXES,
    MAX_FILE_BYTES, MAX_LIST_ITEMS,
)


def _git_available():
    try:
        subprocess.run(["git", "--version"], capture_output=True, timeout=5)
        return True
    except Exception:
        return False


# ---------- list_workspace_tree ----------

def test_list_missing_workspace_returns_error():
    r = list_workspace_tree("/nonexistent/path/xyz")
    assert "error" in r
    assert r["dirs"] == []
    assert r["files"] == []


def test_list_empty_workspace(tmp_path):
    r = list_workspace_tree(str(tmp_path))
    assert r["dirs"] == []
    assert r["files"] == []
    assert r["truncated"] is False


def test_list_files_and_dirs(tmp_path):
    (tmp_path / "a.py").write_text("print('a')")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.py").write_text("print('b')")
    r = list_workspace_tree(str(tmp_path))
    dir_paths = [d["path"] for d in r["dirs"]]
    file_paths = [f["path"] for f in r["files"]]
    assert "sub" in dir_paths
    assert "a.py" in file_paths
    assert "sub/b.py" in file_paths


def test_list_excludes_noise_dirs(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "mod.pyc").write_text("bytes")
    (tmp_path / "real.py").write_text("x")
    r = list_workspace_tree(str(tmp_path))
    file_paths = [f["path"] for f in r["files"]]
    assert "real.py" in file_paths
    assert all(not p.startswith(".git") for p in file_paths)
    assert all("__pycache__" not in p for p in file_paths)


def test_list_excludes_compiled_suffixes(tmp_path):
    (tmp_path / "a.py").write_text("src")
    (tmp_path / "b.pyc").write_text("compiled")
    (tmp_path / "c.so").write_text("shared")
    r = list_workspace_tree(str(tmp_path))
    file_paths = [f["path"] for f in r["files"]]
    assert "a.py" in file_paths
    assert "b.pyc" not in file_paths
    assert "c.so" not in file_paths


def test_list_respects_max_depth(tmp_path):
    # Create deep nesting
    deep = tmp_path
    for i in range(12):
        deep = deep / f"d{i}"
        deep.mkdir()
    deep_file = deep / "leaf.py"
    deep_file.write_text("leaf")

    r = list_workspace_tree(str(tmp_path), max_depth=3)
    # Leaf at depth 13 should be excluded
    file_paths = [f["path"] for f in r["files"]]
    assert all(len(p.split("/")) <= 3 for p in file_paths)


def test_list_returns_size_info(tmp_path):
    (tmp_path / "small.py").write_text("x" * 42)
    r = list_workspace_tree(str(tmp_path))
    file_entries = [f for f in r["files"] if f["path"] == "small.py"]
    assert len(file_entries) == 1
    assert file_entries[0]["size"] == 42


# ---------- read_file ----------

def test_read_file_success(tmp_path):
    (tmp_path / "hello.py").write_text("print('hi')", encoding="utf-8")
    r = read_file(str(tmp_path), "hello.py")
    assert r["content"] == "print('hi')"
    assert r["size"] == len("print('hi')")
    assert r["binary"] is False


def test_read_file_missing(tmp_path):
    r = read_file(str(tmp_path), "nope.py")
    assert "error" in r
    assert "does not exist" in r["error"]


def test_read_file_path_traversal_rejected(tmp_path):
    """`../etc/passwd` must NOT escape the workspace."""
    (tmp_path.parent / "secret.txt").write_text("sensitive", encoding="utf-8")
    r = read_file(str(tmp_path), "../secret.txt")
    assert "error" in r
    assert "traversal" in r["error"].lower()


def test_read_file_rejects_directory(tmp_path):
    (tmp_path / "dir").mkdir()
    r = read_file(str(tmp_path), "dir")
    assert "error" in r
    assert "regular file" in r["error"].lower()


def test_read_file_too_large(tmp_path):
    big = tmp_path / "big.txt"
    big.write_bytes(b"x" * (MAX_FILE_BYTES + 10))
    r = read_file(str(tmp_path), "big.txt")
    assert "error" in r
    assert r["size"] > MAX_FILE_BYTES
    assert "too large" in r["error"]


def test_read_file_binary_detection(tmp_path):
    """Invalid UTF-8 bytes → binary flag, no content."""
    (tmp_path / "img.bin").write_bytes(b"\x00\x01\x80\xff\xfe")
    r = read_file(str(tmp_path), "img.bin")
    assert "error" in r
    assert "binary" in r["error"].lower()
    assert r.get("binary") is True


# ---------- git_diff ----------

def test_git_diff_no_from_sha():
    r = git_diff("/tmp", "", "HEAD")
    assert r["error"] == "no from_sha"


@pytest.mark.skipif(not _git_available(), reason="git binary not available")
def test_git_diff_real_repo(tmp_path):
    """Init a repo, make 2 commits, diff them."""
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t.com"], capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], capture_output=True)
    (tmp_path / "a.py").write_text("v1", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], capture_output=True, check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "initial"], capture_output=True, check=True)

    sha1 = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    (tmp_path / "a.py").write_text("v2 changed", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], capture_output=True, check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "change"], capture_output=True, check=True)

    r = git_diff(str(tmp_path), sha1, "HEAD")
    assert r["exit_code"] == 0
    assert "v2 changed" in r["diff"] or "+v2" in r["diff"]
    assert any(f["path"] == "a.py" for f in r["files"])


@pytest.mark.skipif(not _git_available(), reason="git binary not available")
def test_git_diff_non_git_dir(tmp_path):
    """Running git diff in a non-git dir returns exit_code != 0, no crash."""
    r = git_diff(str(tmp_path), "abc123", "HEAD")
    # Either the command errors with non-zero exit_code, or git returns empty diff
    # Either way we don't raise — diagnostic output is the contract.
    assert "error" in r or r["exit_code"] != 0 or r["diff"] == ""
