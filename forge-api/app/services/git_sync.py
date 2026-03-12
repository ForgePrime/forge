"""Git sync service for skills repository.

Manages git clone of forge-skills.git inside the skills directory.
Provides pull (fetch + reset --hard), push (add synced skills + commit + push),
and status operations.  Graceful degradation when git is unavailable.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class GitSyncResult:
    """Result of a git sync operation."""
    success: bool = True
    message: str = ""
    files_changed: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class GitStatus:
    """Current git status of the skills repo."""
    initialized: bool = False
    has_remote: bool = False
    branch: str = ""
    ahead: int = 0
    behind: int = 0
    local_changes: list[str] = field(default_factory=list)
    last_commit: str = ""
    error: str | None = None


class GitSyncService:
    """Manages git operations for the skills directory."""

    def __init__(
        self,
        skills_dir: Path | str,
        remote_url: str | None = None,
        skill_storage: object | None = None,
    ):
        self.skills_dir = Path(skills_dir)
        self.remote_url = remote_url or os.environ.get("FORGE_SKILLS_REPO_URL", "")
        self._skill_storage = skill_storage  # SkillStorageService for resync
        self._sync_lock = asyncio.Lock()  # Serialize pull/push operations

    def _check_configured(self) -> None:
        """Raise if git remote URL is not configured."""
        if not self.remote_url:
            raise GitSyncNotConfigured(
                "FORGE_SKILLS_REPO_URL not set — git sync is disabled"
            )

    async def _run_git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command in skills_dir via asyncio.to_thread."""
        cmd = ["git", *args]
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                cwd=str(self.skills_dir),
                capture_output=True,
                text=True,
                timeout=60,
            )
            if check and result.returncode != 0:
                raise GitSyncError(
                    f"git {' '.join(args)} failed: {result.stderr.strip()}"
                )
            return result
        except FileNotFoundError:
            raise GitSyncError("git is not installed or not in PATH")
        except subprocess.TimeoutExpired:
            raise GitSyncError(f"git {' '.join(args)} timed out (60s)")

    async def init_or_clone(self) -> GitSyncResult:
        """Clone the remote repo or verify existing .git directory."""
        self._check_configured()
        git_dir = self.skills_dir / ".git"

        if git_dir.is_dir():
            # Verify remote matches
            result = await self._run_git("remote", "get-url", "origin", check=False)
            if result.returncode == 0:
                current_url = result.stdout.strip()
                if current_url != self.remote_url:
                    await self._run_git("remote", "set-url", "origin", self.remote_url)
                return GitSyncResult(
                    success=True,
                    message=f"Repository verified at {self.skills_dir}",
                )
            # Has .git but no origin — add it
            await self._run_git("remote", "add", "origin", self.remote_url)
            return GitSyncResult(success=True, message="Remote origin added")

        # Clone into skills_dir (it may already have local skills)
        self.skills_dir.mkdir(parents=True, exist_ok=True)

        # If directory has content, init + add remote instead of clone
        if any(self.skills_dir.iterdir()):
            await self._run_git("init")
            await self._run_git("remote", "add", "origin", self.remote_url)
            await self._run_git("fetch", "origin")
            return GitSyncResult(
                success=True,
                message="Initialized git in existing skills directory",
            )

        # Empty dir — clone directly
        parent = self.skills_dir.parent
        dir_name = self.skills_dir.name
        cmd = ["git", "clone", self.remote_url, dir_name]
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                cwd=str(parent),
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                raise GitSyncError(f"Clone failed: {result.stderr.strip()}")
        except FileNotFoundError:
            raise GitSyncError("git is not installed or not in PATH")

        return GitSyncResult(success=True, message="Repository cloned successfully")

    async def pull(self) -> GitSyncResult:
        """Pull latest from remote: fetch + reset --hard origin/main.

        Then resync the skill index if storage service is available.
        Auto-initializes the repository if not yet cloned.
        """
        self._check_configured()
        if not (self.skills_dir / ".git").is_dir():
            await self.init_or_clone()

        async with self._sync_lock:
            # Fetch
            await self._run_git("fetch", "origin")

            # Determine default branch
            branch = await self._get_default_branch()

            # Reset to remote
            result = await self._run_git("reset", "--hard", f"origin/{branch}")
            lines = result.stdout.strip().splitlines() if result.stdout else []

            # Resync index
            if self._skill_storage and hasattr(self._skill_storage, "resync_index"):
                await self._skill_storage.resync_index()

            return GitSyncResult(
                success=True,
                message=f"Pulled and reset to origin/{branch}",
                files_changed=len(lines),
            )

    async def push(self, message: str = "Sync skills") -> GitSyncResult:
        """Push synced skills to remote.

        Only stages files from skills that have sync:true in _config.json.
        Auto-initializes the repository if not yet cloned.
        """
        self._check_configured()
        if not (self.skills_dir / ".git").is_dir():
            await self.init_or_clone()

        async with self._sync_lock:
            # Find skills with sync:true
            synced_paths = self._get_synced_skill_dirs()
            if not synced_paths:
                return GitSyncResult(
                    success=True,
                    message="No synced skills to push",
                )

            # Stage only synced skill directories
            for skill_path in synced_paths:
                await self._run_git("add", skill_path)

            # Also add _index.json if present
            index_path = self.skills_dir / "_index.json"
            if index_path.exists():
                await self._run_git("add", "_index.json")

            # Check if there's anything to commit
            status_result = await self._run_git("status", "--porcelain", check=False)
            staged = [
                line for line in status_result.stdout.splitlines()
                if line and line[0] in ("A", "M", "D", "R")
            ]
            if not staged:
                return GitSyncResult(success=True, message="Nothing to push")

            # Commit and push
            await self._run_git("commit", "-m", message)
            branch = await self._get_default_branch()
            await self._run_git("push", "origin", branch)

            return GitSyncResult(
                success=True,
                message=f"Pushed {len(staged)} change(s) to origin/{branch}",
                files_changed=len(staged),
            )

    async def status(self) -> GitStatus:
        """Get current git status: local changes, ahead/behind counts."""
        git_status = GitStatus()

        if not (self.skills_dir / ".git").is_dir():
            git_status.error = "Not a git repository"
            return git_status

        git_status.initialized = True

        # Check remote
        remote_result = await self._run_git("remote", check=False)
        git_status.has_remote = bool(remote_result.stdout.strip())

        # Current branch
        branch_result = await self._run_git(
            "rev-parse", "--abbrev-ref", "HEAD", check=False
        )
        git_status.branch = branch_result.stdout.strip() if branch_result.returncode == 0 else ""

        # Local changes
        status_result = await self._run_git("status", "--porcelain", check=False)
        if status_result.returncode == 0 and status_result.stdout.strip():
            git_status.local_changes = [
                line.strip() for line in status_result.stdout.splitlines()
                if line.strip()
            ]

        # Ahead/behind (only if remote exists)
        if git_status.has_remote and git_status.branch:
            # Fetch first to get accurate counts
            await self._run_git("fetch", "origin", check=False)

            upstream = f"origin/{git_status.branch}"

            # Ahead
            ahead_result = await self._run_git(
                "rev-list", f"{upstream}..HEAD", "--count", check=False
            )
            if ahead_result.returncode == 0:
                git_status.ahead = int(ahead_result.stdout.strip() or "0")

            # Behind
            behind_result = await self._run_git(
                "rev-list", f"HEAD..{upstream}", "--count", check=False
            )
            if behind_result.returncode == 0:
                git_status.behind = int(behind_result.stdout.strip() or "0")

        # Last commit message
        log_result = await self._run_git(
            "log", "-1", "--format=%s", check=False
        )
        if log_result.returncode == 0:
            git_status.last_commit = log_result.stdout.strip()

        return git_status

    # -- helpers ----------------------------------------------------------

    async def _get_default_branch(self) -> str:
        """Detect the default branch (main or master)."""
        result = await self._run_git(
            "symbolic-ref", "refs/remotes/origin/HEAD", check=False
        )
        if result.returncode == 0:
            ref = result.stdout.strip()
            return ref.split("/")[-1]
        # Fallback: try main, then master
        for branch in ("main", "master"):
            check = await self._run_git(
                "rev-parse", "--verify", f"origin/{branch}", check=False
            )
            if check.returncode == 0:
                return branch
        return "main"

    def _get_synced_skill_dirs(self) -> list[str]:
        """Return relative paths of skill dirs with sync:true."""
        synced: list[str] = []
        if not self.skills_dir.is_dir():
            return synced
        for entry in sorted(self.skills_dir.iterdir()):
            if not entry.is_dir() or entry.name.startswith((".", "_")):
                continue
            config_path = entry / "_config.json"
            if config_path.exists():
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        config = json.load(f)
                    if config.get("sync", False):
                        synced.append(entry.name)
                except (json.JSONDecodeError, OSError):
                    continue
        return synced


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class GitSyncError(Exception):
    """General git sync error."""


class GitSyncNotConfigured(Exception):
    """Raised when FORGE_SKILLS_REPO_URL is not set."""
