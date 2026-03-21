"""Platform compatibility helpers for Forge core."""

import os
import sys

_configured = False


def configure_encoding():
    """Configure stdout/stderr for UTF-8 on Windows. Safe to call multiple times."""
    global _configured
    if _configured:
        return
    _configured = True
    if sys.platform == "win32":
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
