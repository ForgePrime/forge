# Praktyki terenowe Claude Code, dokumentacji AI i orkiestracji agentów

**Najważniejszy wniosek z badania:** społeczność praktyków w 2025–2026 zbiega się wokół kilku zaskakująco sprzecznych z intuicją zasad — **im krócej, tym lepiej** (CLAUDE.md <60 linii), **MCP to bloat, CLI wygrywa**, **multi-agent to anti-pattern dla spójnych zadań**, a **skills pod-wywołują się za rzadko, jeśli nie są wymuszone hookiem lub twardymi gate'ami**. Dla FORGE (Python/Databricks) i ITRP (GCP/FastAPI/React) oznacza to: buduj wymuszenie deterministyczne (hooki + Pydantic kontrakty), nie ufaj promptom. Poniżej pełna mapa — cztery obszary, ~65 konkretnych praktyk, każda ze źródłem i trybem adaptacji. Raport kończy sekcja syntezy z rekomendacjami dla Waszego skill ecosystemu.

---

## 1. Claude Code i AI coding workflows — praktyka z terenu

### CLAUDE.md: krótko, ręcznie, ze wskaźnikami — nie z treścią

**HumanLayer (Kyle), "Writing a Good CLAUDE.md"** dokumentuje mechanizm, który tłumaczy 90% problemów z CLAUDE.md: Claude Code owija jego zawartość w `<system-reminder>` z instrukcją *"this context may or may not be relevant… do not respond unless highly relevant"*. Efekt: im dłuższy CLAUDE.md, tym częściej model go **ignoruje**. Badania wskazują, że frontier modele niezawodnie podążają za ~150–200 instrukcjami; przeładowanie degraduje przestrzeganie *wszystkich* instrukcji uniformly, nie tylko nowych. Korzeniowy CLAUDE.md HumanLayera ma **<60 linii**. Konsensus: <300 linii, krócej = lepiej.

**Dlaczego cenne dla FORGE/ITRP:** Wasze enforcement gates i mandatory artifacts mogą łatwo puchnąć do 500+ linii. Zamiast tego — trzymaj w korzeniu 40–60 linii (stack, komendy, twarde zakazy) i używaj **progressive disclosure**: katalog `agent_docs/` z osobnymi plikami (`forge_pyspark_conventions.md`, `itrp_firestore_patterns.md`, `forge_unity_catalog_rules.md`), a w CLAUDE.md tylko jednoliniowce "when working on PySpark DAGs, read agent_docs/forge_pyspark_conventions.md". Zazencodes benchmark: CLAUDE.md **generowany przez LLM** (np. przez `/init`) faktycznie **pogarsza** wyniki agenta. Pisz ręcznie. Traktuj PR do CLAUDE.md jak ADR — wymagany review.

### Nested CLAUDE.md per domenę i `@imports`

MindStudio + Anthropic memory docs opisują trzywarstwową hierarchię: **(a) CLAUDE.md** (<200 linii, trwałe reguły, re-injekted po `/compact`), **(b) `/memories` / `.memory/` dir** (Claude-writable learnings międzysesyjne), **(c) kontekst sesyjny** (ephemeral). Nested CLAUDE.md per subdir pozwala mieć `bronze/CLAUDE.md`, `silver/CLAUDE.md`, `gold/CLAUDE.md` dla FORGE — Claude wczytuje tylko relevantne. Składnia `@docs/api-patterns.md` działa jako late-loading reference.

**Dla ITRP:** `api/CLAUDE.md` (FastAPI/Pydantic v2 patterns), `web/CLAUDE.md` (Next.js/TanStack Query), `infra/CLAUDE.md` (Terraform GCP). Dla FORGE: per-layer CLAUDE.md plus globalny z trzypoziomowym UC naming.

### `thoughts/` symlinkowany katalog jako pamięć krzyżowa

**Ashley Ha / HumanLayer** opisuje wzorzec `thoughts/` (gitignored per-repo, symlinkowany do shared location) z podfolderami `tickets/`, `research/`, `plans/`, `prs/`. Sesje są stateless; CLAUDE.md jest zbyt krótki by przenieść decyzje. Shared filesystem staje się persistent memory. Dla FORGE+ITRP: jeden `thoughts/` mount zapewnia, że decyzja o retry policy czy auth pattern propaguje między repo (ważne dla fintech, gdzie patterns muszą być spójne).

### Frequent Intentional Compaction (FIC): Research → Plan → Implement

Najlepiej udokumentowany workflow 2025. **Dex Horthy / HumanLayer** opisuje trzy slash-commands (`/research_codebase`, `/create_plan`, `/implement_plan`), każdy w **świeżym kontekście** wczytującym tylko artefakt z poprzedniej fazy (`research.md` → `plan.md` → `progress.md`, każdy ~200 linii). Target utilizacji kontekstu: **40–60%**. Case study: naprawa buga w 300k-LOC Rust codebase (BAML); 35k LOC (cancellation + WASM) w 7 godzin (3h research/planning + 4h implementation) — zadania szacowane na 3–5 senior-engineer-days każde. Kluczowa obserwacja: **quality gates idą wcześniej** — review 400 linii research+plan ma wyższy leverage niż review 2000 linii kodu.

**Dla FORGE:** idealne dopasowanie. Research dla DAG data-eng wyliczy schematy tabel i zależności, plan jest human-reviewed PRZED pierwszą linią PySpark. Wymuszaj jako trzy osobne skille z STOP pointem między fazami.

**Dla ITRP:** oddziel "no backend + frontend w jednej sesji" jako twardą regułę — osobne plany per warstwa.

### 60% rule + proaktywny `/compact`, nigdy reaktywny

**MindStudio / Ashley Ha:** uruchamiaj `/compact Focus on <specific thing>` przy ~60% utilizacji, NIE kiedy pojawia się degradacja. Auto-compact przy 95% jest stratny — *"drops the **why** behind decisions and retains only a shallow **what**"*. Zdrowa sesja produkuje lepsze podsumowanie niż zdegradowana. Gdy Claude już sobie zaprzecza lub re-proponuje porzucone podejścia — rot jest już w podsumowaniu. **Zastosowanie:** PreToolUse hook monitorujący `context_window.remaining_pct` blokuje przy 65% i wymusza handover doc. To pasuje jako STOP point w Waszym skill ecosystem.

### Hook exit-code 2 to jedyny realny mechanizm wymuszenia

**dotzlaw.com + Blake Crosley + smartscope.blog:** **Exit 1 jest NIE-blokujące** (Claude Code traktuje jako "proceed anyway"); **tylko exit 2 blokuje**. Kluczowy cytat: *"A CLAUDE.md instruction says 'always run the linter.' The agent usually complies. A PostToolUse hook runs it every single time, no exceptions. That gap between 'usually' and 'always' is where production systems fail."* Prompty dają 70–90% compliance; hooki 100%. **Gotcha: `allowUnsandboxedCommands` default true** — Claude może retry zablokowaną komendę poza sandbox. Explicite deny-list `git commit -n`, `--no-verify`, bo Claude skip'nie pre-commit.

**SubagentStop hooks:** definiowane w YAML frontmatter skilla automatycznie stają się event'ami dla sub-agentów — bez tego sub-agent może obejść parent safety gates. Dla FORGE (parent → child data-eng agents) wpinaj `SubagentStop` do `pytest tests/unit/<changed>`, aby sub-agent nie "finish"nął z broken testami.

**Bezpośredni transfer do ITRP:**
- `PreToolUse: Edit` blokujący na `secrets/`, `.env*`, `terraform/prod/`
- `PreToolUse: Bash` blokujący `bq rm`, `gcloud iam`, `DROP TABLE`, `gcloud ... --project=<prod>`
- `PostToolUse: Edit` na `.tsx` → `pnpm tsc --noEmit` tylko dla zmienionych plików

**Dla FORGE:**
- `PostToolUse: Edit` na `.py` → `ruff check` + `pyright` (tylko zmieniony plik, nie cały suite)
- `PreToolUse: Bash` blokujący `databricks clusters delete`, zapisy do `main` schema UC

### "Claude is not a linter" — przenoś style rules do hooków

Ta sama logika: nigdy nie wysyłaj LLM do roboty deterministycznej (`ruff`, `biome`, `mypy`, `black`). PostToolUse z matcherem `Edit|Write|MultiEdit`, `exit 2` → errors wracają jako `additionalContext` i Claude self-correct. Oszczędność tokenów dramatyczna. HumanLayer jednoznacznie: *"Claude is not an expensive linter."*

### MCP = głównie bloat — wybieraj CLI

**Najmocniej udokumentowana surprise'owa lekcja 2025.** Armin Ronacher: *"try completing a GitHub task with the GitHub MCP, then repeat it with `gh`. You'll almost certainly find the latter uses context far more efficiently."* Simon Willison: *"LLMs know how to call `cli-tool --help`, which means you don't have to spend many tokens describing how to use them."*

**Konkretne liczby token-burn:**
- Scott Spence: **81,986 tokenów** zjedzonych *przed pierwszym promptem* z 5 MCPs
- GitHub issue #13717: user trafił **98.7k tokenów (49.3% okna)** z samych MCP tool defs
- Task Master MCP sam: 63.7k tokenów / 59 narzędzi
- Naqeeb Shamsi: **49 pluginów zarejestrowanych, 3 faktycznie enabled**, MCP skill injection marnował ~25K tokenów *per tool call* × 50 calls = 1.25M tokenów

**Dla FORGE:** zastąp BigQuery/Databricks MCP wrapperami `bq query`, `databricks sql query` w Makefile. Kill GitHub MCP — `gh` jest strict better. **Dla ITRP:** to samo dla GCP SDK — `gcloud`, `gsutil`, `bq`. MCP tylko gdzie nie ma dobrego CLI (np. Ronacher nadal używa `playwright-mcp`).

### Skills > MCP dla domain-specific repetytywnej pracy

Simon Willison (*"Claude Skills are awesome, maybe a bigger deal than MCP"*) rozkłada skills: folder + `SKILL.md` + optional scripts + YAML frontmatter (name, description). Na starcie sesji skanowane jest tylko metadata (~100 tokenów); pełny body (~5k) ładuje się dopiero przy wywołaniu (**progressive disclosure**). Różnica vs MCP: *"MCP is a whole protocol specification… Skills are Markdown with a tiny bit of YAML metadata and some optional scripts."*

**Dla Waszego skill ecosystemu:** idealna architektura. Konkretne skille:
- FORGE: `pyspark-udf-patterns`, `databricks-job-config`, `unity-catalog-three-level`, `delta-live-tables-bronze-silver-gold`, `pyspark-partition-pruning`
- ITRP: `fastapi-pydantic-v2`, `firestore-query-patterns`, `bigquery-partition-pruning`, `react-tanstack-query`, `stripe-webhook-idempotency`

Każdy `SKILL.md` + validator script, który model wywołuje (enforcement via code, nie prose).

### Krytyczny anti-pattern: Vercel pokazał, że skills pod-wywołują się bez enforcement

**Kontrargument z terenu, który zmienia architekturę:** Vercel (*"AGENTS.md Outperforms Skills in Our Agent Evals"*) testował dostarczanie dokumentacji Next.js 16 przez evale na API spoza training data. **Baseline skill był wywoływany tylko w 44% przypadków** (nigdy w 56%). Gdy skill nie był triggerowany, agent działał jak bez dokumentacji. Z explicit "use the skill" instructions: max 79%. **Skompresowany ~8KB docs index wbity w AGENTS.md osiągnął 100%**.

**Rekonsyliacja z Willisonem:** **pasywny kontekst (AGENTS.md)** dla zawsze-aktywnych reguł (security, formatowanie, guardrails) + **aktywny kontekst (skills)** tylko dla wyspecjalizowanych on-demand workflows + **HARD-GATE wrapper** (patrz Superpowers poniżej) dla skilli, które MUSZĄ być wywołane.

### Superpowers framework (obra/Jesse Vincent): enforcement language, nie advisory

Jesse Vincent (github.com/obra/superpowers, ~70k stars) to de-facto reference dla skill-based workflows. Session-start hook injectuje `EXTREMELY_IMPORTANT` prompt każący Claude'owi przeczytać `getting-started/SKILL.md`. Ten plik uczy: *masz skille; szukaj ich; jeśli skill istnieje, MUSISZ go użyć*. Kluczowe zdanie: *"If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill… This is not negotiable."*

**Red-flag tables:** `using-superpowers/SKILL.md` zawiera tabelę racjonalizacji, których modele używają by pominąć skille ("This is just a simple question," "I need more context first," "The skill is overkill") ze stock reply: *"Reality: skills tell you HOW. Check first."*

**Persuasion principles z Cialdini (Influence):** authority, commitment, scarcity, social proof — wpinane w język skilli. Empirycznie zwalidowane (*Call Me a Jerk: Persuading AI* — Wharton/Cialdini/Shapiro).

**Superpowers v4.3.0 lekcja (Feb 2026):** advisory skill language ("present the design in sections") był racjonalizowany away. Fix: dodany `<HARD-GATE>` block zakazujący implementation skills / code writing / scaffolding **dopóki design nie zostanie zaakceptowany**. Plus odkryto cichy bug — `async: true` w session-start-hook blokował injection: *"the system looked healthy from the outside, it just didn't work."*

**Transfer do Waszego skill ecosystemu:** to jest dokładnie Wasz pattern. Każdy enforcement gate powinien mieć:
1. `<HARD-GATE>` block w SKILL.md z negatywnymi ograniczeniami ("YOU MUST NOT write code until architecture.md is approved")
2. Red-flag table z typowymi racjonalizacjami
3. Priority hierarchy jawnie wymieniona
4. Session-start hook injectujący "read the getting-started skill"
5. Hook weryfikujący artefakty przed przejściem dalej

### Git worktree: realny limit to 3–4 równoległe, nie "10–15"

**Code With Seb:** Anthropic obiecuje 10–15 równoległych sesji; praktyka pokazuje że przy >4 cognitive overhead zjada zyski. Dwie sesje edytujące ten sam plik cichu korumpują kontekst siebie nawzajem. **Rule of thumb:** *tasks w tym samym module stay sequential w jednej worktree; tylko cross-module parallelize*. Rebase (nie merge) między worktree — *"Claude's reasoning about history is much better with linear chains."* **Co zaskoczyło autora:** co 20 minut review session robi `git fetch --all` + diff-check — bez heartbeat, "review" zamienia się w "never."

**Dla FORGE:** worktree dla agenta A na ingest DAG + agenta B na transform DAG. NIE parallelize within same PySpark module. **Dla ITRP:** worktree dla api/ + worktree dla web/ osobno.

### Plan mode vs YOLO: dwie ścieżki, obie ważne

**Ronacher (YOLO camp):** omija plan mode, używa `claude --dangerously-skip-permissions` w Dockerze, iteruje na ręcznie edytowanym markdown plan file: *"I get the agent to ask me clarifying questions, take them into an editor, answer them, iterate."* Plan mode's artifact to ukryty MD — replikuj z wizualnie edytowalnym plikiem.

**BSWEN / codewithmukesh (plan mode camp):** *"No planning, 15 minutes later I had a mess: 14 files modified, 3 endpoints broken."* Plan mode dramatycznie redukuje multi-file refactor disasters (Shift+Tab twice).

**Praktyczna reguła:** eksploracyjne FORGE → markdown-handoff Ronachera; produkcyjne ITRP changes (auth, billing) → force plan mode + human plan review. Plan mode jest głównie prompt reinforcement + tool-availability gating, NIE hard read-only enforcement (Ronacher).

### Log-as-tool: stdout jako observability layer agenta

Ronacher: email magic links, webhook events, Stripe test callbacks wszystko loguje się do stdout. `make tail-log` komenda daje Claude'owi deterministic state. CLAUDE.md mówi konsultuj log. **Enables end-to-end signup/payment test flows fully hands-off** — agent klika link "przeczytany z emaila" via log. Logs-as-tools > MCP dla observability.

**Dla ITRP:** routuj Stripe/test-webhook bodies do rolling log file; `make tail-webhook`. **Dla FORGE:** każdy Databricks job pisze structured JSON logs do znanego path.

### YOLO + sandbox = sweet spot, nigdy YOLO na hoście

**Simon Willison ("Living Dangerously with Claude")** + Anthropic auto-mode engineering post: `claude --dangerously-skip-permissions` WEWNĄTRZ Dockera z `--network none` (lub restrictive egress proxy) + `--disallowedTools "Bash(rm:*)"`. Prompt-injection threat: *"The only credible defense is a sandbox on someone else's computer."* Codex Cloud / Claude Code for the web preferred dla untrusted repos.

**Udokumentowane disaster'y:** Dec 2025 home-dir wipe (`rm -rf ... ~/`), token exfiltration, accidental prod DB migrations (Anthropic's Opus 4.6 system card §6.2.1).

**Obligatoryjne dla ITRP (fintech!):** osobny dev GCP project, workload-identity-only (BEZ user JSON keys), pre-push gitleaks, Claude w Dockerze bez dostępu do hostowych GCP creds.

### Ralph Wiggum loop dla depth tasks (nie breadth)

**Geoffrey Huntley (ghuntley.com/ralph):** Stop-hook interceptuje Claude exit, re-feeduje ten sam PROMPT.md aż pojawi się completion-promise string. Brute-iteration na jednym hard taskzie. *"Better to fail predictably than succeed unpredictably."* Używane przez Huntley+hellovai do shipowania 35k LOC BAML features (cancellation + WASM) w ~7h. **Caveat:** wymaga `--dangerously-skip-permissions` + sandbox; exact-string completion check uniemożliwia branching SUCCESS vs BLOCKED; zawsze pair z `--max-iterations`.

**Dla FORGE:** świetne do "napisz X DAG-ów według tego wzoru dla 40 tabel" — backpressure przez `pytest` passing. Słabe fit dla open-ended architectural work.

### Anti-pattern: plugin/MCP/agent hoarding

Naqeeb Shamsi: "I could explain my entire setup by reading two files. If someone asked 'how is your Claude Code configured,' I could answer in under two minutes." **Reguła kwartalnego cleanupu:** map każde tool do capability bucket; jeśli dwa tools robią to samo — jedno out. Session-start audit hook printuje `/mcp` output i failuje jeśli >5 serwerów. Wszystkie MCP w *project-level* `.claude.json`, nigdy user-level.

### Co zaskoczyło: jakość spada od modelu, nie od Twoich promptów

GitHub issue anthropics/claude-code#42796 + r/ClaudeCode ("Gaslightus 4.7"): jeden user zalogował read:edit ratio spadający **21.8 → 1.6 w 8 tygodni**, coinciding z thinking-redaction changes; multi-agent workflows delivering 191k LOC/weekend stały się "completely non-functional" w ciągu dni.

**Krytyczna implikacja:** **pin known-good model versions dla production workflows**; miejcie weekly sanity-check eval (5 canonical tasks → diff vs golden outputs) — regresje wypływają zanim zjedzą sprint. Dla FORGE eval set: 5 reprezentatywnych migracji pipeline; dla ITRP: 5 endpoint implementations + 5 React component refactors.

---

## 2. Dokumentowanie projektów AI/data — co nie rotuje

### README jest dla ludzi, AGENTS.md dla maszyn — komplementarne

Thread HN #44957510 (*"I'm still not convinced that separating README.md and AGENTS.md is a good idea"*) konkluduje: ludzie czytający "ABSOLUTELY NEVER delete migrations" inferują consequences; agenci potrzebują literal rule stated imperatively i redundantly. **Register retoryczny jest fundamentalnie inny.** README stays welcoming/conceptual; AGENTS.md imperative, terse, negative constraints.

**Dla FORGE:** AGENTS.md: *"NEVER write directly to Unity Catalog `main` schema from notebooks; ALL writes go through bronze→silver→gold DLT pipelines."* **Dla ITRP:** *"NEVER call Firestore from React directly; all reads via FastAPI `/api/v1/*`."* CLAUDE.md = Claude-specific extensions via `@imports`.

### ADR jako atomic + immutable — nie używaj jako design doc

**joelparkerhenderson/architecture-decision-record + AWS Prescriptive Guidance:** one decision per ADR, immutable once accepted (supersede, don't edit). Context/Decision/Consequences. Tylko przy decyzji architektonicznie significant (affects ≥2 komponenty, viable alternatives with trade-offs). **Anti-pattern:** używanie ADR jako design docs — ADR to *decision record*, nie plan.

**Dla FORGE:** `docs/adr/0001-delta-live-tables-over-airflow.md`, `0002-unity-catalog-three-level-namespace.md`. **Dla ITRP:** `0003-firestore-vs-bigquery-for-itrp-state.md`, `0004-fastapi-over-cloud-functions.md`. Numbered, append-only.

### AgDR: Agent Decision Records dla AI-made choices

**Emerging pattern (github.com/me2resh/agent-decision-record, 2026):** gdy agent picks library, pattern, data structure autonomously — emit AgDR z fields `{id, timestamp, agent, model, trigger, status}` + Nygard-style context/decision/consequences. Enforced via pre-commit hook lub AGENTS.md rule: *"Before choosing any library or pattern, write an AgDR in `docs/agdr/`."* **Bez tego** decyzje agenta są niewidoczne w `git blame`, context wypaprowuje między sesjami, next run picks konfliktujące podejście.

**Dla ITRP (krytyczne):** agenci mogą wybierać retry strategies, caching layers, Firestore indexing — decyzje z runtime cost. Wbij wymaganie AgDR w enforcement gate dla każdego nowego modułu.

### AI-generated ADRs wymagają hard guardrails

**Equal Experts ("Accelerating Architectural Decision Records with Generative AI"):** LLMs *"frequently hallucinated reference material, including non-existent APIs, web pages, or entire product features."* Guardrails: "References MUST exist — verify each URL resolves," "DO NOT invent product features." **LLM-as-judge**: drugi LLM krytykuje first's output przed human review. Anti-pattern: pozwolić clear, confident LLM-written ADR bypass scrutiny bo *sounds* right.

### Versioned model contracts w dbt-style YAML, enforced at build

**docs.getdbt.com / Sanderson (Secoda):** declaruj column names + data types w YAML z `contract: enforced: true`. Build fail jeśli transformation nie produkuje exactly that schema. **Contracts are consumer-defined, producer-owned** — konsumenci deklarują czego potrzebują, producers own the guarantee i versioning. Contract doc żyje z producer's code ale *reviewed by* konsumenta.

**Dla FORGE:** każda gold-layer tabela konsumowana przez ITRP dostaje YAML contract. Gdy ITRP zależy od FORGE gold table, **ITRP opens PR against FORGE** dodając/amending contract YAML; FORGE reviews. **Dla ITRP:** Pydantic response schemas w FastAPI pełnią tę samą rolę at API boundary — pinned, tested in CI.

### Diátaxis: nie twórz pustych szkieletów — ewoluuj do quadrantów

**diataxis.fr + blog.sequinstream.com:** NIE twórz `/tutorials /how-to /reference /explanation` folderów day one (*"it's horrible"*). Iteruj: pick jeden doc, ask który mode, move sentences które nie należą. Struktura emerge'uje. Sequin używał Claude z załadowanym Diátaxis repo jako project do review każdego doca. **Canonical observation:** adopcja *first makes docs look worse* — to jest point, exposes conflations.

**Dla FORGE/ITRP:** trzymaj `docs/` flat; label page's intent w frontmatter (`type: how-to`); monthly LLM review flag mode-mixing.

### Living docs: generuj z kodu, nie z whiteboards

Co nie rotuje: OpenAPI z FastAPI route decorators; dbt/DLT catalog z model YAML; BDD `.feature` files jako executable requirements; Sphinx/mkdocstrings z Python docstrings. **Anti-pattern:** hand-maintained API tables w Confluence — wrong within one sprint. **Dla ITRP:** `fastapi` → OpenAPI JSON → Redocly w CI. **Dla FORGE:** `dbt docs generate` → static site published on merge to main.

### Lintuj docs w CI

Vale (Google/Microsoft style), markdownlint, `lychee`/`markdown-link-check`, custom check dla forbidden/renamed terms. Doc PR failuje build tak samo jak code PR. Netlify, Stream: catches ~80% rot mechanically. **Dla FORGE/ITRP:** linter rule flagujący references do deprecated UC schema names lub old ITRP route paths — najczęstsza forma silent rot.

### Eugene Yan: 15 min/tydzień documenting your work

Weekly appended `CHANGELOG`/work-log per project: decyzje, dead ends, learnings — NIE status. Każdy prototyp z short design doc (problem → methodology → system). **Dla FORGE/ITRP:** `docs/worklog/YYYY-MM.md` z dated entries — excellent priming material dla Claude context kiedy wracasz do modułu po miesiącach.

### Prompt versioning = operational observability, nie git diffs

**ilovedevops.substack.com + braintrust.dev:** prompts jako production interface artifacts — immutable once published, semver-tagged, draft → staging → production lifecycle, every inference trace logs `prompt_version_id`. **Anti-pattern:** editing prompt string w Python file i redeploy. Same text behaves differently pod new model version.

**Konkretny setup dla FORGE/ITRP:** store prompts w `prompts/<name>/v<n>.md` z `manifest.yaml` pinning model + temperature + max_tokens. Pydantic `PromptRef` type przenosi ID przez FastAPI traces. Logfire/Langfuse loguje `prompt_version_id` na każdym spanie.

### LLM-in-prod runbook: burn-rate, unauthorized models, tool-loop alerts

Cztery alerty z prescribed response: **(a) spend spike** — 2× rolling 7-day hourly baseline, every 5 min; **(b) unauthorized model** — allowlist violation, every 1 min (catches accidental GPT-5-preview deploys kosztujące 10–50×); **(c) high-cost single span** — per-request cap; **(d) tool-failure rate >20%** over rolling window (agent runaway loops multiply cost przez retries). Runbook: integrity → localization → sample review → mitigation → retraining trigger.

**Dla ITRP:** FastAPI layer emituje `cost_usd` span field; scheduled BigQuery alert biegnie burn-rate SQL. Każdy alert linkuje `docs/runbooks/llm-cost-spike.md` z exact containment steps (temporary model tiering, retry cap).

### Stop używać wiki dla software docs — rotuje

Stack Overflow blog (SRE Chris Hunt: *"We have three different wikis, two were broken"*): move technical docs do repo obok kodu, rendered w CI/CD. Wikis fail bo są separate system z context-switching, dev-ii nigdy nie updatują. Reserve Confluence/Notion dla cross-cutting non-code (org charts, policy). **Worst offender:** over-documenting minutiae (rack positions, individual file mappings). **Dla FORGE/ITRP:** oba repo own `docs/`; cross-project architecture index w tiny Backstage catalog.

### Almighty Thud 2.0: AI-generated docs poisoning future AI

**rakiabensassi.substack.com:** stale/AI-hallucinated docs ingested przez RAG/Claude later produkują hallucinated kod przeciwko architekturom które już nie istnieją (Deloitte $300K government report z fabricated citations). Reguły: **(1) delete stale docs aggressively; (2) require human review na wszystkie AI-drafted architecture content; (3) keep `docs/ARCHIVE/` z date-stamped deprecation note** zamiast silently leaving old docs. Quarterly *"doc garbage collection"* PR — skrypt flaguje `.md` files >6 miesięcy bez commit dotykającego opisanego kodu.

### Runbooks dla drift i data-quality incidents

Każdy alert fires z embedded runbook link + metadata (model_version, prompt_version, feature_name, recent_deploys). Runbook: integrity checks → slice dashboards → sample human review → mitigation decision (rollback? model-tier down? rate-limit?) → retraining trigger. Alerts na *sustained* degradation via error budgets. **Dla FORGE:** runbooks dla PSI/KS drift na bronze→silver enrichment features. **Dla ITRP:** runbooks dla RAG groundedness i agent tool-loop depth.

### Mermaid + C4 in-repo; diagrams as code

Wszystkie diagramy jako fenced ```mermaid``` bloki rendered przez MkDocs/Docusaurus/Backstage TechDocs. **NO PNG/Lucid exports w Git — rotują niewidzialnie.** C4 levels 1–2 (System Context + Container) wystarczą dla onboardingu; skip 3–4 chyba że specific review need. **Dla FORGE:** `docs/architecture/c4-context.md` + `c4-container.md`. **Dla ITRP:** request-flow sequence diagram per critical endpoint.

### Onboarding: 1-page map + one working tutorial + failure catalog

**Hamel Husain (error-analysis-first docs) + Eugene Yan + Diátaxis:** new-joiner docs to dokładnie trzy rzeczy — (1) one-page system map (C4-L1), (2) jeden end-to-end tutorial produkujący real artifact w <1h, (3) curated *"how things fail"* katalog z real past incidents/error-analysis — **NIE exhaustive reference**. Husain's approach: error analysis surfaces failure modes; te stają się najcenniejszym onboarding content, bo uczą *modelu systemu*, nie trywii.

**Dla FORGE:** `docs/onboarding/00-map.md`, `01-ship-a-bronze-table.md`, `02-common-failures.md`. **Dla ITRP:** `01-ship-an-endpoint.md`, `02-common-failures.md`.

---

## 3. Struktury promptów i skill systemów — co rzeczywiście jest egzekwowane

### Priority hierarchy jawnie wymieniona w system prompcie

Jesse Vincent's Superpowers: priority hierarchy explicit — *User instructions (CLAUDE.md/GEMINI.md/AGENTS.md/direct) > Superpowers skills > default system prompt*. Bez tego Claude rozwiązuje konflikty "po swojemu" — często na korzyść default system prompt.

### Red-flag tables vs racjonalizacje

Superpowers umieszcza tabele typowych wymówek modelu ("This is just a simple question," "I need more context first," "The skill is overkill") ze stock reply — *"Reality: skills tell you HOW. Check first."* To **jest enforcement via prose**, ale tylko gdy sparowane z twardym hookiem. Vercel evale pokazały, że samo prose daje 44% trigger rate.

### HARD-GATE blocks dla skilli które MUSZĄ być wywołane

**Superpowers v4.3.0 lekcja (krytyczna):** advisory language ("present the design in sections") jest **rationalized away**. Fix: `<HARD-GATE>` block explicit forbidding implementation skills / code writing / scaffolding **dopóki design nie jest approved**. Sparuj z pre-commit hookiem sprawdzającym obecność design artifact.

**Transfer:** każdy gate w Waszym ecosystemie:
```
<HARD-GATE name="design-before-code">
Do NOT write, edit, or scaffold any .py/.ts/.tsx/.sql file
until docs/plans/<feature>/architecture.md exists AND
contains line "STATUS: approved_by_human".
Violation = abandon task and request human review.
</HARD-GATE>
```
+ PreToolUse hook grepujący plan file na każdym Edit/Write.

### XML tags dla Claude, markdown dla czytelności

Anthropic explicite rekomenduje XML dla Claude. Prompt-injection mitigation: XML tags z explicit begin/end lepiej delimitują user-controlled content. Praktyczne: ~15% więcej tokenów niż markdown, ale 40% variation w performance po formacie. Verdict: **XML tags (`<instructions>`, `<constraints>`, `<output_format>`) wokół structured sections i user-supplied inputs**, markdown dla readable body prose. Conditional XML blocks gated by task type (HumanLayer Mar 2026) improve adherence.

### Progressive disclosure w SKILL.md: metadata → body → references

Anthropic skills spec: metadata (~100 tokenów) loaded at startup; body (~<5k tokenów) loaded only when triggered; bundled resources loaded only when referenced. **Field cheat sheet:**
- `disable-model-invocation: true` — tylko user może triggerować (dla sensitive workflows)
- `user-invocable: false` — tylko Claude może triggerować (passive reference knowledge)
- `$ARGUMENTS` placeholder, `$1 $ARGUMENTS[N]` positional, `` !`command` `` pre-processing dla injecting live shell output

**Dla FORGE skill `deploy-bronze-table`:** YAML frontmatter declaruje `description: "Validates and deploys a bronze-layer Delta table to Unity Catalog dev catalog. Triggers on user intent to create/modify bronze tables."`; body ma preflight checks; `scripts/validate_schema.py` wywoływany przez Claude.

### Reinforcement w tool responses

**Ronacher ("Agent Design Is Still Hard"):** *"every tool-call response is an opportunity to remind the agent of the overall objective and current task state."* Claude Code's TODO list to przykład. Reinforcement *"does more heavy lifting than expected."*

**Transfer:** w Waszych custom toolach zwracaj JSON z polami `{result, reminder, next_allowed_actions}`. FORGE validator tool zwraca: `{"result":"pass","reminder":"Current plan step: silver-layer deployment","next_allowed_actions":["write_sql","run_test"]}`.

### Caching discipline: static prefix top, dynamic suffix bottom

Anthropic + ProjectDiscovery Neo (59% cost reduction via caching): **static prefix at top** (system, tools, reference docs), **dynamic suffix at bottom** (user messages, tool outputs). **Nigdy nie mutuj prefixu by update state** — Claude Code appends reminders jako new user messages. Explicit `cache_control: {type: ephemeral}` breakpoints (max 4). Min 1024 tokenów. Pricing: cache writes +25% / +100% (1h), cache reads -90%. Failures są silent (oba `cache_creation_input_tokens` i `cache_read_input_tokens` = 0).

**Neo bug warning:** working memory between breakpoints invalidates every cache hit. 3 breakpoints z intermediate breakpoints every 18 content blocks (Anthropic's 20-block lookback). Claude Code maintains ~92% cache hit rate keeping prefix immutable.

### Opus 4.5+ contextual awareness + dial-back na CRITICAL language

Anthropic's own prompting notes: Opus 4.5/4.6/4.7 **more responsive** do system prompts — jeśli wcześniej miałeś aggressive *"CRITICAL / YOU MUST"* by zmniejszyć undertriggering, teraz potrzebujesz dial-back albo dostaniesz **overtriggering**. Normal *"Use this tool when…"* wystarcza. Tendencja do overengineeringu — dodaj *"avoid over-engineering"*. Context awareness (widzi remaining budget) — tell it jeśli compaction jest active, żeby nie wrap up prematurely.

### Sean Grove: spec = source, code = binary

**AI Engineer World's Fair 2025:** *"A written specification effectively aligns humans."* Specs są do LLM code tym czym source do compiled binary — *"we keep the generated code and delete the prompt… like you shred the source and then very carefully version control the binary."* OpenAI Model Spec jako exemplar: Markdown na GitHubie, każda klauzula ma ID + example prompts jako "unit tests." **Caveat:** Grove nie pokazuje automated spec→code loops w skali; to głównie advocacy dla lepszych requirements docs.

**Dla FORGE/ITRP:** spec per feature z ID-owanymi klauzulami + example inputs/outputs jako eval set. Każda prompt/skill zmiana re-run's tych przykładów.

### Geoffrey Huntley stdlib: biblioteka promptów

**ghuntley.com:** maintaining "standard library" of prompts. Przykład: Amp codebase uses Svelte 5, Claude ciągle sugerował Svelte 4, napisali prompt enforcing Svelte 5. **Core thesis:** *"LLMs can be programmed for consistent outcomes."*

**Transfer:** `stdlib/` folder z promptami per recurring issue — FORGE: `stdlib/prefer_udf_over_map.md`, `stdlib/unity_catalog_fqn.md`. ITRP: `stdlib/pydantic_v2_not_v1.md`, `stdlib/tanstack_query_not_swr.md`. Sprawdzane w pre-commit hooks grepującym kod.

### Don't waste your back pressure

Huntley + Moss: automated feedback (types, linters, tests, builds) **to jest** to co umożliwia agentom pracę na longer horizons. Agenci stają się znacznie bardziej reliable gdy structure around them daje automated correctness signals. **Zastosowanie:** każde Wasze Action/skill kończy się automated verification (test, lint, compile); failure feeds back jako next user message.

### Context-Efficient Backpressure (HumanLayer, Dec 2025)

Wrap test/build/lint commands z `run_silent.sh`: on success → single `✓`; on failure → dump stashed output. Cel: stay w "~75k token smart zone." Surface jedno failure at a time; strip generic stack frames; filter timing info. *Every line of `PASS src/utils/helper.test.ts` is waste.*

---

## 4. Frameworki agentowe i orkiestracja — co przetrwało produkcję

### Zasada dekompozycji: kiedy multi-agent jest WORSE niż single

**Najważniejsza reguła, najczęściej łamana.** DeepMind + McEntire/Wander (CIO): multi-agent wins **tylko** gdy tasks są **decomposable** — subtasks nie zależą od intermediate state siebie nawzajem. Single agent gdy state jest shared, coherence matters, lub tasks są *"deep and narrow."*

**McEntire:** single agent succeeded 28/28 attempts; pipeline/hierarchy/stigmergic structures all failed (*"hierarchy failed to delegate, pipeline went in circles"*). Caveat: small sample.

**Walden Yan (Cognition):** Dla deep interdependent tasks (coding, long-form writing) — **single-threaded linear agent**. Gdy context overflows — compress history dedicated summarizer modelem, nie spawn parallel workers. Flappy Bird przykład: subagent 1 zbudował Mario-styled background, subagent 2 niekompatybilnego birda.

**Reguła decyzji dla FORGE:**
- **Migration ONE pipeline end-to-end = single agent** (shared state: column names, partitioning, lineage)
- **Profiling 100 independent tables = multi-agent** (decomposable)
- **Refactor of cross-pipeline shared library = single agent**
- **Generate boilerplate DAG per każdej z 50 tabel = multi-agent**

### Orchestrator-Worker (Anthropic multi-agent research)

Lead agent plans, decomposes query, spawns 3–5 subagentów z explicit objectives / output format / tool guidance / task boundaries. Subagenci w own context windows; results funnel back do lead. **Evidence:** Opus-4 lead + Sonnet-4 subagents outperformed single-agent Opus-4 by **90.2%** na breadth-first research eval. Token usage accounts for ~80% variance. Costs ~**15× a chat**.

**FORGE fit:** read-heavy tasks (schema discovery cross-catalog, cross-table profiling, lineage expansion). **NOT** dla interdependent coding/write tasks.

**Effort-scaling heuristics w orchestrator prompt (Anthropic):** *"simple fact-find = 1 agent, 3–10 tool calls; comparison = 2–4 agents × 10–15 calls; complex = 10+ agents."* Bez tego agenci spawnowali 50 subagentów dla trivial queries. Hard-code dla FORGE: *"discover 1 table → 1 agent; migrate 1 pipeline → 2–4; whole catalog → ≤10, write to disk."*

### Share full traces, not messages (handoff protocol)

Cognition Principle 1 + GitHub engineering blog: gdy handoff jest required, pass **full agent trace** — nie summaries — i użyj **typed/schema-validated payloads** (MCP-style input/output schemas). Schema violations jako contract failures (retry/repair/escalate).

*"debugging shifts from 'inspect logs and guess' to 'this payload violated schema X.'"*

**FORGE/ITRP:** Pydantic models dla every inter-agent payload (Unity Catalog FQN objects, PySpark column schemas). **Nigdy free-text między agentami w prod.**

### Artifact-based outputs (filesystem jako bus)

Anthropic: subagents write large outputs do **filesystem/blob store** rather niż funnel przez orchestrator context. Lead passes file paths/pointers, not content. Unika "game of telephone" i token bloat; konieczne >~10K tokenów outputu.

**FORGE:** ADLS/Volumes w Databricks lub `/tmp/forge-run-{id}/` dla profiling reports, generated SQL, plans. Orchestrator widzi tylko `abfss://.../plan.md`. **ITRP:** GCS paths.

### Twelve-Factor Agents (HumanLayer)

**Dex Horthy:** *"Good agents are mostly just software"* — deterministic code z LLM steps at decision points. Own prompts, own context window, tools as structured outputs (JSON → typed code path), explicit control flow (DAG), stateless reducer. Horthy surveyed many YC founders — **most rolled their own**, nie używali frameworków. *"Most products billing themselves as AI Agents are not all that agentic."* Zidentyfikował **"dumb zone" — 40–60% context fill** gdzie recall degraduje.

**Dla FORGE (highest relevance):** model FORGE jako **DAG of Python steps z LLM calls at branch points** (plan, review, repair), NIE autonomous loop. Keep LLM utilization <40% context. Pełny autonomous loops fail w customer-facing prod.

### Code execution over tool chains (MCP efficiency)

Anthropic "Code execution with MCP": zamiast exposować hundreds of MCP tools up-front, let agent write code który calls tools/APIs i processes intermediate results locally (filter 10k rows → return 5). Load tool definitions lazily.

**Dla FORGE (bardzo mocny):** zamiast wrapować każdą metodę Databricks SDK jako "tool," daj agentowi sandboxed Python kernel z `from databricks.sdk import WorkspaceClient` i niech pisze code. Huge token savings na list/describe loops. **Dla ITRP:** sandboxed Python z `google.cloud.firestore`, `google.cloud.bigquery`.

### LangGraph checkpointing dla durable state

LangChain v0.2: Checkpointer saves state after each node. **Postgres** dla durable/queryable (recommended production default), **Redis** dla <1ms reads + TTL, **SQLite** dla local dev. Enables resume, time-travel, human-in-loop interrupt.

**Dla FORGE:** Postgres checkpointer na Azure Flexible Postgres dla long-running migration jobs. **Dla ITRP:** Cloud SQL Postgres.

**Anti-pattern (Azguards case study):** naively saving large RAG payloads w checkpoint state causes PostgreSQL write-amplification (TOAST). **Pointer State Pattern:** store payload w Redis/GCS, save tylko `__ptr__:<uri>` w graph state. Krytyczne gdy FORGE agents handle large DataFrames/schemas.

### Framework comparison — co rzeczywiście ships

Field report (hemangjoshi37a, Aaron Yu, Horthy): po shipowaniu na wszystkich trzech 18 miesięcy:
- **LangGraph** dla workflows needing loops/conditionals/resumability (state-machine model)
- **CrewAI** dla linear role-based pipelines (ships faster, poorer debugging — *"print doesn't work in Tasks"*)
- **AutoGen v0.4** tylko gdy open-ended group chat to core value

**Common observation:** logging w CrewAI *"is a huge pain."* AutoGen forcing deterministic flow = rebuilding LangGraph. Horthy: *"I don't see a lot of frameworks in production customer-facing agents"* — most roll own.

**Rekomendacja dla FORGE:** **LangGraph** (Python-native, graph-first, Postgres checkpointer) LUB roll your own z Pydantic AI + własny state store. **Unikaj CrewAI** dla data-eng tasks gdzie observability matters.

**Anti-pattern:** *"Framework loyalty driving architecture."* Mixing jest fine — LangGraph top-level z CrewAI subpipeline common.

### Pydantic AI dla type-safe Python-native agentów

**ZenML comparison:** Pydantic AI V1 (Sep 2025) — graph-optional, type-first, native Logfire/OpenTelemetry tracing. Simpler niż LangGraph dla linear flows; add graphs when needed.

**Primary recommendation dla FORGE** jeśli chcecie Python-native typing throughout. Pydantic validators enforce UC object contracts at every agent boundary. Logfire → export do Azure Monitor/Grafana.

### Cost circuit breaker (runaway loop defense)

Fountain City + Runyard + Digital Applied: **layered defenses:**
1. Per-task iteration cap (~25 turns default)
2. Tool-call dedup hash — trip jeśli same (name, canonical-args) hash appears 3×
3. Per-user i per-tenant daily $ caps
4. Rolling spend-rate monitor (tokens/task vs 5-task average)
5. Alert-first, not auto-kill (kill tylko dla write-access agents)

**Reported evidence:** LangChain retry loop → **$47,000 w 11 dni**; Reddit r/AI_Agents **$30,000 agent loop**. Rate limits alone nie catch "100 normal-sized calls."

**Dla FORGE (critical):** writes do Databricks (może spin jobs clusters); **dla ITRP:** touches payment data. Hard-cap per-run $, circuit-break na repeated identical SQL generations.

### Observability — practitioner ranking

Hamel Husain panel:
- **Braintrust** — cleanest UI, strong human-annotation ("money table" of failure modes); concerns o proprietary BTQL i *"Loop"* feature stacking abstractions
- **Langfuse** — open-source/MIT, self-hosted, framework-agnostic, ClickHouse-native; wymaga Postgres+ClickHouse+Redis+S3+K8s ops
- **LangSmith** — zero-config dla LangChain/LangGraph ale vendor lock-in, closed-source
- **Phoenix** — notebook-centric, Hamel's *"favorite OSS eval tool"*
- **Logfire** — Pydantic's OTel-native (first-class dla Pydantic AI)

**Dla FORGE:** self-host **Langfuse** w Azure (fits existing ClickHouse/Postgres footprint; data sovereignty) LUB **Logfire** jeśli standardize na Pydantic AI. **Dla ITRP:** to samo na GCP. **Skip LangSmith** chyba że fully committed do LangChain.

**Anti-pattern (Hamel):** sceptyczny o auto-eval features gdzie AI zarówno tworzy rubric jak i scores — hides flaws behind confident scores.

### LLM-as-judge dla multi-agent eval

Single LLM call outputting 0.0–1.0 + pass/fail across rubric (factual accuracy, citation accuracy, completeness, source quality, tool efficiency) aligned najlepiej z human judgment. **Multiple narrow judges worse niż one structured judge. Binary pass/fail > 1–5 scales.** ~20 representative queries catches 80% early-stage bugs.

**Dla FORGE:** judge = *"does generated PySpark pass schema validation + lint + dry-run EXPLAIN without errors?"* Binary. Small gold set 20 migration cases; rerun on every prompt change.

**Anti-pattern:** don't evaluate agents tylko as black box — also eval per-stage *"transition failure matrices"* (last successful state vs first failure).

### Chip Huyen's compound error rule

Per-step accuracy 95% over 10 steps → 60% end-to-end; over 100 steps → 0.6%. Therefore: **replace every step you CAN make deterministic z code.** Agent tylko na branches które genuinely need reasoning.

**Dla FORGE:** data-eng tasks mają many deterministic steps (list schemas, run EXPLAIN, validate against contract). **Don't let LLM "decide" these** — pin jako Python. Agent chooses next branch only.

### Context engineering over prompt engineering

Anthropic "Effective context engineering": manage **what tokens są w context at each step**, nie tylko prompt wording. Three tools: **(a) compaction** (summarize when full), **(b) structured note-taking** (agent writes own scratch file), **(c) sub-agent isolation** (detail stays w subagent's window, only synthesis returns).

**Dla FORGE long migrations:** compaction dla chat history; note-taking (`plan.md`, `progress.md` w run dir); subagent dla *"read 50 table schemas and return one-line summaries."*

### Rainbow deployments dla stateful agents

Agenci są long-lived state machines; standard blue/green breaks mid-flight. Gradually shift traffic old→new, keeping oba live until in-progress sessions drain. **Dla FORGE:** jeśli staje się long-running service — Azure Container Apps revisions z traffic split. Dla batch jobs — non-issue.

### Long-context isn't the answer (HumanLayer, Mar 2026)

Po Claude Code defaulting na Opus 4.6 z 1M context, HumanLayer switched back do Opus 4.5. **Instruction adherence zdegradowane even well below 200k tokens:** model ignored design docs, made trivial mistakes. **Key concept: "instruction budget" stays constant even as context window grows** (YaRN-style sequence extension doesn't add capacity to attend).

**Context isolation (subagents, progressive disclosure, backpressure) beats context expansion.** Direct implication dla FORGE: nie licz na 1M context jako rozwiązanie na bloat — używaj FIC + subagents.

---

## Synteza: rekomendacje dla Waszego skill ecosystem

**Trzy nadrzędne zasady wynikające z badania:**

Po pierwsze — **deterministyczne wymuszenie > prompt enforcement**. Każdy Wasz gate powinien mieć dwie warstwy: `<HARD-GATE>` w SKILL.md (dla modelu) + `PreToolUse`/`PostToolUse` hook z `exit 2` (dla pewności). Prompty dają 70–90%, hooki 100%. Ta luka to dokładnie miejsce, gdzie zawodzą Wasze enforcement gates.

Po drugie — **progressive disclosure wszędzie**. CLAUDE.md <60 linii z pointerami do `agent_docs/`. SKILL.md z YAML metadata; body ładuje się on-demand. Thoughts symlink dla cross-session memory. FIC (Research→Plan→Implement) dla każdego >3-pliku zadania. Cel: <25k tokenów startup overhead, utilizacja 40–60%.

Po trzecie — **single-agent dla interdependent work, multi-agent tylko dla decomposable fan-out**. Dla FORGE: migracja jednego pipeline'u end-to-end = single agent; profilowanie 100 tabel = multi-agent. To odwraca intuicję — większość zespołów przeszacowuje kiedy multi-agent pomaga.

**Konkretna architektura do wdrożenia:**

| Warstwa | FORGE | ITRP |
|---|---|---|
| Orkiestracja | LangGraph + Postgres checkpointer LUB Pydantic AI + custom state | To samo, Cloud SQL |
| Stan | Postgres checkpoint + ADLS/Volumes (Pointer Pattern) | Postgres checkpoint + GCS |
| Payload między agentami | Pydantic models walidowane na boundary | To samo |
| Pamięć | CLAUDE.md (reguły) + `.memory/` (learnings) + nested per domain | To samo + per domain (api/web/infra) |
| Single vs multi | Single dla pipeline; multi tylko dla decomposable | Single default |
| Safety | File-artifact outputs, nigdy nie combine kodu dwóch agentów | To samo + fintech-specific gitleaks, deny-list on prod |
| Cost control | Per-run $ cap + iteration cap + dedup hash + daily alerts | To samo + per-user cap |
| Observability | Self-hosted Langfuse LUB Logfire | To samo na GCP |
| Eval | 20-query gold set + binary LLM-as-judge | To samo per warstwę |
| Code execution | Sandboxed Python > typed MCP tools dla Databricks SDK | To samo dla GCP SDK |
| Deterministic vs agentic | Pin każdy non-reasoning step jako Python; LLM only at genuine branches | To samo |

**Co przestać robić natychmiast:** (1) auto-generować CLAUDE.md przez `/init`; (2) używać MCP gdzie jest CLI; (3) spawnować subagentów dla spójnych zadań; (4) trzymać docs na wiki; (5) edytować prompty w Python bez versioning; (6) pisać ADR jako design doc; (7) ufać advisory language w skillach bez hard-gate; (8) hoardować skille/MCPs/plugins bez kwartalnego audytu.

**Czego oczekiwać z szybkiego starzenia się tej wiedzy:** wszyscy cytowani autorzy (Ronacher wprost, Vincent implicite, Huntley w tonie) ostrzegają, że ich posts *"will age poorly."* Okno 2025→kwiecień 2026 zobaczyło launch Claude Code plugin system, launch skills, Opus 4.5→4.6→4.7, AGENTS.md standardization, cztery konkurujące methodologies (Superpowers, FIC, Ralph, 12-Factor Agents). Pinujcie known-good wersje modelu, trzymajcie weekly eval canary (5 canonical tasks), traktujcie każdy specyficzny model version / plugin API / hook behavior jako subject to frequent change.

Najważniejsza nieoczywista konkluzja: **najbardziej "zaawansowane" zespoły 2026 roku produkują najprostsze setupy** — 60-liniowy CLAUDE.md, gh zamiast GitHub MCP, Python w Dockerze zamiast mashup czterech frameworków, single-threaded linear agent zamiast swarm. Złożoność zjada kontekst, kontekst to jedyna skończona rzecz. Kto pierwszy to zrozumie — wygrywa sprint.