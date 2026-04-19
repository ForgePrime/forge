# Wiring Guide — activating starter services in production

Several services landed in the autonomous 2026-04-19 session as
standalone tools with test coverage but intentionally NOT wired into
hot paths. The reason was avoiding surprise failures for existing
callers / tests while the user is asleep. This document consolidates
the wiring decisions you need to make before going to production.

Each section is: **what the tool does → decision knobs → recipe →
rollback pointer**.

Read this top-to-bottom before first external-client deploy.

---

## 1. PII scanner → `/ingest` endpoint

**What it does:** `services/pii_scanner.py` regex-detects EMAIL, PHONE,
IBAN, PESEL, CREDIT_CARD (Luhn-verified), IP_ADDRESS, SSN in any text.
Returns `scan_then_decide(text)` → `"pass" | "warn" | "block"`.

**Why it isn't wired:** `/ingest` today accepts source documents whole,
including test fixtures that may contain fake-but-Luhn-valid card
numbers. Auto-blocking on upload would break existing test data.

**Decision you need to make:**
- Default posture: `block` / `warn` / `redact-inline` / `pass-through-with-flag`
- Per-project override? (Add `pii_policy` column to `organizations`
  or `projects`?)
- Who gets notified on block? (Upload fails → user sees 422; audit
  log gets entry.)

**Recipe (posture = `warn+annotate`, least-disruptive starting point):**

```python
# In app/api/pipeline.py, ingest_documents(), before saving Knowledge:
from app.services.pii_scanner import scan_then_decide

for f in files:
    # ... existing code to read content ...
    findings, decision = scan_then_decide(content)
    pii_meta = {
        "decision": decision,
        "findings_count": len(findings),
        "types": sorted({f.type for f in findings}),
    }
    if decision == "block":  # only when posture=block
        raise HTTPException(422, f"PII detected in {f.filename}: {pii_meta}")
    k = Knowledge(
        # ... existing fields ...
        # Add to Knowledge model first:
        #   pii_scan: Mapped[dict | None] = mapped_column(JSONB)
        # + migration for `pii_scan` column
        pii_scan=pii_meta,
    )
```

**Rollback:** delete the `pii_scan` field assignment and the
`scan_then_decide` call. Pre-wiring state is preserved (no model
fields depend on this).

---

## 2. Rate limiter → per-endpoint guardrails

**What it does:** `services/rate_limit.py` — sliding-window counter
on Redis. `check_rate_limit(key, max_per_window, window_sec)` raises
`RateLimitExceeded` when breached.

**Why it isn't middleware-global:** would 429-reject integration
tests that hammer `/api/v1`. Per-endpoint opt-in is safer.

**Decision you need to make:**
- Which endpoints need limits? (`/api/v1/auth/login` for brute-
  force protection is the obvious first target; `/ingest` for abuse;
  `/orchestrate` for runaway-cost protection.)
- Limit numbers: start conservative (10/min per IP on login), tune
  with traffic measurement.

**Recipe (login brute-force protection):**

```python
# In app/api/auth.py (or wherever login handler lives):
from app.services.rate_limit import check_rate_limit, RateLimitExceeded

@router.post("/auth/login")
def login(request: Request, body: LoginBody, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    try:
        check_rate_limit(
            key=f"login:ip:{client_ip}",
            max_per_window=10,     # 10 attempts
            window_sec=60,         # per minute
        )
    except RateLimitExceeded as e:
        raise HTTPException(
            status_code=429,
            detail={"error": "too_many_requests", "retry_after": e.retry_after},
            headers={"Retry-After": str(e.retry_after)},
        )
    # ... existing login logic ...
```

**Recipe (orchestrate cost-protection):**

```python
# Already-auth'd user — key by user_id + project for precision
try:
    check_rate_limit(
        key=f"orchestrate:user:{user.id}:proj:{proj.id}",
        max_per_window=5,
        window_sec=3600,  # 5 orchestrate runs per hour per user+project
    )
except RateLimitExceeded as e:
    raise HTTPException(429, ...)
```

**Rollback:** remove the `check_rate_limit` + try/except block; no DB
state change involved.

**Strict vs lenient mode:** `FORGE_RATE_LIMIT_FAIL_CLOSED=1` env flips
behavior when Redis is unavailable. Default fail-open (allow, log
warning) is correct for most deployments; set to 1 only if your
security model requires hard denial when the cache is down.

---

## 3. Data retention sweep → scheduled

**What it does:** `services/data_retention.py` + admin endpoint
`POST /api/v1/tier1/gdpr/retention/sweep` deletes rows older than
per-entity TTL (LLMCall 180d, AuditLog 365d, OrchestrateRun 365d).

**Why it isn't scheduled:** Forge has no built-in job scheduler
(Celery/APScheduler/etc.). Decision-heavy addition.

**Decision you need to make:**
- Schedule mechanism: external cron? systemd timer? APScheduler in-
  process? Cloud scheduler (AWS EventBridge / GCP Cloud Scheduler)?
- Schedule frequency: weekly? daily? (Weekly is standard; daily if
  storage growth is aggressive.)
- Dry-run notification: do you want a Slack/email digest of what
  would be deleted before flipping to real?

**Recipe (systemd timer on the host):**

```ini
# /etc/systemd/system/forge-retention.service
[Unit]
Description=Forge GDPR retention sweep
After=network.target

[Service]
Type=oneshot
Environment=FORGE_API_URL=https://forge.example.com
Environment=FORGE_ADMIN_TOKEN=<your-owner-JWT>
ExecStart=/usr/bin/curl -sf -X POST \
  -H "Authorization: Bearer ${FORGE_ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false}' \
  "${FORGE_API_URL}/api/v1/tier1/gdpr/retention/sweep"
```

```ini
# /etc/systemd/system/forge-retention.timer
[Unit]
Description=Run Forge retention sweep weekly

[Timer]
OnCalendar=Mon 03:30
Persistent=true

[Install]
WantedBy=timers.target
```

Enable: `systemctl enable --now forge-retention.timer`.

**First-week protocol:**
1. Run with `dry_run: true` for a week, log output.
2. Review: does the predicted delete volume match your expectation?
3. Flip `dry_run: false` after week-1 review.

**Rollback:** `systemctl disable --now forge-retention.timer`. The
sweep endpoint remains (harmless — callers must explicitly invoke).

---

## 4. N+1 query profiler → request middleware

**What it does:** `services/query_profiler.py` + `QueryProfilerMiddleware`.
Per-request SQL statement tally; WARNING log when a normalized
statement runs ≥ threshold (default 5) times in one request.

**Why it's opt-in:** diagnostic output (WARNING logs) would flood
logs in hot paths; wiring at launch risks masking real errors under
N+1 spam.

**Decision you need to make:** just flip the env:

```bash
# Staging: on, observe for a week
FORGE_PROFILE_NPLUS1=true uvicorn app.main:app --workers 2

# Adjust threshold if default=5 is too noisy
FORGE_PROFILE_NPLUS1=true FORGE_NPLUS1_THRESHOLD=10 uvicorn ...
```

**Operational pattern:**
1. Enable in staging. Let it run one realistic workload cycle.
2. Grep WARNING logs for `n+1 detected` + group by normalized
   statement + route.
3. Top offenders → investigate (likely missing `selectinload`/
   `joinedload` on SQLAlchemy relationships).
4. Fix. Re-run. Repeat until the only findings are expected
   (e.g., legitimate bulk reads).
5. **Do NOT leave enabled in production** unless log volume is under
   control — the profiler itself is cheap but its output logs can be
   expensive to ship.

**Rollback:** unset the env var; middleware becomes no-op.

---

## 5.5 Pre-commit hooks → activated

**What it provides:** `.pre-commit-config.yaml` ships with hygiene hooks
(trailing whitespace, EOL fixer, YAML/JSON validity, large-file check,
merge-conflict marker detection, debug-statement + private-key catchers),
plus ruff lint, ruff format-check, and bandit in non-blocking mode.

**Activate:**

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files   # first run against whole tree
```

**After baseline clean:**
- Remove `--exit-zero` from ruff hook args
- Remove `-lll` from bandit hook args (flip to MEDIUM sensitivity)
- Consider enabling gitleaks hook (stronger secret detection)

**Rollback:** `pre-commit uninstall`. Config file stays.

---

## 5. CI security/lint → strict mode

**What it does:** `.github/workflows/ci.yml` runs pip-audit + bandit +
ruff on every PR. Currently `continue-on-error: true` on those jobs —
they report findings but don't fail the build.

**Why starter mode:** forcing a clean baseline on first push = CI red
on day 1 = onboarding friction.

**Decision you need to make:** after ~1 week of observing CI output:
1. Review pip-audit findings. Patch vulnerable deps (bump versions).
2. Review bandit findings. Suppress false positives with `# nosec`
   inline, fix real issues.
3. Review ruff findings. Add `ruff.toml` with your style preferences;
   fix or ignore per rule.
4. Flip `continue-on-error: true` → `continue-on-error: false` on
   each job individually as its baseline goes clean.

**Rollback:** flip back to `true` if a finding blocks a release.

---

## 6. Production readiness checklist (final pre-launch sanity)

Before any external-client deploy, complete this checklist:

- [ ] `.env` has FORGE_JWT_SECRET + FORGE_ENCRYPTION_KEY + POSTGRES_PASSWORD set from `openssl rand` output (not defaults)
- [ ] Reverse proxy in front (docs/DEPLOY.md § TLS termination); `curl https://domain/ready` returns 200
- [ ] Backup cron active (docs/DEPLOY.md § Backup); one successful nightly dump visible in `$BACKUP_DIR`
- [ ] Monthly restore verification run (docs/DEPLOY.md § Restore verification) with date logged
- [ ] k6 load test baseline recorded (docs/DEPLOY.md § Load testing; values match SLO-1/2/3)
- [ ] Data retention sweep scheduled (§ 3 above; week-1 dry-run review complete)
- [ ] Rate limiter wired on at least `/auth/login` (§ 2 above)
- [ ] PII scanner wired with chosen posture (§ 1 above)
- [ ] CI workflows activated on GitHub side; main push triggers green build
- [ ] First owner user + org created; first project ingested end-to-end in staging
- [ ] First orchestrate run completes; task_report renders; challenger + scrutiny strip visible

When all boxes are checked, you are ≥ 95% CGAID-compliant and
≥ AMBER on every enterprise-audit category.

---

## Changelog

- **v1.0 (2026-04-19, autonomous session)** — Initial consolidation of
  wiring instructions for 5 standalone services + CI strict-mode flip
  + pre-launch checklist.
