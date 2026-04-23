#!/bin/bash
# ITRP Standards Enforcement Hook
# Runs after every Edit/Write on Python and TypeScript files.
# Catches violations that skills alone cannot enforce deterministically.
#
# Exit 0 = allow (with warnings on stderr)
# Exit 2 = BLOCK (violation too severe)

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

EXT="${FILE_PATH##*.}"
BASENAME=$(basename "$FILE_PATH")
ERRORS=0
WARNINGS=0

# ── Python checks ──────────────────────────────────────────────────

if [[ "$EXT" == "py" ]]; then

  # 1. Router with DB access (standards.md §2.1)
  if echo "$BASENAME" | grep -q "router"; then
    if grep -n "db\.collection\|client\.query\|\.document(\|get_bq_client\|bigquery\.Client" "$FILE_PATH" 2>/dev/null | grep -v "^#\|#.*$\|from \|import " | head -3; then
      echo "⛔ STANDARDS VIOLATION: router.py has DB access (standards.md §2.1 — router must be thin, NO DB)" >&2
      WARNINGS=$((WARNINGS + 1))
    fi
  fi

  # 2. except Exception: pass (standards.md §2.6)
  if grep -n "except.*Exception.*:.*pass$\|except.*:.*pass$" "$FILE_PATH" 2>/dev/null | head -3; then
    echo "⛔ STANDARDS VIOLATION: 'except Exception: pass' found (standards.md §2.6)" >&2
    WARNINGS=$((WARNINGS + 1))
  fi

  # 3. Logger used but not defined (most common runtime error)
  if grep -q "logger\.\(info\|warning\|error\|debug\|exception\)" "$FILE_PATH" 2>/dev/null; then
    if ! grep -q "logger.*=.*structlog\|logger.*=.*get_logger\|logger.*=.*logging" "$FILE_PATH" 2>/dev/null; then
      echo "⛔ RUNTIME ERROR: logger.xxx() used but 'logger = structlog.get_logger()' not found in file (standards.md §2.5)" >&2
      ERRORS=$((ERRORS + 1))
    fi
  fi

  # 4. Any in type hints (standards.md §2.3)
  if grep -n ": Any\b\|-> Any\b\|Dict\[str, Any\]\|dict\[str, Any\]" "$FILE_PATH" 2>/dev/null | grep -v "^#\|#.*$\|import \|from " | head -3; then
    echo "⚠️  WARNING: 'Any' found in type hints (standards.md §2.3 — avoid Any)" >&2
    WARNINGS=$((WARNINGS + 1))
  fi

  # 5. Cross-project imports (pipeline ↔ backend)
  if echo "$FILE_PATH" | grep -q "warsaw_data_pipeline"; then
    if grep -n "from app\.\|import app\." "$FILE_PATH" 2>/dev/null | head -3; then
      echo "⛔ DEPLOYMENT ERROR: Pipeline file imports from 'app.*' — separate containers! (standards.md §7)" >&2
      ERRORS=$((ERRORS + 1))
    fi
  fi
  if echo "$FILE_PATH" | grep -q "backend/app"; then
    if grep -n "from warsaw_data_pipeline\|import warsaw_data_pipeline" "$FILE_PATH" 2>/dev/null | head -3; then
      echo "⛔ DEPLOYMENT ERROR: Backend imports from 'warsaw_data_pipeline' — separate containers! (standards.md §7)" >&2
      ERRORS=$((ERRORS + 1))
    fi
  fi

  # 6. Python syntax check
  python3 -c "import ast; ast.parse(open('$FILE_PATH').read())" 2>/dev/null
  if [ $? -ne 0 ]; then
    echo "⛔ SYNTAX ERROR: Python file has syntax errors" >&2
    ERRORS=$((ERRORS + 1))
  fi

fi

# ── TypeScript checks ──────────────────────────────────────────────

if [[ "$EXT" == "ts" || "$EXT" == "tsx" ]]; then

  # 1. 'any' type (standards.md §3.4)
  if grep -n ": any\b\|as any\b\|<any>" "$FILE_PATH" 2>/dev/null | grep -v "^.*//\|/\*\|eslint-disable" | head -3; then
    echo "⚠️  WARNING: 'any' type found in TypeScript (standards.md §3.4 — strict types required)" >&2
    WARNINGS=$((WARNINGS + 1))
  fi

fi

# ── Report ─────────────────────────────────────────────────────────

if [ $ERRORS -gt 0 ]; then
  echo "" >&2
  echo "❌ $ERRORS error(s), $WARNINGS warning(s) — FIX ERRORS before proceeding" >&2
  exit 2  # BLOCK
fi

if [ $WARNINGS -gt 0 ]; then
  echo "" >&2
  echo "⚠️  $WARNINGS warning(s) — review before committing" >&2
fi

exit 0
