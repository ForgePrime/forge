# Exploration: Multi-Entity Graph API & DAG Visualization

## Knowledge Audit

**Known:**
- React Flow (xyflow) required, well-established library for node-based UIs
- 9 entity types with heterogeneous relationships (~8 edge types)
- Existing custom SVG DAG is task-only (635 LOC), needs full replacement
- Backend has per-entity routers with CRUD, no graph endpoint exists
- L-001: store factory pattern works well for multi-entity Zustand
- React Flow performance: memoize custom nodes, avoid fetching full nodes array

**Assumed (fragile):**
- elkjs will produce readable layouts for heterogeneous entity graphs
- Single Graph API endpoint will be faster than N entity fetches
- 100 nodes is a realistic upper bound for typical projects

**Unknown gaps:**
- Real-world layout quality for Objective-Idea-Task-Research hierarchy with cross-edges
- Edge routing behavior with many relationship types (visual clutter)
- Re-layout performance when entities are added/removed in real-time

## Options

| Option | Layout | Graph API | Node Architecture | Key Risk |
|--------|--------|-----------|-------------------|----------|
| A: dagre + server | dagre (40KB) | Single endpoint | Generic EntityNode | dagre deprecated, no edge routing |
| B: elkjs + server | elkjs (1.4MB) | Single endpoint | Generic EntityNode | Large bundle, complex API |
| C: elkjs + client | elkjs | Existing endpoints | Per-type nodes | Data inconsistency |

## Consequence Trace: Option B (Recommended)

**1st order**: Single API call returns full graph; elkjs computes layout with edge routing
**2nd order**: Server-side aggregation enables caching, filtering, future features (subgraph queries)
**3rd order**: Graph API becomes foundation for O-009 (AI conversations), O-011 (inline editing)

## Recommended Path

**Option B: elkjs + server-side Graph API** with:
- elkjs layered algorithm, direction DOWN
- GET /projects/{slug}/graph aggregating all entities
- Generic EntityNode base component with per-type config
- React Flow internal state for layout; entity stores for data
- Lazy-load elkjs via dynamic import
- Exclude Changes from default view
- Phase edge types: start with 4 core, add others incrementally