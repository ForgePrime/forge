# FORGE_PRODUCTIZATION_PLAN.md

**Autor:** Planning agent
**Data:** 2026-04-17
**Status:** Draft for founder review

---

## 1. Executive Summary

**Co mamy.** Forge to zweryfikowany prototyp platformy meta-promptingu, który jako jedyny znany system **nie ufa deklaracjom AI**: sam uruchamia testy (Phase A), ekstrahuje decyzje + findingi z reasoningu (Phase B), wystawia challenge cross-model (Opus weryfikuje Sonneta, Phase C) i dostarcza bootstrap docker-compose dla workspace'ów. Działające E2E na 2 scenariuszach. UI Jinja2/HTMX (Phase D) renderuje pełen "trustworthy DONE report". Budowany solo, koszt dowodu wartości: ~$20 per task w pełnym trybie C.

**Co nie działa / czego brakuje.** Brak auth, single-tenant, orchestrate blokuje HTTP request 10-30 min (brak async queue), brak budżetu per projekt, brak observability, brak push/PR do git, brak SSO, brak compliance artefaktów, brak team collaboration, 33+ endpointów CRUD brakuje (UX agent), guidelines/skills nie są first-class w UI, audit log nie widoczny w UI ani immutable.

**Unikatowy edge.** Konkurencja (Cursor, Windsurf, Devin, Aider, Claude Code) optymalizuje **szybkość i komfort dewelopera**. Ufają modelowi. Forge optymalizuje **accountability**: test execution, git verify, cross-model challenge, pełen audit. To nie jest konkurent Cursora w IDE — to **layer nadzoru** nad autonomiczną generacją kodu w kontekstach gdzie pomyłka jest droga (regulowane branże, enterprise delivery, audit/compliance).

**Gdzie możemy wygrać.** Nie wygramy na latencji IDE. Możemy wygrać na:
- **"Is this AI output deployable?"** — rynku nie ma, Forge odpowiada per-task
- **Regulated enterprises** (banking, healthcare, pharma, insurance, public sector) gdzie "AI self-report" nie przejdzie audytu
- **External delivery firms / software houses** (właśnie Lingaro!) które muszą udowodnić klientowi co zostało zrobione

**Strategia 3 fazy.**
1. **Phase 1 Pilot Commercial (3-4 miesiące, $180-280k):** bezpieczny, płatny pilot u 3-5 designowanych klientów (1 Lingaro-internal, 2-3 external warm leads). Obowiązkowe minimum: auth, multi-tenant, async orchestrate, budżet+alerty, git push/PR, PDF raport, backup, podstawowe compliance. Cena: $15-30k/miesiąc flat per klient.
2. **Phase 2 Enterprise v1 (6-9 miesięcy, $600k-1M):** skalowalna SaaS dla 20-50 klientów. SSO, RBAC, SOC2 Type I, webhooks, JIRA/GitHub integracje, team collaboration, SDK, marketplace guidelines/skills, observability.
3. **Phase 3 Enterprise v2 / Scale (12-18 miesięcy, $1.5-3M):** on-prem, private cloud, HIPAA/GDPR full, marketplace challenge personas, multi-model backend (Anthropic + OpenAI + custom), self-hosted challenger, assurance reports for auditors.

**Rekomendacja.** Iterować w fazach. Nie próbować konkurować z Cursorem/Devinem. Każdy etap kończy się shippable productem.

---

## 2. Market positioning & competitive analysis

### 2.1 Competitive landscape

| Produkt | Finansowanie | Pozycjonowanie | Słabość ważna dla Forge |
|---|---|---|---|
| Cursor | $100M+ | IDE-first speed | Ufa modelowi, brak weryfikacji |
| Windsurf | seed+ | IDE-first flow | jw. |
| Devin (Cognition) | $2B val | Autonomous SWE agent | Demo > reality, brak audit trail |
| Aider | OSS | Pair-programming CLI | Single-user, brak enterprise |
| Claude Code | Anthropic | Official CLI agent | Brak platform layer, brak traceability |
| GitHub Copilot Workspace | MS/GH | Zadaniowa automatyzacja w repo | Brak cross-model challenge, brak audit |
| Sourcegraph Cody | mid | Code-aware assist | Brak orchestrate verification |

**Uwaga asymetrii rynkowej.** Konkurenci biorą **developerów jako primary user**. Forge ma potencjał w **engineering management + compliance + delivery assurance** — innej osobie kupującej, innym workflow.

### 2.2 Forge Unique Value Proposition

"**Zobacz i udowodnij, co AI naprawdę dostarczyło.** Forge nie wierzy — odpala testy, robi cross-model challenge, ekstrahuje ukryte decyzje, trzyma pełen audit. Każda deliverka ma raport dla inżyniera, managera i audytora."

### 2.3 Czego Forge **nie będzie** robić

- Nie będzie IDE. Nie bije Cursora na latencji. Nie nadaje się do "daj mi komplecję tej funkcji".
- Nie będzie darmowy. Darmowy Aider jest lepszy dla hobbystów.
- Nie będzie polegać na jednym modelu — multi-model to feature, nie bug.
- Nie będzie dla 1-osobowych startupów (za duże tarcie vs Cursor). Minimum to zespół z compliance/audit requirement.

---

## 3. Target customer segments (3)

### Segment A — **Regulated Enterprise** (primary)

- **Charakterystyka:** banki, ubezpieczenia, pharma, healthcare, telco, sektor publiczny. Zespoły 50-500 dev. Formalny SDLC, audyt zewnętrzny, compliance (SOC 2, HIPAA, GDPR, DORA, ISO 27001).
- **Pain:** "Używamy GenAI ale security/compliance mówi STOP: nie możemy wypuścić kodu generowanego przez AI do produkcji bez formalnej weryfikacji i audit trail."
- **Buying signals:** wewnętrzna AI governance committee, odmowa security na Cursor, zatrzymany projekt LLM-assisted dev, zapisane wewnętrzne policy "AI output wymaga 2nd review".
- **Decydent:** VP Engineering / CTO / CISO (nie dev lead).
- **ACV (annual contract value):** $60k-$500k.
- **Sales cycle:** 3-9 miesięcy.
- **Moje obawy:** long sales, wymagają on-prem lub private cloud szybko.

### Segment B — **External Software Delivery** (warm, reachable)

- **Charakterystyka:** software houses, consulting (Lingaro sam jest case'em!), ludzie robiący fixed-price/SoW dla klientów. Zespoły 20-200.
- **Pain:** "Klient pyta 'co konkretnie zrobiliście i gdzie dowód?'. AI accelerates delivery ale nie da się udowodnić. Raportujemy ręce, slack, meetings." Dodatkowo: "Chcemy pokazać klientowi, że robimy to bezpieczniej niż on wewnętrznie."
- **Buying signals:** fixed-price contracts, klient pyta o AI governance, SoW-driven, wymagają sign-off per task.
- **Decydent:** Delivery manager / Head of Engineering / PMO.
- **ACV:** $30k-$150k.
- **Sales cycle:** 1-3 miesiące.
- **To nasz sweet spot na pilot.**

### Segment C — **AI-forward Engineering Teams in Mid-Market SaaS** (tail)

- **Charakterystyka:** series B/C SaaS, 50-300 dev, używają już Cursora/Copilota intensywnie, chcą iterować bezpieczniej.
- **Pain:** "Cursor rozpędził nam PR velocity ale mamy więcej prod incidentów. Potrzebujemy 2nd brain przed mergem."
- **Buying signals:** internal AI maturity push, "AI platform team" istnieje, wyższy churn po AI adopcji.
- **Decydent:** VP Eng / Platform lead.
- **ACV:** $20k-$80k.
- **Sales cycle:** 1-2 miesiące.

Segmenty A+B dają ~85% revenue. C to opcja rozszerzenia po Phase 2.

---

## 4. Pricing model hypotheses

Cztery modele, rekomendacja na dole:

| Model | Logika | Plus | Minus |
|---|---|---|---|
| **SaaS per-seat** | $X/user/month | Przewidywalne, prosto sprzedać | Forge nie skaluje per-user; dev wspólne projekty |
| **Per-task delivered** | $X per DONE task (phase A+B+C) | Zgodne z value (per-deliverable) | Zmienna, klient nie lubi niepewności kosztu |
| **% LLM spend + margin** | 25-40% narzut na LLM cost | Skaluje z wartością | Ciężko przewidzieć, klient chce flat |
| **Flat license + usage** | Base fee ($10k/mo) + per-task ($15-30) | Hybrid, daje floor + upside | Złożona umowa |
| **On-prem license** | $200k-$1M/rok + support | Dla Segment A wymusow | Wysoki cost to serve |

**Rekomendacja:**

- **Phase 1 Pilot:** Flat **$15-30k/mo/tenant** (nie per seat, nie per task). Prosta umowa, łatwy pilot, pokrywa koszty LLM (~$500-2k/mo/klient) z marżą. Klient płaci za outcome (platformę + run-rate) a nie za zgadywanie.
- **Phase 2 Enterprise v1:** Hybrid — **base $10k/mo + $20 per DONE task z pełną Phase A+B+C weryfikacją** (tj. płatna jest realna weryfikacja, nie mokra deklaracja). Oddaje naszą wartość.
- **Phase 3 Scale:** Dodanie **on-prem license $200k-$500k/rok** dla Segment A + **usage-based cloud** dla B+C.

Unikać: per-seat (nie skaluje z naszą wartością), pure per-task (skomplikowane rozliczenie LLM retries, challenge itd).

---

## 5. Phase 1: Pilot Commercial

### 5.1 Cel

Pierwszy płatny klient signed + jeden internal Lingaro pilot w <4 miesiącach. Walidacja: "czy ktoś zapłaci za accountability overhead".

### 5.2 Akceptacyjne kryteria pilot ready

- 3-5 klientów w LOI/MSA gotowi uruchomić pilot
- Pierwszy płatny kontrakt signed $15-30k/mo
- Zero data leaks, zero shared-tenant incidentów, SLA 99% w pilot period
- Klient akceptuje DONE report jako evidence wobec swojego PMO/klienta
- Pipeline A+B+C działa na 3 nowych, nietypowych scenariuszach (nie tylko Warehouse/Appointment)

### 5.3 Minimum features (MUST, z odniesieniem do kategorii gap A-M)

Używam notacji: `[Kat]  Feature  — effort dev-weeks`

**Krytyczne blokujące pilot:**

1. **[A] Auth + multi-tenant isolation** — 4 wk. Email+password + OTP, projects przypisane do org, row-level enforcement w API i UI, secrets per-tenant w vault (simple: encrypted at rest).
2. **[A] Secrets management dla klucza API** — 1 wk. Klucz Anthropic per-tenant, zaszyfrowane, nie w plaintext. Na starcie dedicated per-tenant key, bez "shared API".
3. **[B] Async orchestrate + job queue** — 3 wk. Arq albo RQ+Redis (nie Celery jeszcze — za ciężkie na pilot). `orchestrate_runs` table, SSE events, cancel, resume. Koniec blokowania HTTP 30 min.
4. **[B] Retry z idempotency + backup** — 2 wk. Task retry z hintem, daily pg_dump do S3, script to restore.
5. **[C] Budżet per projekt + hard stop + email alert** — 1.5 wk. `projects.budget_usd`, check przed każdym LLM call, email na 80% + stop na 100%. Bez tego klient się boi run-rate.
6. **[E] Challenge NEEDS_REWORK blokuje task DONE** — 0.5 wk. Dodać flag `require_challenge_pass=true` (per-project) + UI wskazanie, że task jest "quarantined".
7. **[G] Git push + PR** — 1.5 wk. `git_push` + GitHub/GitLab OAuth dla klienta + auto-otwarcie PR z body = trustworthy DONE report. To główna wartość dostawki (klient widzi PR w swoim repo).
8. **[G] PDF export raportu** — 1 wk. WeasyPrint, template A4, podpisany hash + timestamp. Klient ma asset dla PMO/audytora.
9. **[F] Observability minimum** — 1.5 wk. Structured logs (JSON + trace_id), OpenTelemetry traces do jednego backendu (rekomendacja: Grafana Cloud free tier na pilot), health endpoints, uptime monitor.
10. **[I] Audit log widoczny w UI + immutable (append-only)** — 1.5 wk. Widok /audit, `llm_calls` + `executions` + `challenges` timeline, export CSV. Kolumna `prev_hash` dla tamper evidence.
11. **[L] 8 krytycznych endpointów CRUD** — 3 wk. `PATCH /tasks`, retry, delete, AC CRUD, `PATCH /objectives`, KR CRUD, `GET /tasks/{ext}/diff`, bulk triage. (Reszta może poczekać do Phase 2.)
12. **[H] Komentarze per task + "share link" do raportu** — 2 wk. Minimum team review workflow, read-only share link z tokenem.
13. **[J] Onboarding wizard + przykładowy projekt** — 1.5 wk. User trial experience. Bez tego pilot wymaga sales engineer na setup.
14. **[M] Basic team workspace** — 1 wk. User invitacje do org, 3 role (owner, editor, viewer), audit kto co zmienił.

**SUMA MUST: ~24 dev-weeks.** Z team 3 inżynierów + 0.5 design + 0.5 PM = **realnie 10-12 tygodni wall time** + 2 tygodnie na security review i SOC 2 readiness.

### 5.4 Co może poczekać (NIE w Phase 1)

- SSO, SCIM, RBAC granular (Phase 2)
- Webhooks, JIRA integracja (Phase 2)
- Marketplace guidelines/skills (Phase 2-3)
- On-prem (Phase 3)
- HIPAA, SOC 2 Type II (Phase 2-3)
- Workspace file browser (Phase 2)
- Notifications center, Slack integration (Phase 2)
- Mobile (out of scope wszystkich faz)
- Cursor-like latency (never)
- DAG dependency viewer (Phase 2)
- Change Request z LLM impact analysis (Phase 2)

### 5.5 Team composition (Phase 1)

| Rola | FTE | Razem |
|---|---|---|
| Eng Lead / Architect | 1.0 | driver, owns API+infra |
| Backend eng (Python/FastAPI) | 1.5-2.0 | core features |
| Frontend eng (Jinja+HTMX+Alpine) | 0.5-1.0 | UI + onboarding |
| DevOps / Platform | 0.5 | deploy, observability, backup |
| Design (UX + visual) | 0.3 | flows, style system |
| Product manager | 0.5 | scope, customer pilot |
| Founder / CEO | 1.0 | pilot sales, first 3 LOI |
| Security / Compliance adviser | 0.2 | contractor, SOC 2 prep |
| **Total headcount** | **~5-6 people** | |

### 5.6 Budget estimate (Phase 1, 3-4 miesiące)

- Zespół (blended $12k-20k/osoba/mo) × 5.5 FTE × 3.5 mo = **$230-385k**
- Infra (Postgres managed, S3 backup, Grafana Cloud free, 1 staging + 1 prod) = **$3-6k**
- LLM run-rate (Anthropic, 3 pilot clients × $1k/mo) = **$10-15k**
- Legal / umowy MSA / DPA = **$10-20k**
- Brand / landing / demo video = **$5-15k**
- Security pre-audit (penetration test minimal) = **$8-15k**
- Buffer (20%) = **$50-90k**

**TOTAL Phase 1: $320-550k** (blended z marżą agencji). Recommended working budget: **$400k**.

### 5.7 Timeline z milestonami

| Tydzień | Milestone |
|---|---|
| W0 | Freeze zakres, signed founder/team alignment, legal MSA template gotowy |
| W1-W2 | Auth + multi-tenant MVP; konfiguracja infra staging |
| W3-W4 | Async orchestrate + job queue + budget control |
| W5-W6 | Git push/PR + PDF export + audit log UI |
| W7-W8 | Onboarding wizard + CRUD endpoints + team workspace minimum |
| W9 | **Milestone M1: Internal Lingaro pilot rozpoczęty**, 1 realny projekt |
| W10-W11 | Fixes + observability + security pre-audit |
| W12 | **Milestone M2: Pilot zewnętrzny #1** signed, onboarded |
| W13-W14 | Fixes from pilot feedback, SLA montoring |
| W15-W16 | **Milestone M3: Go/No-Go decision** — czy idziemy w Phase 2 |

---

## 6. Phase 2: Enterprise v1

### 6.1 Cel

Skalowalne SaaS na 20-50 tenantów, pierwsza formalna SOC 2 Type I, gotowość do enterprise sales cycle.

### 6.2 Akceptacyjne kryteria Enterprise v1 ready

- 20 płatnych tenantów, >$2M ARR run-rate
- SOC 2 Type I attestation
- SSO z >= 3 IdP (Okta, Azure AD, Google Workspace)
- SLA 99.9% dokumentowane + miesięczne SLA reporty
- Incident response process + status page
- Klient self-serve: signup → pilot → paid w <3 godziny bez sales engineer
- Integrations: JIRA, GitHub, GitLab, Slack, webhooks

### 6.3 Minimum features

1. **[A] SSO (SAML + OIDC)** — 4 wk
2. **[A] RBAC granular (org / project / role matrix)** — 3 wk
3. **[A] SCIM provisioning** — 2 wk
4. **[A] Secrets + keys mgmt enterprise (Vault / KMS integration, BYOK)** — 3 wk
5. **[B] Celery queue (replace Arq/RQ), multi-worker, auto-scale** — 2 wk
6. **[B] Read replicas Postgres + connection pooling** — 2 wk
7. **[B] Zero-downtime deploys + canary** — 2 wk
8. **[C] Multi-level budgets (org / project / month), per-user attribution, cost explorer UI** — 3 wk
9. **[C] Cost forecasting + what-if simulation** — 2 wk
10. **[D] Retention policies (per-entity TTL) + GDPR erasure endpoint** — 3 wk
11. **[D] Bulk export / import projects** — 2 wk
12. **[D] PII detection + redaction w logach/promptach** — 3 wk
13. **[E] Security scan (SAST na Forge-produced kod — Semgrep, Bandit) jako dodatkowa Phase D validation** — 3 wk
14. **[E] Human review checkpoint (optional gate przed merge)** — 2 wk
15. **[F] Datadog / Prometheus+Grafana pełne + alerty PagerDuty** — 3 wk
16. **[F] APM traces per-task przez cały pipeline** — 2 wk
17. **[G] JIRA / GitHub Issues integration bidirectional** — 3 wk
18. **[G] Slack / MS Teams notifications** — 2 wk
19. **[G] Webhooks out (task DONE, challenge NEEDS_REWORK, budget alert)** — 2 wk
20. **[H] Comments, @mentions, notifications center, activity feed** — 3 wk
21. **[I] SOC 2 Type I audit** — 8 wk (w tle)
22. **[I] Evidence export for auditor (zip wszystkich raportów + hash chain)** — 2 wk
23. **[J] In-app help, tour, templates (WarehouseFlow-like presets)** — 3 wk
24. **[K] Guidelines first-class w UI (CRUD + wersjonowanie + scope)** — 3 wk
25. **[K] Skills marketplace (internal) — custom orchestrate steps, operational contracts pluggable** — 5 wk
26. **[L] Pozostałe 25+ endpointów CRUD** — 4 wk
27. **[M] PDF branding per-tenant, white-label URL** — 2 wk

**SUMA MUST Phase 2: ~80 dev-weeks** (przy team 6-8 inżynierów = 12-16 tyg wall time + SOC 2 w tle).

### 6.4 Team composition

| Rola | FTE |
|---|---|
| Eng Manager | 1.0 |
| Backend (incl. 1 senior security) | 4.0 |
| Frontend (incl. 1 dedicated to SSO/RBAC UX) | 2.0 |
| DevOps / SRE | 1.5 |
| Data / Observability eng | 0.5 |
| Design | 1.0 |
| Product manager | 1.0 |
| Security / Compliance (contractor + 1 internal) | 1.0 |
| Sales engineer | 1.0 |
| Customer success (for first 10 tenants) | 1.0 |
| **Total** | **~14** |

### 6.5 Budget estimate

- Zespół × 6 mo = **$900k-1.4M**
- Infra skalowane (multi-region, replicas, observability stack) = **$30-60k**
- LLM run-rate (20-50 tenantów × $2k/mo średnio × 6 mo) = **$300-600k** (pokryte przez revenue)
- SOC 2 audit firm = **$40-80k**
- Pen test formalny = **$25-50k**
- Marketing / content / demo = **$40-80k**
- Legal enterprise (MSA, DPA, BAA) = **$30-60k**
- Insurance (cyber, E&O) = **$15-25k**

**TOTAL Phase 2: $1.4-2.4M.** Recommended working budget: **$1.8M** (part self-fund, part revenue-offset).

### 6.6 Timeline

| Miesiąc | Milestone |
|---|---|
| M1 | SSO + RBAC GA, 5 tenantów migracja |
| M2 | Integrations (JIRA, GitHub, Slack), 10 tenantów |
| M3 | SOC 2 Type I audit start, Cost explorer + budgets GA |
| M4 | Retention + GDPR endpoints, Human review gate |
| M5 | SOC 2 Type I attestation |
| M6 | Skills marketplace beta, 20+ tenantów |
| M7-M9 | Polishing + SOC 2 Type II prep + scaling |

---

## 7. Phase 3: Enterprise v2 / Scale

### 7.1 Cel

On-prem / private cloud dostępny dla Segment A (regulated). Multi-model backend. Forge jako standard assurance layer dla AI-generated code w sektorze regulowanym.

### 7.2 Akceptacyjne kryteria

- 3-5 on-prem deployments u klientów Segment A
- 100+ cloud tenantów
- ARR > $20M
- SOC 2 Type II + ISO 27001 + HIPAA available
- Multi-model (Anthropic + OpenAI + Azure OpenAI + self-hosted via vLLM)
- Marketplace publishable przez partners
- $1/task run-rate margin > 60%

### 7.3 Minimum features

1. **[A] On-prem appliance (Kubernetes Helm chart + Operator)** — 10 wk
2. **[A] Air-gapped / data-residency modes** — 4 wk
3. **[A] Customer-managed encryption keys (CMEK)** — 4 wk
4. **[B] Horizontal scaling (sharded DB, task queue federation)** — 8 wk
5. **[B] Multi-region active-active** — 8 wk
6. **[C] Chargeback / showback reports per team** — 3 wk
7. **[D] Archive + retrieval system (cold storage)** — 3 wk
8. **[E] Multi-model challenge (Opus + GPT-5 + Gemini cross-pollinate)** — 6 wk
9. **[E] Policy engine (OPA) — custom rules "no AWS S3 calls", "must include ADR" itp.** — 4 wk
10. **[F] Self-hosted observability stack option** — 3 wk
11. **[G] Plugin SDK (community + partners)** — 6 wk
12. **[H] Multi-team governance (org of orgs dla enterprise)** — 4 wk
13. **[I] SOC 2 Type II + ISO 27001 + HIPAA + FedRAMP Ready** — quarter in background
14. **[I] Customer audit portal (klient widzi swój audit trail z export do SIEM)** — 4 wk
15. **[J] Visual workflow designer (drag-and-drop operational contracts)** — 8 wk
16. **[K] Marketplace public (guidelines + skills + challenge personas)** — 6 wk
17. **[M] Partner program (SI firm enablement)** — 3 wk
18. **[M] Academic / research tier + open dataset** — 2 wk

### 7.4 Team composition

| Rola | FTE |
|---|---|
| VP Engineering | 1.0 |
| Eng Managers | 3.0 |
| Backend | 8-10 |
| Frontend | 3-4 |
| SRE | 3 |
| Security | 2 |
| Data / ML | 2 |
| Design | 2 |
| Product | 3 |
| Sales / SE | 5 |
| Customer Success | 4 |
| Legal / Compliance | 1.5 |
| **Total** | **~40** |

### 7.5 Budget estimate

Roczny run rate: **$6-10M**. Finansowane z revenue + Series A.

---

## 8. Per-feature appendix (detalowa tabela)

Kolumny: **Feature** | **Kat** | **Phase** | **Effort (dev-wk)** | **Blocks / Blocked by** | **Risk (tech/market/ops)** | **AC** | **Key decisions before start**

| Feature | Kat | Phase | Effort | Blocks / Blocked by | Risk | AC | Key decisions |
|---|---|---|---|---|---|---|---|
| Auth + multi-tenant isolation | A | 1 | 4 | Blocks: all multi-user; Blocked by: DB schema migration | T:M M:L O:L | (a) RLS enforcement ve wszystkich SELECT; (b) brak row leak w pen test; (c) signup flow <3 min | Stack: FastAPI-Users vs Authlib vs custom; multi-tenant: row-level vs schema-per-tenant |
| Secrets mgmt v1 | A | 1 | 1 | Blocks: auth; by: auth (circular — rob razem) | T:M | Keys encrypted at rest (AES-GCM), audit of key access | Vault vs SQLCipher vs cloud KMS |
| Async orchestrate + queue | B | 1 | 3 | Blocks: SLA, M3 Live UI; by: infra staging | T:M M:L O:M | Orchestrate 30min task nie blokuje HTTP; survive restart; cancel < 5s | Arq vs RQ vs Celery; w Phase 2 i tak refactor |
| Retry + backup | B | 1 | 2 | by: async | T:L O:H | Daily pg_dump + restore test < 15 min RTO | S3 bucket per tenant czy shared w KMS; retention 30d default |
| Budget + alerts | C | 1 | 1.5 | by: async | T:L M:H | Hard stop przy 100%; email 50/80/100; UI widoczne | Email provider (Resend? Postmark?) |
| Challenge blocks DONE | E | 1 | 0.5 | by: phase C w produkcie | T:L M:M | `project.config.require_challenge_pass=true` blokuje status DONE | Czy configurable per-task (scope z Guideline)? |
| Git push + PR | G | 1 | 1.5 | by: auth, secrets | T:M M:H | Poprawny PR body; approved by klientów PMO jako deliverable | GitHub App vs OAuth token; GitLab |
| PDF export | G | 1 | 1 | by: report endpoint (mamy) | T:L M:H | PDF z hash'em + timestamp; print-friendly CSS fallback | WeasyPrint vs headless Chrome |
| Observability minimum | F | 1 | 1.5 | by: infra | T:L O:H | Alerty: latency p95 > 30s, error rate > 2%, queue backlog > 100 | Backend: Grafana Cloud / Honeycomb / Datadog. Rekomendacja: Grafana Cloud pilot |
| Audit log UI + immutable | I | 1 | 1.5 | by: schema change | T:L M:M | Prev_hash chain; CSV export; >= 1 tamper test | Czy osobna table czy append-only view; hashing alg |
| 8 krytycznych CRUD | L | 1 | 3 | by: auth | T:L M:M | UX agent MUST list zamknięty | — |
| Comments + share link | H | 1 | 2 | by: auth | T:L M:M | Public share token z TTL; komentarze mentions basic | Czy mentions email? |
| Onboarding wizard | J | 1 | 1.5 | — | T:L M:H | 3 z 5 test-userów kończy sample w <15 min | Sample project: Warehouse demo vs abstract |
| Team workspace basic | M | 1 | 1 | by: auth | T:L M:M | 3 role, invite via email, audit | — |
| SSO (SAML + OIDC) | A | 2 | 4 | by: Phase 1 auth | T:H M:H | Okta + AAD + Google working | Stack: pyoidc, saml2, external SaaS (WorkOS?) |
| RBAC granular | A | 2 | 3 | by: SSO | T:M M:H | 5+ roles, per-project override | Model permissions |
| SCIM | A | 2 | 2 | by: SSO | T:M M:M | Okta SCIM certified | — |
| BYOK / KMS | A | 2 | 3 | — | T:H M:H | Customer key rotation | AWS KMS only czy Vault too |
| Celery | B | 2 | 2 | by: P1 queue | T:M | Zero downtime migration | — |
| Read replicas | B | 2 | 2 | — | T:M | Read p95 < 100ms | Managed vs self |
| Canary deploys | B | 2 | 2 | — | T:M | 10% rollout + auto-rollback | — |
| Budgets multi-level | C | 2 | 3 | by: P1 budget | T:L M:H | Org / proj / user / month | — |
| Cost forecasting | C | 2 | 2 | by: budgets | T:M M:M | What-if z +/- 20% accuracy | — |
| Retention + GDPR erasure | D | 2 | 3 | — | T:M M:H | TTL per entity, erasure endpoint SLA 30d | — |
| Bulk export/import | D | 2 | 2 | — | T:L M:M | Zip with schema + restore round-trip | — |
| PII detection | D | 2 | 3 | — | T:H M:M | Presidio detect PII in prompt inputs; >90% recall | Presidio vs custom |
| SAST integration | E | 2 | 3 | by: orchestrate hooks | T:M M:H | Semgrep run po kodowej deliverce, blokuje DONE jeśli HIGH | Semgrep vs Bandit vs CodeQL |
| Human review gate | E | 2 | 2 | by: RBAC | T:L M:M | Configurable per-project, UI do approve | — |
| Observability full | F | 2 | 3 | by: P1 | T:M O:H | Datadog / Grafana Cloud traces | Rekomendacja: Datadog jeżeli budżet, Grafana jeżeli nie |
| JIRA / GH issues | G | 2 | 3 | — | T:M M:H | Bi-dir sync, auto-create task from issue | OAuth app per tenant |
| Slack / Teams | G | 2 | 2 | — | T:L M:M | Interactive buttons approve from Slack | — |
| Webhooks | G | 2 | 2 | — | T:L M:M | Signed with HMAC, retries | — |
| Comments full + notifications | H | 2 | 3 | by: P1 | T:L M:M | @mentions, email + in-app | — |
| SOC 2 Type I | I | 2 | in-parallel | by: everything above | T:M M:H O:H | Attestation letter | Audit firm choice |
| Help / tour / templates | J | 2 | 3 | — | T:L M:M | 3+ template scenariusze | — |
| Guidelines UI | K | 2 | 3 | — | T:L M:M | CRUD + wersjonowanie + scope | — |
| Skills marketplace internal | K | 2 | 5 | by: architektura pluggable | T:H M:M | Pierwsze 5 skills built-in, 2 partner-built | — |
| Pozostałe CRUD | L | 2 | 4 | — | T:L | Full UX gap closed | — |
| White-label PDF | M | 2 | 2 | — | T:L M:H | Logo + kolory + domain | — |
| On-prem appliance | A | 3 | 10 | by: P2 | T:H M:H O:H | 1 klient deployment E2E <2 dni | Helm vs Operator vs simple compose |
| Air-gapped | A | 3 | 4 | by: on-prem | T:H M:H | No call home, proxy LLM | Proxy stack |
| CMEK | A | 3 | 4 | by: BYOK | T:H M:H | AWS KMS / Azure KV / GCP KMS | — |
| Horizontal scaling | B | 3 | 8 | — | T:H | 10k tasks/day per region | Sharding strategy |
| Multi-region A-A | B | 3 | 8 | by: sharding | T:H O:H | Failover < 5 min RPO | — |
| Multi-model challenge | E | 3 | 6 | — | T:M M:M | 3 models consensus | — |
| Policy engine (OPA) | E | 3 | 4 | — | T:M M:H | Custom rules configurable | — |
| Plugin SDK | G | 3 | 6 | by: architektura | T:H M:M | Partner onboarded w 1 wk | — |
| Multi-team governance | H | 3 | 4 | — | T:M M:M | Org of orgs | — |
| SOC 2 Type II + HIPAA | I | 3 | in-parallel | by: everything | T:M M:H O:H | Attestation | — |
| Audit portal dla klienta | I | 3 | 4 | — | T:L M:H | SIEM export, CEF / LEEF | — |
| Workflow designer | J | 3 | 8 | — | T:H M:M | Non-dev creates operational contract | Visual editor lib |
| Marketplace public | K | 3 | 6 | by: internal marketplace | T:M M:M | 20+ community items | Revenue share? |

---

## 9. Cross-cutting technical decisions

### 9.1 Async job queue

- **Phase 1: Arq** (redis-based, async-native, <1 wk integration, well suited for FastAPI async world).
- **Phase 2: Celery** (mature ekosystem, scheduling, webhooks, enterprise). Migration zaplanowana, nie start-from-scratch.
- **Alternative odrzucone:** FastAPI BackgroundTasks — nie survive restart, ostrzeżenie w UX plan. Cloud Tasks / SQS — over-locked do cloudu, słaby local dev.

### 9.2 Observability stack

- **Phase 1: Grafana Cloud free tier** (logs + metrics + traces, OpenTelemetry) + Sentry free tier (errors). Low cost, działa.
- **Phase 2 rekomendacja: Datadog** jeżeli mamy $30-60k infra budget — najszybciej daje dashboard dla enterprise klienta. Alternatywa: **self-hosted Prometheus+Grafana+Tempo+Loki** jeśli on-prem bliski.
- **Phase 3: self-hosted opcja** (bo klient Segment A tego wymaga).

### 9.3 Deploy target

- **Phase 1: single managed Kubernetes cluster** (GKE albo EKS) w 1 region, blue-green deploy przez Argo CD lub Helm upgrade. Single staging + single prod. ALT: **Google Cloud Run** — prostsze, ale ograniczone przy long-running orchestrate workers (gunicorn + worker). Rekomendacja: **K8s od początku** bo Phase 3 wymaga on-prem Helm.
- **Phase 2: multi-region, managed Postgres z replicami, Redis HA.**
- **Phase 3: customer-self-hosted Helm + Operator.**

### 9.4 Database scaling

- Phase 1: single Postgres 16, managed, pg_dump daily, WAL shipping.
- Phase 2: primary + 2 read replicas, pgbouncer, partitioning `llm_calls` by month (bo to największa tabela).
- Phase 3: sharding per-tenant jeśli workload wymagi (tenants >500).

### 9.5 Storage dla workspace'ów

- Phase 1: local volume mounted z backup do S3 (per-project tarball).
- Phase 2: S3-compatible (AWS S3 / GCS / MinIO) per-tenant prefix.
- Phase 3: per-tenant bucket + customer-owned bucket option.

### 9.6 Frontend stack — czy zostajemy przy Jinja+HTMX?

**Rekomendacja: tak w Phase 1, przemyśleć w Phase 2.**

- Plusy: zero build, szybka iteracja, wystarczy dla MVP, SSR = łatwiejsze SEO/auth.
- Minusy: complex forms (multi-step, real-time collab) stają się painful.
- **Phase 2 decyzja:** jeżeli SOC 2 + dashboard enterprise wymaga bardziej interaktywnego UI (kanban findings, drag-drop workflow preview), dodać **selective React/SolidJS** pod `/app/*` podroute, pozostawiając `/ui/*` dla starych widoków.

### 9.7 Multi-model support architecture

- Phase 1: Anthropic only (Claude 4.6 Sonnet + 4.7 Opus). Abstrakcja `llm_backend` w kodzie, jeden driver.
- Phase 2: OpenAI driver (dla challenger — cross-model-cross-vendor jest silniejszy niż Opus-vs-Sonnet tego samego vendora).
- Phase 3: Azure OpenAI + self-hosted vLLM.

---

## 10. Go/No-Go gates per phase

### 10.1 Gate Phase 0 → Phase 1 (start pilot commercial)

**Evidence needed:**
- [ ] 3 design partnerzy zidentyfikowani i gotowi do LOI
- [ ] 1 pilot partner (Lingaro internal) zgoda
- [ ] Founder committed full-time
- [ ] Budget $400k zabezpieczony (self-fund lub angel/seed)
- [ ] Legal MSA template gotowy
- [ ] Architecture decision records zamknięte (queue, observability, deploy)

**STOP jeżeli:** <2 design partners committed lub budget < $250k.

### 10.2 Gate Phase 1 → Phase 2

**Evidence needed:**
- [ ] 1 signed płatny kontrakt ($15-30k/mo)
- [ ] 2 dodatkowe pilots in flight z pipeline do paid
- [ ] 3 referenceable customers (case studies, logo usable)
- [ ] Zero criticial security incidentów w pilot
- [ ] Gross margin > 40% w pilot contracts (po LLM cost)
- [ ] NPS > 30 w pilot customers
- [ ] Dokładnie policzone: CAC (probable), churn signals, LTV model
- [ ] Zespół > 80% retention z Phase 1

**STOP jeżeli:** <50% pilots convert to paid, lub margin < 20%, lub 2+ crit incidents.

### 10.3 Gate Phase 2 → Phase 3

**Evidence needed:**
- [ ] >= 20 płatnych tenantów, >$2M ARR
- [ ] SOC 2 Type I attestation otrzymane
- [ ] Pierwsi enterprise buyers (>$100k ACV) signed
- [ ] Pipeline Segment A (regulated) kwalifikowany, >= 5 opportunities
- [ ] Cashflow positive operationally lub Series A termsheet
- [ ] Technical scale validated (load testy na 10x current traffic pass)

**STOP jeżeli:** ARR stagnuje, churn > 15%, CAC payback > 24 mo.

---

## 11. Top 10 risks + mitigations

| # | Ryzyko | Severity | Likelihood | Mitygacja |
|---|---|---|---|---|
| 1 | **Anthropic / OpenAI uruchamia własne "verified delivery" feature** (Claude Code dodaje challenge + audit trail natywnie) | HIGH | MEDIUM | Forge pozostaje neutral (multi-vendor). Nasza fosa to integracja: JIRA/GitHub/audit/SOC — która Anthropic nie zbuduje. Budować partner relation z Anthropic, nie konkurencję. |
| 2 | **Cursor / Devin spellbound klientów** — "AI governance to overkill, kupujemy szybkość" | HIGH | MEDIUM | Fokus na Segment A (regulated) gdzie governance jest obowiązkowe. Unikać konkurencji B2C developer. Pokazywać wyraźny ROI (cost jednego prod bugu). |
| 3 | **LLM koszty wzrastają nagle** (nowy model Anthropic 2x droższy) | HIGH | MEDIUM | Multi-model architecture w Phase 2. Prompt cache aggressive. Opt-in challenge (nie zawsze Opus). |
| 4 | **Bezpieczeństwo / data leak u klienta** — crisis, press | CRITICAL | LOW | SOC 2 Type I w Phase 2 obowiązkowe. Pen test po Phase 1. Cyber insurance. On-prem option w Phase 3 dla najbardziej wrażliwych. |
| 5 | **Technical debt vs feature velocity** — Forge został zbudowany solo, refactoring 6 miesięcy żeby skalować | HIGH | HIGH | Eng Lead ownership od W0. Codebase health days w sprincie (Friday reduce). Explicit debt backlog widoczny w roadmap. |
| 6 | **Niska convertion pilot → paid** — "ciekawe ale za drogo" | HIGH | MEDIUM | Pricing hypothesis testing. Per-project case study ROI. Pokazywać $0.50 challenge vs $X dla incidentu. |
| 7 | **Legal / IP copyright LLM-generated code** — klient odmawia użyć | MEDIUM | MEDIUM | MSA definiuje ownership, indemnification w MSA, Anthropic ma swoje pokrycie. Pre-wrabiane DPA + AI clause. |
| 8 | **Sales cycle dłuższy niż założony** (6-9 mo dla regulated) | HIGH | HIGH | Phase 1 nie zakładać Segment A. Start z B (software houses, szybszy cycle). A dopiero w Phase 2+. |
| 9 | **Rekrutacja senior Python + DevOps w okresie AI hiring freeze** | MEDIUM | MEDIUM | Remote-first, equity-first oferta, partnerstwo z Lingaro na early sourcing. |
| 10 | **Challenge (cross-model) jako feature okaże się niezauważany** przez klientów (postrzegany jako marketing buzz) | MEDIUM | LOW | Pokazywać TRUE examples: F-013 Twilio, F-005 reminders. Case studies. Demo "przed vs po". To nasza unikalna wartość — musimy ją brandować. |

**Dodatkowo monitorowane:**
- Anthropic API SLA (jednopunktowa dependency w Phase 1)
- Postgres ops skill w zespole
- Churn po Cursor wypuszcza competitor feature

---

## 12. Open strategic questions (15+)

**Musi odpowiedzieć founder / founding team zanim wejdziemy w Phase 1 week 0:**

1. **Który segment (A lub B) jest primary w Phase 1?** Zalecenie: B (software houses), szybszy cycle, cheaper lead to close. A w Phase 2+.
2. **Czy Lingaro jest anchor customer + go-to-market partner?** Jeśli tak — exclusive? warm accounts? equity?
3. **Pricing pilot: $15k, $20k, $25k, $30k/mo?** Uroczyście decide, potem test. Rekomendacja: $20k/mo sweet spot.
4. **Czy przyjmujemy venture money?** (Seed $500k-$1M lub bootstrap z Lingaro?) Ma wpływ na Phase 2 team size.
5. **Open-source core Forge yes/no?** Argumenty za: community, trust, standard. Przeciw: komercyjny moat. Rekomendacja: core-open (Phase A test runner, Phase B extractor, Phase C challenger as libraries) + closed platform layer. Decyzja w Phase 1 tygodnie 8-10.
6. **Gdzie uruchamiamy LLM calls?** Anthropic direct (latencja, koszt) vs AWS Bedrock (enterprise trust, dodatkowy margin). Rekomendacja: direct w Phase 1, Bedrock alternative w Phase 2.
7. **Challenge mandatoryjny czy opcjonalny?** Jeśli opcjonalny — klient może wyłączyć i nasz edge znika. Jeśli mandatoryjny — +40% koszt LLM zawsze. Rekomendacja: default ON dla HIGH scope tasks, configurable per project, ale quarantine UI zawsze widoczny.
8. **Self-hosted runner workspace czy managed?** Klient Segment A będzie chciał on-prem, B może managed. Phase 1 decyzja: tylko managed cloud, Phase 3 on-prem.
9. **Language support — tylko Python + JS w Phase 1?** (test_runner dzisiaj Python + Node detection). Czy dodajemy Java/Go w Phase 2? Rekomendacja: Python+JS tylko Phase 1, Java+Go w Phase 2 po customer signals.
10. **Czy chcemy compete z Cursor na developer DX?** Rekomendacja: NIE. Forge to CI/audit layer, nie IDE. Sprecyzować brand i nie rozpraszać.
11. **Brand name — "Forge" jest wolne w US trademark?** To wymaga sprawdzenia zanim na landing. Alternatyw: "Forge.ai", "ForgeAudit", "ForgeCI". Pilnie!
12. **Hosting Anthropic API key per-tenant czy shared w platformie?** Shared = prostsze billing, ale concentration risk. Per-tenant = klient ma BYO key, zero LLM pass-through revenue ale i zero risk. Rekomendacja: **per-tenant BYO Anthropic key** w Phase 1 (klient sam płaci LLM, my bierzemy platform fee). Phase 2 dodać managed option.
13. **Co jeśli Lingaro chce dostać Forge "za darmo" jako internal tool?** Rekomendacja: Lingaro jako design partner — dyskonto (50%), exclusivity do sektora consulting w PL regionie 12 mo, w zamian case studies + referencje.
14. **Regulatory target — EU AI Act, US FedRAMP, Indie DPDP?** Phase 1 EU GDPR baseline. Phase 2 SOC 2. Phase 3 HIPAA + FedRAMP Ready (nie pełne FedRAMP — za kosztowne). EU AI Act: monitorować.
15. **Partnership z audytorami?** (Big 4 audit firms kupują assurance tools). To może być faster path niż direct enterprise sales. Rekomendacja: jedno partner-próbna rozmowa w Phase 1, pełne partnerstwo Phase 2+.
16. **Data retention default?** 30d / 90d / infinity? Regulated = infinity. Rekomendacja: 90d domyślnie, per-tenant configurable, infinite dostępne w Enterprise tier.
17. **Co z mikro-skills (hardcoded-seeded dzisiaj)?** Czy są pluggable teraz? To zmiana architektury. Rekomendacja: utrzymać seeded w Phase 1, uczynić pluggable w Phase 2 (Skills marketplace).
18. **Founder distribution czasu:** 100% sales czy 50/50 product/sales w Phase 1? Rekomendacja: 70% sales + 30% product decisions (nie kodowanie). Eng Lead włada kodem.
19. **Metrics success Phase 1?** Rekomendacja: 1 paid ($15k/mo lub więcej), 2 active pilots, NPS >= 30, churn = 0, zero security incidents. Jeśli 3/5 = No-Go.

---

## 13. Recommended first 30-day action plan

**Zakładam: founder + 1 Eng Lead + 1 senior backend już w zespole, budget wstępnie zabezpieczony. Jeżeli nie — pierwszy 30 dni = rekrutacja.**

**Tydzień 1 (founder-heavy)**

Mon-Tue: legal & brand
- Trademark check "Forge" + alt names (zapłać kancelarii $1-2k, 2 dni)
- MSA template + DPA + DPIA draft (zapłać lawyerowi $3-5k)
- Signup prostej spółki (jeżeli nie istnieje)

Wed-Thu: pilot pipeline
- Lista 20 warm leads Segment B (software houses, consulting mid)
- Outreach email #1 do 10 z nich z "private pilot invite"
- Spotkanie z Lingaro executive — propose internal pilot + design partner terms

Fri: team alignment
- Pierwszy all-hands (4-5 os): wizja, cele, roadmap Phase 1
- Ownership areas

**Tydzień 2 (tech foundation)**

Mon-Tue: architecture decisions
- ADR #1: queue = Arq
- ADR #2: deploy = GKE single region
- ADR #3: observability = Grafana Cloud + Sentry
- ADR #4: auth = FastAPI-Users + Postgres row-level + org_id column everywhere
- ADR #5: multi-model abstraction (interface dla Claude/OpenAI/Bedrock)

Wed-Fri: environment setup
- Staging + prod clusters provisioned (Terraform)
- CI/CD (GitHub Actions → Helm)
- Postgres managed + backup automatyzacja
- Secrets manager decision + setup (SOPS? Vault? AWS Secrets?)
- Monitoring pipelines (logs, metrics) podpięte

**Tydzień 3 (pierwszy feature sprint)**

- Auth + multi-tenant: SQL migration, auth endpoints, RLS policies, login UI
- Parallel: backup script + restore test end-to-end
- Parallel: async orchestrate prototype (Arq queue, pierwszy task)

**Tydzień 4 (pilot onboarding prep)**

- 3 outstanding deal w pipeline z Tydz 1 — spotkania demo (Forge dzisiaj, roadmap 4 mo)
- Design kickoff: onboarding wizard flow
- Eng: auth GA + async orchestrate GA + budget/alerts MVP
- Pierwszy internal test z Lingaro pilotem (jeszcze nie prod, staging)
- Go/No-Go check na koniec miesiąca: czy mamy >= 2 committed design partners + pipeline 5+?

**Outputs po 30 dniach:**
- Multi-tenant MVP running w staging
- 2-3 LOI signed (design partners)
- 1 internal pilot project (Lingaro)
- Trademark screening done
- ADR docs 1-5 final
- Zespół 5-6 FTE aligned

**Decyzja GATE: Go dla W5+ jeśli wszystko powyżej. STOP jeżeli <2 design partners.**
