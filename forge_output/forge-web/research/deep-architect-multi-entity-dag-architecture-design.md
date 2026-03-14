# Architecture: Multi-Entity DAG Visualization

## Overview

A full-project entity graph visualization replacing the task-only SVG board. Backend Graph API aggregates all 9 entity types and derives edges from their relationships. Frontend uses React Flow with elkjs layout (Web Worker) and a generic EntityNode component.

## Requirements & Constraints

1. Display all 9 entity types as typed, visually distinct nodes
2. Derive edges from entity relationships server-side
3. Support 100+ nodes with acceptable performance (<2s layout)
4. Provide zoom, pan, minimap, filtering by entity type and status
5. Auto-layout via elkjs layered algorithm
6. Real-time updates via WebSocket events
7. Replace existing board/page.tsx DAG view
8. Preserve existing entity stores as data source of truth
9. React Flow is the required library
10. Must work with JSON file storage backend

## Component Decomposition

### Backend
- **GraphRouter** (`forge-api/app/routers/graph.py`): GET /projects/{slug}/graph endpoint
- **GraphBuilder** (`forge-api/app/services/graph_builder.py`): loads entities, derives edges, builds response

### Frontend
- **EntityDAG** (`components/graph/EntityDAG.tsx`): main React Flow wrapper with elkjs layout
- **EntityNode** (`components/graph/EntityNode.tsx`): generic node component with type config
- **EntityEdge** (`components/graph/EntityEdge.tsx`): typed edge component with labels
- **GraphToolbar** (`components/graph/GraphToolbar.tsx`): filters, layout controls, minimap toggle
- **NodeContextMenu** (`components/graph/NodeContextMenu.tsx`): right-click menu (edit, AI, navigate)
- **graphStore** (`stores/graphStore.ts`): filters, viewport prefs, selected node
- **useGraphData** (`hooks/useGraphData.ts`): SWR hook for graph API + WS revalidation

## API Design

### GET /api/v1/projects/{slug}/graph

Query params:
- entity_types: comma-separated filter (default: all except changes, lessons)
- statuses: comma-separated status filter
- root_entity: O-NNN or I-NNN to show subgraph

Response:
```json
{
  "nodes": [
    {
      "id": "O-001",
      "type": "objective",
      "data": {
        "title": "...",
        "status": "ACTIVE",
        "kr_progress": 0.45,
        "appetite": "medium"
      }
    }
  ],
  "edges": [
    {
      "id": "e-I-001-O-001",
      "source": "I-001",
      "target": "O-001",
      "type": "advances_kr",
      "data": { "label": "advances KR-1" }
    }
  ],
  "meta": {
    "total_nodes": 84,
    "total_edges": 130,
    "entity_counts": { "objective": 12, "idea": 8, "task": 33, ... }
  }
}
```

## Data Model: Entity to Node Mapping

| Entity Type | Node Color | Icon | Displayed Fields |
|-------------|-----------|------|-------------------|
| Objective | Amber-500 | Target | title, kr_progress%, appetite |
| Idea | Purple-500 | Lightbulb | title, status, category |
| Task | Blue-500 | CheckSquare | id, name, status, type |
| Decision | Rose-500 | Scale | issue (truncated), status, type |
| Knowledge | Teal-500 | Book | title, category, status |
| Research | Indigo-500 | Microscope | title, category |
| Guideline | Green-500 | Shield | title, weight, scope |
| Lesson | Orange-500 | GraduationCap | title, severity |
| ACTemplate | Cyan-500 | Template | title, category |

## Edge Types

| Relationship | Edge Style | Color | Label |
|-------------|-----------|-------|-------|
| depends_on | Solid | Gray-400 | depends on |
| advances_kr | Dashed | Amber-400 | advances KR-N |
| origin | Dotted | Purple-400 | origin |
| derived_from | Dashed | Green-400 | derived from |
| blocked_by | Solid, thick | Red-400 | blocked by |
| parent_child | Solid | Purple-300 | parent |
| linked_entity | Dotted | Gray-300 | linked |
| knowledge_ref | Dotted | Teal-300 | uses |

## ADR-1: elkjs in Web Worker
- **Context**: elkjs layout computation can take 500ms+ for 100 nodes, freezing main thread
- **Decision**: Run elkjs in a Web Worker loaded from public/ directory
- **Alternatives**: Main thread with loading spinner; requestIdleCallback chunked layout
- **Consequences**: Gain non-blocking layout; lose simple debugging; need message passing

## ADR-2: SWR as Data Source of Truth
- **Context**: Three potential state sources: entity stores, graphStore, React Flow internal
- **Decision**: SWR cache of graph API response is the single source; React Flow is a derived view
- **Alternatives**: graphStore owns nodes/edges; React Flow controlled mode with entity stores
- **Consequences**: Gain simplicity and consistency; lose ability to persist user node positions

## ADR-3: Generic EntityNode over Per-Type Components
- **Context**: 9 entity types need visual representation as React Flow nodes
- **Decision**: Single EntityNode component with config map (color, icon, fields per type)
- **Alternatives**: 9 separate components (ObjectiveNode, IdeaNode, etc.)
- **Consequences**: Gain DRY code, consistent rendering; lose per-type layout flexibility

## ADR-4: Server-Side Edge Derivation
- **Context**: Edges must be derived from entity relationship fields
- **Decision**: Backend scans all relationship fields and returns typed edges
- **Alternatives**: Frontend derives edges from entity data after fetching
- **Consequences**: Gain consistency, single source of edge logic; lose ability to derive edges without API call

## ADR-5: Graph-Specific WS Debounce (2-5s)
- **Context**: Entity WS events at 300ms debounce trigger too-frequent graph re-renders
- **Decision**: Graph data revalidation debounced at 2-5s, only structural changes trigger re-layout
- **Alternatives**: Same 300ms debounce; manual refresh button only
- **Consequences**: Gain smooth UX; lose instant graph updates (acceptable tradeoff)

## Adversarial Findings

| # | Challenge | Finding | Severity | Mitigation |
|---|-----------|---------|----------|------------|
| 1 | STRIDE | Graph API exposes all entity data in single response | Medium | Auth required, same as entity endpoints |
| 2 | FMEA | elkjs Web Worker crash leaves graph unlayouted | Medium | Fallback to simple grid layout |
| 3 | Anti-pattern | God component risk if EntityNode handles too much | Low | Config map keeps component thin |
| 4 | Pre-mortem | 6mo later: graph is unreadable for large projects | High | Filtering, collapsible groups, subgraph views |
| 5 | Dependency | elkjs is sole layout provider | Medium | Dagre as fallback (without edge routing) |
| 6 | Scale | 500+ nodes causes layout freeze | High | Web Worker + node limit + pagination |
| 7 | Cost | elkjs 1.4MB bundle increase | Medium | Lazy loading, code splitting |
| 8 | Ops | Graph API slow for large JSON files | Medium | Async file reads, response caching |