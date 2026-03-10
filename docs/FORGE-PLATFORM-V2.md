# Forge Platform v2 — Architecture Document

> **Status**: DRAFT — pending review
> **Created**: 2026-03-10
> **Context**: Deep-Align + Deep-Verify → Architecture Design
> **Scope**: Full platform redesign — CLI + API + Web UI + Storage + LLM Abstraction

---

## 1. Executive Summary

Forge v1 is a CLI-only change orchestrator integrated with Claude Code, storing state in JSON files. Forge v2 transforms it into a **multi-layer platform** with:

- **Web UI** — drag & drop entity management, execution view, AI-assisted suggestions
- **API layer** — FastAPI backend serving both CLI and Web UI
- **Dual storage** — JSON files (standalone CLI) or PostgreSQL (platform mode)
- **Knowledge base** — versioned knowledge objects linked to all entities
- **LLM abstraction** — provider-agnostic execution with mandatory contracts
- **Reusable components** — acceptance criteria templates, guideline library

### Key Architectural Decisions (from Deep Verify)

| ID | Decision | Rationale |
|----|----------|-----------|
| AD-1 | JSON = basic mode, DB = full features | Knowledge versioning and impact analysis don't work well in flat files |
| AD-2 | Context Assembly Contract is a first-class design artifact | It's the core value proposition — determines LLM execution quality |
| AD-3 | Every LLM interaction goes through a Contract | No ad-hoc prompting — input schema, output schema, validation rules |
| AD-4 | Storage adapter pattern with explicit feature parity matrix | Users know exactly what each mode supports |
| AD-5 | Knowledge objects as new first-class entity (K-NNN) | Fills gap between lessons/decisions and actionable LLM context |
| AD-6 | Acceptance Criteria Templates as library (AC-NNN) | Enables reuse and consistency across tasks |
| AD-7 | Event Sourcing with Redis Streams | Full audit trail, replay, natural fit with real-time events and impact analysis |
| AD-8 | Hybrid LLM: LiteLLM transport + custom Contracts | 100+ providers via LiteLLM, contract enforcement stays custom |
| AD-9 | DnD Kit for drag & drop | Actively maintained, flexible entity-to-entity interactions |

---

## 2. System Architecture

### 2.1 Layer Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        CONSUMERS                                │
│                                                                 │
│  ┌──────────────┐    ┌──────────────────────────────────────┐   │
│  │  forge-cli   │    │         forge-web (React/Next.js)    │   │
│  │              │    │                                      │   │
│  │ Claude Code  │    │  Drag & Drop    AI Suggestions      │   │
│  │ integration  │    │  Execution View  Dashboard           │   │
│  │              │    │  Entity CRUD     Knowledge Mgmt      │   │
│  └──────┬───────┘    └──────────────┬───────────────────────┘   │
│         │                           │                           │
│         │  ┌────────────────────┐   │                           │
│         ├──┤ Standalone (JSON)  │   │                           │
│         │  └────────────────────┘   │                           │
│         │                           │                           │
│         │  REST / WebSocket         │  REST / WebSocket         │
│         ▼                           ▼                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  forge-api (FastAPI)                      │   │
│  │                                                          │   │
│  │  ┌────────────┐  ┌──────────────┐  ┌─────────────────┐  │   │
│  │  │ Entity     │  │ LLM          │  │ Event           │  │   │
│  │  │ Services   │  │ Abstraction  │  │ System          │  │   │
│  │  │            │  │ Layer        │  │ (WebSocket)     │  │   │
│  │  └─────┬──────┘  └──────┬───────┘  └────────┬────────┘  │   │
│  │        │                │                    │           │   │
│  │  ┌─────┴────────────────┴────────────────────┴────────┐  │   │
│  │  │              Storage Adapter Interface              │  │   │
│  │  └─────┬─────────────────────────────────┬────────────┘  │   │
│  │        │                                 │               │   │
│  │  ┌─────┴──────────┐            ┌─────────┴───────────┐  │   │
│  │  │  JSON Adapter  │            │ PostgreSQL Adapter   │  │   │
│  │  │  (standalone)  │            │ (platform mode)      │  │   │
│  │  └────────────────┘            └─────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  LLM Providers                           │   │
│  │  Claude API  │  OpenAI API  │  Local (Ollama)  │  ...   │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Operating Modes

| Mode | CLI | Web UI | Storage | LLM | Real-time |
|------|-----|--------|---------|-----|-----------|
| **Standalone** | Direct JSON read/write | N/A | JSON files | Any (via CLI config) | N/A |
| **Local Platform** | → local API | → local API | PostgreSQL (local) | Any (via API config) | WebSocket |
| **Remote Platform** | → remote API | → remote API | PostgreSQL (cloud) | Any (via API config) | WebSocket |
| **SaaS** (future) | → SaaS API | → SaaS web | PostgreSQL (managed) | Tenant-configured | WebSocket |

**Rule**: CLI detects mode from config (`~/.forge/config.toml`):
```toml
[mode]
type = "standalone"  # standalone | local | remote

[standalone]
data_dir = "./forge_output"

[remote]
api_url = "https://forge.example.com/api"
api_key = "..."
```

### 2.3 Communication Patterns

```
CLI (standalone)  ──→ JSON files (direct I/O, current behavior)

CLI (platform)    ──→ REST API ──→ Storage Adapter ──→ DB
                                ──→ Event Bus ──→ WebSocket ──→ Web UI

Web UI            ──→ REST API (CRUD, actions)
                  ──→ WebSocket (real-time events, execution streaming)

LLM execution     ──→ LLM Abstraction Layer ──→ Provider API
                  ──→ Event Bus (progress updates)
```

---

## 3. Entity Model

### 3.1 Entity Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ENTITY MAP                                  │
│                                                                     │
│  STRATEGIC         PLANNING           EXECUTION         LEARNING    │
│  ─────────         ────────           ─────────         ────────    │
│                                                                     │
│  Objective ──────→ Idea ────────────→ Task ──────────→ Lesson       │
│  (O-NNN)           (I-NNN)            (T-NNN)          (L-NNN)     │
│  │                 │                  │                 │            │
│  │ KR-1..N         │ relations        │ depends_on      │ promotes  │
│  │                 │ parent/child     │ subtasks        ▼            │
│  │                 │                  │                 Knowledge    │
│  │                 ▼                  ▼                 (K-NNN)     │
│  │                Decision           Change                         │
│  │                (D-NNN)            (C-NNN)                        │
│  │                                                                  │
│  │  STANDARDS          VALIDATION        REUSABLE                   │
│  │  ─────────          ──────────        ────────                   │
│  │                                                                  │
│  └──derives──→ Guideline          Gate              AC Template     │
│                (G-NNN)            (config)          (AC-NNN)        │
│                                                                     │
│  All entities linked via:                                           │
│  - Direct reference (field value)                                   │
│  - Scope inheritance (scope matching)                               │
│  - Knowledge links (many-to-many)                                   │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 New Entity: Knowledge Object (K-NNN)

**Purpose**: Condensed, versioned, reusable knowledge that enriches LLM execution context.

**Sources**: Documentation analysis, lessons learned (after acceptance), user input, research findings, codebase analysis.

```json
{
  "id": "K-001",
  "title": "Redis Stack — available data structures",
  "category": "technical-context",
  "content": "Redis Stack 7.4 supports: JSON, Search, TimeSeries, Graph, Bloom...",
  "status": "ACTIVE",
  "version": 3,
  "scopes": ["backend", "database"],
  "tags": ["redis", "data-structures"],

  "source": {
    "type": "documentation",
    "ref": "https://redis.io/docs/stack/",
    "derived_from_lessons": ["L-012", "L-015"]
  },

  "linked_entities": [
    { "entity_type": "objective", "entity_id": "O-001", "relation": "context" },
    { "entity_type": "task", "entity_id": "T-005", "relation": "required" },
    { "entity_type": "idea", "entity_id": "I-003", "relation": "context" }
  ],

  "dependencies": ["K-003"],

  "versions": [
    {
      "version": 3,
      "content": "...(current)...",
      "changed_by": "user",
      "changed_at": "2026-03-10T10:00:00Z",
      "change_reason": "Added TimeSeries module info"
    },
    {
      "version": 2,
      "content": "...(previous)...",
      "changed_by": "ai",
      "changed_at": "2026-03-05T14:00:00Z",
      "change_reason": "Updated for Redis Stack 7.4"
    }
  ],

  "review": {
    "last_reviewed_at": "2026-03-10T10:00:00Z",
    "review_interval_days": 30,
    "next_review_at": "2026-04-09T10:00:00Z"
  },

  "created_at": "2026-02-15T09:00:00Z",
  "updated_at": "2026-03-10T10:00:00Z",
  "created_by": "user"
}
```

**Category taxonomy**:
| Category | Description | Example |
|----------|-------------|---------|
| `domain-rules` | Business rules, domain logic | "Invoice must have at least one line item" |
| `api-reference` | API endpoints, contracts, integration points | "Payment gateway API v3 endpoints" |
| `architecture` | System design, component relationships | "Event sourcing pattern in order service" |
| `business-context` | Business strategy, stakeholder requirements | "Q1 priority: reduce churn by 15%" |
| `technical-context` | Technology capabilities, limitations | "Redis Stack available data structures" |
| `code-patterns` | Code conventions, patterns used in project | "Repository pattern implementation in services/" |
| `integration` | External system integration details | "SAP ERP connection via RFC" |
| `infrastructure` | Deployment, infrastructure, DevOps | "K8s cluster topology and resource limits" |

**Status lifecycle**:
```
DRAFT → ACTIVE → REVIEW_NEEDED → ACTIVE (after review)
                                → DEPRECATED → ARCHIVED
```

**Link relation types**:
| Relation | Meaning |
|----------|---------|
| `required` | Must be included in LLM context for this entity |
| `context` | Provides useful background, include if space permits |
| `reference` | Available for lookup, not auto-included |

**Impact analysis** (when knowledge changes):
1. Find all `linked_entities` with relation `required` or `context`
2. For each linked task (TODO or IN_PROGRESS): flag as potentially affected
3. For completed tasks: log warning, user/AI decides if rework needed
4. For linked ideas/objectives: informational update

**Knowledge operations**:
| Operation | Description |
|-----------|-------------|
| Create | Manual input, from lesson acceptance, from documentation analysis |
| Update | New version created, old version retained, impact analysis triggered |
| Merge | Combine two K objects into one (keep both histories) |
| Split | Break one K object into multiple (maintain links) |
| Link | Drag & drop or AI-suggested linking to entities |
| Review | Periodic or triggered review for staleness |
| Deprecate | Mark as outdated, warn linked entities |

**Contract (add)**:
```
Required: title, category, content
Optional: scopes, tags, source, linked_entities, dependencies, review.review_interval_days
```

**Contract (update)**:
```
Required: id
Optional: title, content (creates new version + requires change_reason),
          status, scopes, tags, linked_entities (append-merge),
          dependencies, review
```

### 3.3 New Entity: Acceptance Criteria Template (AC-NNN)

**Purpose**: Reusable, parameterized acceptance criteria for consistent quality standards.

```json
{
  "id": "AC-001",
  "title": "API Response Time",
  "description": "Ensures API endpoint responds within target latency",
  "template": "API endpoint {endpoint} responds within {max_ms}ms at p{percentile}",
  "category": "performance",
  "parameters": [
    { "name": "endpoint", "type": "string", "description": "API endpoint path" },
    { "name": "max_ms", "type": "number", "default": 200, "description": "Max response time in ms" },
    { "name": "percentile", "type": "number", "default": 95, "description": "Percentile (p95, p99)" }
  ],
  "scopes": ["backend", "api"],
  "tags": ["performance", "latency"],
  "verification_method": "Load test with k6 or equivalent",
  "status": "ACTIVE",
  "usage_count": 12,
  "created_at": "2026-02-01T00:00:00Z"
}
```

**When applied to a task**:
```json
{
  "acceptance_criteria": [
    {
      "text": "API endpoint /api/users responds within 200ms at p95",
      "from_template": "AC-001",
      "params": { "endpoint": "/api/users", "max_ms": 200, "percentile": 95 }
    },
    {
      "text": "User receives clear error message on invalid input",
      "from_template": null
    }
  ]
}
```

**Category taxonomy**: `performance`, `security`, `quality`, `functionality`, `accessibility`, `reliability`, `data-integrity`, `ux`

**Contract (add)**:
```
Required: title, template, category
Optional: description, parameters, scopes, tags, verification_method
```

### 3.4 Modified Existing Entities

#### Task — additions
```json
{
  "...existing fields...",
  "knowledge_ids": ["K-001", "K-003"],
  "acceptance_criteria": [
    {
      "text": "...",
      "from_template": "AC-001",
      "params": { "endpoint": "/api/users" }
    }
  ],
  "test_requirements": {
    "unit": true,
    "integration": false,
    "e2e": false,
    "description": "Unit tests for validation logic"
  }
}
```

#### Idea — additions
```json
{
  "...existing fields...",
  "knowledge_ids": ["K-005"]
}
```

#### Objective — additions
```json
{
  "...existing fields...",
  "knowledge_ids": ["K-010", "K-011"]
}
```

#### Lesson — additions
```json
{
  "...existing fields...",
  "promoted_to_knowledge": "K-015",
  "promoted_to_guideline": "G-020"
}
```

### 3.5 Entity Relationship Map (Complete)

```
                    ┌──────────┐
                    │Objective │ O-NNN
                    │          │
                    │ KR-1..N  │
                    └──┬───┬───┘
                       │   │
          advances_    │   │ derived_from
          key_results  │   │
                       │   ▼
    ┌──────────┐      │  ┌──────────┐
    │   Idea   │◄─────┘  │Guideline │ G-NNN
    │  I-NNN   │         │          │
    │          │         │ scope    │
    │ parent   │         │ weight   │
    │ relations│         └──────────┘
    └──┬───────┘              ▲
       │                      │ promotes
       │ origin               │
       ▼                      │
    ┌──────────┐         ┌────┴─────┐         ┌──────────┐
    │  Task    │────────→│  Lesson  │────────→│Knowledge │ K-NNN
    │  T-NNN   │ task_id │  L-NNN   │ accepts │          │
    │          │         │          │         │ versioned│
    │depends_on│         └──────────┘         │ scoped   │
    │subtasks  │                              └──────────┘
    └──┬───┬───┘                                  │
       │   │                              linked_entities
       │   │ task_id                      (many-to-many)
       │   ▼                                  │
       │  ┌──────────┐                        │
       │  │Decision  │ D-NNN                  ▼
       │  │          │                  ┌─────────────┐
       │  │ type     │                  │ Objective    │
       │  │ status   │                  │ Idea         │
       │  └──────────┘                  │ Task         │
       │                                └─────────────┘
       │ task_id
       ▼
    ┌──────────┐         ┌──────────┐
    │ Change   │ C-NNN   │AC Template│ AC-NNN
    │          │         │           │
    │ file     │         │ template  │
    │ action   │         │ params    │
    └──────────┘         └───────────┘
                              │
                         from_template
                              │
                              ▼
                         task.acceptance_criteria[]
```

---

## 4. Process Architecture

### 4.1 Flexible Process Paths

```
USER INPUT
    │
    ├── Simple task ──────────────────────────────────→ [Quick Path]
    │   "Fix this bug"                                   │
    │                                                    ▼
    │                                              ┌──────────┐
    │                                              │ /do task  │
    │                                              │           │
    │                                              │ • create  │
    │                                              │ • execute │
    │                                              │ • record  │
    │                                              │ • validate│
    │                                              └──────────┘
    │
    ├── Clear goal, multiple tasks ──────────────────→ [Standard Path]
    │   "Add user authentication"                       │
    │                                                   ▼
    │                                     ┌──────────────────────────┐
    │                                     │ Objective (optional)     │
    │                                     │     │                    │
    │                                     │     ▼                    │
    │                                     │ /plan → tasks            │
    │                                     │     │                    │
    │                                     │     ▼                    │
    │                                     │ /run → execute all       │
    │                                     │     │                    │
    │                                     │     ▼                    │
    │                                     │ /compound → lessons      │
    │                                     └──────────────────────────┘
    │
    ├── Complex / risky / unclear ────────────────────→ [Full Path]
    │   "Redesign the data pipeline"                    │
    │                                                   ▼
    │                              ┌─────────────────────────────────────┐
    │                              │ /objective → business goal + KRs    │
    │                              │     │                               │
    │                              │     ▼                               │
    │                              │ /idea → proposals                   │
    │                              │     │                               │
    │                              │     ▼                               │
    │                              │ /discover → explore + risks         │
    │                              │     │                               │
    │                              │     ▼                               │
    │                              │ /decide → resolve open decisions    │
    │                              │     │                               │
    │                              │     ▼                               │
    │                              │ /plan → task graph                  │
    │                              │     │                               │
    │                              │     ▼                               │
    │                              │ /run → execute all                  │
    │                              │     │                               │
    │                              │     ▼                               │
    │                              │ /compound → lessons                 │
    │                              └─────────────────────────────────────┘
    │
    └── Research-first ──────────────────────────────→ [Discovery Path]
        "Can we use event sourcing here?"               │
                                                        ▼
                                      ┌───────────────────────────────┐
                                      │ /idea → capture question      │
                                      │     │                         │
                                      │     ▼                         │
                                      │ /discover → deep analysis     │
                                      │     │                         │
                                      │     ├── GO → /plan            │
                                      │     └── NO-GO → /idea reject  │
                                      └───────────────────────────────┘
```

### 4.2 Feedback Loops

```
┌─────────────────────────────────────────────────────────────────┐
│                    POST-EXECUTION FEEDBACK                       │
│                                                                 │
│  Task DONE                                                      │
│      │                                                          │
│      ├──→ Lesson L-NNN (auto or manual)                         │
│      │        │                                                 │
│      │        ├──→ [User accepts as knowledge?]                 │
│      │        │        │                                        │
│      │        │        ▼ Yes                                    │
│      │        │    Knowledge K-NNN (DRAFT → ACTIVE)             │
│      │        │    → linked to future tasks by scope/tag        │
│      │        │                                                 │
│      │        ├──→ [Promote to guideline?]                      │
│      │        │        │                                        │
│      │        │        ▼ Yes                                    │
│      │        │    Guideline G-NNN (ACTIVE)                     │
│      │        │    → auto-applied to matching scopes            │
│      │        │                                                 │
│      │        └──→ [Triggers new work?]                         │
│      │                 │                                        │
│      │                 ├──→ New Task (add to current project)    │
│      │                 ├──→ New Idea (for future exploration)    │
│      │                 └──→ New Objective (if strategic)         │
│      │                                                          │
│      └──→ Knowledge update trigger                              │
│               │                                                 │
│               ▼                                                 │
│           [Code changed files X, Y, Z]                          │
│           [K-005 references file X]                             │
│           → Flag K-005 for REVIEW_NEEDED                        │
│                                                                 │
│  Knowledge UPDATED                                              │
│      │                                                          │
│      ▼                                                          │
│  Impact Analysis                                                │
│      │                                                          │
│      ├──→ T-008 (TODO) uses K-005 → user notified              │
│      ├──→ T-003 (DONE) used K-005 → warning: rework needed?    │
│      └──→ I-002 references K-005 → informational update        │
│                                                                 │
│  Objective ACHIEVED                                             │
│      │                                                          │
│      ├──→ Review derived guidelines (still relevant?)           │
│      ├──→ Archive or retain knowledge objects                   │
│      └──→ Status: ACHIEVED (immutable)                          │
│                                                                 │
│  Objective ABANDONED                                            │
│      │                                                          │
│      ├──→ Review derived guidelines (deprecate?)                │
│      ├──→ Review linked knowledge (still useful?)               │
│      └──→ Lessons: why was it abandoned?                        │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 Knowledge Lifecycle

```
                    ┌──────────────────────┐
                    │     KNOWLEDGE        │
                    │     SOURCES          │
                    │                      │
                    │  • User input        │
                    │  • Documentation     │
                    │  • Lesson accepted   │
                    │  • Research output   │
                    │  • Codebase analysis │
                    │  • AI extraction     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │      DRAFT           │
                    │                      │
                    │  Created but not     │
                    │  yet validated       │
                    └──────────┬───────────┘
                               │ user reviews
                               ▼
                    ┌──────────────────────┐
                    │      ACTIVE          │◄──────────────────┐
                    │                      │                   │
                    │  Available for       │     reviewed,     │
                    │  linking & context   │     still valid   │
                    └──────┬──────┬────────┘                   │
                           │      │                            │
              version      │      │  review_interval           │
              update       │      │  expired                   │
                           │      │                            │
                           ▼      ▼                            │
              ┌────────────┐  ┌──────────────────────┐         │
              │ New version│  │   REVIEW_NEEDED      │─────────┘
              │ created    │  │                      │
              │ + impact   │  │   Flagged for        │─────────┐
              │   analysis │  │   review             │         │
              └────────────┘  └──────────────────────┘         │
                                                               │
                                                    outdated   │
                                                               ▼
                                               ┌──────────────────────┐
                                               │    DEPRECATED        │
                                               │                      │
                                               │  Marked outdated     │
                                               │  Linked entities     │
                                               │  warned              │
                                               └──────────┬───────────┘
                                                          │
                                                          ▼
                                               ┌──────────────────────┐
                                               │    ARCHIVED          │
                                               │                      │
                                               │  Retained for        │
                                               │  history only        │
                                               └──────────────────────┘
```

### 4.4 AI-Assisted Workflows

AI can assist at every stage (always on user request, never autonomous):

| Workflow | AI Action | Trigger |
|----------|-----------|---------|
| **Knowledge suggestion** | "K-005 (Redis patterns) matches Task T-008 scope [backend, database]" | User asks: "suggest knowledge for this task" |
| **Guideline matching** | "G-012 (API pagination) applies to Objective O-003" | User asks: "which guidelines apply?" |
| **Lesson → Knowledge** | "Lesson L-015 could become knowledge object about retry patterns" | After `/compound`, AI proposes promotions |
| **Lesson → Guideline** | "Lesson L-008 (critical) should be a MUST guideline" | After `/compound`, AI proposes promotions |
| **AC suggestion** | "Based on task type 'api', consider AC-001 (response time) and AC-007 (error format)" | During task creation or plan review |
| **Impact assessment** | "K-005 changed. Tasks T-008, T-012 use it. T-008 may need updated instructions." | After knowledge update |
| **Scope inheritance** | "Idea I-003 advances O-001. Inherit scopes [backend, performance]?" | During idea creation |
| **Risk detection** | "Task T-010 modifies auth module but has no security guideline linked" | During plan review |

**AI suggestion mechanism** (provider-agnostic):
1. **Scope/tag matching** (fast, no LLM call): match entity scopes and tags
2. **LLM evaluation** (on demand): send entity pair to LLM with evaluation contract
3. **Embedding search** (future, requires vector DB): semantic similarity

---

## 5. Context Assembly Contract

> **This is the most critical design artifact of the platform.**
> It defines what the LLM receives when executing a task.

### 5.1 Context Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                    LLM EXECUTION CONTEXT                        │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 1. SYSTEM CONTRACT                          [fixed size]  │  │
│  │    • Role definition                                      │  │
│  │    • Output format contract (JSON schema)                 │  │
│  │    • Behavioral constraints                               │  │
│  │    • Available tools/actions                              │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 2. TASK CONTENT                        [max 30% window]   │  │
│  │    • task.description                                     │  │
│  │    • task.instruction                                     │  │
│  │    • task.acceptance_criteria (instantiated from AC-NNN)  │  │
│  │    • task.type                                            │  │
│  │    • task.test_requirements                               │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 3. MUST GUIDELINES                     [max 10% window]   │  │
│  │    • Global guidelines (weight=must)                      │  │
│  │    • Project guidelines (weight=must, matching scopes)    │  │
│  │    ⚠️ ALWAYS included, never truncated                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 4. KNOWLEDGE                           [max 25% window]   │  │
│  │    Priority order:                                        │  │
│  │    a) Direct links (relation=required) — always included  │  │
│  │    b) Direct links (relation=context) — if space permits  │  │
│  │    c) Idea-inherited knowledge — if space permits         │  │
│  │    d) Objective-inherited knowledge — if space permits    │  │
│  │    Only ACTIVE versions. Latest version only.             │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 5. SHOULD GUIDELINES                   [max 10% window]   │  │
│  │    • Project guidelines (weight=should, matching scopes)  │  │
│  │    ⚠️ Omitted if total context > 80% of window            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 6. DEPENDENCY CONTEXT                  [max 10% window]   │  │
│  │    • Completed dependency task outputs (summary)          │  │
│  │    • Decisions made in dependency tasks                   │  │
│  │    • Changes recorded in dependency tasks (file list)     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 7. RISK CONTEXT                         [max 5% window]   │  │
│  │    • Active risk decisions for origin idea                │  │
│  │    • Mitigated risks (summary only)                       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 8. BUSINESS CONTEXT                     [max 5% window]   │  │
│  │    • Objective title + description                        │  │
│  │    • Key Result progress                                  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 9. TEST CONTEXT                         [max 5% window]   │  │
│  │    • Gate definitions (test commands)                      │  │
│  │    • Test patterns from knowledge                         │  │
│  │    • Coverage requirements                                │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Total budget: 100% of provider's context window                │
│  Reserved for output: ~25% of window                            │
│  Available for context: ~75% of window                          │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Assembly Rules

```python
class ContextAssemblyContract:
    """Rules for composing LLM execution context."""

    # Priority order (1 = highest, never truncated)
    SECTIONS = [
        Section("system_contract",    priority=1, max_pct=None,  truncatable=False),
        Section("task_content",       priority=1, max_pct=0.30,  truncatable=False),
        Section("must_guidelines",    priority=1, max_pct=0.10,  truncatable=False),
        Section("knowledge_required", priority=2, max_pct=0.15,  truncatable=False),
        Section("knowledge_context",  priority=3, max_pct=0.10,  truncatable=True),
        Section("should_guidelines",  priority=4, max_pct=0.10,  truncatable=True),
        Section("dependency_context", priority=5, max_pct=0.10,  truncatable=True),
        Section("risk_context",       priority=6, max_pct=0.05,  truncatable=True),
        Section("business_context",   priority=7, max_pct=0.05,  truncatable=True),
        Section("test_context",       priority=8, max_pct=0.05,  truncatable=True),
    ]

    # Overflow strategy
    OVERFLOW_RULES = """
    When total context exceeds available window:
    1. Truncate sections in reverse priority order (9 → 8 → 7 → ...)
    2. Within a section, truncate by relevance:
       - Knowledge: remove context links before required links
       - Guidelines: remove 'may' before 'should'
       - Dependencies: keep latest, remove oldest
    3. NEVER truncate: task_content, must_guidelines, knowledge_required
    4. Log warning when any section is truncated
    5. Include truncation notice in context: "[N items omitted from {section}]"
    """

    # Format
    OUTPUT_FORMAT = """
    Each section rendered as Markdown with clear headers:
    ## Task
    ## Guidelines (MUST)
    ## Knowledge
    ## Guidelines (SHOULD)
    ## Dependencies
    ## Risks
    ## Business Context
    ## Tests
    """
```

### 5.3 Output Contract (what LLM must return)

```json
{
  "$schema": "task-execution-output-v1",
  "required": ["result", "reasoning_trace", "guidelines_checked"],
  "properties": {
    "result": {
      "description": "The actual output (code changes, analysis, etc.)",
      "type": "object"
    },
    "reasoning_trace": {
      "description": "Step-by-step reasoning for decisions made",
      "type": "array",
      "items": { "step": "string", "detail": "string" },
      "minItems": 1
    },
    "guidelines_checked": {
      "description": "Which MUST guidelines were checked and how",
      "type": "array",
      "items": { "guideline_id": "string", "status": "compliant|not_applicable|deviation", "note": "string" }
    },
    "acceptance_criteria_met": {
      "description": "Which AC are met and how",
      "type": "array",
      "items": { "criterion": "string", "met": "boolean", "evidence": "string" }
    },
    "knowledge_gaps": {
      "description": "Any knowledge that was missing or insufficient",
      "type": "array",
      "items": { "description": "string", "suggested_knowledge": "string" }
    },
    "new_risks_identified": {
      "description": "Risks discovered during execution",
      "type": "array"
    },
    "decisions_made": {
      "description": "Decisions made during execution (to be recorded)",
      "type": "array"
    }
  }
}
```

### 5.4 Validation Rules

```python
class OutputValidation:
    """Rules for validating LLM output before accepting."""

    RULES = [
        # Structural
        Rule("reasoning_trace_present", "reasoning_trace must be non-empty array"),
        Rule("all_must_guidelines_addressed", "Every MUST guideline must appear in guidelines_checked"),
        Rule("all_ac_evaluated", "Every acceptance_criterion must appear in acceptance_criteria_met"),

        # Semantic (requires LLM call to verify)
        Rule("no_hallucinated_refs", "File paths mentioned must exist in codebase"),
        Rule("reasoning_coherent", "Reasoning trace must logically support the result"),

        # Provider-specific
        Rule("output_within_schema", "Output matches expected JSON schema"),
    ]

    ON_FAILURE = """
    1. Structural failure → retry with explicit error message (max 2 retries)
    2. Semantic failure → flag to user, do not auto-retry
    3. Schema failure → retry with schema reminder (max 1 retry)
    4. After max retries → mark task FAILED with failure details
    """
```

---

## 6. LLM Abstraction Layer

### 6.1 Provider Adapter Pattern

```python
from typing import Protocol, AsyncIterator

class LLMProvider(Protocol):
    """Interface every LLM provider must implement."""

    async def complete(
        self,
        messages: list[Message],
        config: CompletionConfig
    ) -> CompletionResult: ...

    async def stream(
        self,
        messages: list[Message],
        config: CompletionConfig
    ) -> AsyncIterator[StreamChunk]: ...

    def capabilities(self) -> ProviderCapabilities: ...


class ProviderCapabilities:
    provider_name: str          # "anthropic", "openai", "ollama"
    model_id: str               # "claude-sonnet-4-20250514", "gpt-4o"
    max_context_window: int     # in tokens
    max_output_tokens: int
    supports_streaming: bool
    supports_tool_use: bool
    supports_json_mode: bool
    supports_vision: bool
    supports_thinking: bool     # extended thinking (Claude)
    cost_per_1k_input: float
    cost_per_1k_output: float


class CompletionConfig:
    model: str
    temperature: float = 0.0
    max_tokens: int = 4096
    response_format: str = "text"  # "text" | "json"
    tools: list[ToolDef] | None = None
    system_prompt: str = ""
    stop_sequences: list[str] | None = None


class Message:
    role: str       # "system" | "user" | "assistant"
    content: str


class CompletionResult:
    content: str
    model: str
    usage: TokenUsage
    stop_reason: str


class StreamChunk:
    content: str
    is_final: bool
    usage: TokenUsage | None  # only on final chunk
```

### 6.2 Contract-Based LLM Interaction

**Every LLM call goes through a Contract. No exceptions.**

```python
class LLMContract:
    """Defines a specific type of LLM interaction."""

    id: str                         # "task-execution-v1", "knowledge-suggest-v1"
    name: str                       # Human-readable name
    version: str                    # Semantic version

    # Input
    input_schema: dict              # JSON Schema for input data
    context_assembly: str           # Which ContextAssembly rules to use
    system_prompt_template: str     # Jinja2 template for system prompt
    user_prompt_template: str       # Jinja2 template for user prompt

    # Output
    output_schema: dict             # JSON Schema for expected output
    output_format: str              # "json" | "text" | "markdown"

    # Validation
    validation_rules: list[Rule]    # Structural + semantic rules
    retry_strategy: RetryStrategy   # What to do on failure

    # Provider adaptation
    min_context_window: int         # Minimum context window required
    requires_tool_use: bool         # Needs function calling?
    requires_json_mode: bool        # Needs JSON mode?
    fallback_format: str            # If JSON mode not supported, use this


class RetryStrategy:
    max_retries: int = 2
    retry_on: list[str]             # ["schema_error", "missing_field"]
    escalate_on: list[str]          # ["semantic_error", "hallucination"]
    backoff: str = "none"           # "none" | "linear" | "exponential"
```

### 6.3 Contract Registry

```python
# Built-in contracts
CONTRACTS = {
    # Task execution
    "task-execution-v1":      TaskExecutionContract,
    "task-quick-v1":          QuickTaskContract,

    # Knowledge management
    "knowledge-suggest-v1":   KnowledgeSuggestionContract,
    "knowledge-extract-v1":   KnowledgeExtractionContract,
    "impact-assess-v1":       ImpactAssessmentContract,

    # Planning
    "plan-decompose-v1":      PlanDecompositionContract,
    "ac-suggest-v1":          ACSuggestionContract,
    "guideline-match-v1":     GuidelineMatchContract,

    # Analysis
    "risk-assess-v1":         RiskAssessmentContract,
    "lesson-promote-v1":      LessonPromotionContract,

    # Review
    "code-review-v1":         CodeReviewContract,
    "verify-v1":              VerificationContract,
}
```

### 6.4 Provider Configuration

```toml
# ~/.forge/providers.toml

[providers.anthropic]
api_key_env = "ANTHROPIC_API_KEY"
default_model = "claude-sonnet-4-20250514"
models = [
    "claude-opus-4-20250514",
    "claude-sonnet-4-20250514",
    "claude-haiku-4-5-20251001"
]

[providers.openai]
api_key_env = "OPENAI_API_KEY"
default_model = "gpt-4o"

[providers.ollama]
base_url = "http://localhost:11434"
default_model = "llama3.1:70b"

[defaults]
provider = "anthropic"
model = "claude-sonnet-4-20250514"

# Contract-specific model overrides
[defaults.contract_models]
"task-execution-v1" = "claude-opus-4-20250514"       # Complex tasks → best model
"knowledge-suggest-v1" = "claude-haiku-4-5-20251001"  # Simple matching → fast model
"ac-suggest-v1" = "claude-haiku-4-5-20251001"
```

---

## 7. Storage Architecture

### 7.1 Storage Adapter Interface

```python
from typing import Protocol

class StorageAdapter(Protocol):
    """Interface for all storage backends."""

    # CRUD
    async def create(self, entity_type: str, data: dict) -> dict: ...
    async def get(self, entity_type: str, entity_id: str) -> dict | None: ...
    async def list(self, entity_type: str, filters: dict | None = None) -> list[dict]: ...
    async def update(self, entity_type: str, entity_id: str, data: dict) -> dict: ...
    async def delete(self, entity_type: str, entity_id: str) -> bool: ...

    # Queries
    async def query(self, entity_type: str, query: Query) -> list[dict]: ...
    async def get_related(self, entity_type: str, entity_id: str,
                          relation_type: str) -> list[dict]: ...

    # Knowledge-specific
    async def get_version(self, knowledge_id: str, version: int) -> dict | None: ...
    async def get_impact(self, knowledge_id: str) -> list[dict]: ...

    # Events (platform mode only)
    async def subscribe(self, entity_type: str, callback: Callable) -> None: ...

    # Transactions (platform mode only)
    async def begin_transaction(self) -> Transaction: ...
```

### 7.2 Feature Parity Matrix

| Feature | JSON (Standalone) | PostgreSQL (Platform) |
|---------|:-----------------:|:---------------------:|
| **Entity CRUD** | ✅ Full | ✅ Full |
| **Filtering by status/scope/tag** | ✅ In-memory | ✅ SQL WHERE |
| **Knowledge create/read/update** | ✅ Full | ✅ Full |
| **Knowledge versioning** | ⚠️ Embedded array, no diff | ✅ Version table, diff support |
| **Knowledge impact analysis** | ⚠️ Full scan all files | ✅ Reverse FK JOIN |
| **Relationship queries** | ⚠️ Full scan, slow | ✅ Fast JOINs |
| **Full-text search** | ❌ Not supported | ✅ PostgreSQL FTS |
| **Event sourcing** | ❌ Not supported | ✅ Redis Streams → projections |
| **Real-time events** | ❌ Not supported | ✅ Redis Pub/Sub → WebSocket |
| **Event replay / audit** | ❌ Not supported | ✅ Full replay from Redis Streams |
| **Concurrent access** | ⚠️ Last-write-wins | ✅ Optimistic locking |
| **Multi-user** | ❌ Single user | ✅ Full |
| **Web UI support** | ❌ Not available | ✅ Full |
| **Execution view** | ❌ Not available | ✅ WebSocket streaming |
| **AI suggestions** | ⚠️ Scope/tag matching only | ✅ Full (FTS + LLM) |
| **Drag & drop** | ❌ CLI only | ✅ Full |
| **Backup** | ✅ Copy files | ✅ pg_dump |
| **Offline work** | ✅ Full | ❌ Requires connection |
| **Zero setup** | ✅ Just files | ❌ Requires DB + API |
| **Data migration** | N/A | ✅ Import from JSON |

**Design principle**: JSON mode is a **fully functional CLI experience** for single-user, offline work. Platform mode (PostgreSQL) unlocks Web UI, real-time, multi-user, and advanced AI features.

### 7.3 JSON → PostgreSQL Migration

```
forge-migrate import --source ./forge_output/my-project --target postgresql://...

Process:
1. Read all JSON files from source project
2. Validate entity integrity (all references resolve)
3. Generate sequential IDs (preserve original IDs as aliases)
4. Create junction table entries for many-to-many relationships
5. Import knowledge versions as separate rows
6. Report: entities imported, warnings, errors
```

### 7.4 Database Schema (Conceptual)

```sql
-- Core entities
CREATE TABLE projects (id SERIAL PRIMARY KEY, slug TEXT UNIQUE, goal TEXT, config JSONB, ...);
CREATE TABLE objectives (id SERIAL PRIMARY KEY, project_id INT REFERENCES projects, ext_id TEXT, ...);
CREATE TABLE key_results (id SERIAL PRIMARY KEY, objective_id INT REFERENCES objectives, ...);
CREATE TABLE ideas (id SERIAL PRIMARY KEY, project_id INT REFERENCES projects, parent_id INT REFERENCES ideas, ...);
CREATE TABLE tasks (id SERIAL PRIMARY KEY, project_id INT REFERENCES projects, origin_idea_id INT REFERENCES ideas, ...);
CREATE TABLE decisions (id SERIAL PRIMARY KEY, project_id INT REFERENCES projects, ...);
CREATE TABLE changes (id SERIAL PRIMARY KEY, project_id INT REFERENCES projects, task_id INT REFERENCES tasks, ...);
CREATE TABLE lessons (id SERIAL PRIMARY KEY, project_id INT REFERENCES projects, ...);
CREATE TABLE guidelines (id SERIAL PRIMARY KEY, project_id INT, ...);  -- NULL project_id = global

-- New entities
CREATE TABLE knowledge (id SERIAL PRIMARY KEY, project_id INT, ext_id TEXT, title TEXT, category TEXT,
                        current_version INT, status TEXT, scopes TEXT[], tags TEXT[], ...);
CREATE TABLE knowledge_versions (id SERIAL PRIMARY KEY, knowledge_id INT REFERENCES knowledge,
                                  version INT, content TEXT, changed_by TEXT, change_reason TEXT, ...);
CREATE TABLE ac_templates (id SERIAL PRIMARY KEY, project_id INT, title TEXT, template TEXT,
                           category TEXT, parameters JSONB, scopes TEXT[], ...);

-- Relationship tables (many-to-many)
CREATE TABLE knowledge_links (knowledge_id INT REFERENCES knowledge,
                               entity_type TEXT, entity_id INT, relation TEXT, ...);
CREATE TABLE task_ac (task_id INT REFERENCES tasks, ac_template_id INT REFERENCES ac_templates,
                      params JSONB, instantiated_text TEXT, ...);
CREATE TABLE task_dependencies (task_id INT REFERENCES tasks, depends_on_id INT REFERENCES tasks);
CREATE TABLE task_knowledge (task_id INT REFERENCES tasks, knowledge_id INT REFERENCES knowledge);
CREATE TABLE idea_relations (idea_id INT REFERENCES ideas, target_id INT REFERENCES ideas, relation_type TEXT);

-- Indexes for common queries
CREATE INDEX idx_knowledge_scopes ON knowledge USING GIN (scopes);
CREATE INDEX idx_knowledge_status ON knowledge (status);
CREATE INDEX idx_guidelines_scope ON guidelines (scope);
CREATE INDEX idx_tasks_status ON tasks (status);
CREATE INDEX idx_knowledge_links_entity ON knowledge_links (entity_type, entity_id);

-- Full-text search
CREATE INDEX idx_knowledge_fts ON knowledge USING GIN (to_tsvector('english', title || ' ' || coalesce(current_content, '')));
```

---

## 8. API Architecture

### 8.1 REST API Design

```
Base: /api/v1

# Projects
GET     /projects                          List projects
POST    /projects                          Create project
GET     /projects/{slug}                   Get project
GET     /projects/{slug}/status            Dashboard

# Objectives
GET     /projects/{slug}/objectives        List objectives
POST    /projects/{slug}/objectives        Create objective(s)
GET     /projects/{slug}/objectives/{id}   Get objective detail
PATCH   /projects/{slug}/objectives/{id}   Update objective
GET     /projects/{slug}/objectives/status Coverage dashboard

# Ideas
GET     /projects/{slug}/ideas             List ideas
POST    /projects/{slug}/ideas             Create idea(s)
GET     /projects/{slug}/ideas/{id}        Get idea detail (hierarchy, decisions)
PATCH   /projects/{slug}/ideas/{id}        Update idea
POST    /projects/{slug}/ideas/{id}/commit Commit idea

# Tasks
GET     /projects/{slug}/tasks             List tasks
POST    /projects/{slug}/tasks             Add tasks
GET     /projects/{slug}/tasks/{id}        Get task
PATCH   /projects/{slug}/tasks/{id}        Update task
DELETE  /projects/{slug}/tasks/{id}        Remove task
POST    /projects/{slug}/tasks/next        Claim next task
POST    /projects/{slug}/tasks/{id}/complete  Complete task
GET     /projects/{slug}/tasks/{id}/context   Get assembled context

# Decisions
GET     /projects/{slug}/decisions         List decisions
POST    /projects/{slug}/decisions         Add decision(s)
GET     /projects/{slug}/decisions/{id}    Get decision
PATCH   /projects/{slug}/decisions/{id}    Update decision

# Knowledge (NEW)
GET     /projects/{slug}/knowledge         List knowledge
POST    /projects/{slug}/knowledge         Create knowledge
GET     /projects/{slug}/knowledge/{id}    Get knowledge (latest version)
PATCH   /projects/{slug}/knowledge/{id}    Update (creates new version)
GET     /projects/{slug}/knowledge/{id}/versions        Version history
GET     /projects/{slug}/knowledge/{id}/versions/{ver}  Specific version
GET     /projects/{slug}/knowledge/{id}/impact          Impact analysis
POST    /projects/{slug}/knowledge/{id}/link            Link to entity
DELETE  /projects/{slug}/knowledge/{id}/link/{link_id}  Unlink

# AC Templates (NEW)
GET     /projects/{slug}/ac-templates      List templates
POST    /projects/{slug}/ac-templates      Create template
GET     /projects/{slug}/ac-templates/{id} Get template
PATCH   /projects/{slug}/ac-templates/{id} Update template
POST    /projects/{slug}/ac-templates/{id}/instantiate  Instantiate with params

# Guidelines
GET     /projects/{slug}/guidelines        List guidelines
POST    /projects/{slug}/guidelines        Create guideline(s)
PATCH   /projects/{slug}/guidelines/{id}   Update guideline
GET     /projects/{slug}/guidelines/context?scopes=a,b  Context for LLM

# Changes
GET     /projects/{slug}/changes           List changes
POST    /projects/{slug}/changes           Record change(s)
POST    /projects/{slug}/changes/auto      Auto-detect from git

# Lessons
GET     /projects/{slug}/lessons           List lessons
POST    /projects/{slug}/lessons           Add lesson(s)
POST    /projects/{slug}/lessons/{id}/promote  Promote to guideline/knowledge

# Gates
GET     /projects/{slug}/gates             Show gates
POST    /projects/{slug}/gates             Configure gates
POST    /projects/{slug}/gates/check?task={id}  Run gates

# AI Suggestions (NEW)
POST    /projects/{slug}/ai/suggest-knowledge?entity_type=task&entity_id=T-001
POST    /projects/{slug}/ai/suggest-guidelines?entity_type=objective&entity_id=O-001
POST    /projects/{slug}/ai/suggest-ac?task_id=T-001
POST    /projects/{slug}/ai/assess-impact?knowledge_id=K-001
POST    /projects/{slug}/ai/evaluate-lesson?lesson_id=L-005

# Plan (draft → approve)
POST    /projects/{slug}/plan/draft        Create draft plan
GET     /projects/{slug}/plan/draft        Show draft
POST    /projects/{slug}/plan/approve      Approve draft → materialize

# LLM Execution (NEW)
POST    /projects/{slug}/execute/{task_id}           Start task execution
GET     /projects/{slug}/execute/{task_id}/status     Execution status
WS      /projects/{slug}/execute/{task_id}/stream     Stream execution output
POST    /projects/{slug}/execute/{task_id}/cancel     Cancel execution
```

### 8.2 WebSocket Events

```
WS /ws/projects/{slug}/events

Events emitted:
  task.status_changed    { task_id, old_status, new_status, agent }
  task.progress          { task_id, step, detail }
  decision.created       { decision_id, type, issue }
  decision.closed        { decision_id, resolution }
  knowledge.updated      { knowledge_id, new_version }
  knowledge.impact       { knowledge_id, affected_entities[] }
  change.recorded        { change_id, task_id, file, action }
  gate.result            { task_id, gate, passed }
  execution.output       { task_id, chunk, is_final }
  ai.suggestion          { type, source, target, confidence }
```

### 8.3 CLI as API Client

```python
# CLI detects mode and uses appropriate backend

class ForgeClient:
    """Unified client used by CLI commands."""

    def __init__(self, config: ForgeConfig):
        if config.mode == "standalone":
            self.backend = JSONBackend(config.data_dir)
        else:
            self.backend = APIBackend(config.api_url, config.api_key)

    # Same interface regardless of backend
    async def create_task(self, project: str, data: dict) -> dict:
        return await self.backend.create("task", project, data)

    async def get_context(self, project: str, task_id: str) -> dict:
        return await self.backend.get_context(project, task_id)
```

---

## 9. Web UI Architecture

### 9.1 Component Architecture (React/Next.js)

```
forge-web/
├── app/
│   ├── layout.tsx                    # Root layout
│   ├── page.tsx                      # Dashboard
│   ├── projects/
│   │   ├── page.tsx                  # Project list
│   │   └── [slug]/
│   │       ├── layout.tsx            # Project layout (sidebar)
│   │       ├── page.tsx              # Project dashboard
│   │       ├── board/page.tsx        # Kanban / DAG view
│   │       ├── objectives/page.tsx   # Objectives + KRs
│   │       ├── ideas/page.tsx        # Ideas hierarchy
│   │       ├── tasks/page.tsx        # Task list + graph
│   │       ├── knowledge/page.tsx    # Knowledge base
│   │       ├── guidelines/page.tsx   # Guideline library
│   │       ├── ac-templates/page.tsx # AC template library
│   │       ├── decisions/page.tsx    # Decision log
│   │       ├── execution/
│   │       │   └── [taskId]/page.tsx # Execution view (streaming)
│   │       └── settings/page.tsx     # Project config, gates, LLM
│   └── settings/page.tsx            # Global settings
├── components/
│   ├── dnd/                          # Drag & Drop components
│   │   ├── DragItem.tsx              # Draggable entity card
│   │   ├── DropZone.tsx              # Drop target area
│   │   ├── RelationshipBuilder.tsx   # Drag entity → connect
│   │   └── EntityPalette.tsx         # Sidebar with draggable items
│   ├── entities/                     # Entity-specific components
│   │   ├── ObjectiveCard.tsx
│   │   ├── TaskCard.tsx
│   │   ├── KnowledgeCard.tsx
│   │   ├── GuidelineChip.tsx
│   │   └── ACTemplateCard.tsx
│   ├── ai/                           # AI suggestion components
│   │   ├── SuggestionPanel.tsx        # Floating panel with AI suggestions
│   │   ├── SuggestionChip.tsx         # Accept/reject suggestion
│   │   └── ImpactAlert.tsx            # Knowledge change impact warning
│   ├── execution/                     # Execution view components
│   │   ├── ExecutionStream.tsx        # Real-time LLM output
│   │   ├── ContextView.tsx            # Show assembled context
│   │   └── ProgressTracker.tsx        # Task progress indicators
│   └── shared/                        # Shared UI components
├── hooks/
│   ├── useWebSocket.ts               # WebSocket connection
│   ├── useDragDrop.ts                # DnD state management
│   └── useAISuggestions.ts           # AI suggestion polling
├── stores/                            # Zustand stores
│   ├── projectStore.ts
│   ├── entityStore.ts
│   └── executionStore.ts
└── lib/
    ├── api.ts                         # API client
    └── ws.ts                          # WebSocket client
```

### 9.2 Drag & Drop Interactions

| Source | Target | Action |
|--------|--------|--------|
| Guideline | Task | Link guideline to task (scope check) |
| Guideline | Objective | Link guideline to objective |
| Guideline | Idea | Link guideline to idea |
| Knowledge | Task | Link knowledge to task (relation: required/context) |
| Knowledge | Objective | Link knowledge to objective |
| Knowledge | Idea | Link knowledge to idea |
| AC Template | Task | Instantiate AC (prompt for params) |
| Lesson | "Create Knowledge" zone | Start knowledge creation from lesson |
| Lesson | "Create Guideline" zone | Start guideline creation from lesson |
| Idea | "Create Tasks" zone | Start plan/decomposition |
| Objective | "Create Ideas" zone | Start idea brainstorming |
| Task | Task | Create dependency (depends_on) |

### 9.3 Execution View

```
┌─────────────────────────────────────────────────────────────────┐
│ Task T-005: implement-user-validation          [IN_PROGRESS]    │
├─────────────────────────────────┬───────────────────────────────┤
│                                 │                               │
│  CONTEXT (assembled)            │  LLM OUTPUT (streaming)       │
│  ─────────────────              │  ──────────────────           │
│                                 │                               │
│  ▶ Task Content                 │  > Analyzing validation       │
│    Description: ...             │    requirements...            │
│    AC: [✓] [✓] [ ] [ ]         │                               │
│                                 │  > Reading src/validators/    │
│  ▶ Guidelines (3 MUST)          │    user.ts...                 │
│    G-001: Always validate...    │                               │
│    G-005: Use zod for...        │  > Creating validation        │
│    G-012: Error messages...     │    schema with zod...         │
│                                 │                               │
│  ▶ Knowledge (2)                │  ```typescript                │
│    K-001: User model fields     │  const userSchema = z.obj...  │
│    K-008: Validation patterns   │  ```                          │
│                                 │                               │
│  ▶ Dependencies                 │  > Running tests...           │
│    T-001: ✅ DONE               │  ✅ 12 passed                 │
│    T-003: ✅ DONE               │  ❌ 1 failed                  │
│                                 │                               │
│  ▶ Risks (1)                    │  > Fixing failing test...     │
│    D-015: Input injection ⚠️    │                               │
│                                 │                               │
├─────────────────────────────────┴───────────────────────────────┤
│  DECISIONS: D-022 (zod over joi) │ CHANGES: 3 files │ GATES: ⏳ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 10. Containerization

### 10.1 Service Architecture

```
┌─────────────────────────────────────────────┐
│              Rancher Desktop                │
│                                             │
│  ┌─────────────┐  ┌──────────────────────┐  │
│  │ forge-web   │  │ forge-api            │  │
│  │             │  │                      │  │
│  │ Next.js     │  │ FastAPI              │  │
│  │ Port: 3000  │  │ Port: 8000           │  │
│  │             │  │                      │  │
│  │ Nginx       │  │ Uvicorn              │  │
│  └──────┬──────┘  └──────────┬───────────┘  │
│         │                    │              │
│         │     ┌──────────────┤              │
│         │     │              │              │
│         │     ▼              ▼              │
│         │  ┌──────────────────────────────┐ │
│         │  │         PostgreSQL           │ │
│         │  │         Port: 5432           │ │
│         │  │                              │ │
│         │  │  forge_db                    │ │
│         │  └──────────────────────────────┘ │
│         │                                   │
│         │  ┌──────────────────────────────┐ │
│         │  │         Redis               │ │
│         │  │         Port: 6379           │ │
│         │  │                              │ │
│         │  │  Event store (Streams),      │ │
│         │  │  Pub/Sub, cache, sessions    │ │
│         │  └──────────────────────────────┘ │
│         │                                   │
└─────────┼───────────────────────────────────┘
          │
   CLI connects to forge-api:8000
```

### 10.2 Docker Compose

```yaml
version: '3.8'

services:
  forge-web:
    build: ./forge-web
    ports:
      - "3000:3000"
    environment:
      - API_URL=http://forge-api:8000
      - NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
    depends_on:
      - forge-api

  forge-api:
    build: ./forge-api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://forge:forge@postgres:5432/forge_db
      - REDIS_URL=redis://redis:6379
      - LLM_CONFIG_PATH=/config/providers.toml
    volumes:
      - ./config:/config
      - forge-data:/data
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:16
    environment:
      - POSTGRES_USER=forge
      - POSTGRES_PASSWORD=forge
      - POSTGRES_DB=forge_db
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
  forge-data:
```

---

## 11. Implementation Roadmap

### Phase 1: Foundation (Core Refactoring)

**Goal**: Refactor current Python core into layered architecture with adapter pattern.

| Task | Description | Dependencies |
|------|-------------|-------------|
| 1.1 | Define StorageAdapter interface (Protocol) | — |
| 1.2 | Wrap current JSON I/O into JSONAdapter | 1.1 |
| 1.3 | Define LLMProvider interface (Protocol) | — |
| 1.4 | Define LLMContract base class | 1.3 |
| 1.5 | Implement Context Assembly engine | 1.4 |
| 1.6 | Add Knowledge entity (K-NNN) to core | 1.2 |
| 1.7 | Add AC Template entity (AC-NNN) to core | 1.2 |
| 1.8 | Modify Task entity (knowledge_ids, structured AC) | 1.6, 1.7 |
| 1.9 | Add Lesson promotion flow (→ knowledge, → guideline) | 1.6 |
| 1.10 | Create ForgeClient abstraction (standalone/api modes) | 1.2 |
| 1.11 | Update all existing contracts for new entities | 1.6, 1.7, 1.8 |
| 1.12 | Migrate SKILL.md files to use new context assembly | 1.5 |

**Deliverable**: CLI works as before BUT through adapter interfaces. Knowledge and AC entities functional in JSON mode. Context assembly produces structured LLM context.

**Validation**: All existing tests pass. New entities have contracts. Context assembly produces valid output.

### Phase 2: Database & API

**Goal**: PostgreSQL adapter + FastAPI REST API + WebSocket events.

| Task | Description | Dependencies |
|------|-------------|-------------|
| 2.1 | Design database schema (SQL migrations) | Phase 1 |
| 2.2 | Implement PostgreSQLAdapter | 2.1 |
| 2.3 | Implement JSON → PostgreSQL migration tool | 2.2 |
| 2.4 | Set up FastAPI project structure | — |
| 2.5 | Implement REST API endpoints (all entities) | 2.2, 2.4 |
| 2.6 | Implement WebSocket event system | 2.5 |
| 2.7 | Add API authentication (API key / JWT) | 2.5 |
| 2.8 | Implement CLI remote mode (APIBackend) | 2.5 |
| 2.9 | Knowledge versioning in PostgreSQL | 2.2 |
| 2.10 | Knowledge impact analysis queries | 2.9 |
| 2.11 | Docker Compose setup (API + PostgreSQL + Redis) | 2.5 |
| 2.12 | API contract validation middleware | 2.5 |

**Deliverable**: Full API running in Docker. CLI can connect to API or work standalone. Knowledge versioning and impact analysis work in DB mode.

**Validation**: API passes integration tests. CLI remote mode works end-to-end. Migration tool imports sample project.

### Phase 3: Web UI

**Goal**: React/Next.js frontend with entity management and drag & drop.

| Task | Description | Dependencies |
|------|-------------|-------------|
| 3.1 | Set up Next.js project with TypeScript | — |
| 3.2 | API client library (REST + WebSocket) | Phase 2 |
| 3.3 | Dashboard / project list | 3.1, 3.2 |
| 3.4 | Entity CRUD pages (objectives, ideas, tasks, etc.) | 3.3 |
| 3.5 | Knowledge base management page | 3.4 |
| 3.6 | Guideline library page | 3.4 |
| 3.7 | AC template library page | 3.4 |
| 3.8 | Drag & drop system (DnD Kit) | 3.4 |
| 3.9 | Relationship builder (drag entity → connect) | 3.8 |
| 3.10 | Task DAG visualization | 3.4 |
| 3.11 | Real-time updates via WebSocket | 3.2 |
| 3.12 | Zustand stores for state management | 3.4 |
| 3.13 | Add forge-web to Docker Compose | 3.11 |

**Deliverable**: Full Web UI with drag & drop entity management, real-time updates, and knowledge base.

**Validation**: All entity types manageable via UI. Drag & drop creates correct relationships. Real-time updates work.

### Phase 4: AI Features & Execution View

**Goal**: AI-assisted suggestions, execution streaming, impact analysis.

| Task | Description | Dependencies |
|------|-------------|-------------|
| 4.1 | LLM provider adapters (Anthropic, OpenAI, Ollama) | Phase 1 (1.3) |
| 4.2 | AI suggestion endpoint (knowledge → task) | 4.1, Phase 2 |
| 4.3 | AI suggestion endpoint (guideline → objective) | 4.1, Phase 2 |
| 4.4 | AI suggestion endpoint (AC → task) | 4.1, Phase 2 |
| 4.5 | Lesson evaluation (promote to knowledge/guideline?) | 4.1, Phase 2 |
| 4.6 | Knowledge impact assessment (on update) | 4.1, Phase 2 |
| 4.7 | Suggestion panel in Web UI | 4.2-4.5, Phase 3 |
| 4.8 | Execution streaming backend (task execution via API) | 4.1, Phase 2 |
| 4.9 | Execution view in Web UI | 4.8, Phase 3 |
| 4.10 | Context view (show assembled context before execution) | Phase 1 (1.5) |
| 4.11 | Knowledge maintenance (staleness detection, review prompts) | Phase 2 |
| 4.12 | AI contracts for all suggestion types | 4.1-4.6 |

**Deliverable**: AI suggests relationships, execution visible in real-time in Web UI, knowledge maintenance automated.

**Validation**: AI suggestions are relevant (evaluated by user). Execution view shows real-time progress. Impact analysis catches affected entities.

### Phase 5: SaaS Preparation (Future)

**Goal**: Multi-tenancy, authentication, deployment.

| Task | Description |
|------|-------------|
| 5.1 | Multi-tenant database schema |
| 5.2 | User authentication (OAuth2) |
| 5.3 | Authorization (RBAC) |
| 5.4 | Tenant isolation |
| 5.5 | Billing integration |
| 5.6 | Cloud deployment pipeline |
| 5.7 | Monitoring & observability |

---

## 12. Addressed Findings (from Deep Verify)

### F1: Local vs Remote feature parity → RESOLVED

**Decision**: Section 7.2 (Feature Parity Matrix) explicitly documents what each mode supports. JSON mode = full CLI experience, single-user, offline. PostgreSQL mode = everything including Web UI, multi-user, real-time. No ambiguity.

**Migration path**: Section 7.3 defines `forge-migrate` tool for JSON → PostgreSQL import.

### F2: Knowledge objects in JSON → RESOLVED

**Decision**: JSON mode supports Knowledge CRUD and basic embedded versioning (array of versions in object). Impact analysis in JSON mode does full file scan (acceptable for small/medium projects). Full versioning with diffs and fast impact analysis requires PostgreSQL.

### F3: Context Assembly rules → RESOLVED

**Decision**: Section 5 defines complete Context Assembly Contract with priority order, size budgets, overflow strategy, and output validation. This is a first-class design artifact.

### F4: Reusable AC entity → RESOLVED

**Decision**: Section 3.3 defines AC Template (AC-NNN) as first-class entity with parameterization, categories, and instantiation.

### F5: AI semantic model → RESOLVED

**Decision**: Section 4.4 defines three-tier AI suggestion mechanism: (1) scope/tag matching (fast, no LLM), (2) LLM evaluation on demand (contract-based), (3) embedding search (future, with vector DB).

### Additional Recommendations

| # | Recommendation | Section | Status |
|---|---------------|---------|--------|
| R1 | Feature Parity Matrix | 7.2 | ✅ Designed |
| R2 | Context Assembly Contract | 5 | ✅ Designed |
| R3 | Knowledge versioning limits in JSON | 7.2, 3.2 | ✅ Documented |
| R4 | AC Template entity | 3.3 | ✅ Designed |
| R5 | Knowledge maintenance lifecycle | 4.3 (lifecycle), 4.4 (AI maintenance) | ✅ Designed |

---

## 13. Resolved Decisions

| ID | Question | Decision | Rationale |
|----|----------|----------|-----------|
| OD-1 | Database | **PostgreSQL** | Relational model fits entity relationships, FTS built-in, JSONB for flexible fields, proven with FastAPI |
| OD-2 | Redis | **Required** | Event bus for event sourcing, cache, Pub/Sub for real-time, session store. Enables OD-5. |
| OD-3 | DnD library | **DnD Kit** | Actively maintained, flexible (entity→entity, not just lists), deprecated rbd not an option |
| OD-4 | LLM abstraction | **Hybrid: LiteLLM + custom Contracts** | LiteLLM as transport (100+ providers), custom Contract layer on top (schemas, validation, context assembly) |
| OD-5 | Knowledge versioning | **Event Sourcing** | Redis as event store/bus makes ES practical. Full audit trail, replay capability, natural fit with real-time events. |
| OD-6 | Completed objectives | **Archive + retain links** | Objectives ACHIEVED/ABANDONED → archive tab (read-only). Derived guidelines and knowledge remain ACTIVE. Links preserved. Reactivation possible. |
| OD-7 | Knowledge scope | **Per-project + import/export (B)** | Analogous to guidelines. `_global/knowledge.json` for shared. `knowledge import` with dedup. No cross-project coupling. |

### Event Sourcing Architecture (OD-5 detail)

```
                    ┌────────────────────────────────┐
                    │        Redis Streams            │
                    │        (Event Store)             │
                    │                                  │
                    │  knowledge.created  { K-001, v1 }│
                    │  knowledge.updated  { K-001, v2 }│
                    │  knowledge.linked   { K-001→T-005}│
                    │  task.started       { T-005 }    │
                    │  task.completed     { T-005 }    │
                    │  decision.created   { D-001 }    │
                    │  ...                             │
                    └──────────┬─────────────────────┘
                               │
                    ┌──────────┴─────────────────────┐
                    │        Event Consumers           │
                    │                                  │
                    │  ┌─────────────────────────────┐ │
                    │  │ PostgreSQL Projector         │ │
                    │  │ Events → relational tables   │ │
                    │  │ (current state for queries)  │ │
                    │  └─────────────────────────────┘ │
                    │                                  │
                    │  ┌─────────────────────────────┐ │
                    │  │ WebSocket Broadcaster        │ │
                    │  │ Events → connected clients   │ │
                    │  │ (real-time UI updates)       │ │
                    │  └─────────────────────────────┘ │
                    │                                  │
                    │  ┌─────────────────────────────┐ │
                    │  │ Impact Analyzer              │ │
                    │  │ knowledge.updated →          │ │
                    │  │   find affected entities →   │ │
                    │  │   emit impact.detected       │ │
                    │  └─────────────────────────────┘ │
                    │                                  │
                    │  ┌─────────────────────────────┐ │
                    │  │ Audit Logger                 │ │
                    │  │ All events → audit table     │ │
                    │  │ (immutable history)          │ │
                    │  └─────────────────────────────┘ │
                    └──────────────────────────────────┘
```

**Key design**:
- **Write path**: API → validate → emit event to Redis Stream → consumers project to PostgreSQL
- **Read path**: API → query PostgreSQL (projected current state)
- **Replay**: Rebuild any projection by replaying events from Redis Stream
- **JSON standalone mode**: No event sourcing — direct CRUD (feature parity matrix applies)

### Open Decisions (remaining)

_None — all architectural decisions resolved._

---

## Appendix A: Contract Examples

### A.1 Knowledge Suggestion Contract

```json
{
  "id": "knowledge-suggest-v1",
  "name": "Suggest Knowledge for Entity",
  "input_schema": {
    "entity_type": "string (objective|idea|task)",
    "entity": "object (full entity data)",
    "available_knowledge": "array of knowledge objects",
    "existing_links": "array of already-linked knowledge IDs"
  },
  "output_schema": {
    "suggestions": [
      {
        "knowledge_id": "K-NNN",
        "relevance_score": "number 0-1",
        "relation": "required|context|reference",
        "reasoning": "string — why this knowledge is relevant"
      }
    ]
  },
  "system_prompt": "You are evaluating which knowledge objects are relevant to a given entity. Score relevance 0-1. Suggest relation type. Explain reasoning briefly.",
  "validation_rules": [
    "All knowledge_ids must exist in available_knowledge",
    "No duplicate suggestions",
    "relevance_score must be 0-1"
  ]
}
```

### A.2 Impact Assessment Contract

```json
{
  "id": "impact-assess-v1",
  "name": "Assess Impact of Knowledge Change",
  "input_schema": {
    "knowledge": "object (the changed knowledge)",
    "previous_version": "string (previous content)",
    "current_version": "string (current content)",
    "linked_entities": "array of linked entities with their details"
  },
  "output_schema": {
    "impact_assessment": [
      {
        "entity_type": "string",
        "entity_id": "string",
        "impact_level": "none|low|medium|high",
        "description": "string — what might be affected",
        "recommended_action": "none|review|update|rework"
      }
    ],
    "summary": "string — overall impact summary"
  },
  "validation_rules": [
    "Every linked entity must be assessed",
    "impact_level must be one of: none, low, medium, high",
    "recommended_action must be one of: none, review, update, rework"
  ]
}
```
