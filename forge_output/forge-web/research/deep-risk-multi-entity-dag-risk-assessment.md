# Risk Assessment: Multi-Entity DAG Visualization

Scope: O-008 implementation | Horizon: medium (weeks)

## Risk Register

| # | Risk | P | I | V | D | R | Composite | Category |
|---|------|---|---|---|---|---|-----------|----------|
| R-001 | elkjs layout freeze on main thread | 4 | 4 | 4 | 2 | 2 | 24 | Technical |
| R-002 | Three-way state sync complexity | 4 | 4 | 3 | 3 | 3 | 25 | Technical |
| R-003 | Visual clutter from 130+ edges | 3 | 3 | 2 | 2 | 2 | 15 | UX |
| R-004 | Bundle size increase (1.6MB) | 3 | 2 | 1 | 1 | 2 | 10 | Technical |
| R-005 | WS-triggered excessive re-layouts | 3 | 3 | 3 | 3 | 2 | 17 | Technical |
| R-006 | Graph API slow for large JSON files | 2 | 3 | 2 | 2 | 2 | 12 | Technical |
| R-007 | elkjs worker setup in Next.js | 3 | 3 | 2 | 3 | 2 | 16 | Dependency |
| R-008 | Migration breaks existing board usage | 2 | 3 | 2 | 2 | 3 | 13 | Temporal |

## Top 5 Risks

### 1. Three-way state sync (Composite: 25)
SWR cache + Zustand graphStore + React Flow internal state could create infinite update loops (per L-018).
Mitigation: SWR as SOLE source of truth. React Flow in uncontrolled mode. graphStore only for UI prefs (filters, viewport).

### 2. elkjs layout freeze (Composite: 24)
100+ nodes with edge routing can take 500ms-2s, freezing the UI.
Mitigation: Web Worker for elkjs computation. Fallback to grid layout if worker fails.

### 3. WS-triggered re-layouts (Composite: 17)
Entity WS events at 300ms debounce trigger too-frequent expensive re-layouts.
Mitigation: Graph-specific 2-5s debounce. Only structural changes (add/remove node/edge) trigger re-layout.

### 4. elkjs worker in Next.js (Composite: 16)
Next.js has no webpack worker config. Dynamic imports of workers are non-trivial.
Mitigation: Load elkjs from public/ as static file. Bypass webpack entirely.

### 5. Visual clutter (Composite: 15)
130+ edges across 8 types create spaghetti graph.
Mitigation: Phase edge types (4 core first). Filtering by entity type. Edge hiding toggles.

## Mitigations + Cobra Effect Check

| Mitigation | Fixes | Could Cause | Cobra? |
|-----------|-------|-------------|--------|
| Web Worker for elkjs | R-001 layout freeze | Debugging complexity, message passing overhead | Minor |
| SWR as sole truth | R-002 state sync | No user-positioned nodes (positions lost on re-layout) | Acceptable |
| Graph-specific debounce | R-005 re-layouts | Graph shows stale data for 2-5s | Acceptable |
| Phase edge types | R-003 visual clutter | Missing relationships in initial version | Acceptable |
| Lazy load elkjs | R-004 bundle size | Delay on first graph render | Minor |

## Uncertainties
- elkjs layout quality for heterogeneous entity graphs (no precedent in this codebase)
- User expectations for node positioning (auto-layout only vs draggable)
- Performance profile of Graph API with large projects (100+ entities across 9 types)