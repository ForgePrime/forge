# Analysis Methods

Methods used in Steps 2 and 3. Step 2 uses Tier 1 (always). Step 3 selects from Tier 2 based on signals.

## Tier 1 — Always Applied (Step 2: Scan)

### First Principles Analysis

1. Identify 3-5 core claims of the artifact
2. For each: "What must be fundamentally true for this to work?"
3. Check if those fundamentals are:
   - Explicitly stated and justified
   - Consistent with known constraints
   - Not contradicting each other
4. Finding = fundamental is missing, contradicted, or unverifiable

### Vocabulary Consistency

1. Extract all key terms with locations
2. Check: same concept always uses same word?
3. Find **synonyms** (same concept, different words — confusion risk)
4. Find **homonyms** (same word, different meanings — contradiction risk)
5. Finding = term meaning shifts between sections

### Abstraction Coherence

1. Map abstraction levels: HIGH (goals/promises) → MID (design/approach) → LOW (implementation/details)
2. Check vertical coherence: does each level support the one above?
3. Find **gaps**: high-level promise with no mid/low support
4. Find **orphans**: low-level detail not connected to any higher goal
5. Finding = promise without backing, or detail without purpose

---

## Tier 2 — Signal-Based (Step 3: Targeted Analysis)

Select 1-3 based on what Step 2 revealed. **Cluster rule**: if two methods probe the same angle and the first finds nothing, skip the second.

### Theoretical Impossibility Check
**Use when**: absolute claims ("always", "never", "100%", "guaranteed")

1. Flag ambitious/absolute claims
2. Check against known theorems: CAP, FLP, Halting, Rice, Arrow, Green-Laffont, No-Free-Lunch
3. Check for valid exceptions (synchrony assumptions, probabilistic termination, bounded scope)
4. Violation without valid exception = CRITICAL

### Definitional Contradiction Detector
**Use when**: multiple requirements that might conflict

1. List requirements as R1, R2, R3...
2. For each, expand: MEANS (literal) / IMPLIES (logical consequences) / EXCLUDES (incompatibilities)
3. Check each pair: does R_i.EXCLUDES overlap with R_j.MEANS?
4. Overlap = definitional contradiction = CRITICAL

### Grounding Check
**Use when**: claims without supporting evidence

1. Extract significant claims
2. Classify evidence: Explicit (cited/demonstrated) / Implicit (logical) / Missing (assertion only)
3. CUI BONO: who benefits from ungrounded claims?
4. Missing evidence for central claim = IMPORTANT

### Coherence Check
**Use when**: "something feels off" or diffuse unease

1. Summarize each section in one sentence
2. Cross-compare: do section claims support, contradict, or ignore each other?
3. Check for orphan mechanisms (described but never used)
4. Contradiction between sections = IMPORTANT

### Strange Loop Detection
**Use when**: complex dependencies, layered systems

1. Map dependency graph (A depends on B, B depends on C...)
2. Look for cycles (A → B → C → A)
3. Check if cycles have termination conditions
4. Circular dependency without dampening = IMPORTANT

### Assumption Excavation
**Use when**: clean Phase 1 (nothing obvious) or hidden complexity

1. For each core claim, list what the author is ASSUMING (not stating)
2. Classify: reasonable / questionable / unstated-but-critical
3. Test questionable assumptions: what breaks if this is false?
4. Critical unstated assumption = IMPORTANT

### Contraposition Inversion
**Use when**: need to find hidden implications

1. For key claim "If A then B"
2. Invert: "If NOT B, then NOT A"
3. Is the contrapositive surprising or problematic?
4. If the artifact relies on A→B but NOT-B is plausible, the claim is fragile

### Constructive Counterexample
**Use when**: testing whether claims hold in practice

1. Identify a specific claim
2. Construct a concrete scenario where the claim fails
3. Is the scenario realistic (not pathological)?
4. Realistic counterexample to a stated guarantee = CRITICAL

---

## Tier 3 — Adversarial (Step 4)

### Challenge from Critical Perspective
Used for adversarial self-review, not as a standalone method.

1. Review all findings as a whole
2. Ask: "How do these findings combine into a systemic problem?"
3. Are findings independent incidents or compounding failures?
4. Compounding findings may elevate overall severity
