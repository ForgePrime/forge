# Exploration: Decision & Notification Infrastructure (O-002)

## Knowledge Audit

### Known Facts
1. **WebSocket infrastructure exists**: ForgeWebSocket class (lib/ws.ts), useWebSocket hook, wsDispatcher - all production-ready
2. **Redis Pub/Sub EventBus** in forge-api with 39 event types, fire-and-forget pattern
3. **notificationStore + DecisionNotificationPopup** already handle decision.created notifications via wsDispatcher
4. **toastStore** handles ephemeral notifications (auto-dismiss, max 3 visible)
5. **NotificationCenter.tsx** polls every 30s - fetches open decisions + paused LLM sessions, dismissal via localStorage
6. **wsDispatcher** routes decision.created to notificationStore.addDecision(), decision.closed to auto-resume paused sessions
7. **Decision status machine** exists with validation (OPEN to CLOSED, etc.)
8. **Store factory pattern** (createEntityStore) generates typed stores with WS event handling
9. **SWR + Zustand coexistence** established (L-002) - SWR for reads, Zustand for WS events
10. **mutationTracker** prevents echo dedup with 5s TTL
11. **Execution stream** has its own WebSocket for task output (separate from project events WS)
12. **Entity-level locking** in backend (_helpers.py) prevents concurrent write corruption

### Assumptions (need validation)
1. **NotificationCenter.tsx is extendable** (O-002 assumption) - TRUE, self-contained 252-line component
2. **WebSocket transport is sufficient** (O-002 assumption) - LIKELY TRUE for single-project, UNCERTAIN for cross-project
3. **Single WS connection per project handles notification volume** - needs stress testing under concurrent workflows
4. **Redis Pub/Sub can handle persistence needs** - FALSE, Pub/Sub is fire-and-forget. Need Redis Streams or server-side storage
5. **JSON file storage works for notification history** - RISKY under high volume but consistent with existing patterns

### Unknown Gaps
1. **Offline notification delivery** - user closes tab, reopens later. How to show missed notifications?
2. **Cross-project notification routing** - user works on project A, workflow on project B needs attention
3. **Notification volume ceiling** - how many notifications/minute under 3 concurrent workflows?
4. **Read/dismiss state ownership** - currently localStorage, should it be server-side?
5. **Notification grouping** - 5 decisions from same discovery: 5 separate popups or 1 grouped?
6. **Priority interruption model** - should HIGH severity risk block other notifications?

## Options

### Decision 1: Notification Persistence Strategy

| Option | Requirements | Risks | Benefits | Key Unknown |
|--------|-------------|-------|----------|-------------|
| **A. Client-only (current)** | No backend changes | Missed notifications on disconnect | Simplest, already works for decisions | How often are users offline during workflows? |
| **B. Server-side entity (notifications.json)** | New notification entity + CRUD router | File I/O under high volume | Consistent with Forge patterns, audit trail, survives offline | Will file locks cause contention? |
| **C. Redis Streams** | Redis Stream consumer groups | New infrastructure pattern | Built for persistent ordered messages | Redis Streams not yet used in project |
| **D. Hybrid: Redis delivery + entity audit** | Both B and C | More complexity, two sources of truth | Best reliability | Is the complexity justified? |

**Recommendation: Option B (Server-side entity)** - Consistent with Forge patterns, uses existing StorageAdapter. For v1, file-based storage with entity locking is sufficient. Redis Streams can be added later if volume demands it.

### Decision 2: Notification Backend Architecture

| Option | Requirements | Risks | Benefits | Key Unknown |
|--------|-------------|-------|----------|-------------|
| **A. Event enrichment only** | Modify wsDispatcher for notifications from events | Frontend-dependent, no server persistence | Zero backend changes, fast to implement | What if logic diverges across clients? |
| **B. Notification service in forge-api** | New router, entity, event-to-notification mapping | Backend complexity | Server decides what is notification-worthy, persistent | How complex is the mapping? |
| **C. Event hooks (configurable)** | Configurable rules | Flexible but complex | User-configurable notification rules | Do users need this configurability? |

**Recommendation: Option B (Dedicated notification service)** - Backend creates notifications on relevant events, stores them, emits WebSocket events. Frontend receives and displays. Separation of concerns.

### Decision 3: Notification UI Architecture

| Option | Requirements | Risks | Benefits | Key Unknown |
|--------|-------------|-------|----------|-------------|
| **A. Enhanced bell dropdown** | Extend NotificationCenter with WS | Limited space for detail views | Familiar pattern, minimal UI changes | Is dropdown enough for response forms? |
| **B. Full notification drawer** | New sliding panel component | May conflict with AISidebar | Room for details, filters, batch actions | Space competition with sidebars? |
| **C. Hybrid: bell + modals** | Bell for count, modals for responses | Modal fatigue | Each type gets proper view, no space constraints | Does modal pattern work for workflows? |
| **D. Notification center page + popups** | Dedicated /notifications route + popups | Split attention | Full detail views, persistent history | Do users want a separate page? |

**Recommendation: Option C (Hybrid bell + response modals)** - Enhanced NotificationCenter bell with WebSocket shows count + summary. Clicking navigates to entity page or opens response modal for blocking notifications. Builds on existing UI.

### Decision 4: Multi-Workflow Notification Routing

| Option | Requirements | Risks | Benefits | Key Unknown |
|--------|-------------|-------|----------|-------------|
| **A. Tag with workflow context** | Add execution_id, workflow_step to notifications | Frontend must filter/group | Single WS, metadata routing | How complex is filtering UI? |
| **B. Separate WS channels per workflow** | New subscription model | Connection overhead | Clean separation | How many concurrent workflows? |
| **C. Server-side filtering** | Backend filters events | Backend must know user context | Reduces noise | How does backend know user context? |

**Recommendation: Option A (Tag with workflow context)** - Add workflow_id/execution_id metadata. Frontend wsDispatcher groups/filters. Simple, no new infrastructure.

## Consequence Trace

### Server-side notification entity + dedicated service

**1st order**: Backend creates notification records on relevant events. Notifications persist in notifications.json. Frontend fetches unread on connect, receives new ones via WebSocket.

**2nd order**: Notification entity needs CRUD endpoints, storage schema, event types. This means: new router, new store, new API namespace. But patterns are 100% established - same as decisions, knowledge, etc. Factory store handles 90% of frontend code.

**3rd order**: With server-side notifications, we can later add: notification preferences, cross-project aggregation, email/webhook delivery. The entity becomes a foundation for future communication features.

### Hybrid bell + response modals

**1st order**: NotificationCenter gets WebSocket integration. Click-through navigates to entity pages or opens response modal.

**2nd order**: Existing entity detail pages may need response forms when opened from notifications. Response modals need per-type components (decision response, plan approval, etc.).

**3rd order**: Navigation from notification to entity creates context-switching. Need return-to-previous-context UX. Modal approach avoids full navigation but modals within modals is an anti-pattern.

## Challenge Round

### Server-side notification entity
**Strongest counter-argument**: Adding another entity increases complexity. Every entity in Forge = ~200 lines router + ~50 lines store + ~100 lines API. Is this justified when client-only (notificationStore) already works?

**Failure condition**: If users are always online during workflows and never refresh, client-side suffices. Server-side is wasted effort.

**Rebuttal**: KR-4 requires zero missed notifications and persistent notification until resolved. Client-only cannot guarantee this on page refresh. Server-side is necessary.

### Hybrid bell + response modals
**Strongest counter-argument**: Notification types proliferate over time. Each new notification type needs its own modal component. This creates a growing maintenance burden.

**Failure condition**: If notification types exceed 10+, the modal system becomes unwieldy. A unified response pattern would be better.

**Rebuttal**: Start with 4-5 core types (decision, plan approval, LLM question, error, task completion). Use a base modal with type-specific content slots. Keeps it manageable.

## Recommended Path

**READY TO DECIDE**

**Recommended architecture:**
1. **Server-side notification entity** (notifications.json) with CRUD router
2. **Notification service** mapping events to notifications with priority/metadata
3. **Enhanced NotificationCenter** with WebSocket (replacing 30s poll)
4. **Response modals** per type for KR-2 dedicated detail views
5. **Workflow tagging** on all notifications for multi-workflow support
6. **Fetch-on-reconnect** to catch missed notifications (GET /notifications?status=UNREAD)

**Caveats:**
- Cross-project notifications needs further design
- Notification grouping strategy deferred to implementation
- AI-proposed options UI (KR-2) needs design mockup

## What Was NOT Explored
- Cross-project notification aggregation (global notification channel)
- Email/webhook notification delivery (out of scope for v1)
- Notification preferences/settings per user
- Notification analytics
- Mobile/responsive notification UX
- Browser notification API / sound integration
- Rate limiting for notification generation