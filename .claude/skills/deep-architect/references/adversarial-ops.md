# Adversarial Operations Reference

8 operations to systematically attack a design before it ships.

## 1. STRIDE Threat Model

Analyze each component for six threat categories:

| Threat | Question | Example |
|--------|----------|---------|
| **S**poofing | Can someone pretend to be another user/service? | API without mutual TLS between services |
| **T**ampering | Can data be modified in transit or at rest? | Unsigned messages on a queue |
| **R**epudiation | Can someone deny they did something? | No audit log on admin actions |
| **I**nfo Disclosure | Can data leak to unauthorized parties? | Stack traces in production error responses |
| **D**enial of Service | Can the system be overwhelmed? | No rate limiting on public endpoints |
| **E**levation of Privilege | Can someone gain unauthorized access? | JWT with mutable role claims, no server-side check |

For each component, produce a row per applicable threat.

## 2. FMEA (Failure Mode and Effects Analysis)

For each component, ask:

| Column | Description |
|--------|-------------|
| **Failure mode** | How can this component fail? (crash, slow, wrong output, data loss) |
| **Effect** | What happens to the system when it fails? |
| **Severity** (1-10) | How bad is the effect? |
| **Occurrence** (1-10) | How likely is this failure? |
| **Detection** (1-10) | How quickly can you detect it? (10 = undetectable) |
| **RPN** | Severity x Occurrence x Detection. Prioritize highest. |

Example:
| Failure Mode | Effect | Sev | Occ | Det | RPN |
|-------------|--------|-----|-----|-----|-----|
| Auth service crashes | All logins fail, users locked out | 9 | 3 | 2 | 54 |
| Cache returns stale data | Users see outdated prices | 6 | 5 | 7 | 210 |
| Queue message lost | Order placed but never processed | 10 | 2 | 8 | 160 |

High RPN items need mitigation plans.

## 3. Anti-Pattern Check

Scan the design for known architectural anti-patterns:

| Anti-Pattern | Symptom |
|-------------|---------|
| **Big Ball of Mud** | No clear boundaries, everything calls everything |
| **God Service** | One service does too much, changes constantly |
| **Distributed Monolith** | Microservices that must deploy together |
| **Chatty Communication** | Excessive inter-service calls for single operations |
| **Shared Database** | Multiple services writing to the same tables |
| **Golden Hammer** | Using one technology for everything regardless of fit |
| **Premature Optimization** | Complexity added for scale that may never come |
| **Resume-Driven Development** | Tech chosen for novelty, not fit |

For each detected pattern, state: what it is, where it appears, and how to fix it.

## 4. Pre-Mortem

Write a failure narrative:

> "It is 6 months after launch. The system has failed. Write the incident post-mortem."

Cover:
- What went wrong (pick the most likely failure)
- Root cause chain (5 whys)
- What warning signs were ignored
- What would have prevented it

This surfaces risks that formal analysis misses because it engages narrative thinking.

## 5. Dependency Analysis

Map every dependency and classify:

| Dependency | Type | If Unavailable | Fallback? |
|-----------|------|---------------|-----------|
| PostgreSQL | Data store | Total outage | No |
| Redis | Cache | Degraded performance | Yes, bypass cache |
| Auth0 | Identity | No new logins | Cached tokens work for N hours |
| Stripe | Payments | Cannot process orders | Queue for retry |

Identify:
- **Single points of failure** (no redundancy, no fallback)
- **Diamond dependencies** (A depends on B and C, both depend on D)
- **Circular dependencies** (A calls B calls A)

## 6. Scale Stress Test

Take current design and mentally apply load multipliers:

| Scenario | 1x (now) | 10x | 100x |
|----------|----------|-----|------|
| Requests/sec | 100 | 1,000 | 10,000 |
| Data volume | 10 GB | 100 GB | 1 TB |
| Concurrent users | 500 | 5,000 | 50,000 |

For each 10x jump, identify:
- What component breaks first?
- What's the bottleneck? (CPU, memory, I/O, network, database connections)
- What architectural change is needed? (can you scale horizontally, or does the design need restructuring?)

## 7. Cost Projection

Estimate infrastructure cost at different scales:

| Component | Unit Cost | 1x Monthly | 10x Monthly | 100x Monthly |
|-----------|-----------|------------|-------------|--------------|
| Compute | $/hour | ... | ... | ... |
| Database | $/GB/month | ... | ... | ... |
| Network | $/GB transfer | ... | ... | ... |
| Third-party APIs | $/call | ... | ... | ... |

Flag:
- **Cost cliffs**: where does pricing jump non-linearly?
- **Runaway costs**: which component grows fastest with scale?
- **Hidden costs**: egress, logging, monitoring, backups

## 8. Operational Complexity

Answer these questions for the proposed design:

| Question | Answer |
|----------|--------|
| How many things can break independently? | {count} |
| What's the deployment process? | {steps, duration, rollback} |
| What monitoring is needed? | {metrics, alerts, dashboards} |
| What happens at 3am when it pages? | {runbook complexity} |
| How many different technologies must the on-call know? | {count} |
| What's the debug path for a user complaint? | {how many systems to check} |
| Can a new team member deploy safely in week 1? | {yes/no + why} |

The goal: if operational complexity is high, either simplify the design or budget for the ops investment.
