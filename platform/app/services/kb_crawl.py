"""Knowledge-base ingestion (C4 URL crawler + C5 folder scanner).

C4 URL crawler:
  - httpx fetch with 10s timeout, follow redirects
  - BeautifulSoup text extraction (strip script/style)
  - Truncate to 200k chars (Postgres TEXT safe)
  - Returns (content, title_from_html)

C5 Folder scanner:
  - Walk path recursively
  - Skip binary files (by extension + size)
  - Respect include/ignore globs (user-provided)
  - Returns list of (relative_path, content_preview)
"""
import fnmatch
import os
from dataclasses import dataclass


DEFAULT_IGNORES = {
    ".git", ".venv", "venv", "__pycache__", "node_modules", "dist", "build",
    ".pytest_cache", ".mypy_cache", ".next", ".nuxt", "target", "vendor",
}
DEFAULT_BINARY_EXTS = {
    ".pyc", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".zip", ".tar",
    ".gz", ".7z", ".exe", ".dll", ".so", ".dylib", ".class", ".jar",
    ".mp3", ".mp4", ".mov", ".avi", ".ico", ".woff", ".woff2", ".ttf",
}
MAX_FILE_BYTES = 500_000
MAX_FOLDER_SAMPLES = 200


@dataclass
class CrawlResult:
    ok: bool
    title: str | None = None
    content: str = ""
    status_code: int | None = None
    error: str | None = None


def crawl_url(url: str, timeout_sec: int = 10,
              headers: dict | None = None) -> CrawlResult:
    """Fetch URL + extract plain text via BeautifulSoup."""
    try:
        import httpx
        from bs4 import BeautifulSoup
    except ImportError as e:
        return CrawlResult(ok=False, error=f"dependency missing: {e}")

    try:
        with httpx.Client(follow_redirects=True, timeout=timeout_sec) as client:
            r = client.get(url, headers=headers or {})
            content_type = r.headers.get("content-type", "")
            if r.status_code >= 400:
                return CrawlResult(ok=False, status_code=r.status_code,
                                   error=f"HTTP {r.status_code}")
            if "html" in content_type:
                soup = BeautifulSoup(r.text, "html.parser")
                # Remove script/style/nav/footer
                for tag in soup(["script", "style", "noscript"]):
                    tag.decompose()
                title = (soup.title.string.strip() if soup.title and soup.title.string else None)
                # Collapse whitespace
                text = soup.get_text(separator="\n").strip()
                lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
                content = "\n".join(lines)[:200_000]
                return CrawlResult(ok=True, title=title, content=content,
                                   status_code=r.status_code)
            elif content_type.startswith(("text/", "application/json",
                                          "application/xml")):
                return CrawlResult(ok=True, content=r.text[:200_000],
                                   status_code=r.status_code)
            else:
                return CrawlResult(ok=False, status_code=r.status_code,
                                   error=f"unsupported content-type: {content_type}")
    except Exception as e:
        return CrawlResult(ok=False, error=f"{type(e).__name__}: {e}")


@dataclass
class FolderScanResult:
    ok: bool
    files_found: int
    text_files: int
    samples: list[dict]  # [{path, size, preview}]
    error: str | None = None


def scan_folder(root: str, *, include_globs: list[str] | None = None,
                ignore_globs: list[str] | None = None,
                max_samples: int = MAX_FOLDER_SAMPLES) -> FolderScanResult:
    """Walk a folder recursively, return a capped sample of text files with previews."""
    if not os.path.isdir(root):
        return FolderScanResult(ok=False, files_found=0, text_files=0, samples=[],
                                error=f"not a directory: {root}")
    include_globs = include_globs or ["*"]
    ignore_globs = ignore_globs or []
    files_found = 0
    text_files = 0
    samples: list[dict] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune default-ignored dirs in-place
        dirnames[:] = [d for d in dirnames if d not in DEFAULT_IGNORES]
        for fn in filenames:
            files_found += 1
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            # user-ignore
            if any(fnmatch.fnmatch(rel, pat) for pat in ignore_globs):
                continue
            # include
            if not any(fnmatch.fnmatch(rel, pat) for pat in include_globs):
                continue
            ext = os.path.splitext(fn)[1].lower()
            if ext in DEFAULT_BINARY_EXTS:
                continue
            try:
                size = os.path.getsize(full)
            except OSError:
                continue
            if size > MAX_FILE_BYTES:
                continue
            text_files += 1
            if len(samples) >= max_samples:
                continue
            # Read as text (attempt utf-8, fall back to latin-1 preview)
            try:
                with open(full, "r", encoding="utf-8", errors="replace") as f:
                    preview = f.read(4000)
            except OSError:
                continue
            samples.append({"path": rel.replace("\\", "/"), "size": size,
                            "preview": preview})
    return FolderScanResult(ok=True, files_found=files_found,
                            text_files=text_files, samples=samples)
