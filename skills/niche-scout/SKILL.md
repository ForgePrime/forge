---
name: niche-scout
id: SKILL-NICHE-SCOUT
version: "1.0"
description: >
  Systematic discovery of untapped AI business niches — services, tools, and platforms
  that don't exist yet but will become essential. Combines market signal analysis,
  gap detection, demand validation, and competitive moat assessment.
allowed-tools: [Read, Glob, Grep, WebSearch, WebFetch, Agent]
---

# Niche Scout — AI Business Opportunity Discovery

## Identity

| Field | Value |
|-------|-------|
| ID | SKILL-NICHE-SCOUT |
| Version | 1.0 |
| Description | Find high-potential AI business opportunities with strong foundations and no established competition. |

## What This Adds (Beyond Native Capability)

- **Signal triangulation**: Cross-references multiple weak signals (forums, job postings, funding, research papers, regulatory shifts) to detect emerging needs before they become obvious
- **Gap matrix**: Maps existing solutions against user pain points to find systematic blind spots
- **Demand validation framework**: Tests whether a gap is real demand or just wishful thinking
- **Moat assessment**: Evaluates defensibility — not just "is it empty?" but "can you hold it?"
- **Timing analysis**: Determines if the market is too early, just right, or about to be crowded

---

## Procedure

### Step 1: Define the Search Space

Narrow the exploration domain. Without boundaries, "AI niches" is infinite.

Ask or infer from user input:

| Dimension | Question | Example |
|-----------|----------|---------|
| **Vertical** | Which industry or domain? | Healthcare, legal, education, SMB, creator economy, DevOps |
| **Modality** | What type of AI capability? | LLM, vision, voice, agents, multimodal, edge AI |
| **Business model** | SaaS, API, marketplace, managed service? | Any — or constrained |
| **Geography/language** | Global or specific market? | Poland/CEE, LATAM, global English |
| **Budget** | Solo founder, small team, or funded startup? | Determines complexity ceiling |
| **Timeframe** | Emerging now, 6 months, 1-2 years? | Determines signal maturity |

If the user says "just find me something good" — default to:
- Vertical: cross-industry (horizontal plays)
- Modality: LLM-based (lowest barrier)
- Model: SaaS or API
- Market: global English + Polish/CEE as edge
- Budget: small team (2-5 people)
- Timeframe: 3-12 months

Output: **Search Space Definition** — a 1-paragraph scope statement.

---

### Step 2: Signal Harvesting

Collect weak and strong signals from multiple independent sources. The goal is volume — filtering comes later.

#### 2a. Pain Signal Mining

Search for unmet needs people are already expressing:

| Source | What to look for | Search patterns |
|--------|------------------|-----------------|
| Reddit/HN/forums | "I wish there was...", "Why doesn't X exist?", "I'd pay for..." | `site:reddit.com "I wish" AI {vertical}`, `site:news.ycombinator.com "doesn't exist" AI` |
| Twitter/X | Complaints about manual workflows, broken tooling | `"someone should build" AI`, `"why is there no" AI {vertical}` |
| Job postings | New roles that imply missing tools | `"AI {role}" site:linkedin.com`, roles with "manual" or "spreadsheet" in description |
| GitHub Issues | Feature requests on popular AI tools that are never addressed | Top repos in the vertical → Issues labeled "enhancement" with most thumbs-up |
| ProductHunt/alternatives | Products with high interest but low ratings | "AI {vertical}" sorted by interest, read complaints |
| App store reviews | 1-2 star reviews on existing AI tools | "{vertical} AI" app reviews mentioning "missing", "can't", "wish" |

For each source, extract:
```
Signal: {what people are asking for}
Source: {URL or reference}
Volume: {how many independent mentions}
Intensity: {mild wish vs. desperate need}
Existing alternatives: {what they're using now, if anything}
```

#### 2b. Supply-Side Gap Detection

Analyze what exists and what's missing:

| Method | How |
|--------|-----|
| **Competitor mapping** | Search `{vertical} AI tool/platform/service` → list top 10-20 → map features → find white spaces |
| **Adjacent category scan** | What exists for neighboring verticals that doesn't exist for this one? |
| **Workflow decomposition** | Map the end-to-end workflow in the vertical → which steps have no AI tooling? |
| **Integration gaps** | Popular tools in the vertical → which have no AI-powered integrations? |
| **Pricing gaps** | Enterprise solutions exist but nothing for SMB/solo? Or vice versa? |

#### 2c. Macro Trend Signals

Identify structural shifts creating new opportunities:

| Signal type | Where to find |
|-------------|---------------|
| **Regulatory changes** | New laws requiring compliance (AI Act, DORA, sector-specific) → creates tooling demand |
| **Technology inflection** | New model capabilities (multimodal, agents, long context) → enables previously impossible products |
| **Funding patterns** | What VCs are funding → what's the next layer of the stack that's missing |
| **Research → product gaps** | Papers with high citations but no product implementation |
| **Platform shifts** | New APIs/platforms (OpenAI Assistants, Claude MCP, etc.) → ecosystem gaps |

Output: **Raw Signal List** — minimum 15-20 signals, unsorted.

---

### Step 3: Signal Clustering & Pattern Detection

Group raw signals into opportunity clusters.

For each cluster:

```
Cluster: {descriptive name}
Signals: [{list of contributing signals}]
Core unmet need: {1 sentence}
Who feels the pain: {specific persona, not "businesses"}
Current workaround: {what they do today without this}
Why now: {what changed that makes this solvable/urgent now}
```

Merge overlapping clusters. Discard signals that don't cluster (isolated noise).

**Pattern detection rules:**
- 3+ independent signals from different sources → real pattern
- Pain + timing + no existing solution → hot opportunity
- Pain + existing bad solutions → disruption opportunity
- New capability + old workflow → automation opportunity

Output: **5-10 Opportunity Clusters**, ranked by signal density.

---

### Step 4: Opportunity Scoring

Score each cluster on 6 dimensions. Be brutally honest — most ideas fail on at least one dimension.

| Dimension | Weight | Score 1-5 | Criteria |
|-----------|--------|-----------|----------|
| **Demand evidence** | 20% | | 1=theoretical, 3=forum posts, 5=people actively paying for workarounds |
| **Competition vacuum** | 15% | | 1=crowded, 3=weak players, 5=genuinely nothing exists |
| **Defensibility (moat)** | 15% | | 1=trivially copyable, 3=data/network effect possible, 5=deep technical moat |
| **AI absorption resistance** | 15% | | 1=next model update solves this natively, 3=models help but product layer needed, 5=fundamentally cannot be solved by a general model alone (requires domain data, integrations, regulatory context, or physical-world coupling) |
| **Adjacent pivot risk** | 15% | | 1=established player can add this as a feature in weeks, 3=requires significant effort to pivot, 5=no adjacent player has the domain/data/distribution to absorb this quickly |
| **Timing** | 10% | | 1=too early (tech not ready), 3=good window, 5=perfect moment (need is acute, no one moved) |
| **Feasibility** | 5% | | 1=needs huge team/data, 3=doable with 3-5 people in 6mo, 5=MVP in weeks |
| **Revenue clarity** | 5% | | 1=unclear who pays, 3=obvious buyer, 5=buyer + clear pricing + willingness to pay |

**Weighted score = Σ(weight × score)**

**Moat types to evaluate:**
- Data moat: Does usage generate proprietary data that improves the product?
- Network effect: Does each user make it better for others?
- Switching cost: Once adopted, is it painful to leave?
- Domain expertise: Does building this require deep vertical knowledge?
- Speed/execution: First mover with good execution can build brand loyalty
- Regulatory moat: Compliance requirements create barriers to entry

**AI Absorption Risk — how to evaluate:**

The core question: "Could the next foundation model update (GPT-5, Claude 5, Gemini 3) make this product irrelevant overnight?"

| Score | Meaning | Examples |
|-------|---------|---------|
| 1 — Will be absorbed | The gap is purely a capability gap in current models. Once models improve, standalone product is dead. | Generic summarization, basic code generation, simple translation, general Q&A chatbots |
| 2 — Likely absorbed | Models + a thin prompt/UI layer solve 80%+ of the need. Defensible product layer is minimal. | Content rewriting tools, generic email drafters, simple document parsers |
| 3 — Partially resistant | Models are a component but significant product engineering is needed (integrations, workflows, UX). Risk: model providers may add this to their own apps. | Code review tools, meeting summarizers with calendar integration |
| 4 — Mostly resistant | Requires domain-specific data, regulatory knowledge, or multi-system integration that models alone cannot provide. Model improvements help but don't replace the product. | Industry-specific compliance platforms, ERP integration layers, domain-trained analytics |
| 5 — Fully resistant | Fundamentally cannot be solved by a general model. Requires proprietary data pipelines, physical-world coupling, regulatory certification, or deep institutional integration. | Hardware-coupled AI, certified medical devices, financial audit systems with regulatory approval |

**Ask these questions:**
- If OpenAI/Anthropic/Google added a feature tomorrow, would it kill this product?
- Does the value come from the MODEL or from the DATA + INTEGRATIONS + WORKFLOW around it?
- Is the product a "wrapper" (model in, answer out) or a "system" (model as one component among many)?
- Would a 10x better model eliminate the need for this product, or just make it work better?

**Adjacent Pivot Risk — how to evaluate:**

The core question: "Is there an established company that could ship this as a feature update in 1-3 months?"

| Score | Meaning | Examples |
|-------|---------|---------|
| 1 — Trivial pivot | An existing player has the data, distribution, and technical proximity. It's a feature, not a product. | Adding AI summarization to Slack, adding AI search to Notion |
| 2 — Easy pivot | 2-3 adjacent players could build this with moderate effort (1-2 sprints). They have distribution + partial tech overlap. | CRM adding AI lead scoring, project management tool adding AI planning |
| 3 — Moderate effort | Adjacent players exist but would need to build new competency, acquire data, or enter a new regulatory domain. 3-6 month effort. | Accounting software adding AI tax optimization, HR tool adding compliance engine |
| 4 — Hard pivot | Would require the adjacent player to fundamentally change their business model, acquire deep domain expertise, or build entirely new infrastructure. | ERP vendor building AI-native legal tech, cloud provider building certified medical AI |
| 5 — No adjacent player | No established company has the combination of domain, data, distribution, and technical capability to absorb this quickly. | Sovereign LLM application layer, niche regulatory compliance for a specific jurisdiction |

**How to identify adjacent threats:**
1. List the top 5-10 companies in the same ecosystem (same buyer, same workflow, same vertical)
2. For each: How many of these do they already have? → Domain expertise, Technical capability, Data access, Distribution/customers, Incentive to enter
3. If ANY company scores 4/5 on those dimensions → Adjacent Pivot Risk score ≤ 2
4. Search for: "{competitor} AI roadmap", "{competitor} + AI announcement", "{vertical} AI features 2026"
5. Check recent product launches, blog posts, and job postings of adjacent players for signals of intent

**Kill criteria** (auto-reject if ANY is true):
- Score 1 on Demand evidence (no signal = no market)
- Score 1 on Competition vacuum (already crowded = uphill battle)
- Score 1 on AI absorption resistance (next model update kills you)
- Score 1 on Adjacent pivot risk AND the adjacent player has announced AI features
- Score 1 on Feasibility AND budget is small team
- Combined score < 2.5

Output: **Scored Opportunity Table**, sorted by weighted score. Top 3-5 survive.

---

### Step 5: Deep Dive — Top Opportunities

For each surviving opportunity (top 3-5), conduct a structured deep dive:

#### 5a. Market Sizing (Bottom-Up)

Do NOT use TAM/SAM/SOM hand-waving. Use bottom-up:

```
1. Who exactly is the buyer? → {persona}
2. How many of them exist? → {number with source}
3. What would they pay monthly/annually? → {price point with reasoning}
4. What % would realistically adopt in year 1? → {conversion rate}
5. Year 1 revenue estimate = count × price × adoption rate
```

#### 5b. Competitive Landscape Validation

Deeper search for hidden competition:

- Search in non-English markets (competitors may exist in Chinese, Korean, etc.)
- Check AngelList/Crunchbase for stealth startups with similar descriptions
- Check recent YC/accelerator batches
- Search patent filings
- Check if big players (Google, Microsoft, OpenAI) have announced anything adjacent

Result: **Competition dossier** — either "confirmed vacuum" or "actually, these exist: ..."

#### 5c. Build vs. Moat Timeline

```
MVP scope: {minimum feature set to test demand}
MVP timeline: {weeks/months}
Time to defensibility: {when does the moat start forming}
Risk window: {period where you're vulnerable to fast followers}
```

#### 5d. AI Absorption Analysis

For each opportunity, conduct a structured assessment of how likely foundation model improvements will eliminate the need for a standalone product.

```
## AI Absorption Analysis: {opportunity name}

### Current model capability
What can today's best models (GPT-4o, Claude Opus, Gemini 2) already do in this space?
→ {description}

### 12-month model trajectory
Based on announced research directions, what will models likely be able to do in 12 months?
→ {description}

### What the PRODUCT does that the MODEL cannot
List concrete value-adds that are NOT model capability:
- Integration: {specific systems, APIs, data sources the product connects}
- Data: {proprietary/domain data the model doesn't have access to}
- Workflow: {multi-step processes, approvals, handoffs the model can't orchestrate alone}
- Regulatory: {certifications, audit trails, compliance the model can't provide}
- Trust: {verification, guarantees, liability the model can't offer}

### Absorption timeline estimate
- {X months} until models can do 50% of what this product does natively
- {X months} until models can do 80%
- NEVER for: {aspects that cannot be absorbed — list specific reasons}

### Verdict
[ ] SAFE — core value is in the system, not the model
[ ] AT RISK — need to build non-model value fast (data moat, integrations, workflow lock-in)
[ ] DEAD ON ARRIVAL — this is a capability gap, not a product opportunity
```

#### 5e. Adjacent Player Threat Assessment

Identify companies that could ship this opportunity as a feature addition to their existing product, rather than you building it as a standalone product.

```
## Adjacent Player Threat Assessment: {opportunity name}

### Adjacent player map
| Company | Domain | Tech | Data | Distribution | Incentive | Pivot effort | Threat level |
|---------|--------|------|------|-------------|-----------|-------------|-------------|
| {name}  | {1-5}  | {1-5}| {1-5}| {1-5}       | {1-5}     | {weeks/months}| {LOW/MED/HIGH} |

### Signals of intent
For each HIGH threat player, search for:
- Recent AI feature announcements or blog posts
- Job postings suggesting AI capability building (e.g., "AI engineer" + {vertical})
- Patent filings or research papers in the space
- Partnerships with AI providers (OpenAI, Anthropic, Google)
- Acquisitions of startups in adjacent spaces

### Speed-to-feature estimate
- Could the top adjacent player ship a basic version in < 4 weeks? → {yes/no + reasoning}
- Would it be good enough to satisfy 80% of the market? → {yes/no + reasoning}
- What would they NOT build that a dedicated product would? → {list}

### Defensive positioning
If adjacent players CAN pivot quickly:
- What must you build FIRST that they cannot easily replicate? (data moat, deep integration, regulatory certification)
- What distribution channel can you own that they don't control?
- Can you partner WITH them instead of competing? (plugin, integration, white-label)

### Verdict
[ ] LOW RISK — no adjacent player has the combination to pivot quickly
[ ] MEDIUM RISK — players could pivot but would need 3-6 months + new competency
[ ] HIGH RISK — an established player could ship this as a feature in weeks
[ ] PARTNER PLAY — better to build FOR adjacent players than compete against them
```

#### 5f. Risk Register

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Big tech builds this | HIGH | ? | Speed, niche focus, switching costs |
| Foundation model absorbs the need | HIGH | ? | Build value in data/integrations/workflow, not model capability |
| Adjacent player ships as feature | HIGH | ? | Speed, deeper domain, partnership strategy |
| Demand was illusory | HIGH | ? | Pre-sell, waitlist, LOIs before building |
| Tech doesn't work well enough | MEDIUM | ? | Prototype fast, test core assumption |
| Regulatory blockers | MEDIUM | ? | Research before building |
| Can't monetize | MEDIUM | ? | Validate willingness to pay early |

---

### Step 6: Validation Playbook

For the #1 opportunity, produce a concrete validation plan:

```
## Validation Plan: {opportunity name}

### Hypothesis
{1 sentence: "We believe {persona} will pay {$X/mo} for {solution} because {reason}"}

### Pre-Build Validation (Week 1-2)
1. Landing page test: {describe the page, CTA, what to measure}
2. Community outreach: {which forums/communities to post in}
3. Expert interviews: {who to talk to, 3-5 people}
4. Competitor deep-check: {final search patterns}

### MVP Scope (Week 3-6)
- Core feature 1: {description}
- Core feature 2: {description}
- NOT in MVP: {explicitly list what to cut}
- Tech stack recommendation: {based on speed + vertical fit}

### Success Metrics
- Validation passed if: {specific numbers — signups, LOIs, usage}
- Pivot signal: {what would tell you to change direction}
- Kill signal: {what would tell you to abandon this}

### Go-to-Market Seed
- First 10 customers: {where to find them}
- Distribution channel: {organic, paid, community, partnerships}
- Pricing: {freemium, trial, direct pricing — with reasoning}
```

---

### Step 7: Synthesis & Recommendation

Present final output:

```
## Niche Scout Report: {search space}

### Executive Summary
{2-3 sentences: what was found, top recommendation}

### Opportunity Ranking

| # | Opportunity | Score | Demand | Vacuum | Moat | Timing | Key Insight |
|---|------------|-------|--------|--------|------|--------|-------------|
| 1 | ...        | X.X   | X      | X      | X    | X      | ...         |
| 2 | ...        | X.X   | X      | X      | X    | X      | ...         |
| 3 | ...        | X.X   | X      | X      | X    | X      | ...         |

### #1 Recommendation: {name}
{Why this one. What makes it special. Honest assessment of biggest risk.}

### Rejected Opportunities
{Brief note on each rejected cluster and why — useful for future reference}

### What Was NOT Explored
{Verticals, modalities, geographies, or signals that were out of scope}

### Recommended Next Steps
1. {Concrete action 1}
2. {Concrete action 2}
3. {Concrete action 3}
```

---

## Output Format

The full deliverable is the Step 7 synthesis, supported by data from all prior steps.

Intermediate outputs (signal list, clusters, scores) should be preserved for reference but the user gets the final synthesis first.

## Counter-Checks

Before finalizing, verify:

- [ ] Did you search for competition in non-obvious places (non-English markets, adjacent verticals)?
- [ ] Is demand evidence based on real signals, not your own reasoning about what "should" exist?
- [ ] Did you honestly score moat potential — or did you inflate it because the idea is exciting?
- [ ] Is the timing assessment grounded in specific events/trends, not vague "AI is growing"?
- [ ] Does the validation plan test the RISKIEST assumption first?
- [ ] Did you check if a big tech company has this on their roadmap?
- [ ] Did you assess AI absorption risk — could the next model update make this product irrelevant?
- [ ] Did you map adjacent players — who could ship this as a feature in weeks, not months?
- [ ] For each "competition vacuum" — is it truly empty, or is an adjacent player one sprint away from filling it?
- [ ] Are you recommending the BEST opportunity, or just the most interesting one?
- [ ] Would YOU pay for this? Would someone you know? If neither, demand score should be ≤2.

## Anti-Patterns to Avoid

| Anti-Pattern | Why It's Bad | What to Do Instead |
|--------------|-------------|-------------------|
| "AI for X" without specific pain | Every vertical "could use AI" — that's not a business | Find the specific workflow step that's broken |
| Wrapper plays (thin layer over GPT API) | Zero moat, OpenAI can kill you with a feature update | Require data moat, domain expertise, or workflow lock-in |
| Solution looking for problem | Cool tech ≠ business | Start from pain, not capability |
| "No competition" because you didn't search hard enough | Competition always exists — even if it's a spreadsheet | Map ALL alternatives including non-AI workarounds |
| Ignoring AI model trajectory | Today's gap is tomorrow's built-in feature | Ask: "Would GPT-6 kill this?" If yes, don't build a company on it |
| Ignoring adjacent players | "No one does this" when Salesforce is one sprint away | Map every company in the buyer's stack — any of them could add your feature |
| Confusing "no product" with "no solution" | Maybe there's no product because a prompt + API call already works | Test if the gap requires a PRODUCT or just better prompting |
| Overestimating market size | "Every company needs this" = 0 customers | Bottom-up sizing only |
| Ignoring distribution | Building is 20%, distribution is 80% | Plan GTM before building |

---

## Forge Integration

When running inside Forge pipeline:

**Record findings as ideas:**
```bash
python -m core.ideas add {project} --data '[{
  "title": "{opportunity name}",
  "category": "business-opportunity",
  "description": "{1-para summary with niche_score, demand_evidence, competition_status, moat_type, ai_absorption_risk, adjacent_pivot_risk, validation_status, market_size_y1 embedded}",
  "source": "niche-scout analysis",
  "priority": "HIGH|MEDIUM|LOW",
  "metadata": {
    "niche_score": X.X,
    "demand_evidence": "{key signal}",
    "competition_status": "vacuum|weak|emerging",
    "moat_type": "{primary moat}",
    "ai_absorption_risk": "NEVER|LOW|MEDIUM|HIGH",
    "adjacent_pivot_risk": "LOW|MEDIUM|HIGH",
    "adjacent_threats": "{top 1-2 companies that could pivot}",
    "validation_status": "unvalidated"
  }
}]'
```
Note: `business-opportunity` and `research` are valid idea categories in Forge.

**Record risks:**
```bash
python -m core.risks add {project} --data '[{
  "title": "{risk name}",
  "description": "{what could go wrong}",
  "linked_entity_type": "idea",
  "linked_entity_id": "{I-NNN}",
  "severity": "HIGH|MEDIUM|LOW",
  "likelihood": "HIGH|MEDIUM|LOW",
  "mitigation_plan": "{proposed mitigation}"
}]'
```

**Record key decisions:**
```bash
python -m core.decisions add {project} --data '[{
  "task_id": "DISCOVERY",
  "type": "strategy",
  "issue": "Which opportunity to pursue",
  "recommendation": "{#1 pick}",
  "reasoning": "{from scoring + deep dive}",
  "alternatives": ["{#2}", "{#3}"],
  "confidence": "MEDIUM",
  "decided_by": "claude",
  "status": "OPEN"
}]'
```

**Record exploration artifacts:**
```bash
python -m core.explorations add {project} --data '[{
  "idea_id": "{I-NNN}",
  "exploration_type": "business",
  "summary": "{key conclusion}",
  "findings": ["{signal 1}", "{signal 2}"],
  "options": [{"name": "...", "pros": ["..."], "cons": ["..."], "recommendation": "GO|NO-GO"}],
  "open_questions": ["{unresolved}"],
  "recommendation": "{overall}"
}]'
```

**Record lessons:**
Note: valid lesson categories are: `pattern-discovered`, `mistake-avoided`, `decision-validated`, `decision-reversed`, `tool-insight`, `architecture-lesson`, `process-improvement`, `market-insight`.
```bash
python -m core.lessons add {project} --data '[{
  "category": "market-insight",
  "title": "{key insight}",
  "detail": "{why this matters}",
  "task_id": "DISCOVERY",
  "severity": "important",
  "applies_to": "niche-scout, business-discovery",
  "tags": ["niche-scout", "{vertical}"]
}]'
```
