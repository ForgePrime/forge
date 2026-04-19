"""Unit tests for services/github_pr — starter PR flow.

No live GitHub required — httpx client is injected + mocked.
"""
import pytest
from unittest.mock import MagicMock

from app.services.github_pr import (
    GitHubConfig, GitHubError, create_pr, get_pr_status,
)


# ---------- GitHubConfig.from_env ----------

def test_config_from_env_raises_when_incomplete(monkeypatch):
    monkeypatch.delenv("FORGE_GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("FORGE_GITHUB_REPO_OWNER", raising=False)
    monkeypatch.delenv("FORGE_GITHUB_REPO_NAME", raising=False)
    with pytest.raises(GitHubError) as exc:
        GitHubConfig.from_env()
    assert "not configured" in str(exc.value).lower()
    assert "FORGE_GITHUB_TOKEN" in str(exc.value)


def test_config_from_env_happy(monkeypatch):
    monkeypatch.setenv("FORGE_GITHUB_TOKEN", "ghp_xxx")
    monkeypatch.setenv("FORGE_GITHUB_REPO_OWNER", "acme")
    monkeypatch.setenv("FORGE_GITHUB_REPO_NAME", "api")
    cfg = GitHubConfig.from_env()
    assert cfg.token == "ghp_xxx"
    assert cfg.owner == "acme"
    assert cfg.repo == "api"
    assert cfg.base_branch == "main"  # default


def test_config_from_env_base_branch_override(monkeypatch):
    monkeypatch.setenv("FORGE_GITHUB_TOKEN", "t")
    monkeypatch.setenv("FORGE_GITHUB_REPO_OWNER", "o")
    monkeypatch.setenv("FORGE_GITHUB_REPO_NAME", "r")
    monkeypatch.setenv("FORGE_GITHUB_BASE", "develop")
    cfg = GitHubConfig.from_env()
    assert cfg.base_branch == "develop"


def test_config_partial_env_lists_missing(monkeypatch):
    monkeypatch.setenv("FORGE_GITHUB_TOKEN", "t")
    monkeypatch.delenv("FORGE_GITHUB_REPO_OWNER", raising=False)
    monkeypatch.delenv("FORGE_GITHUB_REPO_NAME", raising=False)
    with pytest.raises(GitHubError) as exc:
        GitHubConfig.from_env()
    assert "REPO_OWNER" in str(exc.value)
    assert "REPO_NAME" in str(exc.value)
    assert "TOKEN" not in str(exc.value)  # token was set


# ---------- create_pr ----------

def _mock_client(response_status: int, response_body: dict | None = None, response_text: str = ""):
    c = MagicMock()
    resp = MagicMock()
    resp.status_code = response_status
    resp.json.return_value = response_body or {}
    resp.text = response_text or ""
    c.post.return_value = resp
    c.get.return_value = resp
    return c


def test_create_pr_success():
    cfg = GitHubConfig(token="t", owner="o", repo="r")
    fake_body = {
        "number": 42,
        "html_url": "https://github.com/o/r/pull/42",
        "title": "[T-1] demo",
    }
    client = _mock_client(201, fake_body)
    result = create_pr(cfg, head_branch="forge/t-1",
                       title="[T-1] demo", body="ok", client=client)
    assert result["number"] == 42
    assert result["html_url"].endswith("/pull/42")
    # POST called with expected URL + headers
    client.post.assert_called_once()
    call = client.post.call_args
    assert "/repos/o/r/pulls" in call.args[0]
    assert call.kwargs["json"]["head"] == "forge/t-1"
    assert call.kwargs["json"]["base"] == "main"


def test_create_pr_honors_base_override():
    cfg = GitHubConfig(token="t", owner="o", repo="r", base_branch="main")
    client = _mock_client(201, {"number": 1})
    create_pr(cfg, head_branch="b", title="t", body="b",
              base_branch="develop", client=client)
    assert client.post.call_args.kwargs["json"]["base"] == "develop"


def test_create_pr_raises_on_4xx():
    cfg = GitHubConfig(token="t", owner="o", repo="r")
    client = _mock_client(422, {}, "validation failed")
    with pytest.raises(GitHubError) as exc:
        create_pr(cfg, head_branch="b", title="t", body="b", client=client)
    assert exc.value.status_code == 422
    assert "422" in str(exc.value)


def test_create_pr_raises_on_network_error():
    import httpx
    cfg = GitHubConfig(token="t", owner="o", repo="r")
    client = MagicMock()
    client.post.side_effect = httpx.ConnectError("DNS failed")
    with pytest.raises(GitHubError) as exc:
        create_pr(cfg, head_branch="b", title="t", body="b", client=client)
    assert "network error" in str(exc.value).lower()


def test_create_pr_sends_auth_header():
    cfg = GitHubConfig(token="ghp_secret", owner="o", repo="r")
    client = _mock_client(201, {"number": 1})
    create_pr(cfg, head_branch="b", title="t", body="b", client=client)
    headers = client.post.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer ghp_secret"
    assert "application/vnd.github" in headers["Accept"]


# ---------- get_pr_status ----------

def test_get_pr_status_projects_minimal_fields():
    """Full API body is large; service returns the projection we need."""
    cfg = GitHubConfig(token="t", owner="o", repo="r")
    full_body = {
        "number": 7,
        "state": "open",
        "merged": False,
        "mergeable": True,
        "html_url": "https://github.com/o/r/pull/7",
        "title": "[T-7] hello",
        "head": {"ref": "forge/t-7", "sha": "abc"},
        "base": {"ref": "main"},
        "lots_of_other_fields": "ignored",
    }
    client = _mock_client(200, full_body)
    out = get_pr_status(cfg, 7, client=client)
    assert out["number"] == 7
    assert out["state"] == "open"
    assert out["merged"] is False
    assert out["head_ref"] == "forge/t-7"
    assert out["base_ref"] == "main"
    # Noise not leaked
    assert "lots_of_other_fields" not in out


def test_get_pr_status_merged_state():
    cfg = GitHubConfig(token="t", owner="o", repo="r")
    body = {
        "number": 7, "state": "closed", "merged": True, "mergeable": None,
        "html_url": "x", "title": "x", "head": {"ref": "b"}, "base": {"ref": "main"},
    }
    client = _mock_client(200, body)
    out = get_pr_status(cfg, 7, client=client)
    assert out["state"] == "closed"
    assert out["merged"] is True


def test_get_pr_status_raises_on_404():
    cfg = GitHubConfig(token="t", owner="o", repo="r")
    client = _mock_client(404, {}, "not found")
    with pytest.raises(GitHubError) as exc:
        get_pr_status(cfg, 999, client=client)
    assert exc.value.status_code == 404
