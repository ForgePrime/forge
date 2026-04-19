"""GitHub PR integration — push Forge workspace branch + open PR + check status.

Zero new Python deps: uses the `httpx` already in the venv (0.27+) and
`git` subprocess for the push itself.

Decision #7 A — starter mode. Standalone functions; orchestrate auto-
integration deferred until the `FORGE_GITHUB_TOKEN` env is confirmed
working against a real repo.

Config via env (or Settings):
  FORGE_GITHUB_TOKEN       — PAT or GitHub App token with `repo` scope
  FORGE_GITHUB_REPO_OWNER  — e.g. "acme-corp"
  FORGE_GITHUB_REPO_NAME   — e.g. "payments-api"
  FORGE_GITHUB_BASE        — default base branch (optional; default "main")

Design notes:
- `Assisted-by` trailer already lands on commits via git_verify (v1.2).
  The HUMAN opening the PR (via this service) becomes the legal author
  per the Linux Kernel 2026 policy.
- We DO NOT auto-merge. Reviewer approval + merge button remain human-
  driven — that is the whole point of the PR review gate.
- Failures (auth, network, repo not found) raise GitHubError; caller
  decides whether to 500 or surface to the UI.

Tests mock the httpx client — no live GitHub required for unit tests.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import Any

import httpx


class GitHubError(Exception):
    """Raised on any GitHub API failure — auth, network, 4xx/5xx."""

    def __init__(self, message: str, status_code: int | None = None, response_body: str | None = None):
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message)


@dataclass
class GitHubConfig:
    token: str
    owner: str
    repo: str
    base_branch: str = "main"

    @classmethod
    def from_env(cls) -> "GitHubConfig":
        """Build config from FORGE_GITHUB_* env vars. Raises GitHubError if incomplete."""
        token = os.environ.get("FORGE_GITHUB_TOKEN", "").strip()
        owner = os.environ.get("FORGE_GITHUB_REPO_OWNER", "").strip()
        repo = os.environ.get("FORGE_GITHUB_REPO_NAME", "").strip()
        base = os.environ.get("FORGE_GITHUB_BASE", "main").strip() or "main"
        missing = [k for k, v in (
            ("FORGE_GITHUB_TOKEN", token),
            ("FORGE_GITHUB_REPO_OWNER", owner),
            ("FORGE_GITHUB_REPO_NAME", repo),
        ) if not v]
        if missing:
            raise GitHubError(
                f"GitHub integration not configured — missing env: {', '.join(missing)}"
            )
        return cls(token=token, owner=owner, repo=repo, base_branch=base)


# ---------- git push helpers ----------

def push_branch(workspace_dir: str, branch_name: str, remote: str = "origin") -> tuple[bool, str]:
    """Push current HEAD of `workspace_dir` to `remote`/`branch_name`.

    Returns (success, detail_message). Does not touch Forge DB.
    Callers are responsible for creating the branch and committing first
    (Forge's git_verify.commit_all handles that for orchestrate workflow).
    """
    try:
        # Create local branch at current HEAD if it doesn't exist
        subprocess.run(
            ["git", "-C", workspace_dir, "branch", "-f", branch_name],
            capture_output=True, check=True, timeout=15,
        )
        # Push to remote with --set-upstream
        proc = subprocess.run(
            ["git", "-C", workspace_dir, "push", "-u", remote, branch_name],
            capture_output=True, text=True, timeout=60,
        )
    except subprocess.TimeoutExpired:
        return False, f"git push timeout after 60s"
    except subprocess.CalledProcessError as e:
        return False, f"git branch failed: {e.stderr.decode('utf-8', errors='replace') if e.stderr else ''}"
    except FileNotFoundError:
        return False, "git binary not found"

    if proc.returncode != 0:
        return False, f"git push failed (rc={proc.returncode}): {proc.stderr[:500]}"
    return True, proc.stdout or "pushed"


# ---------- GitHub REST API ----------

_API_BASE = "https://api.github.com"


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "forge-platform",
    }


def create_pr(
    cfg: GitHubConfig,
    head_branch: str,
    title: str,
    body: str,
    *,
    base_branch: str | None = None,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """POST /repos/{owner}/{repo}/pulls — create a pull request.

    Returns the parsed JSON response on success.
    Raises GitHubError on any non-2xx.
    """
    url = f"{_API_BASE}/repos/{cfg.owner}/{cfg.repo}/pulls"
    payload = {
        "title": title,
        "body": body,
        "head": head_branch,
        "base": base_branch or cfg.base_branch,
    }
    _client = client or httpx.Client(timeout=30.0)
    try:
        resp = _client.post(url, json=payload, headers=_headers(cfg.token))
    except httpx.HTTPError as e:
        raise GitHubError(f"GitHub network error: {type(e).__name__}: {e}")
    finally:
        if client is None:
            _client.close()

    if resp.status_code < 200 or resp.status_code >= 300:
        raise GitHubError(
            f"GitHub PR creation failed: HTTP {resp.status_code}",
            status_code=resp.status_code,
            response_body=resp.text[:1000],
        )
    return resp.json()


def get_pr_status(
    cfg: GitHubConfig,
    pr_number: int,
    *,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """GET /repos/{owner}/{repo}/pulls/{pr_number} — fetch PR state + merge status.

    Returns {state, merged, mergeable, reviews_count, ...} — minimal projection.
    Raises GitHubError on non-2xx.
    """
    url = f"{_API_BASE}/repos/{cfg.owner}/{cfg.repo}/pulls/{pr_number}"
    _client = client or httpx.Client(timeout=30.0)
    try:
        resp = _client.get(url, headers=_headers(cfg.token))
    except httpx.HTTPError as e:
        raise GitHubError(f"GitHub network error: {type(e).__name__}: {e}")
    finally:
        if client is None:
            _client.close()

    if resp.status_code < 200 or resp.status_code >= 300:
        raise GitHubError(
            f"GitHub PR fetch failed: HTTP {resp.status_code}",
            status_code=resp.status_code,
            response_body=resp.text[:1000],
        )
    body = resp.json()
    return {
        "number": body.get("number"),
        "state": body.get("state"),           # "open" | "closed"
        "merged": body.get("merged", False),
        "mergeable": body.get("mergeable"),
        "html_url": body.get("html_url"),
        "title": body.get("title"),
        "head_ref": (body.get("head") or {}).get("ref"),
        "base_ref": (body.get("base") or {}).get("ref"),
    }


def open_pr_for_task(
    workspace_dir: str,
    task_external_id: str,
    task_name: str,
    assisted_by: str = "",
    *,
    cfg: GitHubConfig | None = None,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Convenience: push a branch named `forge/{task_ext_id}` + open PR.

    Returns {pr_number, html_url, branch} on success. Raises GitHubError
    on config/network/API issues. Caller (admin endpoint, orchestrate
    hook, etc.) catches and surfaces to user.
    """
    cfg = cfg or GitHubConfig.from_env()
    branch = f"forge/{task_external_id.lower()}"

    ok, detail = push_branch(workspace_dir, branch)
    if not ok:
        raise GitHubError(f"push failed: {detail}")

    title = f"[{task_external_id}] {task_name}"
    body_parts = [
        f"Task: {task_external_id}",
        f"Name: {task_name}",
    ]
    if assisted_by:
        body_parts.append("")
        body_parts.append(f"{assisted_by}")
    body = "\n".join(body_parts)

    pr = create_pr(cfg, head_branch=branch, title=title, body=body, client=client)
    return {
        "pr_number": pr.get("number"),
        "html_url": pr.get("html_url"),
        "branch": branch,
    }
